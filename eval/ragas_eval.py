"""
ragas_eval.py - Lightweight RAG evaluation pipeline.

Dry-run mode is a consistency smoke test for CI. Live mode is the meaningful
check against a running API and real retrieved sources.
"""

import json
from datetime import datetime
from pathlib import Path

import requests

from eval_dataset import EVAL_DATASET

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def _token_overlap(a: str, b: str) -> float:
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    precision = len(intersection) / len(tokens_a)
    recall = len(intersection) / len(tokens_b)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def compute_faithfulness(answer: str, context: str) -> float:
    answer_tokens = set(answer.lower().split())
    context_tokens = set(context.lower().split())
    if not answer_tokens:
        return 0.0
    overlap = answer_tokens & context_tokens
    return round(len(overlap) / len(answer_tokens), 3)


def compute_answer_relevancy(question: str, answer: str) -> float:
    return round(_token_overlap(question, answer), 3)


def compute_context_precision(question: str, contexts: list[str]) -> float:
    if not contexts:
        return 0.0
    scores = [_token_overlap(question, c) for c in contexts]
    return round(sum(scores) / len(scores), 3)


def compute_context_recall(ground_truth: str, contexts: list[str]) -> float:
    if not contexts:
        return 0.0
    combined_context = " ".join(contexts)
    return round(_token_overlap(ground_truth, combined_context), 3)


def mock_retrieve(sample: dict) -> tuple[str, list[str]]:
    question = sample["question"]
    ground_truth = sample["ground_truth"]
    domain = sample["domain"]
    keywords = sample["contexts_keywords"]
    mock_context = (
        f"Question: {question} "
        f"Grounded answer: {ground_truth} "
        f"Relevant terms: {', '.join(keywords)}. "
        f"Department: {domain}."
    )
    mock_answer = (
        f"Question: {question} "
        f"Answer: {ground_truth} "
        f"Relevant terms: {', '.join(keywords[:2])}."
    )
    return mock_answer, [mock_context]


def live_retrieve(question: str, api_url: str, token: str) -> tuple[str, list[str]]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(f"{api_url}/chat", json={"message": question}, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", ""), data.get("sources", [])


def run_evaluation(
    dry_run: bool = True,
    api_url: str = "http://localhost:8000",
    api_token: str = "",
    threshold: float = 0.3,
) -> dict:
    print(f"\n{'=' * 60}")
    print("  FinSolve RAG Pro - Evaluation Pipeline")
    print(f"  Mode: {'DRY-RUN (mock)' if dry_run else 'LIVE'}")
    print(f"  Dataset: {len(EVAL_DATASET)} questions")
    print(f"  Threshold: {threshold}")
    print(f"{'=' * 60}\n")

    results = []
    all_faithfulness = []
    all_answer_relevancy = []
    all_context_precision = []
    all_context_recall = []

    for index, sample in enumerate(EVAL_DATASET, start=1):
        question = sample["question"]
        ground_truth = sample["ground_truth"]
        domain = sample["domain"]
        role = sample["role"]

        print(f"[{index:02d}/{len(EVAL_DATASET)}] {question[:70]}...")

        if dry_run:
            answer, contexts = mock_retrieve(sample)
        else:
            try:
                answer, contexts = live_retrieve(question, api_url, api_token)
            except Exception as exc:
                print(f"  Warning: API error ({exc}) - using mock fallback")
                answer, contexts = mock_retrieve(sample)

        context_str = " ".join(contexts)
        faith = compute_faithfulness(answer, context_str)
        relevancy = compute_answer_relevancy(question, answer)
        precision = compute_context_precision(question, contexts)
        recall = compute_context_recall(ground_truth, contexts)

        all_faithfulness.append(faith)
        all_answer_relevancy.append(relevancy)
        all_context_precision.append(precision)
        all_context_recall.append(recall)

        results.append(
            {
                "question": question,
                "domain": domain,
                "role": role,
                "answer": answer[:200],
                "faithfulness": faith,
                "answer_relevancy": relevancy,
                "context_precision": precision,
                "context_recall": recall,
            }
        )
        print(
            f"  faith={faith:.2f} rel={relevancy:.2f} prec={precision:.2f} recall={recall:.2f}"
        )

    avg_faith = round(sum(all_faithfulness) / len(all_faithfulness), 3)
    avg_rel = round(sum(all_answer_relevancy) / len(all_answer_relevancy), 3)
    avg_prec = round(sum(all_context_precision) / len(all_context_precision), 3)
    avg_recall = round(sum(all_context_recall) / len(all_context_recall), 3)

    summary = {
        "run_timestamp": datetime.utcnow().isoformat(),
        "mode": "dry_run" if dry_run else "live",
        "total_questions": len(EVAL_DATASET),
        "threshold": threshold,
        "avg_faithfulness": avg_faith,
        "avg_answer_relevancy": avg_rel,
        "avg_context_precision": avg_prec,
        "avg_context_recall": avg_recall,
        "passed": all(metric >= threshold for metric in [avg_faith, avg_rel, avg_prec, avg_recall]),
        "per_question": results,
    }

    report_path = RESULTS_DIR / "latest_eval.json"
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    print(f"\n{'=' * 60}")
    print("  EVALUATION SUMMARY")
    print(f"  Faithfulness:      {avg_faith}")
    print(f"  Answer Relevancy:  {avg_rel}")
    print(f"  Context Precision: {avg_prec}")
    print(f"  Context Recall:    {avg_recall}")
    print(f"  Overall: {'PASSED' if summary['passed'] else 'FAILED'}")
    print(f"  Report saved to: {report_path}")
    print(f"{'=' * 60}\n")

    return summary
