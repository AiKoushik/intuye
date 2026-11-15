"""The learner's own language (English for now): words that mark a token in a mixed sentence as English.

When learners with other first languages are supported, this becomes a pack of its own like the target languages.
"""
from __future__ import annotations

NAME = "English"
HINT_WORDS = frozenset({
    "the", "a", "an", "of", "and", "is", "are", "was", "were", "be", "to", "in", "on", "at", "for", "with", "my", "your",
    "his", "her", "our", "their", "i", "you", "he", "she", "we", "they", "it", "this", "that", "these", "those", "what",
    "when", "where", "why", "how", "who", "do", "does", "did", "have", "has", "had", "will", "would", "can", "could",
    "should", "want", "like", "love", "hear", "hearing", "mind", "think", "know", "go", "going", "get", "just", "about",
    "from", "not", "but", "so", "if", "or", "because", "really", "very", "today", "tomorrow", "yesterday", "work",
    "brain", "tooth", "food", "say", "said", "mean", "means", "it's", "i'm", "don't",
})
SUFFIXES = ("ing", "tion", "ly", "ness", "'s")
