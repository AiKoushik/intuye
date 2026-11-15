# Languages

Intuye teaches Spanish today, but nothing outside a language pack knows that. App logic, configuration and
both clients reach a language only through its pack, so a new language is a new folder plus one line.

## Where a language lives

```
backend/app/languages/
  base.py          LanguagePack, Variety, Trigger, Lesson: the contract
  __init__.py      registry (ALL), enabled(), for_variety(), default_variety()
  native_en.py     the learner's own language (English): words that mark a token as English
  es/              Spanish
    __init__.py    PACK = LanguagePack(...): name, varieties, voices, copy, prompt examples
    text.py        letters, accent marks, common words, suffixes, articles, stopwords, "¿cómo se dice…?"
    phonemes.py    spelling -> phonemes, one tip per sound learners miss
    grammar.py     patterns in the learner's English that call for a lesson
    lessons.py     the 60-second lessons, written by hand
    lexicon.py     high-frequency backbone words
```

Language-neutral logic that uses a pack:

| Module | Uses from the pack |
|---|---|
| `curation/text.py` | letters, marks, hint words, suffixes, articles (tokenising, mixed-sentence detection, dictionary entries) |
| `curation/pronunciation.py` | `phonemes()`, `sound_tips` |
| `curation/grammar.py`, `curation/lessons.py` | `grammar`, `lessons` |
| `services/curation.py` | `base_lexicon`, `grammar` |
| `agents/*` via `AgentContext.prompt()` | `name`, variety `prompt_name`, `prompt_examples`, `rescue_phrases` |
| `agents/coach.py` | `ask_in_target` plus the text helpers |
| `routers/languages.py` | `public()`: name, varieties, voices, client copy (`ui`) |

Prompts (`llm/prompts.py`) say `{language}` and `{variety}`; structured outputs use `target` and `en`.

## Configuration

`LANGUAGES=es` in the backend environment lists the packs offered, first one the default. The learner picks
a variety (`dialect`, e.g. `es-419`); the server rejects varieties of packs that aren't enabled.

## Data

`lexemes`, `scenarios` and `utterances` carry a `lang` column, and every learner-facing query filters by the
learner's current language, so switching language later shows that language's words, scenes and progress.
Database column names from before language packs (`es`, `close_es`) are kept and mapped to neutral attribute
names (`target`, `close_target`) in `models.py`. New nullable or defaulted columns are added to existing
databases at startup (`db._add_missing_columns`); anything else needs an Alembic migration.

## Clients

Web (`web/js/language.js`) and iPhone (`IntuyeKit/Languages.swift`, read through `AppModel.lang` and `AppModel.variety`) fetch `GET /v1/languages` and cache it.
Screens use the pack's `name` in copy ("English in your Spanish"), its varieties for pickers, `tts` for the
voice and `stt` for speech recognition. No screen names a language or a variety.

## Adding a language

1. Copy `backend/app/languages/es/` to `backend/app/languages/<code>/` and replace the content: letters and
   marks, common words, G2P rules and sound tips, grammar triggers, lessons, backbone words, rescue phrases,
   varieties with their voices and recognition locales, prompt examples, and the `ui` copy.
2. Register it in `app/languages/__init__.py` (`ALL = {p.code: p for p in (SPANISH, FRENCH)}`).
3. Add the code to `LANGUAGES` (`LANGUAGES=es,fr`).
4. Run `tests/test_languages.py`: its toy French pack shows the minimum a pack needs.
5. Check the variety's voice and recognition locale exist on iOS (`AVSpeechSynthesisVoice`, `SFSpeechRecognizer`).

## Not yet language-neutral

* The learner's own language is English (`native_en.py`, the `en` fields, English UI copy). Supporting other first
  languages means turning `native_en` into a pack and localising the interface strings.
* The offline fake model used in tests speaks only Spanish (`dev_dictionary`).
* The lexeme unique key includes `lang` for new databases; databases created before keep `(user_id, es)` until
  a migration rebuilds it, which matters only once a learner studies two languages.
