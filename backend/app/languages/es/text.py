"""Spanish words and marks used to tell Spanish from English inside a mixed (Spanglish) sentence."""
from __future__ import annotations

import re

LETTERS = "a-zA-ZáéíóúüñÁÉÍÓÚÜÑ"
MARKS = frozenset("áéíóúüñ¿¡")
HINT_WORDS = frozenset({
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "que", "y", "en", "es", "son", "está", "esta",
    "este", "esto", "eso", "ese", "mi", "mis", "tu", "tus", "su", "sus", "me", "te", "se", "nos", "le", "les", "lo",
    "por", "para", "con", "sin", "pero", "muy", "más", "como", "cómo", "qué", "quién", "cuando", "cuándo", "donde",
    "dónde", "yo", "tú", "usted", "él", "ella", "nosotros", "ellos", "hola", "gracias", "bueno", "buenos", "buenas",
    "días", "noches", "tardes", "sí", "no", "va", "voy", "vas", "estoy", "tengo", "tiene", "quiero", "puedo", "gusta",
    "gusto", "hay", "hace", "hacer", "ser", "estar", "ir", "pues", "también", "ahora", "hoy", "mañana", "ayer", "aquí",
    "allí", "mucho", "poco", "todo", "nada", "algo", "porque", "entonces", "vale", "claro", "escuchar", "hablar",
    "comer", "duele", "desde", "cosa", "cosas", "casa", "trabajo", "amigo", "amiga",
})
SUFFIXES = ("ción", "mente", "dad", "ito", "ita", "aba", "ando", "iendo")
ARTICLES = ("el", "la", "los", "las", "un", "una")
STOPWORDS = frozenset({"el", "la", "los", "las", "un", "una", "de", "y", "a", "en", "que", "yo", "mi", "me", "te", "se", "lo", "es"})

# "¿Cómo se dice X?" asked in Spanish.
ASK_IN_TARGET = re.compile(r"^\s*¿?\s*c[oó]mo\s+se\s+dice\s+[\"“']?(.+?)[\"”']?\s*\??\s*$", re.I)
