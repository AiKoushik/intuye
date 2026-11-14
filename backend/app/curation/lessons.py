"""Sixty-second grammar lessons, one per trigger in grammar.py. Written by hand, not generated."""
from __future__ import annotations

import random

from app.curation.grammar import TRIGGERS

LESSONS = {
    "subjunctive_want": {
        "title": "Wanting someone else to do something",
        "pattern": "quiero que + subjunctive",
        "rule": "When you want someone else to do something, Spanish doesn't use an infinitive. Say quiero que, then the verb in the subjunctive.",
        "examples": [("I want you to come early.", "Quiero que vengas temprano."), ("She wants us to wait.", "Quiere que esperemos."),
                     ("I don't want him to worry.", "No quiero que se preocupe.")],
        "check": {"prompt": "I want you to call me.", "options": ["Quiero que me llames.", "Quiero llamarte.", "Quiero que me llamas."], "answer": 0},
    },
    "gustar": {
        "title": "Saying you like something",
        "pattern": "me gusta / me gustan / me encanta",
        "rule": "With gustar the thing you like is the subject: it pleases you. One thing takes gusta, several take gustan.",
        "examples": [("I like coffee.", "Me gusta el café."), ("I love these songs.", "Me encantan estas canciones."),
                     ("Do you like cooking?", "¿Te gusta cocinar?")],
        "check": {"prompt": "I like the tacos.", "options": ["Me gustan los tacos.", "Me gusta los tacos.", "Yo gusto los tacos."], "answer": 0},
    },
    "desde_hace": {
        "title": "How long something has been going on",
        "pattern": "present tense + desde hace + time",
        "rule": "For something that started in the past and is still going on, Spanish keeps the present tense and adds desde hace.",
        "examples": [("I've lived here for two years.", "Vivo aquí desde hace dos años."),
                     ("It's hurt for three days.", "Me duele desde hace tres días."), ("We've known each other for ages.", "Nos conocemos desde hace años.")],
        "check": {"prompt": "I've been studying Spanish for a month.", "options": ["Estudio español desde hace un mes.", "He estudiado español por un mes.", "Estudié español hace un mes."], "answer": 0},
    },
    "ir_a": {
        "title": "Talking about what you're going to do",
        "pattern": "ir a + infinitive",
        "rule": "For plans and the near future, use ir (voy, vas, va…) plus a, plus the verb as it appears in the dictionary.",
        "examples": [("I'm going to call the dentist.", "Voy a llamar al dentista."), ("We're going to eat out.", "Vamos a comer fuera."),
                     ("It's going to rain.", "Va a llover.")],
        "check": {"prompt": "I'm going to cook tonight.", "options": ["Voy a cocinar esta noche.", "Voy cocinar esta noche.", "Voy a cocino esta noche."], "answer": 0},
    },
    "hay": {
        "title": "There is, there are",
        "pattern": "hay / había",
        "rule": "Hay means both there is and there are; it never changes for plural. In the past, use había.",
        "examples": [("There's a pharmacy nearby.", "Hay una farmacia cerca."), ("There are two problems.", "Hay dos problemas."),
                     ("There was a lot of traffic.", "Había mucho tráfico.")],
        "check": {"prompt": "There are three people.", "options": ["Hay tres personas.", "Están tres personas.", "Hayan tres personas."], "answer": 0},
    },
    "tener_que": {
        "title": "Having to do something",
        "pattern": "tener que + infinitive",
        "rule": "For obligation, use tener (tengo, tienes…) plus que, plus the verb in the infinitive.",
        "examples": [("I have to work tomorrow.", "Tengo que trabajar mañana."), ("You have to see this.", "Tienes que ver esto."),
                     ("We had to wait an hour.", "Tuvimos que esperar una hora.")],
        "check": {"prompt": "I have to leave now.", "options": ["Tengo que irme ahora.", "Tengo irme ahora.", "Debo de irme ahora mismo que."], "answer": 0},
    },
    "si_imperfect": {
        "title": "If I were, if I had",
        "pattern": "si + imperfect subjunctive, then conditional",
        "rule": "For things that aren't true now, say si with the imperfect subjunctive (tuviera, fuera), then what would happen in the conditional.",
        "examples": [("If I had time, I'd travel more.", "Si tuviera tiempo, viajaría más."), ("If I were you, I'd ask.", "Si yo fuera tú, preguntaría."),
                     ("If I could, I'd stay.", "Si pudiera, me quedaría.")],
        "check": {"prompt": "If I had money, I would buy it.", "options": ["Si tuviera dinero, lo compraría.", "Si tengo dinero, lo compraría.", "Si tendría dinero, lo compraba."], "answer": 0},
    },
}

BY_ES = {t.es: t.id for t in TRIGGERS}


def lesson_id_for(es: str) -> str | None:
    return BY_ES.get(es)


def lesson(lesson_id: str) -> dict | None:
    data = LESSONS.get(lesson_id)
    if data is None:
        return None
    trig = next(t for t in TRIGGERS if t.id == lesson_id)
    # The right answer is written first; shuffle so it isn't always the top option.
    options = list(data["check"]["options"])
    right = options[data["check"]["answer"]]
    random.shuffle(options)
    return {"id": lesson_id, **data, "examples": [{"en": en, "es": es} for en, es in data["examples"]], "es": trig.es, "en": trig.en,
            "check": {"prompt": data["check"]["prompt"], "options": options, "answer": options.index(right)}}
