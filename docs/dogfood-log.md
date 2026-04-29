# Dogfood log

Build plan §10 starts dogfooding **Day 14** (today). This file records
issues hit during real-world use of ARIA. Triaged daily; product-quality
bugs become eval items, cosmetic ones get GitHub issues, P0s pause the
build calendar.

## Format

```
## YYYY-MM-DD — short title
- **What I tried**: …
- **What happened**: …
- **Expected**: …
- **Severity**: P0 (blocker) / P1 (annoying) / P2 (cosmetic)
- **Filed**: GH#N (if escalated)
```

Severities:
- **P0** — data loss, security, app unusable. Halts build calendar.
- **P1** — workflow broken, user confused. Triaged within 48 h.
- **P2** — typo, polish, edge case. Bundled into Week 6 polish day.

## Hot fixes from dogfood (running list)

> Items that escaped to a GitHub issue and aren't yet closed.

_None yet._

## Daily entries

### 2026-04-28 — kickoff
- **Setup**: applied 0001/0002/0003 migrations, enabled pg_cron.
- **Doc**: uploaded a Hindi PDF and an English PDF.
- **Notes**: …
