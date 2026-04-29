# Day 26 — security review pass

Build plan §6 + §26. Single-day audit before private beta (Day 28
launch). Re-run before any public-launch milestone.

## Reviewer

Hemant — single operator. Day 28+ private beta should add a second
reviewer for any non-trivial security change.

## Threats checked vs controls

| # | Threat | Control | Day 26 status |
|---|---|---|---|
| 1 | API key theft from browser bundle | All third-party calls via backend; keys live only in HF Space secrets | ✅ verified Day 20; CI `no-client-side-ai` job blocks regressions |
| 2 | XSS via rendered Markdown | `react-markdown` (no `rehype-raw`); `disallowedElements` blocklist; CI fails on `dangerouslySetInnerHTML` | ✅ |
| 3 | Prompt injection from uploaded document | XML-tag wrapper around chunks + system-prompt rule; output filter rejects credentials/scripts/JS-URLs; 30-payload regression test in CI | ✅ |
| 4 | Malicious file upload | MIME + magic-byte check, 50 MB cap, EXIF strip, no script execution path | ✅ |
| 5 | Abuse / quota drain | slowapi per-IP limits, per-user daily caps, `KILL_SWITCH` env, circuit-breaker on Groq | ✅ |
| 6 | PII leakage in logs / Sentry | `sendDefaultPii=False` both ends; URL token-stripping in Sentry beforeBreadcrumb; audit log redacts content | ✅ |
| 7 | Unauthorised data access | RLS on every user-facing table; `user_client(JWT)` for user data, `admin_client()` only for backend-owned tables | ✅ verified — see `rls-checklist.md` |
| 8 | DoS via expensive prompts | 30s Groq timeout; `MAX_TTS_CHARS=4000`; `MAX_TEXT_CHARS=8000` for translate; 50 MB upload cap | ✅ |
| 9 | Data retention / DPDP | 14-day auto-delete via pg_cron; `DELETE /user/me` wipes everything; `GET /user/me/export` for portability | ✅ Day 25 |
| 10 | Copyright abuse | ToS forbids piracy; DMCA channel; no cross-user content cache (only translation/audio caches keyed by content hash) | ✅ Day 25 |
| 11 | Supply-chain CVE | `pip-audit` + `npm audit --audit-level=high` in CI | ✅ Day 26 |
| 12 | Supply-chain license drift | `pip-licenses` + `license-checker` block AGPL/SSPL/Commons-Clause | ✅ Day 1 |
| 13 | Idempotency-key replay | 24h TTL via pg_cron; `request_hash` mismatch → 409 | ✅ Day 4 |
| 14 | Stolen JWT replay | 1-hour Supabase access-token TTL; `auth.users` delete invalidates all sessions; KILL_SWITCH for emergency lockdown | ✅ |

## CSP review (Day 26 pass)

`Content-Security-Policy` directives audited against current dependencies.

| Directive | Allowed origin | Why | Day 38 tighten? |
|---|---|---|---|
| `default-src 'self'` | same origin | baseline | — |
| `script-src 'self' 'unsafe-eval' https://cdn.tailwindcss.com` | Tailwind Play CDN | JIT in-browser compile | drop both when compiled Tailwind ships |
| `style-src 'self' 'unsafe-inline'` | inline styles from Tailwind | runtime style injection | drop `'unsafe-inline'` after Day 38 |
| `font-src 'self' data:` | inline data URIs | none external (we removed Google Fonts Day 1) | — |
| `img-src 'self' data: blob: https:` | broad `https:` for Supabase Storage signed URLs | doc images served via signed URLs | replace `https:` with explicit Supabase host once known |
| `media-src 'self' blob: https:` | TTS audio blob URLs + Supabase signed audio | — | replace `https:` similarly |
| `connect-src` | `*.supabase.co`, `*.hf.space`, `*.ingest.sentry.io`, `*.sentry.io`, `us.i.posthog.com`, `eu.i.posthog.com` | API + observability | — |
| `worker-src 'self' blob:` | pdf.js worker | Vite hashes the worker URL same-origin; pdf.js wraps in blob internally | — |
| `frame-ancestors 'none'` | nothing can iframe us | clickjacking defense | — |
| `base-uri 'self'`, `form-action 'self'` | locked | SSRF/exfil defense | — |

## Audits that ran

| Tool | What | Result |
|---|---|---|
| gitleaks | git history secret scan | no findings |
| pip-audit | `requirements.txt` + `requirements-dev.txt` CVEs | run nightly; fails CI on any |
| npm audit | frontend prod deps | fails on `high` or `critical` |
| pip-licenses | block AGPL/SSPL/Commons-Clause in Python | clean |
| license-checker | same for npm | clean |
| no-client-side-ai | grep guard | clean |
| ruff | Python lint with security rules (`S`) | clean |
| schemathesis | OpenAPI conformance fuzz | clean |
| 30-payload prompt-injection regression | unit tests | passing |
| Playwright + axe-core | a11y baseline | clean |

## Manual verifications

- ☐ Run `npm install` then check `package-lock.json` for unexpected entries.
- ☐ Apply `infra/supabase/migrations/0001-0004` to a fresh project, confirm
  RLS policies exist via `select schemaname, tablename, policyname from
  pg_policies;`.
- ☑ Run `RUN_INTEGRATION=1 pytest tests/integration` against staging Supabase.
- ☑ Walk `docs/security/rls-checklist.md` with two test accounts.
- ☐ Walk `docs/a11y-test-plan.md` with NVDA on Firefox.
- ☐ Verify Sentry receives a synthetic test error and that no PII is in the payload.
- ☐ Verify PostHog receives `auth.signed_in` only after consent banner accept.
- ☐ Run `axe DevTools` against the prod build manually for the top 5 surfaces.

## Open follow-ups (Day 27/28)

| Item | Owner | When |
|---|---|---|
| Compiled Tailwind → drop `unsafe-eval` from CSP | Hemant | Day 38 polish |
| `https:` in `img-src`/`media-src` → explicit Supabase host | Hemant | when project URL is final |
| Sentry `setUser({id: hash})` decision | Hemant | now or before launch |
| Move `npm audit` to `--audit-level=moderate` | Hemant | before public Day 42 launch |

## Vulnerability disclosure

`hemantkumar.bk@gmail.com` with subject `SECURITY` (see `docs/SECURITY.md`).
We aim to triage within 72 h.
