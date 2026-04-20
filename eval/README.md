# Eval harness

Why: free-tier LLM apps silently degrade when providers change models. The eval suite is our early-warning system.

See `PLAN.md §8` for metrics and targets.

## Layout

```
eval/
├── datasets/   # golden Q/A pairs, multilingual (En/Hi/Ta)
├── runners/    # one script per metric
└── reports/    # JSON + HTML output, ignored by git
```

## Runbook

```bash
# from repo root
cd eval
python runners/retrieval_eval.py --dataset datasets/rag_golden_v1.jsonl
```

Reports land in `eval/reports/<timestamp>/`.

## CI

`eval-nightly.yml` (GitHub Actions, Week 4) runs the full suite at 03:00 IST daily. Regressions > 2% post a comment on the most recent `main` commit.
