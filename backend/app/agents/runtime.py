"""LangChain Deep Agents runtime: every model call in Intuye runs through an agent built here.

Agents get a lean harness: Deep Agents' filesystem and shell tools are hidden and its general-purpose
subagent is off, because no agent here touches files. What remains is our per-call system prompt (a
`dynamic_prompt` middleware reading the run context), our own tools and subagents, structured output,
tool-call patching, summarisation and, on Anthropic, prompt caching.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, TypeVar

from deepagents import GeneralPurposeSubagentProfile, HarnessProfile, create_deep_agent, register_harness_profile
from deepagents._models import get_model_identifier, get_model_provider
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import BaseModel

from app import languages
from app.languages import LanguagePack
from app.llm import prompts

T = TypeVar("T", bound=BaseModel)
FS_AND_SHELL_TOOLS = frozenset({"ls", "read_file", "write_file", "edit_file", "delete", "glob", "grep", "execute"})
LEAN = HarnessProfile(excluded_tools=FS_AND_SHELL_TOOLS, general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False))

LibrarySearch = Callable[[str], Awaitable[list[dict]]]


@dataclass
class AgentContext:
    """Run-scoped context. Subagents receive the same context as their parent."""

    dialect: str = field(default_factory=lambda: languages.get(None).default_variety)  # the learner's variety code
    level: int = 0
    title: str = ""
    difficulty: str = "gentle"
    direction: str = "to_target"  # or "to_native"
    library_search: LibrarySearch | None = None

    @property
    def pack(self) -> LanguagePack:
        return languages.for_variety(self.dialect)

    def prompt(self, template: str, **extra: Any) -> str:
        """Fill a prompt template with this run's language, variety, example and the data rule."""
        pack = self.pack
        return template.format(language=pack.name, variety=pack.variety(self.dialect).prompt_name,
                               example=pack.prompt_examples.get(self.direction, ""), data_rule=prompts.DATA_RULE, **extra)


PromptFn = Callable[[AgentContext], str]


def use_lean_harness(model: BaseChatModel) -> None:
    """Register the lean profile under this model's `provider:identifier` key (idempotent)."""
    provider, identifier = get_model_provider(model), get_model_identifier(model)
    if provider and identifier:
        register_harness_profile(f"{provider}:{identifier}", LEAN)


def make_agent(model: BaseChatModel, name: str, prompt: PromptFn, schema: type[BaseModel], *, tools: Sequence[Any] = (),
               subagents: Sequence[dict] | None = None, checkpointer=None):
    @dynamic_prompt
    def system(request: ModelRequest) -> str:
        return prompt(request.runtime.context or AgentContext())

    return create_deep_agent(model, list(tools), middleware=[system], subagents=subagents, context_schema=AgentContext,
                             response_format=schema, checkpointer=checkpointer, name=name)


def subagent(name: str, description: str, prompt: PromptFn, schema: type[BaseModel]) -> dict:
    @dynamic_prompt
    def system(request: ModelRequest) -> str:
        return prompt(request.runtime.context or AgentContext())

    return {"name": name, "description": description, "system_prompt": "", "tools": [], "middleware": [system],
            "response_format": schema}


async def ask(agent, schema: type[T], message: str | list[BaseMessage], ctx: AgentContext, config: dict | None = None,
              full: bool = False):
    """Run an agent and return its structured response (and the final state when `full`)."""
    messages = [HumanMessage(message)] if isinstance(message, str) else message
    state = await agent.ainvoke({"messages": messages}, config=config, context=ctx)
    out = state.get("structured_response")
    if out is None:
        raise ValueError(f"agent returned no {schema.__name__}")
    out = out if isinstance(out, schema) else schema.model_validate(out)
    return (out, state) if full else out
