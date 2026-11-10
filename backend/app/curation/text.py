"""Cheap, deterministic text helpers: tokenising, language guessing per token, normalising lexemes."""
from __future__ import annotations

import re
import unicodedata

TOKEN = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ']+")

SPANISH_HINTS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "que", "y", "en", "es", "son", "está", "esta",
    "este", "esto", "eso", "ese", "mi", "mis", "tu", "tus", "su", "sus", "me", "te", "se", "nos", "le", "les", "lo",
    "por", "para", "con", "sin", "pero", "muy", "más", "como", "cómo", "qué", "quién", "cuando", "cuándo", "donde",
    "dónde", "yo", "tú", "usted", "él", "ella", "nosotros", "ellos", "hola", "gracias", "bueno", "buenos", "buenas",
    "días", "noches", "tardes", "sí", "no", "va", "voy", "vas", "estoy", "tengo", "tiene", "quiero", "puedo", "gusta",
    "gusto", "hay", "hace", "hacer", "ser", "estar", "ir", "pues", "también", "ahora", "hoy", "mañana", "ayer", "aquí",
    "allí", "mucho", "poco", "todo", "nada", "algo", "porque", "pero", "entonces", "vale", "claro", "escuchar", "hablar",
    "comer", "duele", "desde", "cosa", "cosas", "casa", "trabajo", "amigo", "amiga",
}
ENGLISH_HINTS = {
    "the", "a", "an", "of", "and", "is", "are", "was", "were", "be", "to", "in", "on", "at", "for", "with", "my", "your",
    "his", "her", "our", "their", "i", "you", "he", "she", "we", "they", "it", "this", "that", "these", "those", "what",
    "when", "where", "why", "how", "who", "do", "does", "did", "have", "has", "had", "will", "would", "can", "could",
    "should", "want", "like", "love", "hear", "hearing", "mind", "think", "know", "go", "going", "get", "just", "about",
    "from", "not", "but", "so", "if", "or", "because", "really", "very", "today", "tomorrow", "yesterday", "work",
    "brain", "tooth", "food", "say", "said", "mean", "means", "it's", "i'm", "don't",
}
SPANISH_CHARS = set("áéíóúüñ¿¡")


def tokens(text: str) -> list[str]:
    return [t.lower() for t in TOKEN.findall(text)]


def is_spanish_token(tok: str) -> bool | None:
    """True/False when confident, None when unknown."""
    t = tok.lower()
    if any(c in SPANISH_CHARS for c in t):
        return True
    in_es, in_en = t in SPANISH_HINTS, t in ENGLISH_HINTS
    if in_es and not in_en:
        return True
    if in_en and not in_es:
        return False
    if t.endswith(("ción", "mente", "dad", "ito", "ita", "aba", "ando", "iendo")):
        return True
    if t.endswith(("ing", "tion", "ly", "ness", "'s")):
        return False
    return None


def english_share(text: str) -> float:
    """Share of tokens we can classify that look English (0 = all Spanish, 1 = all English)."""
    votes = [is_spanish_token(t) for t in tokens(text)]
    known = [v for v in votes if v is not None]
    if not known:
        return 1.0
    return round(sum(1 for v in known if v is False) / len(known), 3)


def looks_spanish(text: str) -> bool:
    if any(c in SPANISH_CHARS for c in text):
        return True
    return english_share(text) < 0.35


def normalize_es(phrase: str) -> str:
    p = phrase.strip().lower()
    p = re.sub(r"^[¿¡\"'(]+|[?!.,;:\"')]+$", "", p)
    p = re.sub(r"^(el|la|los|las|un|una)\s+", "", p)
    return re.sub(r"\s+", " ", p)[:120]


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
