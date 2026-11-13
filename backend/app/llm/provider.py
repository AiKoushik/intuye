"""Chat-model factory. Every agent is built on one of two slots: fast or smart."""
from __future__ import annotations

from typing import Literal

from langchain_core.language_models import BaseChatModel

from app.config import Settings

Slot = Literal["fast", "smart"]


def build_chat_model(settings: Settings, slot: Slot) -> BaseChatModel:
    name = settings.llm_fast_model if slot == "fast" else settings.llm_smart_model
    max_tokens = 1024 if slot == "fast" else 2048
    if settings.llm_provider == "fake":
        from app.llm.fake import FakeChatModel

        return FakeChatModel(model_name=f"fake-{slot}")
    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=name, api_key=settings.anthropic_api_key, temperature=0.2, max_tokens=max_tokens, timeout=60)
    from langchain_openai import ChatOpenAI

    # Chat Completions, not the Responses API: Hearth, Ollama, vLLM and llama.cpp only speak the former.
    return ChatOpenAI(model=name, base_url=settings.llm_base_url, api_key=settings.llm_api_key, temperature=0.2,
                      max_tokens=max_tokens, timeout=60, use_responses_api=False)
