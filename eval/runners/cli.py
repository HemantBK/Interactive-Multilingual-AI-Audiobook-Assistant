"""
Eval CLI — orchestrates retrieval / citation / faithfulness runs and
writes a single dated report.

Usage:
  PYTHONPATH=backend python -m eval.runners.cli \
      --dataset eval/datasets/golden_set.json \
      --map eval/datasets/doc_id_by_path.json \
      --user-id <test-user-uuid> \
      --out eval/reports/2026-04-28.json

`doc_id_by_path.json` is `{ "fixtures/sample.pdf": "<doc_uuid>" }` —
mapping the static fixture paths in the golden set to the live Supabase
documents you've seeded. Eval doesn't re-upload — it queries existing
ready docs.

Exit code:
  0 — pass (no metric < target)
  1 — fail (any metric below the configured target → blocks deploy)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from .answer_eval import evaluate_faithfulness
from .citation_eval import evaluate_citations
from .loader import filter_by_set, load
from .retrieval_eval import evaluate_retrieval

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Targets per build plan A2 §8.
TARGETS = {
    "hit_at_5": 0.85,
    "citation_precision": 0.90,
    "faithfulness": 0.80,
}


async def run(args) -> dict:
    items = load(Path(args.dataset))
    doc_id_by_path = json.loads(Path(args.map).read_text())

    retrieval = evaluate_retrieval(
        list(filter_by_set(items, "retrieval")),
        doc_id_by_path,
    )
    citation = await evaluate_citations(
        list(filter_by_set(items, "citation")),
        doc_id_by_path,
        user_id=args.user_id,
    )
    answer = await evaluate_faithfulness(
        list(filter_by_set(items, "answer")),
        doc_id_by_path,
        user_id=args.user_id,
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "targets": TARGETS,
        "retrieval": retrieval.to_dict(),
        "citation": citation.to_dict(),
        "answer": answer.to_dict(),
    }


def fail_on_target_miss(report: dict) -> bool:
    misses = []
    if report["retrieval"]["n"] and report["retrieval"]["hit_at_5"] < TARGETS["hit_at_5"]:
        misses.append(f"hit@5 {report['retrieval']['hit_at_5']:.3f} < {TARGETS['hit_at_5']}")
    if report["citation"]["n"] and report["citation"]["precision"] < TARGETS["citation_precision"]:
        misses.append(
            f"citation precision {report['citation']['precision']:.3f} < {TARGETS['citation_precision']}"
        )
    if report["answer"]["n"] and report["answer"]["mean_faithfulness"] < TARGETS["faithfulness"]:
        misses.append(
            f"faithfulness {report['answer']['mean_faithfulness']:.3f} < {TARGETS['faithfulness']}"
        )
    if misses:
        logger.error("eval failed targets: %s", "; ".join(misses))
        return True
    logger.info("eval passes all configured targets")
    return False


# Day 24: deploy gate — block when current report regresses > REGRESSION_PP
# percentage points vs the last passing baseline. Compares aligned metrics
# only (e.g. ignores citation precision when n=0).
REGRESSION_PP = 2.0


def fail_on_regression(current: dict, baseline_path: Path | None) -> bool:
    if baseline_path is None or not baseline_path.exists():
        logger.info("no baseline at %s — skipping regression check", baseline_path)
        return False
    try:
        baseline = json.loads(baseline_path.read_text())
    except json.JSONDecodeError:
        logger.warning("baseline %s is malformed — skipping regression check", baseline_path)
        return False

    misses: list[str] = []

    def _diff(label: str, base: float, cur: float) -> None:
        delta_pp = (cur - base) * 100
        if delta_pp < -REGRESSION_PP:
            misses.append(
                f"{label}: {cur:.3f} vs baseline {base:.3f} ({delta_pp:+.2f}pp, threshold -{REGRESSION_PP}pp)"
            )

    if current["retrieval"]["n"] and baseline.get("retrieval", {}).get("n"):
        _diff(
            "hit@5",
            baseline["retrieval"]["hit_at_5"],
            current["retrieval"]["hit_at_5"],
        )
    if current["citation"]["n"] and baseline.get("citation", {}).get("n"):
        _diff(
            "citation_precision",
            baseline["citation"]["precision"],
            current["citation"]["precision"],
        )
    if current["answer"]["n"] and baseline.get("answer", {}).get("n"):
        _diff(
            "faithfulness",
            baseline["answer"]["mean_faithfulness"],
            current["answer"]["mean_faithfulness"],
        )

    if misses:
        logger.error("regression vs baseline: %s", "; ".join(misses))
        return True
    logger.info("no regression > %.1fpp vs baseline", REGRESSION_PP)
    return False


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="ARIA eval CLI")
    p.add_argument("--dataset", required=True, help="path to golden_set.json")
    p.add_argument("--map", required=True, help="path to doc_id_by_path.json")
    p.add_argument("--user-id", required=True, help="test user UUID")
    p.add_argument("--out", required=True, help="report json output path")
    p.add_argument(
        "--baseline",
        default=None,
        help="path to last green report (for regression deploy-gate, Day 24)",
    )
    p.add_argument("--no-fail", action="store_true",
                   help="always exit 0 (for first-run / shadowing)")
    args = p.parse_args(argv)

    report = asyncio.run(run(args))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    logger.info("wrote %s", out)

    if args.no_fail:
        return 0

    target_miss = fail_on_target_miss(report)
    baseline_path = Path(args.baseline) if args.baseline else None
    regression = fail_on_regression(report, baseline_path)
    return 1 if (target_miss or regression) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
