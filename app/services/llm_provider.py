"""
llm_provider.py - Unified text generation helpers for Groq and Ollama.

Groq is the default because it makes the project easier to run in CI and
simpler to publish on GitHub. Ollama remains available as an optional local
backend for offline or low-cost development.
"""

from __future__ import annotations

import os
from typing import Optional

import requests

VALID_PROVIDERS = {"groq", "ollama"}
DEFAULT_PROVIDER = "groq"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


def get_active_provider(provider: Optional[str] = None) -> str:
    """Return the configured LLM provider, validating supported values."""
    resolved = (provider or os.environ.get("LLM_PROVIDER", DEFAULT_PROVIDER)).strip().lower()
    if resolved not in VALID_PROVIDERS:
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{resolved}'. Expected one of: {', '.join(sorted(VALID_PROVIDERS))}."
        )
    return resolved


def get_ollama_base_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")


def get_provider_health() -> dict:
    """Expose non-secret provider configuration details for /health."""
    provider = get_active_provider()
    return {
        "provider": provider,
        "groq_key_configured": bool(os.environ.get("GROQ_API_KEY", "")),
        "ollama_base_url": get_ollama_base_url(),
    }


def _generate_with_groq(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> str:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to your environment or switch LLM_PROVIDER to ollama.")

    try:
        from langchain_core.messages import HumanMessage
        from langchain_groq import ChatGroq
    except Exception as exc:
        raise RuntimeError(f"Groq dependencies are unavailable: {exc}") from exc

    llm = ChatGroq(
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    text = (response.content or "").strip()
    if not text:
        raise RuntimeError("Groq returned an empty response.")
    return text


def _generate_with_ollama(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> str:
    response = requests.post(
        f"{get_ollama_base_url()}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    text = (data.get("response") or "").strip()
    if not text:
        raise RuntimeError("Ollama returned an empty response.")
    return text


def generate_text(
    prompt: str,
    model: str,
    provider: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    timeout: int = 60,
) -> str:
    """Generate text using the configured Groq or Ollama backend."""
    active_provider = get_active_provider(provider)
    if active_provider == "groq":
        return _generate_with_groq(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    return _generate_with_ollama(
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
