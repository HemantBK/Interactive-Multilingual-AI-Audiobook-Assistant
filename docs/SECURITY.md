# Security

## Threat model

| # | Threat | Control | Status |
|---|---|---|---|
| 1 | API key theft from browser bundle | All third-party API calls via backend; keys live only in HF Space secrets | Day 1 started (vite.config.ts hardened); direct Gemini calls removed Week 3 |
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

## Supply chain

- `pip-audit` + `npm audit` run in CI on every PR (Week 4)
- Dependabot alerts enabled (Week 4)
- No transitive dep with a known high-severity CVE may be merged without an exemption note in the PR
