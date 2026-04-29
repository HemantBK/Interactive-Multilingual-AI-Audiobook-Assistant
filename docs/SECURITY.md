# Security

## Threat model

| # | Threat | Control | Status |
|---|---|---|---|
| 1 | API key theft from browser bundle | All third-party API calls via backend; keys live only in HF Space secrets | **Verified Day 20** — see "Day 20 audit" below |
| 2 | XSS via rendered Markdown | DOMPurify on every model-output render; strict CSP | Week 2 Day 13 |
| 3 | Prompt injection from uploaded document | Wrap untrusted content in XML delimiters + explicit system-prompt rule; output filter for exfiltration patterns | Week 2 Day 13 |
| 4 | Malicious file upload (zip bomb, polyglot PDF, EXIF attack) | MIME + magic-byte check, 50 MB cap, strip EXIF, reject scripted PDFs | Week 1 Day 4 |
| 5 | Abuse / quota drain | Per-IP rate limits (slowapi) pre-auth, per-user daily caps post-auth, global kill switch | Week 3 Day 18 |
| 6 | PII leakage in logs | Never log raw doc text or user messages; redact in Sentry | Week 4 Day 22 |
| 7 | Unauthorised data access | Supabase RLS everywhere; backend verifies JWT; service-role key never reaches browser | Week 1 Day 2 |
| 8 | DoS via expensive prompts | Max input tokens, 30s LLM timeout, circuit breaker | Week 3 Day 18 |
| 9 | Data retention (GDPR / DPDP) | 30-day auto-delete, user export + delete endpoints | Week 4 Day 25 |
| 10 | Copyright abuse | Terms of Service, DMCA contact, no cross-user cache of full-text | Week 4 Day 25 |

## Reporting a vulnerability

Email `hemantkumar.bk@gmail.com` with subject `SECURITY`. Do not open a public issue. We aim to respond within 72 hours.

## Periodic reviews

- **Day 26 (pre-private-beta)** — full pass at [day-26-review.md](security/day-26-review.md). Threat-model walk, CSP audit, audit results.
- **RLS verification runbook** — [rls-checklist.md](security/rls-checklist.md). 9 manual tests with two accounts. Run before every public deploy and after any user-facing migration.
- **Quarterly** — repeat the Day 26 review pass; update CVE pins; tighten CSP by one notch.

## Supply chain

- `pip-audit` + `npm audit` run in CI on every PR (Week 4)
- Dependabot alerts enabled (Week 4)
- No transitive dep with a known high-severity CVE may be merged without an exemption note in the PR

## Day 20 audit — no client-side AI keys

**Date verified**: 2026-04-28 (Day 20). Re-verified by the
`no-client-side-ai` CI job on every PR going forward.

### Scan results

| Check | Pattern | Result |
|---|---|---|
| Provider SDKs in `frontend/package.json` | `openai`, `@anthropic-ai/*`, `groq-sdk`, `@google-ai/*`, `cohere-ai` | ✅ none present |
| `VITE_*` env vars in `frontend/src` | `VITE_GEMINI*`, `VITE_GROQ*`, `VITE_OPENAI*`, `VITE_ANTHROPIC*`, `VITE_COHERE*` | ✅ none present |
| Direct provider URLs in source | `generativelanguage.googleapis.*`, `api.openai.com`, `api.groq.com`, `api.anthropic.com`, `api.cohere.com` | ✅ none present |
| Leftover legacy files | `_legacy*`, `*gemini*` | ✅ none in frontend/ (only in plan/CHANGELOG markdown — historical context) |
| `dangerouslySetInnerHTML` | any | ✅ none (Day 13 forbade it) |

### Allowed `VITE_*` env vars

These are intentionally bundled into the client. None are secrets:

| Var | Why it's safe |
|---|---|
| `VITE_API_BASE_URL` | URL of our backend — public by definition |
| `VITE_SUPABASE_URL` | Project URL — public; shown in any inspection |
| `VITE_SUPABASE_ANON_KEY` | Designed to be public; RLS enforces auth |
| `VITE_SENTRY_DSN_FRONTEND` | DSN-style URL; not a secret (Day 22) |
| `VITE_POSTHOG_API_KEY` | "Project API key" in PostHog terms; safe to expose (Day 22) |

### How AI calls actually flow

```
Browser
  │
  │ Authorization: Bearer <Supabase JWT>
  ▼
ARIA FastAPI backend  (HF Space)
  │
  ├── Groq API   (server-side, GROQ_API_KEY in HF Space secrets)
  ├── Gemini API (server-side, paid only, GEMINI_API_KEY blank in v1)
  ├── edge-tts   (no key)
  └── Piper      (local CPU)
```

There is **zero direct path** from the browser to any AI provider. The
backend is the trust boundary; provider keys live only in HF Space
repository secrets.

### CI enforcement

`.github/workflows/ci.yml` job `no-client-side-ai` runs on every PR and
push to main. It will fail the build if any of the patterns above
re-appears. See the job for the exact regex set.
