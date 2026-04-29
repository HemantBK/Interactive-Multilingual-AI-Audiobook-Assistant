# Privacy Policy

**Effective date:** 2026-04-29
**Operator:** Hemant (sole operator, India)
**Contact:** hemantkumar.bk@gmail.com

> ⚠️ **Draft v1.** This is the operator's good-faith policy at v1 launch.
> A licensed lawyer should review before public launch outside India and
> before SOC 2 / large-scale enterprise sales.

## 1. What we collect

| Category | Data | Why |
|---|---|---|
| Account | email, OAuth provider id, JWT | Sign in (Supabase Auth) |
| Documents | files you upload (PDF, image, text) | Indexing, retrieval |
| Derived | extracted text, embeddings, OCR output, audio narration | Powering the product |
| Conversations | questions, answers, citations, latency, token counts | History, feedback, prompt iteration |
| Usage counters | per-day uploads, queries, TTS chars | Quotas, cost attribution |
| Audit log | auth events, doc upload events, query events | Security, abuse triage |
| Telemetry (opt-in) | anonymous events via PostHog (no PII), errors via Sentry (no PII) | Product analytics, error reporting |

We **do not** collect: IP addresses (only daily-salted hashes for rate-limit
correlation), payment info (no payments), location, contacts, biometrics.

## 2. Where data lives

| Hop | Provider | Region |
|---|---|---|
| Auth, DB, Storage | Supabase (Postgres + S3-like) | Mumbai (ap-south-1) |
| Backend container | Hugging Face Spaces (Docker) | provider-managed |
| Frontend hosting | Cloudflare Pages | global edge |
| LLM (RAG, translate) | Groq | provider-managed |
| TTS | Microsoft Edge-TTS (no SLA) / Piper (local) | provider-managed / on our server |
| Error reports | Sentry | provider-managed |
| Product analytics | PostHog | provider-managed (US default) |
| Backups (Day 28) | Cloudflare R2 | global edge |

## 3. How long we keep it

| Data | Retention |
|---|---|
| Documents (uploaded files + derived chunks) | **14 days** unless you opt-in to keepalive (build plan §1) |
| Conversations | 14 days (matches doc retention) |
| Audit log | 30 days |
| Usage counters | 365 days for billing analytics |
| Backups | 90 days (R2 retention) |
| Telemetry (PostHog/Sentry) | 90 days; you control via consent |

The 14-day cleanup runs daily at 03:00 IST via Postgres pg_cron.

## 4. Who we share with

We do **not** sell your data. We share it only with the providers above
(necessary processors). Specifically:
- **Groq** sees the document chunks we send for RAG / translation.
- **Supabase** stores everything but the LLM payloads.
- We do **not** send user content to free-tier Gemini (its terms allow
  training on inputs). See the build plan §3.

## 5. Your rights (DPDP / GDPR)

You always have the right to:

| Right | How |
|---|---|
| Access (right to portability) | `Account → Export my data` (calls `GET /user/me/export`) |
| Erasure (right to be forgotten) | `Account → Delete my account` (calls `DELETE /user/me`) |
| Correction | re-upload a document with the corrected content |
| Withdraw consent (analytics) | dismiss / revoke consent in the cookie banner |
| Lodge a complaint | India: Data Protection Board; EU: your local authority |

Erasure is irreversible and runs immediately. We don't keep tombstone rows.

## 6. Security

- All third-party API keys server-side only (build plan §6).
- Row-Level Security on every user-facing table.
- HTTPS + HSTS (`max-age=63072000; includeSubDomains; preload`).
- CSP that blocks inline scripts (Day 13).
- Daily backup to a separate vendor (Day 28).

Vulnerability reports: `hemantkumar.bk@gmail.com` with subject `SECURITY`.

## 7. Cookies + storage

We do **not** set cookies. PostHog uses `localStorage` for an anonymous
session identifier — only after you accept the analytics banner.
If you decline, no analytics-side storage is set.

## 8. Children

Audiobook-Assistant is not directed at children under 13 (US) / 18 (India DPDP).
If you believe a child has signed up, email us and we'll erase the account.

## 9. Breach notification

We will notify affected users within **72 hours** of becoming aware of a
breach that affects their data (DPDP §8(6) / GDPR Art. 33).

## 10. Changes

Substantive changes will be announced via email (to the address you signed
up with) at least 14 days before they take effect.

---

This policy is licensed under CC BY 4.0 — you may reuse the structure for
your own service with attribution.
