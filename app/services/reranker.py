"""
reranker.py — Cross-Encoder Reranking for FinSolve RAG Pro

After ChromaDB returns an over-retrieved candidate set, the cross-encoder
scores each (query, chunk) pair jointly and re-orders them by relevance.
Only the top_k highest-scoring chunks are forwarded to the LLM, dramatically
improving context quality over pure vector-similarity retrieval.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
  - ~80 MB on disk, CPU-friendly, < 100ms on M1/M2
  - Trained on MS-MARCO passage ranking — strong general relevance signal

Usage
-----
    from services.reranker import rerank

    candidates = vectordb.similarity_search(query, k=8)
    top_docs   = rerank(query, candidates, top_k=4)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger("finsolve.reranker")

# ─────────────────────────────────────────────
# Lazy-load the cross-encoder to avoid slowing
# down server startup; model is cached after
# the first call.
# ─────────────────────────────────────────────
_cross_encoder = None
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _get_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder
            _cross_encoder = CrossEncoder(RERANKER_MODEL)
            logger.info(f"Reranker loaded: {RERANKER_MODEL}")
        except Exception as exc:
            logger.error(f"Failed to load cross-encoder: {exc}")
            _cross_encoder = None
    return _cross_encoder


def rerank(query: str, docs: list, top_k: int = 4) -> list:
    """
    Re-order `docs` by cross-encoder relevance to `query`.

    Parameters
    ----------
    query   : The user's (or HyDE-generated) query string.
    docs    : List of LangChain Document objects from ChromaDB.
    top_k   : How many top documents to return after reranking.

    Returns
    -------
    Top-`top_k` Documents ordered by descending relevance score.
    Falls back to original order if the model fails to load.
    """
    if not docs:
        return docs

    encoder = _get_encoder()
    if encoder is None:
        logger.warning("Cross-encoder unavailable — skipping rerank, returning original order")
        return docs[:top_k]

    # Build (query, passage) pairs for batch scoring
    pairs = [(query, doc.page_content) for doc in docs]

    try:
        scores = encoder.predict(pairs)
    except Exception as exc:
        logger.error(f"Reranker predict error: {exc}")
        return docs[:top_k]

    # Attach scores and sort descending
    scored = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)

    top_docs = [doc for _, doc in scored[:top_k]]

    logger.info(
        f"Reranker: {len(docs)} candidates → top {len(top_docs)} | "
        f"best_score={scored[0][0]:.3f} worst_kept={scored[min(top_k-1, len(scored)-1)][0]:.3f}"
    )
    return top_docs


def rerank_with_scores(query: str, docs: list, top_k: int = 4) -> list[tuple[float, object]]:
    """
    Same as `rerank` but returns (score, Document) tuples.
    Useful for debugging / monitoring.
    """
    if not docs:
        return []

    encoder = _get_encoder()
    if encoder is None:
        return [(0.0, doc) for doc in docs[:top_k]]

    pairs = [(query, doc.page_content) for doc in docs]
    try:
        scores = encoder.predict(pairs)
    except Exception as exc:
        logger.error(f"Reranker predict error: {exc}")
        return [(0.0, doc) for doc in docs[:top_k]]

    scored = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    return scored[:top_k]
