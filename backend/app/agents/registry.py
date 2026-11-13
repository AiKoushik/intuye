"""Builds every agent once per app: Deep Agents for model calls, LangGraph pipelines around them."""
from __future__ import annotations

from app.agents.coach import build_coach_graph, build_explainer, build_translator
from app.agents.ingest import build_ingest_analyst, build_ingest_graph
from app.agents.rehearse import build_partner, build_summariser
from app.agents.runtime import use_lean_harness
from app.agents.scene_builder import build_phrase_writer, build_scene_builder
from app.config import Settings
from app.llm.provider import build_chat_model


class Agents:
    def __init__(self, settings: Settings, checkpointer=None) -> None:
        fast, smart = build_chat_model(settings, "fast"), build_chat_model(settings, "smart")
        use_lean_harness(fast)
        use_lean_harness(smart)
        self.translator = build_translator(fast)
        self.explainer = build_explainer(smart)
        self.ingest_analyst = build_ingest_analyst(fast)
        self.phrase_writer = build_phrase_writer(smart)
        self.scene_builder = build_scene_builder(smart)
        self.partner = build_partner(smart, checkpointer)
        self.summariser = build_summariser(smart)
        self.coach = build_coach_graph(self)
        self.ingest = build_ingest_graph(self)
