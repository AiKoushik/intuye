"""Language packs: the app logic works for any pack, and the server says which languages it offers."""
import re

import pytest
from sqlalchemy import text

from app import languages
from app.agents.coach import route_input
from app.curation.grammar import matches
from app.curation.lessons import lesson
from app.curation.pronunciation import compare
from app.curation.text import english_share, normalize_entry
from app.db import Database
from app.languages import Lesson, LanguagePack, Trigger, Variety

pytestmark = pytest.mark.anyio

# A toy French pack, defined only here, to prove nothing in the logic assumes Spanish.
FR = LanguagePack(
    code="fr", name="French", native_name="Français",
    varieties=(Variety("fr-FR", "France", "standard French", tts="fr-FR", stt="fr-FR"),), default_variety="fr-FR",
    letters="a-zA-ZàâçéèêëîïôûùüÿœÀÂÇÉÈÊËÎÏÔÛÙÜŸŒ", marks=frozenset("àâçéèêëîïôûùüÿœ"),
    hint_words=frozenset({"le", "la", "les", "je", "tu", "est", "et", "mon", "dans", "aime", "bonjour"}),
    suffixes=("eux", "ment"), articles=("le", "la", "les", "un", "une"), stopwords=frozenset({"le", "la", "et"}),
    ask_in_target=re.compile(r"^\s*comment\s+dit-on\s+(.+?)\s*\??\s*$", re.I),
    phonemes=lambda word, variety: list(word.lower()), sound_tips={"r": "The French r is made at the back of the throat."},
    grammar=(Trigger("aimer", re.compile(r"\bi like\b", re.I), "j'aime + nom", "I like", "aimer takes a direct object"),),
    lessons={"aimer": Lesson("Saying you like something", "j'aime", "Use j'aime with the thing you like.",
                             (("I like coffee.", "J'aime le café."),), "I like tea.", ("J'aime le thé.", "Je aime le thé."))},
    base_lexicon=(("bonjour", "hello"),), rescue_phrases=(("Slower, please", "Plus lentement, s'il vous plaît"),),
)


def test_logic_runs_on_any_pack():
    assert english_share("j'aime le café", FR) < 0.35 and english_share("I love my dog", FR) == 1.0
    assert route_input("comment dit-on tooth?", "auto", FR) == ("to_target", "tooth")
    assert route_input("bonjour je suis dans le train", "auto", FR)[0] == "to_native"
    assert normalize_entry("Le café!", FR) == "café"
    assert [t.id for t in matches("I like this song", FR)] == ["aimer"]
    assert lesson("aimer", FR)["examples"][0]["target"] == "J'aime le café."


def test_pronunciation_is_scored_by_the_learners_pack(monkeypatch):
    monkeypatch.setitem(languages.ALL, "fr", FR)
    r = compare("rare", "rale", "fr-FR")
    assert not r["ok"] and r["tips"] == ["The French r is made at the back of the throat."]


async def test_languages_endpoint_and_variety_check(client, auth):
    body = (await client.get("/v1/languages", headers=auth)).json()
    es = body["languages"][0]
    assert body["default"] == "es" and es["name"] == "Spanish" and {v["code"] for v in es["varieties"]} == {"es-419", "es-MX", "es-ES"}
    assert (await client.patch("/v1/me/settings", json={"dialect": "fr-FR"}, headers=auth)).status_code == 422
    assert (await client.patch("/v1/me/settings", json={"dialect": "es-ES"}, headers=auth)).json()["dialect"] == "es-ES"


async def test_words_are_tagged_with_their_language(client, auth, app):
    await client.post("/v1/coach", json={"text": "my mind is tired"}, headers=auth)
    async with app.state.db.engine.connect() as conn:
        langs = {r[0] for r in await conn.execute(text("SELECT lang FROM lexemes"))}
    assert langs == {"es"}


async def test_existing_databases_get_new_columns(tmp_path):
    db = Database(f"sqlite+aiosqlite:///{tmp_path}/old.db")
    async with db.engine.begin() as conn:  # a lexemes table from before language packs
        await conn.execute(text("CREATE TABLE lexemes (id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36), es VARCHAR(120), "
                                "en VARCHAR(120), origin VARCHAR(16), topic VARCHAR(64), context TEXT, first_seen_at DATETIME)"))
        await conn.execute(text("INSERT INTO lexemes (id, user_id, es, en, origin) VALUES ('x', 'u', 'mente', 'mind', 'spoken')"))
    await db.create_all()
    async with db.engine.connect() as conn:
        assert (await conn.execute(text("SELECT lang FROM lexemes WHERE id = 'x'"))).scalar_one() == "es"
    await db.dispose()
