"""
hyde_retriever.py - Provider-aware HyDE generation.

HyDE improves retrieval recall by generating a short hypothetical passage that
resembles the kind of internal document chunk we want the vector store to find.
The same provider choice used for final answering can also be used for HyDE.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from services.llm_provider import generate_text, get_active_provider

logger = logging.getLogger("finsolve.hyde")
HYDE_TIMEOUT = 15

HYDE_DEFAULT_MODELS = {
    "groq": "llama3-8b-8192",
    "ollama": "llama3.2:1b",
}

HYDE_PROMPT_TEMPLATE = """\
You are a document expert. Write a concise, factual passage (2-4 sentences) \
that would directly answer the following question. \
Use professional, domain-specific language as if it came from an internal company document.

Question: {query}

Passage:"""


def get_hyde_model(provider: Optional[str] = None) -> str:
    active_provider = get_active_provider(provider)
    configured = os.environ.get("HYDE_MODEL", "").strip()
    if configured:
        return configured
    return HYDE_DEFAULT_MODELS[active_provider]


def generate_hypothesis(
    query: str,
    provider: Optional[str] = None,
    model: str = "",
    timeout: int = HYDE_TIMEOUT,
) -> str:
    """Generate a hypothetical passage or fall back to the original query."""
    active_provider = get_active_provider(provider)
    resolved_model = model or get_hyde_model(active_provider)
    prompt = HYDE_PROMPT_TEMPLATE.format(query=query)

    try:
        hypothesis = generate_text(
            prompt=prompt,
            model=resolved_model,
            provider=active_provider,
            temperature=0.4,
            max_tokens=120,
            timeout=timeout,
        ).strip()
        if hypothesis:
            logger.info(
                "HyDE generated hypothesis (%s chars) using provider=%s model=%s",
                len(hypothesis),
                active_provider,
                resolved_model,
            )
            return hypothesis
        logger.warning("HyDE returned an empty response for provider=%s - falling back", active_provider)
        return query
    except Exception as exc:
        logger.warning("HyDE provider error (%s) - falling back to original query", exc)
        return query
