"""ORM tables. See docs/07-data-model.md. Every user-owned row cascades on user deletion."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, TypeDecorator, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def UserFK() -> Mapped[str]:  # noqa: N802
    return mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)


class TZDateTime(TypeDecorator):
    """Stores UTC; always returns timezone-aware datetimes (SQLite drops tzinfo)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
            if dialect.name == "sqlite":
                value = value.replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    apple_sub: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(TZDateTime(), default=utcnow)


class UserSettings(Base):
    __tablename__ = "settings"
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    dialect: Mapped[str] = mapped_column(String(8), default="es-419")
    level: Mapped[int] = mapped_column(Integer, default=0)
    daily_notification_budget: Mapped[int] = mapped_column(Integer, default=3)
    quiet_start: Mapped[str] = mapped_column(String(5), default="22:00")
    quiet_end: Mapped[str] = mapped_column(String(5), default="08:00")
    moment_retention_days: Mapped[int] = mapped_column(Integer, default=90)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = UserFK()
    family_id: Mapped[str] = mapped_column(String(36), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    family_started_at: Mapped[datetime] = mapped_column(TZDateTime())
    expires_at: Mapped[datetime] = mapped_column(TZDateTime())
    consumed_at: Mapped[datetime | None] = mapped_column(TZDateTime())
    revoked_at: Mapped[datetime | None] = mapped_column(TZDateTime())
    created_at: Mapped[datetime] = mapped_column(TZDateTime(), default=utcnow)


class AttestChallenge(Base):
    __tablename__ = "attest_challenges"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    challenge: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(TZDateTime())
    used_at: Mapped[datetime | None] = mapped_column(TZDateTime())


class AttestKey(Base):
    __tablename__ = "attest_keys"
    key_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    public_key_pem: Mapped[str] = mapped_column(Text)
    counter: Mapped[int] = mapped_column(Integer, default=0)
    environment: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(TZDateTime(), default=utcnow)


class Utterance(Base):
    __tablename__ = "utterances"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = UserFK()
    text: Mapped[str] = mapped_column(Text)
    lang_mix: Mapped[float] = mapped_column(Float, default=0.0)  # share of English tokens
    source: Mapped[str] = mapped_column(String(16))  # say | ambient | rehearsal
    topic: Mapped[str | None] = mapped_column(String(64), index=True)
    close_es: Mapped[str | None] = mapped_column(Text)
    spoken_at: Mapped[datetime] = mapped_column(TZDateTime(), default=utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime(), default=utcnow)


class Lexeme(Base):
    __tablename__ = "lexemes"
    __table_args__ = (UniqueConstraint("user_id", "es"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = UserFK()
    es: Mapped[str] = mapped_column(String(120))
    en: Mapped[str] = mapped_column(String(120))
    origin: Mapped[str] = mapped_column(String(16))  # spoken | base | scenario | grammar
    topic: Mapped[str | None] = mapped_column(String(64))
    context: Mapped[str | None] = mapped_column(Text)  # a sentence where it appeared
    first_seen_at: Mapped[datetime] = mapped_column(TZDateTime(), default=utcnow)


class LexemeEvent(Base):
    __tablename__ = "lexeme_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = UserFK()
    lexeme_id: Mapped[str] = mapped_column(String(36), ForeignKey("lexemes.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # said_en | said_es | looked_up | mispronounced | forgot
    utterance_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("utterances.id", ondelete="SET NULL"))
    at: Mapped[datetime] = mapped_column(TZDateTime(), default=utcnow)


class Card(Base):
    __tablename__ = "cards"
    lexeme_id: Mapped[str] = mapped_column(String(36), ForeignKey("lexemes.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = UserFK()
    state: Mapped[str] = mapped_column(String(12), default="new")
    stability: Mapped[float] = mapped_column(Float, default=0.0)
    difficulty: Mapped[float] = mapped_column(Float, default=0.0)
    due_at: Mapped[datetime] = mapped_column(TZDateTime(), default=utcnow, index=True)
    last_review_at: Mapped[datetime | None] = mapped_column(TZDateTime())
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = UserFK()
    lexeme_id: Mapped[str] = mapped_column(String(36), ForeignKey("lexemes.id", ondelete="CASCADE"))
    rating: Mapped[int] = mapped_column(Integer)
    elapsed_days: Mapped[float] = mapped_column(Float)
    scheduled_days: Mapped[float] = mapped_column(Float)
    retrievability: Mapped[float | None] = mapped_column(Float)
    reviewed_at: Mapped[datetime] = mapped_column(TZDateTime(), default=utcnow)


class Batch(Base):
    __tablename__ = "batches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = UserFK()
    created_at: Mapped[datetime] = mapped_column(TZDateTime(), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(TZDateTime())


class BatchItem(Base):
    __tablename__ = "batch_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("batches.id", ondelete="CASCADE"), index=True)
    lexeme_id: Mapped[str] = mapped_column(String(36), ForeignKey("lexemes.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(200))
    reason_kind: Mapped[str] = mapped_column(String(16))
    score: Mapped[float] = mapped_column(Float)


class Scenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = UserFK()
    title: Mapped[str] = mapped_column(String(160))
    details: Mapped[str | None] = mapped_column(Text)  # the learner's own description; never shared
    kind: Mapped[str] = mapped_column(String(12))  # upcoming | recurring | manual
    topic: Mapped[str | None] = mapped_column(String(64))
    starts_at: Mapped[datetime | None] = mapped_column(TZDateTime())
    status: Mapped[str] = mapped_column(String(12), default="active")  # suggested | active | done
    created_at: Mapped[datetime] = mapped_column(TZDateTime(), default=utcnow)


class ScenarioPhrase(Base):
    __tablename__ = "scenario_phrases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scenario_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenarios.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(8))  # key | rescue | hear
    en: Mapped[str] = mapped_column(String(300))
    es: Mapped[str] = mapped_column(String(300))
    alignment: Mapped[list] = mapped_column(JSON, default=list)
    position: Mapped[int] = mapped_column(Integer)


class Readiness(Base):
    __tablename__ = "readiness"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = UserFK()
    scenario_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenarios.id", ondelete="CASCADE"), index=True)
    value: Mapped[int] = mapped_column(Integer)
    phase: Mapped[str] = mapped_column(String(8))  # before | after
    at: Mapped[datetime] = mapped_column(TZDateTime(), default=utcnow)


class Rehearsal(Base):
    __tablename__ = "rehearsals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = UserFK()
    scenario_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenarios.id", ondelete="CASCADE"))
    difficulty: Mapped[str] = mapped_column(String(8), default="gentle")
    started_at: Mapped[datetime] = mapped_column(TZDateTime(), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(TZDateTime())
    summary: Mapped[str | None] = mapped_column(Text)


class RehearsalTurn(Base):
    __tablename__ = "rehearsal_turns"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    rehearsal_id: Mapped[str] = mapped_column(String(36), ForeignKey("rehearsals.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(8))  # coach | user
    text: Mapped[str] = mapped_column(Text)
    en: Mapped[str | None] = mapped_column(Text)
    native: Mapped[str | None] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(TZDateTime(), default=utcnow)


class PronunciationAttempt(Base):
    __tablename__ = "pronunciation_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = UserFK()
    lexeme_id: Mapped[str] = mapped_column(String(36), ForeignKey("lexemes.id", ondelete="CASCADE"))
    expected: Mapped[str] = mapped_column(String(300))
    heard: Mapped[str] = mapped_column(String(300))
    score: Mapped[float] = mapped_column(Float)
    at: Mapped[datetime] = mapped_column(TZDateTime(), default=utcnow)
