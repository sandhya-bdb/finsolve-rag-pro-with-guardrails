"""
model_router.py - Query complexity routing with provider-aware model selection.

The app can run against either:
- Groq: API-hosted models, best for cloud demos and GitHub publishing.
- Ollama: local models, best for offline development.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum

from services.llm_provider import get_active_provider


class QueryComplexity(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


@dataclass
class ModelConfig:
    model_name: str
    complexity: QueryComplexity
    rationale: str
    provider: str
    cost_per_1k_tokens: float = 0.0


GROQ_DEFAULT_MODELS = {
    QueryComplexity.SIMPLE: "llama-3.1-8b-instant",
    QueryComplexity.MODERATE: "llama-3.3-70b-versatile",
    QueryComplexity.COMPLEX: "llama-3.3-70b-versatile",
}

OLLAMA_DEFAULT_MODELS = {
    QueryComplexity.SIMPLE: "llama3.2:1b",
    QueryComplexity.MODERATE: "llama3.2",
    QueryComplexity.COMPLEX: "mistral",
}

PROVIDER_COSTS = {
    "groq": {
        QueryComplexity.SIMPLE: 0.00005,
        QueryComplexity.MODERATE: 0.00079,
        QueryComplexity.COMPLEX: 0.00027,
    },
    "ollama": {
        QueryComplexity.SIMPLE: 0.0,
        QueryComplexity.MODERATE: 0.0,
        QueryComplexity.COMPLEX: 0.0,
    },
}

COMPLEX_KEYWORDS: list[str] = [
    "compare", "contrast", "analyze", "analyse", "explain why", "reason",
    "calculate", "forecast", "predict", "evaluate", "assess", "strategy",
    "recommend", "justify", "pros and cons", "trade-off", "risk", "impact",
    "difference between", "how does", "why did", "what caused",
    "break down", "deep dive", "comprehensive", "step by step",
]

SIMPLE_KEYWORDS: list[str] = [
    "what is", "who is", "when is", "where is", "define", "list",
    "name", "tell me", "show me", "give me the", "what are the",
]

POWER_ROLES: set[str] = {"c-levelexecutives"}


def classify_complexity(query: str, role: str = "employee") -> QueryComplexity:
    """Determine query complexity based on role, length, and keyword signals."""
    if role.lower().strip() in POWER_ROLES:
        return QueryComplexity.COMPLEX

    q_lower = query.lower().strip()
    word_count = len(q_lower.split())

    for kw in COMPLEX_KEYWORDS:
        if kw in q_lower:
            return QueryComplexity.COMPLEX

    if word_count <= 8:
        return QueryComplexity.SIMPLE

    for kw in SIMPLE_KEYWORDS:
        if q_lower.startswith(kw) and word_count <= 20:
            return QueryComplexity.SIMPLE

    if word_count > 40:
        return QueryComplexity.MODERATE

    if query.count("?") > 1 or q_lower.count(" and ") >= 2:
        return QueryComplexity.MODERATE

    return QueryComplexity.MODERATE


def _default_model_for(provider: str, complexity: QueryComplexity) -> str:
    table = GROQ_DEFAULT_MODELS if provider == "groq" else OLLAMA_DEFAULT_MODELS
    return table[complexity]


def _configured_model_for(provider: str, complexity: QueryComplexity) -> str:
    env_name = {
        QueryComplexity.SIMPLE: "MODEL_SIMPLE",
        QueryComplexity.MODERATE: "MODEL_MODERATE",
        QueryComplexity.COMPLEX: "MODEL_COMPLEX",
    }[complexity]
    configured = os.environ.get(env_name, "").strip()
    if configured:
        return configured
    return _default_model_for(provider, complexity)


def build_routing_table(provider: str | None = None) -> dict[QueryComplexity, ModelConfig]:
    active_provider = get_active_provider(provider)
    provider_label = "Groq" if active_provider == "groq" else "Ollama"

    return {
        QueryComplexity.SIMPLE: ModelConfig(
            model_name=_configured_model_for(active_provider, QueryComplexity.SIMPLE),
            complexity=QueryComplexity.SIMPLE,
            rationale=f"Short factual query - routed to the fast {provider_label} model.",
            provider=active_provider,
            cost_per_1k_tokens=PROVIDER_COSTS[active_provider][QueryComplexity.SIMPLE],
        ),
        QueryComplexity.MODERATE: ModelConfig(
            model_name=_configured_model_for(active_provider, QueryComplexity.MODERATE),
            complexity=QueryComplexity.MODERATE,
            rationale=f"Standard analytical query - routed to the balanced {provider_label} model.",
            provider=active_provider,
            cost_per_1k_tokens=PROVIDER_COSTS[active_provider][QueryComplexity.MODERATE],
        ),
        QueryComplexity.COMPLEX: ModelConfig(
            model_name=_configured_model_for(active_provider, QueryComplexity.COMPLEX),
            complexity=QueryComplexity.COMPLEX,
            rationale=f"Complex reasoning query - routed to the strongest {provider_label} model.",
            provider=active_provider,
            cost_per_1k_tokens=PROVIDER_COSTS[active_provider][QueryComplexity.COMPLEX],
        ),
    }


def route_query(query: str, role: str = "employee", provider: str | None = None) -> ModelConfig:
    """Classify the query and return a provider-aware ModelConfig."""
    complexity = classify_complexity(query, role)
    routing_table = build_routing_table(provider)
    return routing_table[complexity]
