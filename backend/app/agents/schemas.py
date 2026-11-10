"""Structured outputs for every LLM call. No schema has an 'explanation' field on purpose."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AlignPair(BaseModel):
    src: str = Field(description="A word or short phrase from the input, verbatim")
    tgt: str = Field(description="Its counterpart in the output, verbatim")


class TranslationOut(BaseModel):
    close: str = Field(description="One-line translation that keeps the input's structure and word choice")
    alignment: list[AlignPair] = Field(description="Every input word/phrase in order, paired with its counterpart")
    natural: str | None = Field(default=None, description="Only if the close version would sound wrong to a native")


class AnswerOut(BaseModel):
    answer: str = Field(description="At most three short sentences answering only what was asked")


class IngestItem(BaseModel):
    index: int
    close_es: str
    alignment: list[AlignPair]
    topic: str | None = Field(default=None, description="1-3 lowercase words, e.g. 'neuroscience', 'food'")


class IngestOut(BaseModel):
    items: list[IngestItem]


class PhraseOut(BaseModel):
    en: str
    es: str
    alignment: list[AlignPair]


class PrepPackOut(BaseModel):
    key: list[PhraseOut] = Field(description="8-12 things the learner will want to say")
    rescue: list[PhraseOut] = Field(description="3-5 phrases for when they get stuck")
    hear: list[PhraseOut] = Field(description="3-6 things they are likely to hear")


class CoachTurnOut(BaseModel):
    native: str | None = Field(default=None, description="How a native would say the learner's line, only if theirs was wrong or not Spanish")
    reply_es: str = Field(description="The other person's next line, in Spanish, one or two short sentences")
    reply_en: str = Field(description="Close English version of reply_es")
    done: bool = Field(default=False, description="True when the scene has naturally ended")


class RehearsalSummaryOut(BaseModel):
    went_well: str = Field(description="One short sentence")
    keep: list[PhraseOut] = Field(description="Three phrases worth keeping")
