"""Coach pipeline (Say tab): route -> translate | answer -> brevity_guard.

Routing and the brevity guard are deterministic; the model steps call the translator and explainer
deep agents.

Brevity contract: translations are one line with alignment and an optional 'natural' variant only
when it differs; answers are at most three sentences / 320 characters. Nothing else is returned.
"""
from __future__ import annotations

import re
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.runtime import AgentContext, ask, make_agent
from app.agents.schemas import AnswerOut, TranslationOut
from app.curation.text import fold, is_spanish_token, looks_spanish, normalize_es, tokens
from app.llm import prompts

Intent = Literal["to_es", "to_en", "ask"]

# "what does X mean" / "what is X in English" -> short to_en translation of X
MEANING = re.compile(r"^\s*(?:what\s+does|what's|what\s+is)\s+[\"“']?(.+?)[\"”']?\s+(?:mean|in\s+english)\s*\??\s*$", re.I)
# "how do I say X (in Spanish)?" / "¿cómo se dice X?" -> to_es of X
HOW_SAY = re.compile(r"^\s*(?:how\s+(?:do\s+(?:i|you)|would\s+i|to)\s+say|¿?\s*c[oó]mo\s+se\s+dice)\s+[\"“']?(.+?)[\"”']?"
                     r"(?:\s+in\s+spanish)?\s*\??\s*$", re.I)
# Explicit questions about the language -> ask
ASK = re.compile(r"^\s*(?:when|why|which|should|is\s+it|can\s+i|do\s+i|what'?s\s+the\s+difference|difference\s+between|"
                 r"how\s+(?:do|would|should)\s+i\s+(?:use|address|greet|answer|respond|talk)|what\s+(?:do|should)\s+i\s+say|explain)\b",
                 re.I)


class CoachState(TypedDict, total=False):
    text: str
    direction: Literal["auto", "to_es", "to_en"]
    dialect: str
    known: set[str]
    intent: Intent
    payload: str
    close: str
    natural: str | None
    alignment: list[dict]
    answer: str | None


def route_input(text: str, direction: str) -> tuple[Intent, str]:
    if direction in ("to_es", "to_en"):
        return direction, text  # type: ignore[return-value]
    if m := MEANING.match(text):
        return "to_en", m.group(1)
    if m := HOW_SAY.match(text):
        return "to_es", m.group(1)
    if ASK.match(text) and text.rstrip().endswith("?"):
        return "ask", text
    # Any English word inside Spanish = Spanglish: the learner wants the whole thing in Spanish.
    has_english = any(is_spanish_token(t) is False for t in tokens(text))
    return ("to_en" if looks_spanish(text) and not has_english else "to_es"), text


def translator_prompt(ctx: AgentContext) -> str:
    template = prompts.TRANSLATE_TO_ES if ctx.direction == "to_es" else prompts.TRANSLATE_TO_EN
    return template.format(dialect=ctx.dialect_name, data_rule=prompts.DATA_RULE)


def explainer_prompt(ctx: AgentContext) -> str:
    return prompts.ANSWER.format(dialect=ctx.dialect_name, data_rule=prompts.DATA_RULE)


def build_translator(model):
    return make_agent(model, "translator", translator_prompt, TranslationOut)


def build_explainer(model):
    return make_agent(model, "explainer", explainer_prompt, AnswerOut)


def build_coach_graph(agents):
    async def route(state: CoachState) -> CoachState:
        intent, payload = route_input(state["text"], state.get("direction", "auto"))
        return {"intent": intent, "payload": payload}

    async def translate(state: CoachState) -> CoachState:
        ctx = AgentContext(dialect=state.get("dialect", "es-419"), direction=state["intent"])
        out = await ask(agents.translator, TranslationOut, f"DIRECTION: {state['intent']}\n{prompts.wrap(state['payload'])}", ctx)
        return {"close": out.close, "natural": out.natural, "alignment": [p.model_dump() for p in out.alignment], "answer": None}

    async def answer(state: CoachState) -> CoachState:
        out = await ask(agents.explainer, AnswerOut, prompts.wrap(state["payload"]), AgentContext(dialect=state.get("dialect", "es-419")))
        return {"answer": out.answer, "close": "", "natural": None, "alignment": []}

    async def brevity_guard(state: CoachState) -> CoachState:
        if state["intent"] == "ask":
            return {"answer": trim_answer(state.get("answer") or "")}
        close = " ".join((state.get("close") or "").split())
        natural = state.get("natural")
        if natural and _same(natural, close):
            natural = None
        known = state.get("known") or set()
        to_es = state["intent"] == "to_es"
        aligned = []
        for p in state.get("alignment") or []:
            src, tgt = p["src"].strip(), p["tgt"].strip()
            if not src:
                continue
            es_side = tgt if to_es else src
            new = _is_new(src, tgt, es_side, known, to_es)
            aligned.append({"src": src, "tgt": tgt, "new": new})
        return {"close": close, "natural": " ".join(natural.split()) if natural else None, "alignment": aligned}

    g = StateGraph(CoachState)
    g.add_node("route", route)
    g.add_node("translate", translate)
    g.add_node("answer", answer)
    g.add_node("brevity_guard", brevity_guard)
    g.add_edge(START, "route")
    g.add_conditional_edges("route", lambda s: "answer" if s["intent"] == "ask" else "translate",
                            {"answer": "answer", "translate": "translate"})
    g.add_edge("translate", "brevity_guard")
    g.add_edge("answer", "brevity_guard")
    g.add_edge("brevity_guard", END)
    return g.compile()


def _same(a: str, b: str) -> bool:
    norm = lambda x: re.sub(r"[^\w ]", "", fold(x)).strip()  # noqa: E731
    return norm(a) == norm(b)


def _is_new(src: str, tgt: str, es_side: str, known: set[str], to_es: bool) -> bool:
    """A pair is 'new' when Spanish had to be supplied and the learner hasn't learned that Spanish yet."""
    es = normalize_es(es_side)
    if not es or es in known:
        return False
    if to_es:
        # The learner already said it in Spanish (e.g. 'mi' -> 'mi'), so nothing new.
        if _same(src, tgt) or all(is_spanish_token(t) for t in tokens(src)):
            return False
        return True
    return True


def trim_answer(text: str, max_sentences: int = 3, max_chars: int = 320) -> str:
    text = " ".join(text.split())
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out = " ".join(sentences[:max_sentences])
    if len(out) > max_chars:
        out = out[:max_chars].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return out
