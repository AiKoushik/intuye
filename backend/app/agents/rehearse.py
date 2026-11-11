"""Rehearse graph (role-play): read_user_turn -> (escape_hatch | pass) -> coach_reply -> maybe_end.

Stateful per rehearsal via a LangGraph checkpointer (thread_id = rehearsal id). The DB transcript is
the durable record; if a checkpoint is missing (e.g. after a restart) the caller seeds `turns` from it.
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.schemas import CoachTurnOut, RehearsalSummaryOut, TranslationOut
from app.curation.text import english_share
from app.llm import prompts
from app.llm.provider import LLM

MAX_TURNS = 24


class Turn(TypedDict, total=False):
    role: str  # coach | user
    text: str
    en: str | None
    native: str | None


class RehearseState(TypedDict, total=False):
    title: str
    dialect: str
    difficulty: str
    turns: Annotated[list[Turn], operator.add]
    user_text: str | None
    escape_es: str | None
    last: Turn
    done: bool


def _transcript(turns: list[Turn]) -> str:
    return "\n".join(f"{'COACH' if t['role'] == 'coach' else 'LEARNER'}: {t['text']}" for t in turns)


def build_rehearse_graph(llm: LLM, checkpointer=None):
    async def read_user_turn(state: RehearseState) -> RehearseState:
        return {"escape_es": None}

    async def escape_hatch(state: RehearseState) -> RehearseState:
        """Learner switched to English: give them the Spanish, close to what they said."""
        dialect = prompts.DIALECT_NAMES.get(state.get("dialect", "es-419"), "Spanish")
        out = await llm.structured(TranslationOut, prompts.TRANSLATE_TO_ES.format(dialect=dialect, data_rule=prompts.DATA_RULE),
                                   f"DIRECTION: to_es\n{prompts.wrap(state['user_text'] or '')}")
        return {"escape_es": out.close}

    async def coach_reply(state: RehearseState) -> RehearseState:
        dialect = prompts.DIALECT_NAMES.get(state.get("dialect", "es-419"), "Spanish")
        system = prompts.COACH.format(title=state["title"], dialect=dialect, difficulty=state.get("difficulty", "gentle"),
                                      data_rule=prompts.DATA_RULE)
        history = list(state.get("turns") or [])
        if state.get("user_text"):
            history.append({"role": "user", "text": state["user_text"]})
            user_msg = f"{_transcript(history)}\n{prompts.wrap(state['user_text'])}"
        else:
            user_msg = "LEARNER: (scene starts — say your opening line)"
        out = await llm.structured(CoachTurnOut, system, user_msg, slot="smart")
        new_turns: list[Turn] = []
        if state.get("user_text"):
            native = state.get("escape_es") or out.native
            new_turns.append({"role": "user", "text": state["user_text"], "en": None, "native": native})
        coach: Turn = {"role": "coach", "text": out.reply_es, "en": out.reply_en, "native": None}
        new_turns.append(coach)
        return {"turns": new_turns, "last": {**coach, "native": new_turns[0].get("native") if state.get("user_text") else None},
                "done": out.done}

    async def maybe_end(state: RehearseState) -> RehearseState:
        return {"done": bool(state.get("done")) or len(state.get("turns") or []) >= MAX_TURNS, "user_text": None}

    def branch(state: RehearseState) -> str:
        text = state.get("user_text")
        return "escape_hatch" if text and english_share(text) >= 0.6 else "coach_reply"

    g = StateGraph(RehearseState)
    g.add_node("read_user_turn", read_user_turn)
    g.add_node("escape_hatch", escape_hatch)
    g.add_node("coach_reply", coach_reply)
    g.add_node("maybe_end", maybe_end)
    g.add_edge(START, "read_user_turn")
    g.add_conditional_edges("read_user_turn", branch, {"escape_hatch": "escape_hatch", "coach_reply": "coach_reply"})
    g.add_edge("escape_hatch", "coach_reply")
    g.add_edge("coach_reply", "maybe_end")
    g.add_edge("maybe_end", END)
    return g.compile(checkpointer=checkpointer or MemorySaver())


async def summarise(llm: LLM, title: str, dialect: str, turns: list[Turn]) -> RehearsalSummaryOut:
    system = prompts.SUMMARY.format(title=title, dialect=prompts.DIALECT_NAMES.get(dialect, "Spanish"), data_rule=prompts.DATA_RULE)
    return await llm.structured(RehearsalSummaryOut, system, prompts.wrap(_transcript(turns)), slot="smart")
