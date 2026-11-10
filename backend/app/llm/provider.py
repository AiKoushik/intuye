"""Provider-agnostic structured chat model used by every LangGraph graph."""
from __future__ import annotations

import logging
from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import Settings

T = TypeVar("T", bound=BaseModel)
Slot = Literal["fast", "smart"]
log = logging.getLogger("langcoach.llm")


class LLM(Protocol):
    async def structured(self, schema: type[T], system: str, user: str, slot: Slot = "fast") -> T: ...


class LangChainLLM:
    """Wraps a LangChain chat model (OpenAI-compatible endpoint such as Hearth/vLLM/Ollama, or Anthropic)."""

    def __init__(self, settings: Settings) -> None:
        self.s = settings
        self._models: dict[str, object] = {}

    def _model(self, slot: Slot):
        name = self.s.llm_fast_model if slot == "fast" else self.s.llm_smart_model
        if name not in self._models:
            if self.s.llm_provider == "anthropic":
                from langchain_anthropic import ChatAnthropic

                self._models[name] = ChatAnthropic(model=name, api_key=self.s.anthropic_api_key, temperature=0.2,
                                                   max_tokens=1024, timeout=30)
            else:
                from langchain_openai import ChatOpenAI

                self._models[name] = ChatOpenAI(model=name, base_url=self.s.llm_base_url, api_key=self.s.llm_api_key,
                                                temperature=0.2, max_tokens=1024, timeout=30)
        return self._models[name]

    async def structured(self, schema: type[T], system: str, user: str, slot: Slot = "fast") -> T:
        from langchain_core.messages import HumanMessage, SystemMessage

        runnable = self._model(slot).with_structured_output(schema)  # type: ignore[attr-defined]
        messages = [SystemMessage(system), HumanMessage(user)]
        for attempt in range(2):
            try:
                out = await runnable.ainvoke(messages)
                return out if isinstance(out, schema) else schema.model_validate(out)
            except (ValidationError, ValueError) as e:
                log.warning("structured output invalid (attempt %d): %s", attempt + 1, e)
        raise ValueError("model did not return valid structured output")


def build_llm(settings: Settings) -> LLM:
    if settings.llm_provider == "fake":
        from app.llm.fake import FakeLLM

        return FakeLLM()
    return LangChainLLM(settings)
