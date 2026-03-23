"""
run_evaluation.py — CLI runner for the FinSolve RAG evaluation pipeline.

Usage:
  python eval/run_evaluation.py                          # dry-run, threshold=0.3
  python eval/run_evaluation.py --threshold 0.5         # stricter threshold
  python eval/run_evaluation.py --live --token <JWT>    # live API evaluation

Exit codes:
  0 → All metrics above threshold (CI passes)
  1 → One or more metrics below threshold (CI fails)
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ragas_eval import run_evaluation


def main():
    parser = argparse.ArgumentParser(description="FinSolve RAG Evaluation Runner")
    parser.add_argument("--threshold",  type=float, default=0.3,
                        help="Minimum acceptable score for each metric (default: 0.3)")
    parser.add_argument("--live",       action="store_true",
                        help="Run against live API instead of mock (requires --token)")
    parser.add_argument("--api-url",    default="http://localhost:8000",
                        help="Base URL of the FinSolve API (default: http://localhost:8000)")
    parser.add_argument("--token",      default="",
                        help="JWT Bearer token for live API evaluation")
    args = parser.parse_args()

    dry_run = not args.live
    summary = run_evaluation(
        dry_run=dry_run,
        api_url=args.api_url,
        api_token=args.token,
        threshold=args.threshold,
    )

    # Exit 1 if evaluation failed (CI gate)
    if not summary["passed"]:
        print("❌ Evaluation FAILED — one or more metrics below threshold.")
        sys.exit(1)
    else:
        print("✅ Evaluation PASSED — all metrics above threshold.")
        sys.exit(0)


if __name__ == "__main__":
    main()
