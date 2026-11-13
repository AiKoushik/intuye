"""In-process vector index over published library scenes, one shard per Spanish variety.

Cosine similarity on unit vectors is a dot product, so a shard is one NumPy matrix. A shard reloads
when the published row count for its variety changes (another worker added or hid a scene). Rows
embedded by a different model are re-embedded on load. Comfortable to ~50k scenes per variety;
beyond that, move to pgvector with an HNSW index.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.embeddings import Embedder
from app.models import SceneTemplate


def card_text(title: str, situation: str) -> str:
    return f"{title}. {situation}"


@dataclass
class _Shard:
    count: int
    ids: list[str] = field(default_factory=list)
    matrix: np.ndarray | None = None


class LibraryIndex:
    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder
        self._shards: dict[str, _Shard] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def embed(self, text: str) -> np.ndarray:
        return (await self.embedder.embed([text]))[0]

    async def _published_count(self, db: AsyncSession, dialect: str) -> int:
        return (await db.execute(select(func.count()).select_from(SceneTemplate)
                                 .where(SceneTemplate.dialect == dialect, SceneTemplate.status == "published"))).scalar_one()

    async def _shard(self, db: AsyncSession, dialect: str) -> _Shard:
        count = await self._published_count(db, dialect)
        shard = self._shards.get(dialect)
        if shard is not None and shard.count == count:
            return shard
        async with self._locks.setdefault(dialect, asyncio.Lock()):
            rows = list((await db.execute(select(SceneTemplate).where(SceneTemplate.dialect == dialect,
                                                                      SceneTemplate.status == "published"))).scalars())
            stale = [r for r in rows if r.embed_model != self.embedder.model_id]
            if stale:
                vecs = await self.embedder.embed([card_text(r.title, r.situation) for r in stale])
                for r, v in zip(stale, vecs):
                    r.embedding, r.embed_model = v.tolist(), self.embedder.model_id
                await db.commit()
            matrix = np.asarray([r.embedding for r in rows], dtype=np.float32) if rows else None
            shard = _Shard(count=len(rows), ids=[r.id for r in rows], matrix=matrix)
            self._shards[dialect] = shard
            return shard

    async def nearest(self, db: AsyncSession, dialect: str, vector: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
        shard = await self._shard(db, dialect)
        if shard.matrix is None:
            return []
        sims = shard.matrix @ vector
        top = np.argsort(-sims)[:k]
        return [(shard.ids[i], float(sims[i])) for i in top]
