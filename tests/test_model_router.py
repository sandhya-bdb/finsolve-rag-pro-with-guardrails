"""test_model_router.py - Unit tests for provider-aware model routing logic."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from services.model_router import QueryComplexity, classify_complexity, route_query


class TestModelRouter:
    def test_short_query_is_simple(self):
        complexity = classify_complexity("What is leave?", "employee")
        assert complexity == QueryComplexity.SIMPLE

    def test_clevel_always_gets_complex(self):
        complexity = classify_complexity("What is the leave balance?", "c-levelexecutives")
        assert complexity == QueryComplexity.COMPLEX

    def test_analyze_keyword_triggers_complex(self):
        complexity = classify_complexity(
            "Analyze the financial performance across all departments",
            "finance",
        )
        assert complexity == QueryComplexity.COMPLEX

    def test_compare_keyword_triggers_complex(self):
        complexity = classify_complexity("Compare the Q3 and Q4 revenue figures", "finance")
        assert complexity == QueryComplexity.COMPLEX

    def test_groq_default_simple_route(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("MODEL_SIMPLE", raising=False)
        config = route_query("What is the leave policy?", "employee")
        assert config.model_name == "llama3-8b-8192"
        assert config.provider == "groq"
        assert config.complexity == QueryComplexity.SIMPLE

    def test_groq_default_complex_route(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("MODEL_COMPLEX", raising=False)
        config = route_query(
            "Analyze the strategic financial risk and recommend mitigation strategies",
            "finance",
        )
        assert config.model_name == "mixtral-8x7b-32768"
        assert config.provider == "groq"
        assert config.complexity == QueryComplexity.COMPLEX

    def test_ollama_route_uses_local_defaults(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.delenv("MODEL_COMPLEX", raising=False)
        config = route_query("Show me the budget", "c-levelexecutives")
        assert config.model_name == "mistral"
        assert config.provider == "ollama"

    def test_model_override_wins(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("MODEL_MODERATE", "custom-balanced-model")
        query = "Summarize the company performance review process for managers and employees."
        config = route_query(query, "hr")
        assert config.complexity == QueryComplexity.MODERATE
        assert config.model_name == "custom-balanced-model"

    def test_model_config_has_rationale(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        config = route_query("What is payroll?", "finance")
        assert config.rationale != ""
        assert config.model_name != ""
