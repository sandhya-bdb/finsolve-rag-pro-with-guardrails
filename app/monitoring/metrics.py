"""
metrics.py - Query performance metrics collection.
Tracks latency, token usage, cost, cache hits, and guardrail events.
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass

MODEL_COST_PER_1K: dict[str, float] = {
    "llama3-8b-8192": 0.00005,
    "llama3-70b-8192": 0.00079,
    "mixtral-8x7b-32768": 0.00027,
    "llama3.2:1b": 0.0,
    "llama3.2": 0.0,
    "mistral": 0.0,
    "gpt-3.5-turbo": 0.0015,
    "gpt-4o-mini": 0.00015,
    "gpt-4o": 0.005,
    "claude-3-haiku": 0.00025,
    "claude-3-sonnet": 0.003,
    "claude-3-opus": 0.015,
}

AVG_TOKENS_PER_WORD = 1.3


@dataclass
class QueryMetrics:
    model_used: str = "llama3-70b-8192"
    complexity: str = "moderate"
    latency_ms: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    cache_hit: bool = False
    guardrail_triggered: bool = False
    guardrail_reason: str = ""


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text.split()) * AVG_TOKENS_PER_WORD))


def calculate_cost(tokens: int, model: str) -> float:
    rate = MODEL_COST_PER_1K.get(model, 0.0)
    return round((tokens / 1000) * rate, 6)


@contextmanager
def timer():
    start = time.perf_counter()
    result = {"ms": 0.0}
    try:
        yield result
    finally:
        result["ms"] = round((time.perf_counter() - start) * 1000, 2)
