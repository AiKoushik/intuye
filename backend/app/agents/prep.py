"""Prep graph (scenarios): draft_pack -> validate -> (retry <= 2) -> finalise."""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.schemas import PhraseOut, PrepPackOut
from app.llm import prompts
from app.llm.provider import LLM

MAX_ATTEMPTS = 3
DEFAULT_RESCUE = [("Can you repeat that, please?", "¿Puede repetirlo, por favor?"), ("Slower, please", "Más despacio, por favor"),
                  ("How do you say ...?", "¿Cómo se dice ...?")]


class PrepState(TypedDict, total=False):
    title: str
    dialect: str
    level: int
    pack: dict
    problems: list[str]
    attempts: int


def validate_pack(pack: PrepPackOut) -> list[str]:
    problems = []
    if len(pack.key) < 8:
        problems.append(f"only {len(pack.key)} key phrases (need 8-12)")
    if len(pack.rescue) < 3:
        problems.append("fewer than 3 rescue phrases")
    if len(pack.hear) < 3:
        problems.append("fewer than 3 likely-to-hear phrases")
    if any(len(p.es) > 120 for p in pack.key + pack.rescue + pack.hear):
        problems.append("some phrases are too long to say")
    return problems


def build_prep_graph(llm: LLM):
    async def draft_pack(state: PrepState) -> PrepState:
        dialect = prompts.DIALECT_NAMES.get(state.get("dialect", "es-419"), "Spanish")
        system = prompts.PREP.format(dialect=dialect, title=state["title"].replace('"', "'"), level=state.get("level", 0),
                                     data_rule=prompts.DATA_RULE)
        user = prompts.wrap(state["title"])
        if state.get("problems"):
            user += "\nThe previous draft had problems: " + "; ".join(state["problems"])
        pack = await llm.structured(PrepPackOut, system, user, slot="smart")
        return {"pack": pack.model_dump(), "attempts": state.get("attempts", 0) + 1}

    async def validate(state: PrepState) -> PrepState:
        return {"problems": validate_pack(PrepPackOut.model_validate(state["pack"]))}

    async def finalise(state: PrepState) -> PrepState:
        pack = PrepPackOut.model_validate(state["pack"])
        pack.key = [p for p in pack.key if len(p.es) <= 120][:12]
        pack.hear = [p for p in pack.hear if len(p.es) <= 120][:6]
        rescue = [p for p in pack.rescue if len(p.es) <= 120][:5]
        for en, es in DEFAULT_RESCUE:
            if len(rescue) >= 3:
                break
            if all(r.es != es for r in rescue):
                rescue.append(PhraseOut(en=en, es=es, alignment=[{"src": en, "tgt": es}]))
        pack.rescue = rescue
        return {"pack": pack.model_dump()}

    def after_validate(state: PrepState) -> str:
        return "finalise" if not state["problems"] or state["attempts"] >= MAX_ATTEMPTS else "draft_pack"

    g = StateGraph(PrepState)
    g.add_node("draft_pack", draft_pack)
    g.add_node("validate", validate)
    g.add_node("finalise", finalise)
    g.add_edge(START, "draft_pack")
    g.add_edge("draft_pack", "validate")
    g.add_conditional_edges("validate", after_validate, {"finalise": "finalise", "draft_pack": "draft_pack"})
    g.add_edge("finalise", END)
    return g.compile()
