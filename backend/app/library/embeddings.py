"""Embedding models for the scene library. Vectors are always returned unit-length."""
from __future__ import annotations

import hashlib
import re
from typing import Protocol

import numpy as np

from app.config import Settings
from app.curation.text import fold

STOP = {
    "a", "an", "the", "at", "to", "in", "on", "for", "of", "with", "from", "my", "your", "his", "her", "our", "their",
    "i", "me", "we", "you", "going", "go", "get", "getting", "have", "has", "is", "am", "are", "be", "and", "or",
    "some", "about", "this", "that", "el", "la", "los", "las", "un", "una", "de", "del", "en", "con", "mi", "al", "y",
    "o", "para", "por", "ir", "voy",
}
WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


class Embedder(Protocol):
    model_id: str

    async def embed(self, texts: list[str]) -> np.ndarray: ...


def _unit(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    return (m / np.where(norms == 0, 1, norms)).astype(np.float32)


def content_words(text: str) -> list[str]:
    out = []
    for w in WORD.findall(fold(text)):
        w = re.sub(r"'s$", "", w)
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        if w and w not in STOP:
            out.append(w)
    return out


class HashEmbedder:
    """Deterministic hashed word, word-pair and character 4-gram features. Offline and keyword-like:
    good for tests and dev, but it can't tell that 'dentist' and 'toothache' are related."""

    model_id = "hash-v1"

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    def _features(self, text: str) -> dict[str, float]:
        words = content_words(text)
        feats: dict[str, float] = {}
        for w in words:
            feats[f"w:{w}"] = feats.get(f"w:{w}", 0) + 1.0
            grams = [f"#{w}#"[i:i + 4] for i in range(max(1, len(w) - 1))]
            for g in grams:
                feats[f"c:{g}"] = feats.get(f"c:{g}", 0) + 0.3 / len(grams)
        for a, b in zip(words, words[1:]):
            feats[f"b:{a}_{b}"] = feats.get(f"b:{a}_{b}", 0) + 0.5
        return feats

    async def embed(self, texts: list[str]) -> np.ndarray:
        m = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for f, w in self._features(t).items():
                h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), "big")
                m[i, h % self.dim] += w if (h >> 63) & 1 else -w
        return _unit(m)


class OpenAICompatibleEmbedder:
    """`/v1/embeddings` on any OpenAI-style server (Ollama, vLLM, Hearth). bge-m3 is multilingual, so a
    Spanglish query lands near an English scene title."""

    def __init__(self, settings: Settings) -> None:
        from langchain_openai import OpenAIEmbeddings

        self.model_id = f"oa:{settings.embed_model}"
        self._emb = OpenAIEmbeddings(model=settings.embed_model, base_url=settings.embed_base_url or settings.llm_base_url,
                                     api_key=settings.llm_api_key, check_embedding_ctx_length=False)

    async def embed(self, texts: list[str]) -> np.ndarray:
        return _unit(np.asarray(await self._emb.aembed_documents(texts), dtype=np.float32))


def build_embedder(settings: Settings) -> Embedder:
    return OpenAICompatibleEmbedder(settings) if settings.embed_provider == "openai_compatible" else HashEmbedder()
