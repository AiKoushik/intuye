"""Deterministic offline chat model for tests and local development without a model server.

It speaks the same tool-calling protocol as a real model, so Deep Agents run unchanged: it calls the
scene builder's tools and subagent in order, then answers through the structured-output tool. Its
Spanish comes from a tiny dictionary, so output is plausible only for the phrases below.
"""
from __future__ import annotations

import json
import re
import uuid
from typing import Any, TypeVar

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel

from app.agents import schemas as s

T = TypeVar("T", bound=BaseModel)

EN_ES = {
    "i like": "me gusta", "i": "yo", "like": "gusta", "hearing": "escuchar", "hear": "escuchar", "this": "esto",
    "in": "en", "my": "mi", "mind": "mente", "brain": "cerebro", "tooth": "muela", "hurts": "duele", "since": "desde",
    "yesterday": "ayer", "work": "trabajo", "food": "comida", "neuroscience": "neurociencia", "want": "quiero",
    "that you": "que", "come": "vengas", "early": "temprano", "the": "el", "is": "es", "very": "muy",
    "interesting": "interesante", "cook": "cocinar", "dinner": "cena", "son": "hijo", "school": "escuela",
}
ES_EN_PHRASES = {"como te va": "How's it going?", "cómo te va": "How's it going?", "que tal": "How are things?"}
ES_EN = {v: k for k, v in EN_ES.items()} | {"este": "this", "esto": "this", "me gusta": "I like", "te": "you", "va": "goes"}
TOPICS = {"neuroscience": ("brain", "neuron", "neuroscience", "cerebro", "mind"), "food": ("food", "cook", "dinner", "eat"),
          "health": ("tooth", "dentist", "doctor", "hurts"), "kids": ("son", "school", "kid")}


def _user_text(user: str) -> str:
    m = re.search(r"<user_text>\n?(.*?)\n?</user_text>", user, re.S)
    return (m.group(1) if m else user).strip()


def _to_es(text: str) -> s.TranslationOut:
    words = re.findall(r"[\w']+", text.lower())
    pairs, i = [], 0
    while i < len(words):
        two = " ".join(words[i:i + 2])
        if two in EN_ES:
            pairs.append(s.AlignPair(src=two, tgt=EN_ES[two])); i += 2; continue
        w = words[i]
        pairs.append(s.AlignPair(src=w, tgt=EN_ES.get(w, "esto" if w == "este" else w))); i += 1
    close = " ".join(p.tgt for p in pairs)
    return s.TranslationOut(close=close[:1].upper() + close[1:] + ".", alignment=pairs, natural=None)


def _to_en(text: str) -> s.TranslationOut:
    key = re.sub(r"[¿?¡!.]", "", text.lower()).strip()
    if key in ES_EN_PHRASES:
        parts = key.split(" ", 1)
        return s.TranslationOut(close=ES_EN_PHRASES[key], natural=None,
                                alignment=[s.AlignPair(src=parts[0], tgt="how's"), s.AlignPair(src=parts[1], tgt="it going?")])
    words = re.findall(r"[\wáéíóúñ']+", key)
    pairs = [s.AlignPair(src=w, tgt=ES_EN.get(w, w)) for w in words]
    close = " ".join(p.tgt for p in pairs)
    return s.TranslationOut(close=close[:1].upper() + close[1:], alignment=pairs, natural=None)


def _topic(text: str) -> str | None:
    low = text.lower()
    return next((t for t, keys in TOPICS.items() if any(k in low for k in keys)), None)


def _phrase(en: str, es: str) -> s.PhraseOut:
    return s.PhraseOut(en=en, es=es, alignment=[s.AlignPair(src=en, tgt=es)])


def _card(text: str) -> s.SceneCardOut:
    title = re.split(r"\n", text)[0].strip().removeprefix("SCENE:").strip() or "A scene"
    return s.SceneCardOut(title=title[:80], situation=f"Getting through this in Spanish: {title.lower()}.",
                          topic=_topic(text) or "everyday", shareable=not re.search(r"\d{3,}|@", text))


def fake_structured(schema: type[T], system: str, user: str) -> T:
    """What the fake model answers for each output schema."""
    text = _user_text(user)
    if schema is s.SceneCardOut:
        return _card(text)  # type: ignore[return-value]
    return _structured(schema, text, user)


