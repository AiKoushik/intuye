"""Rehearsal partner deep agent: plays the other person; one checkpointer thread per rehearsal.

The database transcript is the durable record. If the thread is gone (a restart), `turn` rebuilds the
conversation from it. English lines go through the translator first so the learner gets the Spanish.
"""
from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from app.agents.runtime import AgentContext, ask, make_agent
from app.agents.schemas import CoachTurnOut, RehearsalSummaryOut, TranslationOut
from app.curation.text import english_share
from app.llm import prompts

MAX_TURNS = 12  # learner turns
OPENING = "(scene starts — say your opening line)"


class Turn(TypedDict, total=False):
    role: str  # coach | user
    text: str
    en: str | None
    native: str | None


def partner_prompt(ctx: AgentContext) -> str:
    return prompts.COACH.format(title=ctx.title, dialect=ctx.dialect_name, difficulty=ctx.difficulty, data_rule=prompts.DATA_RULE)


def summary_prompt(ctx: AgentContext) -> str:
    return prompts.SUMMARY.format(title=ctx.title, dialect=ctx.dialect_name, data_rule=prompts.DATA_RULE)


def build_partner(model, checkpointer=None):
    return make_agent(model, "rehearsal-partner", partner_prompt, CoachTurnOut, checkpointer=checkpointer or MemorySaver())


def build_summariser(model):
    return make_agent(model, "summariser", summary_prompt, RehearsalSummaryOut)


def _config(rehearsal_id: str) -> dict:
    return {"configurable": {"thread_id": rehearsal_id}}


def _rebuild(turns: list[Turn]) -> list[BaseMessage]:
    messages: list[BaseMessage] = [HumanMessage(OPENING)]
    for t in turns:
        messages.append(AIMessage(t["text"]) if t["role"] == "coach" else HumanMessage(prompts.wrap(t["text"])))
    return messages


async def opening(agents, rehearsal_id: str, ctx: AgentContext) -> CoachTurnOut:
    return await ask(agents.partner, CoachTurnOut, OPENING, ctx, _config(rehearsal_id))


async def turn(agents, rehearsal_id: str, ctx: AgentContext, text: str, history: list[Turn]) -> tuple[str | None, CoachTurnOut, bool]:
    """One learner turn -> (native version of their line, partner reply, scene done)."""
    escape_es = None
    if english_share(text) >= 0.6:  # escape hatch: they switched to English, give the Spanish back
        tr = await ask(agents.translator, TranslationOut, f"DIRECTION: to_es\n{prompts.wrap(text)}",
                       AgentContext(dialect=ctx.dialect, direction="to_es"))
        escape_es = tr.close
    snapshot = await agents.partner.aget_state(_config(rehearsal_id))
    messages = [] if snapshot.values else _rebuild(history)
    messages.append(HumanMessage(prompts.wrap(text)))
    out = await ask(agents.partner, CoachTurnOut, messages, ctx, _config(rehearsal_id))
    learner_turns = sum(1 for t in history if t["role"] == "user") + 1
    return escape_es or out.native, out, out.done or learner_turns >= MAX_TURNS


async def summarise(agents, ctx: AgentContext, turns: list[Turn]) -> RehearsalSummaryOut:
    transcript = "\n".join(f"{'COACH' if t['role'] == 'coach' else 'LEARNER'}: {t['text']}" for t in turns)
    return await ask(agents.summariser, RehearsalSummaryOut, prompts.wrap(transcript), ctx)
