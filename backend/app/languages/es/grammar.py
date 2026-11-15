"""Spanish grammar triggers: patterns in the learner's English that call for a Spanish micro-lesson."""
from __future__ import annotations

import re

from app.languages.base import Trigger

TRIGGERS = (
    Trigger("subjunctive_want", re.compile(r"\b(i want|quiero) (that )?(you|him|her|them|que)\b", re.I),
            "quiero que + subjuntivo", "I want (someone) to…", "Wanting someone else to do something uses que + subjunctive"),
    Trigger("gustar", re.compile(r"\bi (really )?(like|love)\b", re.I),
            "me gusta / me encanta", "I like / I love", "In Spanish the thing is the subject: it pleases me"),
    Trigger("desde_hace", re.compile(r"\b(for|since) (\d+|a|an|two|three|few|several) (minute|hour|day|week|month|year)s?\b", re.I),
            "desde hace + tiempo", "for (a length of time)", "Ongoing for a while: present tense + desde hace"),
    Trigger("ir_a", re.compile(r"\b(i'?m|we'?re|i am|we are) (going to|gonna)\b", re.I),
            "voy a + infinitivo", "I'm going to…", "Near future: ir a + infinitive"),
    Trigger("hay", re.compile(r"\bthere (is|are|was|were)\b", re.I), "hay / había", "there is / there was",
            "One word, singular or plural: hay"),
    Trigger("tener_que", re.compile(r"\b(i|we|you) (have|had|has) to\b", re.I), "tener que + infinitivo", "to have to…",
            "Obligation: tener que + infinitive"),
    Trigger("si_imperfect", re.compile(r"\bif i (were|had|could)\b", re.I), "si + imperfecto de subjuntivo", "if I were / had…",
            "Hypotheticals: si tuviera…, sería…"),
)