def _structured(schema: type[T], text: str, user: str) -> T:
    if schema is s.TranslationOut:
        return _to_en(text) if "DIRECTION: to_en" in user else _to_es(text)  # type: ignore[return-value]
    if schema is s.AnswerOut:
        return s.AnswerOut(answer="Use usted with people you'd address formally, like strangers, officials or a "
                                  "landlord. Use tú with friends, family and people your age.")  # type: ignore[return-value]
    if schema is s.IngestOut:
        items = []
        for m in re.finditer(r"^\[(\d+)\] (.+)$", text, re.M):
            t = _to_es(m.group(2))
            items.append(s.IngestItem(index=int(m.group(1)), close_es=t.close, alignment=t.alignment, topic=_topic(m.group(2))))
        return s.IngestOut(items=items)  # type: ignore[return-value]
    if schema is s.PrepPackOut:
        key = [_phrase("This tooth hurts", "Me duele esta muela"), _phrase("since yesterday", "desde ayer"),
               _phrase("It hurts when I eat cold things", "Me duele cuando como cosas frías"),
               _phrase("I have an appointment", "Tengo una cita"), _phrase("at ten", "a las diez"),
               _phrase("Is it serious?", "¿Es grave?"), _phrase("How much does it cost?", "¿Cuánto cuesta?"),
               _phrase("Thank you very much", "Muchas gracias")]
        rescue = [_phrase("Can you repeat that, please?", "¿Puede repetirlo, por favor?"),
                  _phrase("Slower, please", "Más despacio, por favor"),
                  _phrase("How do you say ...?", "¿Cómo se dice ...?")]
        hear = [_phrase("What's wrong?", "¿Qué le pasa?"), _phrase("Since when?", "¿Desde cuándo?"),
                _phrase("Open your mouth", "Abra la boca")]
        return s.PrepPackOut(key=key, rescue=rescue, hear=hear)  # type: ignore[return-value]
    if schema is s.CoachTurnOut:
        if "(scene starts" in user:
            return s.CoachTurnOut(reply_es="Buenos días. ¿Qué le pasa?", reply_en="Good morning. What's wrong with you?")  # type: ignore[return-value]
        turns = user.count("LEARNER:")
        native = None if any(c in text for c in "áéíóúñ¿") or "duele" in text.lower() else _to_es(text).close
        if turns >= 4:
            return s.CoachTurnOut(native=native, reply_es="Muy bien. Nos vemos el jueves.", reply_en="Very good. See you Thursday.", done=True)  # type: ignore[return-value]
        return s.CoachTurnOut(native=native, reply_es="¿Desde cuándo le duele?", reply_en="Since when does it hurt you?")  # type: ignore[return-value]
    if schema is s.RehearsalSummaryOut:
        return s.RehearsalSummaryOut(went_well="You described the pain and when it started without switching to English.",
                                     keep=[_phrase("This tooth hurts", "Me duele esta muela"),
                                           _phrase("since yesterday", "desde ayer"),
                                           _phrase("Slower, please", "Más despacio, por favor")])  # type: ignore[return-value]
    raise NotImplementedError(schema.__name__)


SCHEMAS = {c.__name__: c for c in (s.TranslationOut, s.AnswerOut, s.IngestOut, s.PrepPackOut, s.SceneCardOut,
                                   s.CoachTurnOut, s.RehearsalSummaryOut)}


def _text(m: BaseMessage) -> str:
    return m.content if isinstance(m.content, str) else " ".join(b.get("text", "") for b in m.content if isinstance(b, dict))


class FakeChatModel(BaseChatModel):
    """Tool-calling fake: scene-builder tools first, then the structured-output tool for the bound schema."""

    model_name: str = "fake"

    @property
    def _llm_type(self) -> str:
        return "langcoach-fake"

    def _get_ls_params(self, stop: list[str] | None = None, **kwargs: Any) -> dict:
        return {"ls_provider": "langcoach", "ls_model_name": self.model_name, "ls_model_type": "chat"}

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):  # type: ignore[override]
        return self.bind(tools=[convert_to_openai_tool(t) for t in tools], tool_choice=tool_choice, **kwargs)

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, tools=None, **kwargs) -> ChatResult:
        names = [t["function"]["name"] for t in tools or []]
        system = next((_text(m) for m in messages if isinstance(m, SystemMessage)), "")
        humans = [_text(m) for m in messages if isinstance(m, HumanMessage)]
        done = {m.name for m in messages if isinstance(m, ToolMessage)}
        last = humans[-1] if humans else ""
        if "search_scene_library" in names and "search_scene_library" not in done:
            return _call("search_scene_library", {"query": _user_text(last).split("\n")[0].removeprefix("SCENE:").strip()})
        if "task" in names and "task" not in done:
            return _call("task", {"subagent_type": "phrase-writer", "description": f"Write the pack for: {_user_text(last)}"})
        schema = next((SCHEMAS[n] for n in names if n in SCHEMAS), None)
        if schema is None:
            return ChatResult(generations=[ChatGeneration(message=AIMessage("OK"))])
        learner_turns = sum(1 for h in humans if "(scene starts" not in h)
        user = "LEARNER:\n" * learner_turns + last
        return _call(schema.__name__, json.loads(fake_structured(schema, system, user).model_dump_json()))


def _call(name: str, args: dict) -> ChatResult:
    call = {"name": name, "args": args, "id": "call_" + uuid.uuid4().hex[:12], "type": "tool_call"}
    return ChatResult(generations=[ChatGeneration(message=AIMessage("", tool_calls=[call]))])
