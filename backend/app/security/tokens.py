"""Access tokens (Ed25519 JWT, 10 min) and rotating refresh tokens with reuse detection (RFC 9700)."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.errors import APIError
from app.models import RefreshToken


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


class TokenService:
    def __init__(self, settings: Settings) -> None:
        self.s = settings
        if settings.jwt_private_key_pem:
            key = serialization.load_pem_private_key(settings.jwt_private_key_pem.encode(), password=None)
            if not isinstance(key, Ed25519PrivateKey):
                raise ValueError("JWT_PRIVATE_KEY_PEM must be an Ed25519 key")
            self._key = key
        else:  # development/test only (production guard in Settings)
            self._key = Ed25519PrivateKey.generate()
        self._public = self._key.public_key()

    # ---- access
    def issue_access(self, user_id: str, session_id: str) -> str:
        now = _now()
        claims = {"sub": user_id, "sid": session_id, "iat": now, "nbf": now,
                  "exp": now + timedelta(seconds=self.s.access_ttl_seconds),
                  "iss": self.s.jwt_issuer, "aud": self.s.jwt_audience, "jti": secrets.token_hex(8)}
        return jwt.encode(claims, self._key, algorithm="EdDSA")

    def decode_access(self, token: str) -> dict:
        try:
            return jwt.decode(token, self._public, algorithms=["EdDSA"], audience=self.s.jwt_audience,
                              issuer=self.s.jwt_issuer, options={"require": ["exp", "sub", "sid"]})
        except jwt.ExpiredSignatureError as e:
            raise APIError(401, "token_expired", "Session expired. Refresh and retry.") from e
        except jwt.PyJWTError as e:
            raise APIError(401, "invalid_token", "Invalid access token.") from e

    # ---- refresh
    async def start_session(self, db: AsyncSession, user_id: str) -> TokenPair:
        family = str(uuid.uuid4())
        return await self._issue(db, user_id, family, _now())

    async def rotate(self, db: AsyncSession, refresh_token: str) -> TokenPair:
        row = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == _hash(refresh_token)))).scalar_one_or_none()
        now = _now()
        if row is None:
            raise APIError(401, "invalid_refresh", "Sign in again.")
        if row.revoked_at is not None:
            raise APIError(401, "session_revoked", "Sign in again.")
        if row.consumed_at is not None:
            # Reuse of a rotated token: assume theft, kill the whole family.
            await self.revoke_family(db, row.family_id)
            await db.commit()
            raise APIError(401, "refresh_reuse", "Sign in again.")
        absolute_end = row.family_started_at + timedelta(days=self.s.refresh_absolute_days)
        if row.expires_at <= now or absolute_end <= now:
            raise APIError(401, "refresh_expired", "Sign in again.")
        row.consumed_at = now
        return await self._issue(db, row.user_id, row.family_id, row.family_started_at)

    async def revoke(self, db: AsyncSession, refresh_token: str) -> None:
        row = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == _hash(refresh_token)))).scalar_one_or_none()
        if row:
            await self.revoke_family(db, row.family_id)
            await db.commit()

    async def revoke_family(self, db: AsyncSession, family_id: str) -> None:
        await db.execute(update(RefreshToken).where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
                         .values(revoked_at=_now()))

    async def _issue(self, db: AsyncSession, user_id: str, family: str, family_started: datetime) -> TokenPair:
        raw = secrets.token_urlsafe(32)
        db.add(RefreshToken(user_id=user_id, family_id=family, token_hash=_hash(raw), family_started_at=family_started,
                            expires_at=_now() + timedelta(days=self.s.refresh_idle_days)))
        await db.commit()
        return TokenPair(self.issue_access(user_id, family), raw, self.s.access_ttl_seconds)
