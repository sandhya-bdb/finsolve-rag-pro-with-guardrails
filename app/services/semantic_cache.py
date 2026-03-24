"""
semantic_cache.py — Embedding-based semantic cache with TTL.

Avoids redundant LLM + retrieval calls for semantically similar queries.

How it works
────────────
1. On each new query, compute its embedding.
2. Compare against existing cached embeddings using cosine similarity.
3. If similarity ≥ threshold (default 0.95) AND within TTL → return cached response.
4. Otherwise, call the full RAG pipeline and cache the result.

 Cost impact: In practice, 30–50% of enterprise queries are near-duplicates
 (e.g., "What is the leave policy?" vs "Tell me about leave policy").
"""

import time
import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CacheEntry:
    query: str
    embedding: list[float]
    response: str
    sources: list[str]
    model_used: str
    role: str  # The owner role of this cached response
    created_at: float = field(default_factory=time.time)
    hits: int = 0


class SemanticCache:
    """
    In-memory semantic cache.

    Parameters
    ----------
    ttl_seconds : int
        Time-to-live per cached entry (default: 3600 = 1 hour).
    similarity_threshold : float
        Minimum cosine similarity to consider a cache hit (default: 0.95).
    max_size : int
        Maximum number of entries to keep (LRU eviction, default: 500).
    """

    def __init__(
        self,
        ttl_seconds: int = 3600,
        similarity_threshold: float = 0.95,
        max_size: int = 500,
    ):
        self.ttl = ttl_seconds
        self.threshold = similarity_threshold
        self.max_size = max_size
        self._cache: list[CacheEntry] = []

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────

    def get(self, query: str, embedding: list[float], current_role: str) -> Optional[CacheEntry]:
        """
        Look up a semantically similar cached response.
        Returns the CacheEntry if found AND current_role has access to original role's data.
        """
        from services.rbac import can_access
        self._evict_expired()
        best_sim = 0.0
        best_entry: Optional[CacheEntry] = None

        for entry in self._cache:
            sim = self._cosine_similarity(embedding, entry.embedding)
            if sim > best_sim:
                best_sim = sim
                best_entry = entry

        if best_sim >= self.threshold and best_entry is not None:
            # RBAC check: Only return hit if current user is at least as privileged as the cache owner
            if can_access(current_role, best_entry.role):
                best_entry.hits += 1
                return best_entry

        return None

    def put(
        self,
        query: str,
        embedding: list[float],
        response: str,
        sources: list[str],
        model_used: str,
        role: str,
    ) -> None:
        """Store a new response in the cache."""
        if len(self._cache) >= self.max_size:
            # Evict the oldest entry
            self._cache.sort(key=lambda e: e.created_at)
            self._cache.pop(0)

        self._cache.append(
            CacheEntry(
                query=query,
                embedding=embedding,
                response=response,
                sources=sources,
                model_used=model_used,
                role=role,
            )
        )

    def invalidate(self) -> None:
        """Clear the entire cache (e.g., after re-ingestion)."""
        self._cache.clear()

    def stats(self) -> dict:
        """Return cache statistics."""
        total_hits = sum(e.hits for e in self._cache)
        return {
            "entries": len(self._cache),
            "total_hits": total_hits,
            "ttl_seconds": self.ttl,
            "threshold": self.threshold,
        }

    # ─────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────

    def _evict_expired(self) -> None:
        now = time.time()
        self._cache = [e for e in self._cache if (now - e.created_at) < self.ttl]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(y * y for y in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)


# Singleton instance (shared across the app)
semantic_cache = SemanticCache(ttl_seconds=3600, similarity_threshold=0.95)
