"""What a language pack provides. App logic only ever talks to a `LanguagePack`, never to a language directly.

To add a language, create `app/languages/<code>/` with a `PACK` and register it in `app/languages/__init__.py`.
See docs/09-languages.md.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Variety:
    """A regional variety the learner can pick, e.g. Latin American Spanish."""
    code: str          # BCP-47, stored as the learner's `dialect` setting ("es-419")
    label: str         # shown in pickers ("Latin America")
    prompt_name: str   # how prompts name it ("neutral Latin American Spanish")
    tts: str           # text-to-speech voice language (AVSpeechSynthesisVoice / Web Speech)
    stt: str           # speech-recognition locale


@dataclass(frozen=True)
class Trigger:
    """A pattern in the learner's own (English) sentence that calls for a grammar lesson in the target language."""
    id: str
    pattern: re.Pattern[str]
    target: str        # the target-language pattern, e.g. "quiero que + subjuntivo"
    en: str            # what it covers in English
    lesson: str        # one-line gist


@dataclass(frozen=True)
class Lesson:
    title: str
    pattern: str
    rule: str
    examples: tuple[tuple[str, str], ...]    # (en, target)
    check_prompt: str
    check_options: tuple[str, ...]           # the right one first; shuffled when served
    check_answer: int = 0


@dataclass(frozen=True)
class LanguagePack:
    code: str                                   # ISO 639-1, e.g. "es"
    name: str                                   # English name, used in UI copy and prompts ("Spanish")
    native_name: str                            # endonym ("Español")
    varieties: tuple[Variety, ...]
    default_variety: str

    # Telling target-language words from English ones in mixed sentences.
    letters: str                                # every letter the language writes, for tokenising
    marks: frozenset[str]                       # characters English never uses (accents, ¿ ¡)
    hint_words: frozenset[str]                  # common words that are clearly this language
    suffixes: tuple[str, ...]                   # endings that are clearly this language
    articles: tuple[str, ...]                   # stripped when a phrase becomes a dictionary entry
    stopwords: frozenset[str]                   # never worth a flashcard on their own

    # "How do I say X?" asked in the target language itself (the English form lives in the coach).
    ask_in_target: re.Pattern[str]

    # Pronunciation: spelling -> phonemes for one word, and a tip per phoneme learners tend to miss.
    phonemes: Callable[[str, str], list[str]]
    sound_tips: dict[str, str]

    # Curation content.
    grammar: tuple[Trigger, ...]
    lessons: dict[str, Lesson]
    base_lexicon: tuple[tuple[str, str], ...]  # (target, en), most useful first
    rescue_phrases: tuple[tuple[str, str], ...]  # (en, target): asking to repeat, slow down, how to say a word

    # Short worked examples that prompts show the model, in this language.
    prompt_examples: dict[str, str] = field(default_factory=dict)

    # Copy clients show that needs this language's own words: "variety_note" (why the variety matters),
    # "example" (an interlinear sample: [{src, tgt, new?}]) and "try_saying" (sample inputs for the Say tab).
    ui: dict = field(default_factory=dict)

    # Optional tiny dictionary for the offline fake model used in tests and local runs.
    dev_dictionary: dict[str, str] = field(default_factory=dict)

    def variety(self, code: str | None) -> Variety:
        return next((v for v in self.varieties if v.code == code), self.variety_default)

    @property
    def variety_default(self) -> Variety:
        return next(v for v in self.varieties if v.code == self.default_variety)

    def public(self) -> dict:
        """What clients need to build pickers, speech and copy. Content stays on the server."""
        return {"code": self.code, "name": self.name, "native_name": self.native_name, "default_variety": self.default_variety,
                "varieties": [{"code": v.code, "label": v.label, "tts": v.tts, "stt": v.stt} for v in self.varieties], "ui": self.ui}
