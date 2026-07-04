"""VectorStore — sqlite-vec KNN over past WORKING drivers, for few-shot
retrieval into AuthorDeps.few_shot. Day-2 nicety; the skeleton's job is the
degrade contract: construction NEVER raises, and without the sqlite-vec
extension the store runs in disabled mode (add() drops, knn() returns []).

Embeddings are taken PRECOMPUTED — the embedding provider is out of scope
here (and must stay out: memory/ does no model calls, ever).
"""

from pathlib import Path
from typing import Any


class VectorStore:
    """KNN store over driver-code embeddings; disabled-mode capable."""

    def __init__(self, path: str | Path, dim: int = 768) -> None:
        self._path = Path(path)
        self._dim = dim
        self._conn: Any = None
        try:
            import sqlite_vec  # noqa: F401 — optional extra [vec]

            self._enabled = True
        except ImportError:
            self._enabled = False  # honest disabled mode — never raises

    @property
    def enabled(self) -> bool:
        return self._enabled

    def ensure_schema(self) -> None:
        """Build-day job: open sqlite, sqlite_vec.load(conn), then
        CREATE VIRTUAL TABLE IF NOT EXISTS drivers_vec USING vec0(embedding float[dim])
        plus a rowid-joined plain table for (slug, code, protocol_class).
        No-op in disabled mode."""
        if not self._enabled:
            return
        raise NotImplementedError("build day: sqlite_vec.load + vec0 virtual table")

    def add(self, slug: str, code: str, protocol_class: str, embedding: list[float]) -> None:
        """Build-day job: INSERT into both tables (serialize with
        sqlite_vec.serialize_float32). Drops silently in disabled mode."""
        if not self._enabled:
            return
        raise NotImplementedError("build day: insert row + embedding")

    def knn(self, embedding: list[float], k: int = 3) -> list[dict[str, Any]]:
        """Build-day job: MATCH + ORDER BY distance + LIMIT k (vec0 requires
        the k bound). Returns [] in disabled mode."""
        if not self._enabled:
            return []
        raise NotImplementedError("build day: vec0 knn query")
