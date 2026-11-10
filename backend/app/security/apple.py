"""Sign in with Apple identity-token verification."""
from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Awaitable, Callable

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from app.config import Settings
from app.errors import APIError

JWKSProvider = Callable[[], Awaitable[dict]]


class AppleIdentityVerifier:
    """Verifies signature (RS256 via Apple's JWKS), issuer, audience, expiry and nonce."""

    def __init__(self, settings: Settings, jwks_provider: JWKSProvider | None = None) -> None:
        self.s = settings
        self._provider = jwks_provider or self._fetch_jwks
        self._cache: tuple[float, dict] | None = None

    async def _fetch_jwks(self) -> dict:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(self.s.apple_jwks_url)
            r.raise_for_status()
            return r.json()

    async def _keys(self, force: bool = False) -> dict[str, object]:
        if force or not self._cache or time.time() - self._cache[0] > 86400:
            jwks = await self._provider()
            self._cache = (time.time(), {k["kid"]: RSAAlgorithm.from_jwk(json.dumps(k)) for k in jwks["keys"]})
        return self._cache[1]

    async def verify(self, identity_token: str, raw_nonce: str) -> dict:
        try:
            kid = jwt.get_unverified_header(identity_token)["kid"]
        except (jwt.PyJWTError, KeyError) as e:
            raise APIError(401, "invalid_identity_token", "Apple sign-in failed.") from e
        keys = await self._keys()
        if kid not in keys:
            keys = await self._keys(force=True)  # Apple rotated keys
        if kid not in keys:
            raise APIError(401, "invalid_identity_token", "Apple sign-in failed.")
        try:
            claims = jwt.decode(identity_token, keys[kid], algorithms=["RS256"], audience=self.s.apple_bundle_id,
                                issuer=self.s.apple_issuer, options={"require": ["exp", "iat", "sub", "nonce"]})
        except jwt.PyJWTError as e:
            raise APIError(401, "invalid_identity_token", "Apple sign-in failed.") from e
        if claims["nonce"] != hashlib.sha256(raw_nonce.encode()).hexdigest():
            raise APIError(401, "nonce_mismatch", "Apple sign-in failed.")
        return claims
