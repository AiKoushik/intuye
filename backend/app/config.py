from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite+aiosqlite:///./langcoach.db"

    # Session tokens
    jwt_private_key_pem: str = ""
    jwt_issuer: str = "langcoach"
    jwt_audience: str = "langcoach-api"
    access_ttl_seconds: int = 600
    refresh_idle_days: int = 14
    refresh_absolute_days: int = 60

    # Apple
    apple_team_id: str = "TEAMID1234"
    apple_bundle_id: str = "com.example.langcoach"
    apple_jwks_url: str = "https://appleid.apple.com/auth/keys"
    apple_issuer: str = "https://appleid.apple.com"
    app_attest_mode: Literal["enforce", "report", "off"] = "enforce"
    app_attest_root_pem: str = ""  # empty = bundled Apple App Attestation Root CA
    assertion_max_skew_seconds: int = 300

    # LLM
    llm_provider: Literal["fake", "openai_compatible", "anthropic"] = "fake"
    llm_base_url: str = "http://localhost:8000/v1"
    llm_api_key: str = "not-needed"
    llm_fast_model: str = "qwen3-27b"
    llm_smart_model: str = "qwen3-27b"
    anthropic_api_key: str = ""

    # Local testing: dev sign-in (no Apple) and the web client served at /web. Refused in production.
    dev_login_enabled: bool = False
    web_client_dir: str = ""  # empty = <repo>/web
    cors_origins: str = ""    # comma-separated, e.g. http://localhost:5173

    # Limits
    max_body_bytes: int = 64 * 1024
    max_batch_body_bytes: int = 256 * 1024
    rate_limit_per_minute: int = 60
    coach_rate_limit_per_minute: int = 20
    auth_rate_limit_per_minute: int = 10

    @property
    def app_id(self) -> str:
        return f"{self.apple_team_id}.{self.apple_bundle_id}"

    @model_validator(mode="after")
    def _production_guards(self) -> "Settings":
        if self.env == "production":
            if self.app_attest_mode == "off":
                raise ValueError("APP_ATTEST_MODE=off is not allowed in production")
            if not self.jwt_private_key_pem:
                raise ValueError("JWT_PRIVATE_KEY_PEM is required in production")
            if self.llm_provider == "fake":
                raise ValueError("LLM_PROVIDER=fake is not allowed in production")
            if self.dev_login_enabled:
                raise ValueError("DEV_LOGIN_ENABLED is not allowed in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
