"""Ingest pipeline (ambient capture): normalise -> analyse (ingest analyst agent, batches of 25) -> extract lexeme candidates."""
from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.runtime import AgentContext, ask, make_agent
from app.agents.schemas import IngestOut
from app.curation.text import english_share
from app.llm import prompts
from app.services.lexicon import candidates_from_alignment

CHUNK = 25


class Item(TypedDict, total=False):
    text: str
    spoken_at: datetime
    source: str
    lang_mix: float
    close_es: str | None
    alignment: list[dict]
    topic: str | None
    candidates: list[tuple[str, str]]


class IngestState(TypedDict, total=False):
    items: list[Item]
    dialect: str


def analyst_prompt(ctx: AgentContext) -> str:
    return prompts.INGEST.format(dialect=ctx.dialect_name, data_rule=prompts.DATA_RULE)


def build_ingest_analyst(model):
    return make_agent(model, "ingest-analyst", analyst_prompt, IngestOut)


def build_ingest_graph(agents):
    async def normalise(state: IngestState) -> IngestState:
        seen, out = set(), []
        for it in state["items"]:
            text = " ".join(it["text"].split())[:500]
            key = (text.lower(), it["spoken_at"])
            if len(text) < 2 or key in seen:
                continue
            seen.add(key)
            out.append({**it, "text": text, "lang_mix": english_share(text)})
        return {"items": out}

    async def analyse(state: IngestState) -> IngestState:
        ctx = AgentContext(dialect=state.get("dialect", "es-419"))
        items = list(state["items"])
        for start in range(0, len(items), CHUNK):
            chunk = items[start:start + CHUNK]
            numbered = "\n".join(f"[{i}] {it['text']}" for i, it in enumerate(chunk))
            out = await ask(agents.ingest_analyst, IngestOut, prompts.wrap(numbered), ctx)
            for r in out.items:
                if 0 <= r.index < len(chunk):
                    topic = (r.topic or "").strip().lower()[:64] or None
                    i = start + r.index
                    items[i] = {**items[i], "close_es": r.close_es,
                                "alignment": [p.model_dump() for p in r.alignment], "topic": topic}
        return {"items": items}

    async def extract(state: IngestState) -> IngestState:
        return {"items": [{**it, "candidates": candidates_from_alignment(it.get("alignment") or [], to_es=True)}
                          for it in state["items"]]}

    g = StateGraph(IngestState)
    g.add_node("normalise", normalise)
    g.add_node("analyse", analyse)
    g.add_node("extract", extract)
    g.add_edge(START, "normalise")
    g.add_edge("normalise", "analyse")
    g.add_edge("analyse", "extract")
    g.add_edge("extract", END)
    return g.compile()
