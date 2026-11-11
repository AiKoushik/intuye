"""Compiles every LangGraph graph once per app, over one shared chat model."""
from __future__ import annotations

from app.agents.coach import build_coach_graph
from app.agents.ingest import build_ingest_graph
from app.agents.prep import build_prep_graph
from app.agents.rehearse import build_rehearse_graph
from app.llm.provider import LLM


class Graphs:
    def __init__(self, llm: LLM) -> None:
        self.llm = llm
        self.coach = build_coach_graph(llm)
        self.ingest = build_ingest_graph(llm)
        self.prep = build_prep_graph(llm)
        self.rehearse = build_rehearse_graph(llm)
