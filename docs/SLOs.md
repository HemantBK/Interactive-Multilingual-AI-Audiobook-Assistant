# Service Level Objectives

Build plan §17 + Day 22. SLOs are user-facing promises tied to a
fixed measurement window. They drive paging thresholds, deploy-freeze
decisions, and the v1.5 capacity-trigger policy in §25.

## Tier-1 SLOs (page on burn)

| SLI | Target | Window | Burn-rate alert |
|---|---|---|---|
| **RAG availability (warm)** — `2xx ÷ total` for `POST /rag/ask`, excluding cold-start sessions | 99.5% | 30 days | 6× burn for 1h |
| **RAG p95 latency, warm** — first SSE byte within 3s | ≤ 3 s | 7 days | p95 > 5s for 15 min |
| **Indexing success rate** — `documents.status='ready' ÷ uploaded` | 98% | 7 days | < 95% for 24h |
| **TTS availability** — `2xx ÷ total` for `POST /tts` | 99% | 30 days | 6× burn for 1h |

## Tier-2 SLOs (track but don't page)

| SLI | Target | Window |
|---|---|---|
| Citation precision — cited chunk truly contains answer (LLM-as-judge) | ≥ 90% | weekly eval set |
| Retrieval hit@5 | ≥ 85% | weekly eval set |
| Translation BLEU (En→Hi) | ≥ 35 | weekly FLORES sample |
| TTS MOS (human rating) | ≥ 3.8 / 5 | monthly 20-sample set |

## Error budgets

A 99.5% / 30-day SLO buys **3.6 hours** of downtime per month. We do not
ship new features when more than 50% of the current window's budget is
consumed. The kill-switch (build plan §6) is the lever for stopping
budget burn during an incident.

| Window | Budget at 99.5% | Budget at 99% |
|---|---|---|
| 30 days | 3 h 36 min | 7 h 12 min |
| 7 days  | 50 min     | 1 h 41 min |

## Latency targets, honest

| Path | p95 warm | p95 cold | Cold-rate target |
|---|---|---|---|
| RAG first token | ≤ 3 s | ≤ 45 s | < 5% of sessions |
| TTS gen / 1 k chars | ≤ 5 s | ≤ 50 s | < 5% |
| Indexing 20-page PDF | ≤ 45 s | n/a (background) | — |

Cold-start mitigation: UptimeRobot 5-min `/health` ping (best-effort on
HF Spaces free). Real fix is the v1.5 trigger to Fly.io shared-CPU.

## Where the data comes from

| SLI | Source |
|---|---|
| RAG availability | Sentry transactions on `/rag/ask` (Day 22) |
| RAG p95 latency | Sentry transaction durations + `conversations.latency_ms` |
| Indexing success | `count(status='ready') ÷ count(*)` on `documents` |
| TTS availability | Sentry transactions on `/tts` |
| Citation precision | `eval/runners/citation_eval.py` nightly (Day 23) |
| Retrieval hit@5 | `eval/runners/retrieval_eval.py` nightly |
| Translation BLEU | `eval/runners/translation_eval.py` weekly |
| TTS MOS | `eval/runners/tts_eval.py` monthly human pass |

## Alert routing (Day 29)

- **Sentry** → email + Discord webhook on Tier-1 burn
- **UptimeRobot** → email on `/health` 5-min outage
- **Supabase** → dashboard alerts when DB / Storage > 80%

The full alert wiring lands Day 29 (`Capacity watermarks + auto-issue
cron`). Day 22 just makes the data visible.
