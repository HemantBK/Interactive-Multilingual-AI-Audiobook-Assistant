"""
Prompt A/B runner (build plan §9 + §19, Day 33 wires automation).

Runs the answer-faithfulness + citation-precision eval against TWO prompt
versions back-to-back and reports the delta. Used by the Day 33 prompt
iteration loop: write a new row in `public.prompts` with is_active=false,
run this script, promote (flip is_active) only if delta > +2pp.

Day 23 ships the runner; Day 33 schedules it weekly and writes the ADR.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from app.db.supabase import admin_client
from app.services import prompts as prompt_module

from .answer_eval import evaluate_faithfulness
from .citation_eval import evaluate_citations
from .loader import filter_by_set, load

logger = logging.getLogger(__name__)


async def run_with_prompt(
    items, doc_id_by_path, *, user_id: str, system_prompt_override: str
):
    """
    Evaluate the same items twice: faithfulness + citation precision.
    The override is monkey-patched into prompt_module.SYSTEM_PROMPT for
    the duration of this call — single-process, no concurrency issue.
    """
    original = prompt_module.SYSTEM_PROMPT
    prompt_module.SYSTEM_PROMPT = system_prompt_override
    try:
        cit = await evaluate_citations(
            list(filter_by_set(items, "citation")),
            doc_id_by_path,
            user_id=user_id,
        )
        ans = await evaluate_faithfulness(
            list(filter_by_set(items, "answer")),
            doc_id_by_path,
            user_id=user_id,
        )
        return {
            "citation_precision": cit.precision,
            "faithfulness": ans.mean_faithfulness,
            "n_citation": cit.n,
            "n_answer": ans.n,
        }
    finally:
        prompt_module.SYSTEM_PROMPT = original


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Prompt A/B eval runner")
    p.add_argument("--dataset", required=True, help="path to golden_set.json")
    p.add_argument("--map", required=True, help="path to doc_id_by_path.json")
    p.add_argument("--user-id", required=True, help="service test user UUID")
    p.add_argument("--baseline-prompt", required=True, help="path to A.txt")
    p.add_argument("--candidate-prompt", required=True, help="path to B.txt")
    p.add_argument("--out", required=True, help="path to write report json")
    args = p.parse_args(argv)

    items = load(Path(args.dataset))
    doc_id_by_path = json.loads(Path(args.map).read_text())
    a_text = Path(args.baseline_prompt).read_text()
    b_text = Path(args.candidate_prompt).read_text()

    async def run():
        a = await run_with_prompt(items, doc_id_by_path, user_id=args.user_id, system_prompt_override=a_text)
        b = await run_with_prompt(items, doc_id_by_path, user_id=args.user_id, system_prompt_override=b_text)
        return {
            "baseline": a,
            "candidate": b,
            "delta": {
                "citation_precision_pp": (b["citation_precision"] - a["citation_precision"]) * 100,
                "faithfulness_pp": (b["faithfulness"] - a["faithfulness"]) * 100,
            },
        }

    report = asyncio.run(run())
    Path(args.out).write_text(json.dumps(report, indent=2))
    logger.info("wrote %s — delta cite=%+.2fpp faith=%+.2fpp",
                args.out, report["delta"]["citation_precision_pp"],
                report["delta"]["faithfulness_pp"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
