"""test_enhancements.py - Unit tests for reranking, HyDE, and feedback."""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


def _make_doc(content: str, source: str = "test.pdf"):
    class FakeDoc:
        def __init__(self, text, src):
            self.page_content = text
            self.metadata = {"source": src}

    return FakeDoc(content, source)


class TestReranker:
    def test_reranker_trims_to_top_k(self):
        from services.reranker import rerank

        docs = [_make_doc(f"Document {i}") for i in range(8)]

        class FakeEncoder:
            def predict(self, pairs):
                return [0.9, 0.1, 0.8, 0.2, 0.7, 0.3, 0.6, 0.4]

        with patch("services.reranker._get_encoder", return_value=FakeEncoder()):
            result = rerank("test query", docs, top_k=4)

        assert len(result) == 4

    def test_reranker_orders_by_score_descending(self):
        from services.reranker import rerank

        docs = [_make_doc(f"Doc {i}") for i in range(4)]

        class FakeEncoder:
            def predict(self, pairs):
                return [0.3, 0.9, 0.1, 0.7]

        with patch("services.reranker._get_encoder", return_value=FakeEncoder()):
            result = rerank("test query", docs, top_k=4)

        assert result[0].page_content == "Doc 1"
        assert result[1].page_content == "Doc 3"

    def test_reranker_fallback_on_encoder_failure(self):
        from services.reranker import rerank

        docs = [_make_doc(f"Doc {i}") for i in range(6)]

        class BrokenEncoder:
            def predict(self, pairs):
                raise RuntimeError("Model error")

        with patch("services.reranker._get_encoder", return_value=BrokenEncoder()):
            result = rerank("test query", docs, top_k=4)

        assert len(result) == 4
        assert result[0].page_content == "Doc 0"

    def test_reranker_empty_docs_returns_empty(self):
        from services.reranker import rerank

        result = rerank("query", [], top_k=4)
        assert result == []

    def test_reranker_none_encoder_fallback(self):
        from services.reranker import rerank

        docs = [_make_doc(f"Doc {i}") for i in range(6)]
        with patch("services.reranker._get_encoder", return_value=None):
            result = rerank("test query", docs, top_k=3)

        assert len(result) == 3
        assert result[0].page_content == "Doc 0"


class TestHyDE:
    def test_hyde_returns_hypothesis_on_success(self):
        from services.hyde_retriever import generate_hypothesis

        with patch(
            "services.hyde_retriever.generate_text",
            return_value="Annual leave is 20 days per year for all employees.",
        ):
            result = generate_hypothesis("What is the leave policy?", provider="groq")

        assert result == "Annual leave is 20 days per year for all employees."
        assert result != "What is the leave policy?"

    def test_hyde_fallback_on_provider_error(self):
        from services.hyde_retriever import generate_hypothesis

        with patch("services.hyde_retriever.generate_text", side_effect=RuntimeError("timeout")):
            result = generate_hypothesis("What is the leave policy?", provider="groq")

        assert result == "What is the leave policy?"

    def test_hyde_fallback_on_empty_response(self):
        from services.hyde_retriever import generate_hypothesis

        with patch("services.hyde_retriever.generate_text", return_value="   "):
            result = generate_hypothesis("What is the HR policy?", provider="ollama")

        assert result == "What is the HR policy?"

    def test_hyde_returns_string_type(self):
        from services.hyde_retriever import generate_hypothesis

        with patch("services.hyde_retriever.generate_text", side_effect=Exception("Unexpected")):
            result = generate_hypothesis("Any query")

        assert isinstance(result, str)

    def test_hyde_uses_provider_specific_default_model(self):
        from services.hyde_retriever import get_hyde_model

        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}, clear=False):
            assert get_hyde_model() == "llama3.2:1b"


class TestHITLFeedback:
    def setup_method(self):
        import importlib

        os.environ["DUCKDB_PATH"] = "/tmp/finsolve_test_feedback.db"
        import db

        importlib.reload(db)
        db.init_db()

    def teardown_method(self):
        try:
            os.remove("/tmp/finsolve_test_feedback.db")
        except FileNotFoundError:
            pass

    def test_log_feedback_thumbs_up(self):
        from db import get_feedback_summary, log_feedback

        log_feedback(
            chat_id="test-chat-001",
            username="Binoy",
            role="finance",
            rating=1,
            comment="Very helpful!",
        )
        summary = get_feedback_summary(hours=24)
        assert summary["total_ratings"] == 1
        assert summary["thumbs_up"] == 1
        assert summary["thumbs_down"] == 0

    def test_log_feedback_thumbs_down(self):
        from db import get_feedback_summary, log_feedback

        log_feedback(
            chat_id="test-chat-002",
            username="sangit",
            role="hr",
            rating=-1,
            comment="",
        )
        summary = get_feedback_summary(hours=24)
        assert summary["thumbs_down"] == 1
        assert summary["thumbs_up"] == 0

    def test_log_feedback_invalid_rating_raises(self):
        from db import log_feedback

        with pytest.raises(ValueError):
            log_feedback(chat_id="x", username="u", role="r", rating=0)
        with pytest.raises(ValueError):
            log_feedback(chat_id="x", username="u", role="r", rating=2)

    def test_feedback_summary_satisfaction_pct(self):
        from db import get_feedback_summary, log_feedback

        log_feedback("c1", "u1", "r", 1)
        log_feedback("c2", "u2", "r", 1)
        log_feedback("c3", "u3", "r", -1)
        summary = get_feedback_summary(hours=24)
        assert summary["total_ratings"] == 3
        assert summary["satisfaction_pct"] == pytest.approx(66.7, abs=0.1)

    def test_feedback_summary_empty(self):
        from db import get_feedback_summary

        summary = get_feedback_summary(hours=24)
        assert summary["total_ratings"] == 0
        assert summary["thumbs_up"] == 0
        assert summary["thumbs_down"] == 0
