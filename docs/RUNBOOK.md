# Runbook

On-call playbook. Each scenario has: how to detect, blast radius, the
fix, and the postmortem trigger.

## Quick reference

| Symptom | Page | First action |
|---|---|---|
| `/health` 5xx for >5 min | UptimeRobot email | check HF Spaces dashboard |
| Sentry error rate > 5/min for 10 min | Sentry email | grep recent commits, kill-switch if needed |
| Groq error rate > 10% for 5 min | Sentry email | flip primary to Gemini paid (env flag) |
| Supabase DB > 80% | Supabase dashboard | enable Pro tier OR force 7-day cleanup |
| Daily quota burn > 70% by 12:00 IST | PostHog dashboard | investigate suspicious user, raise per-user cap if legit |

## Kill switch

Operator emergency stop: every AI / mutation endpoint returns 503 immediately.

```
HF Space dashboard → Settings → Repository secrets → KILL_SWITCH=true
→ Restart Space
```

`/health` and `/auth/*` keep working so users can sign in and read existing
docs. Day 18 implemented [middleware/kill_switch.py](../backend/app/middleware/kill_switch.py).

To turn off: set `KILL_SWITCH=false` (or remove the secret) and restart.

## Scenario: HF Space asleep

**Symptom**: First request after ~48h idle takes 30–90s.

**Why**: HF Spaces free tier sleeps after no traffic.

**Fix**: UptimeRobot pings `/health` every 5 min — should keep it warm.
If a real user hits a cold start, they see a `Loading…` state for ~30s.
Acceptable v1 behaviour; flagged in [SLOs.md](SLOs.md) honest-latency table.

**Permanent fix**: v1.5 trigger in [build plan.md §25](../build%20plan.md) moves the
backend to Fly.io (3 always-on free VMs).

## Scenario: Groq rate limit

**Symptom**: Sentry transactions on `/rag/ask` show 429 from Groq;
circuit breaker opens after 5 fails.

**Blast radius**: All RAG queries fail with `LLM unavailable` until
Groq's daily window resets (UTC midnight).

**Fix (immediate)**:
1. Check Groq console — confirm at quota.
2. Either wait for reset, OR
3. Set `GEMINI_API_KEY` (paid) and flip the LLM choice via env flag (TODO Day 33: make this a single config switch; today it's a code change).

**Postmortem**: at 60% RPD for 14 days running the v1.5 trigger
(build plan §25) fires automatically — file an issue and migrate
before this scenario recurs.

## Scenario: Indexing stuck in `processing`

**Symptom**: User uploads, status stays `processing` for >5 min.

**Why**: HF Space restarted mid-`run_indexing` BackgroundTask. The doc
is orphaned in `processing` because the worker that owns it died.

**Fix**:
```sql
update public.documents
set status = 'queued'
where status = 'processing'
  and updated_at < now() - interval '5 minutes';
```
Then the next upload (or a manual `python -m backend.app.scripts.drain`
once we ship it) will retry.

**Permanent fix**: startup hook to drain orphans on every worker boot
([build plan §10 Day 5](../build%20plan.md)). Scheduled, not
yet implemented.

## Scenario: Supabase DB > 80%

**Symptom**: Supabase dashboard shows DB usage spike.

**Fix (urgent)**: Trigger an early run of the 14-day cleanup:
```sql
delete from public.documents where created_at < now() - interval '14 days'
  and not exists (select 1 from public.documents_keepalive k where k.document_id = documents.id);
```

**Fix (sustained)**: Migrate to Supabase Pro ($25/mo, 8 GB DB). Per
[build plan §25](../build%20plan.md) capacity watermarks, this
should auto-trigger via the cron at >70% for 7 days.

## Scenario: prompt iteration introduced a regression

**Symptom**: Nightly eval (`.github/workflows/eval-nightly.yml`) fails
with `regression > 2pp`.

**Fix**:
```sql
-- Roll back to the previous prompt version
update public.prompts set is_active = false where id='rag.system' and version=<bad>;
update public.prompts set is_active = true  where id='rag.system' and version=<previous>;
```
The change takes effect on the next request — no deploy needed.

**Postmortem**: file an ADR documenting which version + why it failed +
what the next iteration learned.

## Scenario: PII leak suspected

**Severity**: P0. **DPDP §8(6) requires notice within 72 hours.**

1. Set `KILL_SWITCH=true` immediately.
2. Email `hemantkumar.bk@gmail.com` and start the incident timer.
3. Pull the relevant `audit_log` rows.
4. Identify scope (which users? which data fields? when?).
5. Notify affected users by email (Supabase Auth gives us the address).
6. Notify India Data Protection Board within 72h.
7. File breach disclosure on this repo.

Refer to [legal/privacy.md §9 Breach notification](legal/privacy.md).

## Rollback

| Surface | Procedure |
|---|---|
| Frontend | Cloudflare Pages dashboard → Deployments → Rollback |
| Backend | `git revert <commit> && git push` — HF Space rebuilds; no one-click rollback exists |
| DB | every migration ≥0002 ships with `-- Down` block; apply manually with `psql -v ON_ERROR_STOP=1` |
| Prompt | flip `prompts.is_active` (above) — instant |

## DR (lands Day 28)

Daily pg_dump to Cloudflare R2. RTO 4h, RPO 24h. Full restore drill
documented quarterly per [build plan §24](../build%20plan.md).

## Pages route to

| Channel | Used for |
|---|---|
| email (operator) | UptimeRobot, Sentry, Supabase webhook |
| Discord webhook | Day 29 alert wiring |
| GitHub issue (auto-filed cron) | capacity watermark crossings |

## After the fire

Postmortem template lives at `docs/postmortems/_template.md` (Day 29).
Goal of the writeup: blameless, three artefacts (timeline, root cause,
preventive action items + owner + date).
