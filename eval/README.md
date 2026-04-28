# ARIA evaluation harness

Build plan A2 §8 + Day 23 wire the actual harness. Day 7 ships the
**scaffolding + golden-set methodology** so labeling can run in parallel
with the rest of the build.

Why this matters: free-tier LLM apps silently degrade when providers
swap models or rate-limit. The eval suite is our early-warning system —
nightly Action posts a regression check on every PR before merge.

## Goals (per build plan A2 §8)

| Set | Target | Use |
|---|---|---|
| OCR ground truth (clean PDFs) | 20 docs across 5 langs | Tesseract char-accuracy ≥ 95% |
| Retrieval Q→chunk pairs | 50 per priority lang × 6 = 300 | hit@5 ≥ 85% |
| Citation precision Q/A | 100 pairs | LLM-as-judge precision ≥ 90% |
| Translation BLEU | FLORES-200 subset | En→Hi BLEU ≥ 35 |
| TTS MOS samples | 20 per lang × 5 = 100 | MOS ≥ 3.8/5 |

## Where it gets built

Use **Kaggle** for batch labeling — its CPU is plenty for OCR ground-truth
generation and for trying alternative embedders against bge-m3 before any
swap. Notebooks live in `eval/notebooks/` (gitignored heavy outputs).

The shipped artefact is `eval/datasets/golden_set.json` — see schema below.

## Status (Day 7)

- [ ] 20 OCR docs collected (en, hi, ta, bn, mr, te)
- [ ] 50×6 retrieval pairs labeled
- [ ] 100 citation precision Q/A pairs
- [ ] FLORES-200 subset extracted
- [ ] 20×5 TTS MOS samples picked

## Layout

```
eval/
├── datasets/   # golden Q/A pairs, multilingual (en, hi, ta, bn, mr, te)
│   └── template.json
├── runners/    # one script per metric (lands Day 23)
└── reports/    # JSON + HTML output, gitignored
```

## Schema

See `datasets/template.json` for the full structure. One entry:

```json
{
  "id": "ret-en-001",
  "set": "retrieval",
  "language": "en",
  "doc_path": "fixtures/ncert-class10-math/ch1.pdf",
  "question": "What is the formula for the sum of an arithmetic series?",
  "expected_chunk_text_excerpt": "Sn = n/2 (a + l)",
  "expected_page": 12,
  "labeler": "hemant",
  "labeled_at": "2026-04-28"
}
```

## Pipeline (lands Day 23)

```
golden_set.json
       │
       ├── eval/runners/retrieval_eval.py     → hit@k, MRR
       ├── eval/runners/answer_eval.py        → ragas faithfulness, relevancy
       ├── eval/runners/citation_eval.py      → cited chunk truly contains answer (LLM-as-judge)
       ├── eval/runners/translation_eval.py   → BLEU on FLORES subset
       └── eval/runners/tts_eval.py           → MOS aggregation
                ↓
       eval/reports/<date>_<slug>.json
       (regression > 2% on any metric blocks deploy — wired in CI Day 24)
```

## Runbook (Day 23+)

```bash
# from repo root
cd eval
python runners/retrieval_eval.py --dataset datasets/golden_set.json
```

Reports land in `eval/reports/<timestamp>/`. Nightly GitHub Action
(`eval-nightly.yml`, Day 23) runs the full suite at 03:00 IST and posts a
comment on the most recent `main` commit.
