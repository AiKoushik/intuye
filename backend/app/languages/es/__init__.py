"""Spanish."""
from __future__ import annotations

from app.languages.base import LanguagePack, Variety
from app.languages.es import text
from app.languages.es.grammar import TRIGGERS
from app.languages.es.lessons import LESSONS
from app.languages.es.lexicon import BASE
from app.languages.es.phonemes import TIPS, word_phonemes

PACK = LanguagePack(
    code="es",
    name="Spanish",
    native_name="Español",
    varieties=(
        Variety("es-419", "Latin America", "neutral Latin American Spanish", tts="es-MX", stt="es-MX"),
        Variety("es-MX", "Mexico", "Mexican Spanish", tts="es-MX", stt="es-MX"),
        Variety("es-ES", "Spain", "Spain Spanish", tts="es-ES", stt="es-ES"),
    ),
    default_variety="es-419",
    letters=text.LETTERS,
    marks=text.MARKS,
    hint_words=text.HINT_WORDS,
    suffixes=text.SUFFIXES,
    articles=text.ARTICLES,
    stopwords=text.STOPWORDS,
    ask_in_target=text.ASK_IN_TARGET,
    phonemes=word_phonemes,
    sound_tips=TIPS,
    grammar=TRIGGERS,
    lessons=LESSONS,
    base_lexicon=BASE,
    rescue_phrases=(("Can you repeat that, please?", "¿Puede repetirlo, por favor?"), ("Slower, please", "Más despacio, por favor"),
                    ("How do you say ...?", "¿Cómo se dice ...?")),
    prompt_examples={
        "to_native": '"como te va" -> "How\'s it going?"',
        "to_target": '"I like hearing this in my mind" -> "Me gusta escuchar esto en mi mente"',
    },
    ui={
        "variety_note": "Words differ by place: ordenador or computadora.",
        "example": [{"src": "me gusta", "tgt": "Me gusta"}, {"src": "escuchar", "tgt": "escuchar"}, {"src": "this", "tgt": "esto"},
                    {"src": "in my", "tgt": "en mi"}, {"src": "mind", "tgt": "mente", "new": True}],
        "try_saying": ["me gusta escuchar esto en mi mind", "what does cómo te va mean?"],
    },
    dev_dictionary={
        "i like": "me gusta", "i": "yo", "like": "gusta", "hearing": "escuchar", "hear": "escuchar", "this": "esto",
        "in": "en", "my": "mi", "mind": "mente", "brain": "cerebro", "tooth": "muela", "hurts": "duele", "since": "desde",
        "yesterday": "ayer", "work": "trabajo", "food": "comida", "neuroscience": "neurociencia", "want": "quiero",
        "that you": "que", "come": "vengas", "early": "temprano", "the": "el", "is": "es", "very": "muy",
        "interesting": "interesante", "cook": "cocinar", "dinner": "cena", "son": "hijo", "school": "escuela",
    },
)
