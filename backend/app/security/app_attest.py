"""App Attest: one-time key attestation and per-request assertions.

Follows Apple's "Validating apps that connect to your server" procedure. Client-data conventions
shared with the iOS app (ios/LangCoach/Services/AttestService.swift):

* Attestation: clientDataHash = SHA256(challenge string as UTF-8).
* Assertion:   clientData = "METHOD\\nPATH?QUERY\\nSHA256_HEX(body)\\nUNIX_TIMESTAMP",
               clientDataHash = SHA256(clientData).
"""
from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone

import cbor2
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db import get_session
from app.errors import APIError
from app.models import AttestChallenge, AttestKey
from app.security.apple_root import APPLE_APP_ATTEST_ROOT_PEM

log = logging.getLogger("langcoach.attest")

NONCE_OID = x509.ObjectIdentifier("1.2.840.113635.100.8.2")
AAGUID_DEV = b"appattestdevelop"
AAGUID_PROD = b"appattest" + b"\x00" * 7


def _b64d(s: str) -> bytes:
    s = s.strip()
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)) if ("-" in s or "_" in s) else base64.b64decode(s + "=" * (-len(s) % 4))


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AttestError(APIError):
    def __init__(self, message: str) -> None:
        super().__init__(401, "attestation_failed", message)


def parse_auth_data(auth: bytes) -> dict:
    if len(auth) < 37:
        raise AttestError("authenticator data too short")
    out = {"rp_id_hash": auth[:32], "flags": auth[32], "counter": int.from_bytes(auth[33:37], "big")}
    if len(auth) >= 55:
        cred_len = int.from_bytes(auth[53:55], "big")
        out["aaguid"] = auth[37:53]
        out["credential_id"] = auth[55:55 + cred_len]
    return out


def client_data_for(method: str, path_qs: str, body: bytes, timestamp: str) -> bytes:
    return f"{method.upper()}\n{path_qs}\n{hashlib.sha256(body).hexdigest()}\n{timestamp}".encode()


