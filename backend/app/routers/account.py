from __future__ import annotations

import re
from datetime import datetime

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models as m
from app.db import get_session
from app.security.deps import current_user

router = APIRouter(prefix="/v1", tags=["account"])

DIALECTS = {"es-ES", "es-MX", "es-419"}
HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class SettingsOut(BaseModel):
    dialect: str
    level: int
    daily_notification_budget: int
    quiet_start: str
    quiet_end: str
    moment_retention_days: int
    timezone: str


class SettingsPatch(BaseModel):
    dialect: str | None = None
    level: int | None = Field(default=None, ge=0, le=5)
    daily_notification_budget: int | None = Field(default=None, ge=0, le=6)
    quiet_start: str | None = None
    quiet_end: str | None = None
    moment_retention_days: int | None = Field(default=None, ge=1, le=3650)
    timezone: str | None = Field(default=None, max_length=64)

    @field_validator("dialect")
    @classmethod
    def _dialect(cls, v: str | None) -> str | None:
        if v is not None and v not in DIALECTS:
            raise ValueError(f"must be one of {sorted(DIALECTS)}")
        return v

    @field_validator("quiet_start", "quiet_end")
    @classmethod
    def _hhmm(cls, v: str | None) -> str | None:
        if v is not None and not HHMM.match(v):
            raise ValueError("must be HH:MM")
        return v


async def _settings(db: AsyncSession, user_id: str) -> m.UserSettings:
    row = await db.get(m.UserSettings, user_id)
    if row is None:
        row = m.UserSettings(user_id=user_id)
        db.add(row)
        await db.commit()
    return row


@router.get("/me")
async def me(user: m.User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    s = await _settings(db, user.id)
    return {"user": {"id": user.id, "display_name": user.display_name},
            "settings": SettingsOut.model_validate(s, from_attributes=True).model_dump()}


@router.patch("/me/settings", response_model=SettingsOut)
async def patch_settings(body: SettingsPatch, user: m.User = Depends(current_user),
                         db: AsyncSession = Depends(get_session)) -> SettingsOut:
    s = await _settings(db, user.id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(s, k, v)
    await db.commit()
    return SettingsOut.model_validate(s, from_attributes=True)


# Tables exported / deleted, each with how to scope it to the user.
_USER_TABLES = [m.UserSettings, m.Utterance, m.Lexeme, m.LexemeEvent, m.Card, m.Review, m.Batch, m.Scenario,
                m.Readiness, m.Rehearsal, m.PronunciationAttempt, m.AttestKey, m.RefreshToken]
_SKIP_EXPORT = {"refresh_tokens", "attest_keys"}


def _row(obj) -> dict:
    out = {}
    for col in obj.__table__.columns:
        v = getattr(obj, col.key)
        out[col.key] = v.isoformat() if isinstance(v, datetime) else v
    return out


@router.get("/account/export")
async def export(user: m.User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> dict:
    data: dict = {"user": _row(user)}
    for t in _USER_TABLES:
        if t.__tablename__ in _SKIP_EXPORT:
            continue
        rows = (await db.execute(select(t).where(t.user_id == user.id))).scalars().all()
        data[t.__tablename__] = [_row(r) for r in rows]
    scen_ids = [s["id"] for s in data["scenarios"]]
    reh_ids = [r["id"] for r in data["rehearsals"]]
    batch_ids = [b["id"] for b in data["batches"]]
    data["scenario_phrases"] = [_row(r) for r in (await db.execute(
        select(m.ScenarioPhrase).where(m.ScenarioPhrase.scenario_id.in_(scen_ids)))).scalars()]
    data["rehearsal_turns"] = [_row(r) for r in (await db.execute(
        select(m.RehearsalTurn).where(m.RehearsalTurn.rehearsal_id.in_(reh_ids)))).scalars()]
    data["batch_items"] = [_row(r) for r in (await db.execute(
        select(m.BatchItem).where(m.BatchItem.batch_id.in_(batch_ids)))).scalars()]
    return data


@router.delete("/account", status_code=204)
async def delete_account(user: m.User = Depends(current_user), db: AsyncSession = Depends(get_session)) -> Response:
    # Explicit deletes (children first) so behaviour doesn't depend on DB-level cascade support.
    scen = select(m.Scenario.id).where(m.Scenario.user_id == user.id)
    reh = select(m.Rehearsal.id).where(m.Rehearsal.user_id == user.id)
    bat = select(m.Batch.id).where(m.Batch.user_id == user.id)
    await db.execute(delete(m.ScenarioPhrase).where(m.ScenarioPhrase.scenario_id.in_(scen)))
    await db.execute(delete(m.RehearsalTurn).where(m.RehearsalTurn.rehearsal_id.in_(reh)))
    await db.execute(delete(m.BatchItem).where(m.BatchItem.batch_id.in_(bat)))
    for t in [m.Readiness, m.Review, m.Card, m.LexemeEvent, m.PronunciationAttempt, m.Rehearsal, m.Batch,
              m.Scenario, m.Lexeme, m.Utterance, m.UserSettings, m.RefreshToken, m.AttestKey]:
        await db.execute(delete(t).where(t.user_id == user.id))
    await db.execute(delete(m.User).where(m.User.id == user.id))
    await db.commit()
    return Response(status_code=204)
