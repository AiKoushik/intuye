"""Test doubles for Apple: a fake Sign in with Apple issuer and a fake App Attest device + CA."""
from __future__ import annotations

import base64
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone

import cbor2
import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import NameOID
from jwt.algorithms import RSAAlgorithm

from app.security.app_attest import AAGUID_DEV, NONCE_OID, client_data_for


class FakeAppleID:
    def __init__(self, bundle_id: str) -> None:
        self.bundle_id = bundle_id
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.kid = "TESTKID"

    async def jwks(self) -> dict:
        jwk = json.loads(RSAAlgorithm.to_jwk(self.key.public_key()))
        return {"keys": [{**jwk, "kid": self.kid, "alg": "RS256", "use": "sig"}]}

    def identity_token(self, sub: str, raw_nonce: str) -> str:
        now = int(time.time())
        claims = {"iss": "https://appleid.apple.com", "aud": self.bundle_id, "sub": sub, "iat": now, "exp": now + 600,
                  "nonce": hashlib.sha256(raw_nonce.encode()).hexdigest()}
        return jwt.encode(claims, self.key, algorithm="RS256", headers={"kid": self.kid})


def _name(cn: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def _cert(subject: str, issuer: str, pub, signer, ca: bool, extra=None) -> x509.Certificate:
    now = datetime.now(timezone.utc)
    b = (x509.CertificateBuilder().subject_name(_name(subject)).issuer_name(_name(issuer)).public_key(pub)
         .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=1))
         .not_valid_after(now + timedelta(days=30))
         .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True))
    if extra is not None:
        b = b.add_extension(extra, critical=False)
    return b.sign(signer, hashes.SHA384() if ca else hashes.SHA256())


class FakeAttestDevice:
    """Plays both Apple's attestation CA and a device's Secure Enclave key."""

    def __init__(self, app_id: str) -> None:
        self.app_id_hash = hashlib.sha256(app_id.encode()).digest()
        self.root_key = ec.generate_private_key(ec.SECP384R1())
        self.root = _cert("Test App Attest Root", "Test App Attest Root", self.root_key.public_key(), self.root_key, True)
        self.inter_key = ec.generate_private_key(ec.SECP384R1())
        self.inter = _cert("Test App Attest CA 1", "Test App Attest Root", self.inter_key.public_key(), self.root_key, True)
        self.cred = ec.generate_private_key(ec.SECP256R1())
        point = self.cred.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        self.key_id = hashlib.sha256(point).digest()
        self.counter = 0

    @property
    def root_pem(self) -> str:
        return self.root.public_bytes(serialization.Encoding.PEM).decode()

    @property
    def key_id_b64(self) -> str:
        return base64.b64encode(self.key_id).decode()

    def attest(self, challenge: str) -> str:
        auth = (self.app_id_hash + bytes([0x41]) + (0).to_bytes(4, "big") + AAGUID_DEV
                + len(self.key_id).to_bytes(2, "big") + self.key_id + b"\xa0")
        nonce = hashlib.sha256(auth + hashlib.sha256(challenge.encode()).digest()).digest()
        ext = x509.UnrecognizedExtension(NONCE_OID, bytes([0x30, 0x24, 0xA1, 0x22, 0x04, 0x20]) + nonce)
        leaf = _cert("device", "Test App Attest CA 1", self.cred.public_key(), self.inter_key, False, ext)
        att = {"fmt": "apple-appattest", "authData": auth,
               "attStmt": {"x5c": [leaf.public_bytes(serialization.Encoding.DER),
                                   self.inter.public_bytes(serialization.Encoding.DER)], "receipt": b""}}
        return base64.b64encode(cbor2.dumps(att)).decode()

    def headers(self, method: str, path_qs: str, body: bytes = b"") -> dict:
        self.counter += 1
        ts = str(int(time.time()))
        auth = self.app_id_hash + bytes([0x01]) + self.counter.to_bytes(4, "big")
        nonce = hashlib.sha256(auth + hashlib.sha256(client_data_for(method, path_qs, body, ts)).digest()).digest()
        sig = self.cred.sign(nonce, ec.ECDSA(hashes.SHA256()))
        assertion = base64.b64encode(cbor2.dumps({"signature": sig, "authenticatorData": auth})).decode()
        return {"x-lc-key-id": self.key_id_b64, "x-lc-assertion": assertion, "x-lc-timestamp": ts}