class AppAttestService:
    def __init__(self, settings: Settings) -> None:
        self.s = settings
        self.root = x509.load_pem_x509_certificate((settings.app_attest_root_pem or APPLE_APP_ATTEST_ROOT_PEM).encode())
        self.app_id_hash = hashlib.sha256(settings.app_id.encode()).digest()

    # ------------------------------------------------------------------ registration
    async def new_challenge(self, db: AsyncSession) -> str:
        challenge = secrets.token_urlsafe(32)
        db.add(AttestChallenge(challenge=challenge, expires_at=_now() + timedelta(minutes=5)))
        await db.commit()
        return challenge

    async def register(self, db: AsyncSession, key_id_b64: str, attestation_b64: str, challenge: str) -> AttestKey:
        row = (await db.execute(select(AttestChallenge).where(AttestChallenge.challenge == challenge))).scalar_one_or_none()
        if row is None or row.used_at is not None or row.expires_at < _now():
            raise AttestError("challenge invalid or expired")
        row.used_at = _now()
        await db.commit()

        key_id = _b64d(key_id_b64)
        try:
            att = cbor2.loads(_b64d(attestation_b64))
            stmt, auth_data = att["attStmt"], att["authData"]
            if att["fmt"] != "apple-appattest":
                raise AttestError("unexpected format")
            leaf = x509.load_der_x509_certificate(stmt["x5c"][0])
            inter = x509.load_der_x509_certificate(stmt["x5c"][1])
        except (KeyError, IndexError, ValueError, cbor2.CBORDecodeError) as e:
            raise AttestError("malformed attestation") from e

        # 1. Certificate chain to the Apple App Attestation root, all currently valid.
        try:
            inter.verify_directly_issued_by(self.root)
            leaf.verify_directly_issued_by(inter)
        except (InvalidSignature, ValueError, TypeError) as e:
            raise AttestError("certificate chain invalid") from e
        now = _now()
        for c in (leaf, inter):
            if not (c.not_valid_before_utc <= now <= c.not_valid_after_utc):
                raise AttestError("certificate expired")

        # 2–4. Nonce extension == SHA256(authData || SHA256(challenge)).
        nonce = hashlib.sha256(auth_data + hashlib.sha256(challenge.encode()).digest()).digest()
        try:
            ext = leaf.extensions.get_extension_for_oid(NONCE_OID).value
            ext_bytes = ext.value if hasattr(ext, "value") else ext.public_bytes()
        except x509.ExtensionNotFound as e:
            raise AttestError("nonce extension missing") from e
        if ext_bytes[-32:] != nonce:
            raise AttestError("nonce mismatch")

        # 5. Key id == SHA256(credential public key, uncompressed point).
        pub = leaf.public_key()
        if not isinstance(pub, ec.EllipticCurvePublicKey):
            raise AttestError("unexpected key type")
        point = pub.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        if hashlib.sha256(point).digest() != key_id:
            raise AttestError("key id mismatch")

        # 6–9. Authenticator data checks.
        ad = parse_auth_data(auth_data)
        if ad["rp_id_hash"] != self.app_id_hash:
            raise AttestError("app id mismatch")
        if ad["counter"] != 0:
            raise AttestError("counter must start at 0")
        if ad.get("aaguid") not in (AAGUID_DEV, AAGUID_PROD):
            raise AttestError("unexpected environment")
        if ad.get("credential_id") != key_id:
            raise AttestError("credential id mismatch")

        key_id_str = base64.b64encode(key_id).decode()
        existing = await db.get(AttestKey, key_id_str)
        if existing:
            raise AttestError("key already registered")
        key = AttestKey(key_id=key_id_str, public_key_pem=pub.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode(),
            counter=0, environment="development" if ad["aaguid"] == AAGUID_DEV else "production")
        db.add(key)
        await db.commit()
        return key

    # ------------------------------------------------------------------ per request
    async def verify_request(self, db: AsyncSession, request: Request) -> AttestKey | None:
        mode = self.s.app_attest_mode
        if mode == "off":
            return None
        try:
            return await self._verify(db, request)
        except AttestError:
            if mode == "report":
                log.warning("attestation failed (report mode) path=%s", request.url.path)
                return None
            raise

    async def _verify(self, db: AsyncSession, request: Request) -> AttestKey:
        h = request.headers
        key_id, assertion_b64, ts = h.get("x-lc-key-id"), h.get("x-lc-assertion"), h.get("x-lc-timestamp")
        if not (key_id and assertion_b64 and ts and ts.isdigit()):
            raise AttestError("missing attestation headers")
        if abs(time.time() - int(ts)) > self.s.assertion_max_skew_seconds:
            raise AttestError("stale request")
        key = await db.get(AttestKey, base64.b64encode(_b64d(key_id)).decode())
        if key is None:
            raise AttestError("unknown key")
        try:
            assertion = cbor2.loads(_b64d(assertion_b64))
            signature, auth_data = assertion["signature"], assertion["authenticatorData"]
        except (KeyError, ValueError, cbor2.CBORDecodeError) as e:
            raise AttestError("malformed assertion") from e

        path_qs = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        client_data = client_data_for(request.method, path_qs, await request.body(), ts)
        nonce = hashlib.sha256(auth_data + hashlib.sha256(client_data).digest()).digest()
        pub = serialization.load_pem_public_key(key.public_key_pem.encode())
        try:
            pub.verify(signature, nonce, ec.ECDSA(hashes.SHA256()))  # type: ignore[union-attr,call-arg]
        except InvalidSignature as e:
            raise AttestError("bad signature") from e
        ad = parse_auth_data(auth_data)
        if ad["rp_id_hash"] != self.app_id_hash:
            raise AttestError("app id mismatch")
        if ad["counter"] <= key.counter:
            raise AttestError("replayed assertion")
        key.counter = ad["counter"]
        await db.commit()
        request.state.attest_key_id = key.key_id
        return key

    async def bind_user(self, db: AsyncSession, request: Request, user_id: str) -> None:
        key_id = getattr(request.state, "attest_key_id", None)
        if key_id:
            key = await db.get(AttestKey, key_id)
            if key and key.user_id is None:
                key.user_id = user_id
                await db.commit()


async def attested(request: Request, db: AsyncSession = Depends(get_session)) -> None:
    await request.app.state.attest.verify_request(db, request)
