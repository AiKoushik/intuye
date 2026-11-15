import pytest

from app.curation.pronunciation import compare
from app.languages.es.phonemes import word_phonemes

pytestmark = pytest.mark.anyio


def test_spanish_g2p_follows_spelling_rules():
    assert word_phonemes("perro") == ["p", "e", "r", "o"] and word_phonemes("pero") == ["p", "e", "ɾ", "o"]
    assert word_phonemes("guitarra") == ["g", "i", "t", "a", "r", "a"] and word_phonemes("gente") == ["x", "e", "n", "t", "e"]
    assert word_phonemes("cena", "es-ES")[0] == "θ" and word_phonemes("cena")[0] == "s"
    assert word_phonemes("hola") == ["o", "l", "a"] and word_phonemes("llamo")[0] == "ʝ"


def test_compare_marks_the_missed_sounds_and_explains_one():
    r = compare("Más despacio, por favor", "mas despacio por favor", "es-419")
    assert r["score"] == 1.0 and r["ok"]
    r = compare("el perro", "el pero", "es-419")
    assert not r["words"][1]["ok"] and r["words"][1]["phonemes"][2] == {"p": "r", "ok": False, "heard": "ɾ"}
    assert any("rr" in t for t in r["tips"])


async def test_practice_endpoint_scores_a_drill_attempt(client, auth):
    r = (await client.post("/v1/practice/compare", json={"expected": "¿Puede repetirlo, por favor?", "heard": "puede repetirlo por favor"},
                           headers=auth)).json()
    assert r["ok"] and len(r["words"]) == 4
    miss = (await client.post("/v1/practice/compare", json={"expected": "Más despacio, por favor", "heard": "mas despacio"},
                              headers=auth)).json()
    assert not miss["ok"] and miss["words"][2]["heard"] is None
