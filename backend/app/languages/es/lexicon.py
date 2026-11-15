"""High-frequency Spanish backbone, ordered roughly by frequency in speech (after Davies, A Frequency
Dictionary of Spanish, Routledge, 2006), plus survival phrases. (target, en). Rank = position + 1."""

BASE: tuple[tuple[str, str], ...] = (
    # survival phrases first: they buy time and confidence
    ("por favor", "please"), ("gracias", "thank you"), ("perdón", "sorry / excuse me"), ("no entiendo", "I don't understand"),
    ("¿puede repetir?", "can you repeat?"), ("más despacio", "more slowly"), ("¿cómo se dice...?", "how do you say...?"),
    ("de nada", "you're welcome"), ("lo siento", "I'm sorry"), ("¿qué tal?", "how's it going?"),
    # core verbs
    ("ser", "to be (permanent)"), ("estar", "to be (state, place)"), ("tener", "to have"), ("hacer", "to do / make"),
    ("poder", "to be able to"), ("decir", "to say"), ("ir", "to go"), ("ver", "to see"), ("dar", "to give"),
    ("saber", "to know (facts)"), ("querer", "to want"), ("llegar", "to arrive"), ("pasar", "to happen / pass"),
    ("deber", "to have to / owe"), ("poner", "to put"), ("parecer", "to seem"), ("quedar", "to stay / remain"),
    ("creer", "to believe"), ("hablar", "to speak"), ("llevar", "to carry / take"), ("dejar", "to leave / let"),
    ("seguir", "to follow / keep on"), ("encontrar", "to find"), ("llamar", "to call"), ("venir", "to come"),
    ("pensar", "to think"), ("salir", "to go out"), ("volver", "to return"), ("tomar", "to take / drink"),
    ("conocer", "to know (people, places)"), ("vivir", "to live"), ("sentir", "to feel"), ("mirar", "to look at"),
    ("contar", "to count / tell"), ("empezar", "to begin"), ("esperar", "to wait / hope"), ("buscar", "to look for"),
    ("entrar", "to enter"), ("trabajar", "to work"), ("escribir", "to write"), ("perder", "to lose"),
    ("entender", "to understand"), ("pedir", "to ask for / order"), ("recordar", "to remember"),
    ("terminar", "to finish"), ("necesitar", "to need"), ("leer", "to read"), ("cambiar", "to change"),
    ("abrir", "to open"), ("oír", "to hear"), ("traer", "to bring"), ("explicar", "to explain"),
    ("preguntar", "to ask"), ("estudiar", "to study"), ("pagar", "to pay"), ("ayudar", "to help"),
    ("gustar", "to be pleasing (to like)"), ("jugar", "to play"), ("escuchar", "to listen"), ("comer", "to eat"),
    ("beber", "to drink"), ("dormir", "to sleep"), ("comprar", "to buy"), ("usar", "to use"), ("aprender", "to learn"),
    # core nouns
    ("tiempo", "time / weather"), ("año", "year"), ("día", "day"), ("vez", "time (occasion)"), ("vida", "life"),
    ("parte", "part"), ("mundo", "world"), ("casa", "house / home"), ("momento", "moment"), ("forma", "way / shape"),
    ("persona", "person"), ("lugar", "place"), ("trabajo", "work / job"), ("noche", "night"), ("cosa", "thing"),
    ("ciudad", "city"), ("problema", "problem"), ("hora", "hour / time"), ("agua", "water"), ("mano", "hand"),
    ("nombre", "name"), ("semana", "week"), ("palabra", "word"), ("amigo", "friend"), ("familia", "family"),
    ("hijo", "son / child"), ("padre", "father"), ("madre", "mother"), ("niño", "child"), ("idea", "idea"),
    ("cabeza", "head"), ("puerta", "door"), ("dinero", "money"), ("comida", "food / meal"), ("mes", "month"),
    ("pregunta", "question"), ("respuesta", "answer"), ("verdad", "truth"), ("calle", "street"), ("mañana", "morning / tomorrow"),
    ("tarde", "afternoon / late"), ("país", "country"), ("gente", "people"), ("escuela", "school"), ("libro", "book"),
    ("coche", "car"), ("teléfono", "phone"), ("médico", "doctor"), ("tienda", "shop"), ("cuenta", "bill / account"),
    # adjectives & adverbs
    ("bueno", "good"), ("grande", "big"), ("nuevo", "new"), ("mismo", "same"), ("otro", "other"), ("mucho", "a lot"),
    ("poco", "a little"), ("mejor", "better / best"), ("primero", "first"), ("último", "last"), ("solo", "alone / only"),
    ("pequeño", "small"), ("importante", "important"), ("posible", "possible"), ("fácil", "easy"), ("difícil", "difficult"),
    ("ahora", "now"), ("siempre", "always"), ("nunca", "never"), ("también", "also"), ("después", "after / later"),
    ("antes", "before"), ("aquí", "here"), ("ya", "already"), ("todavía", "still / yet"), ("hoy", "today"),
    ("bien", "well"), ("mal", "badly"), ("muy", "very"), ("cerca", "near"), ("lejos", "far"), ("rápido", "fast"),
    ("despacio", "slowly"), ("listo", "ready / clever"), ("cansado", "tired"), ("contento", "happy"),
    # question words & connectors
    ("¿qué?", "what?"), ("¿cómo?", "how?"), ("¿dónde?", "where?"), ("¿cuándo?", "when?"), ("¿por qué?", "why?"),
    ("¿cuánto?", "how much?"), ("¿quién?", "who?"), ("porque", "because"), ("pero", "but"), ("entonces", "so / then"),
    ("aunque", "although"), ("si", "if"), ("cuando", "when"), ("mientras", "while"), ("sin embargo", "however"),
)
