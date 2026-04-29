# Terms of Service

**Effective date:** 2026-04-29
**Operator:** Hemant (sole operator, India)
**Contact:** hemantkumar.bk@gmail.com

> ⚠️ **Draft v1.** Lawyer review required before commercial launch.

## 1. What this service is

Audiobook-Assistant is a multilingual AI reader: upload a document, ask questions
backed by precise citations, listen via text-to-speech, translate
between 14 languages. The service is provided **as-is** at v1.

## 2. Who can use it

- You must be 18+ (DPDP threshold for Indian users).
- You must own or have a valid right to use any document you upload.
- You must not use this service to violate anyone's copyright, privacy, or
  applicable law.

## 3. Acceptable use

You agree not to:
- Upload pirated or copyright-infringing material.
- Upload material containing CSAM, terrorist content, or non-consensual
  intimate imagery.
- Use the service to harass, defame, or harm others.
- Reverse-engineer rate limits, attempt to extract our prompts /
  embeddings, or otherwise abuse the service.
- Upload anything containing API keys, passwords, or other secrets you
  don't want a third-party LLM to see (we redact what we can — see
  Day 13 output filter — but the safest policy is "don't upload it").

We may suspend or terminate your account for violations.

## 4. Content you upload

- You retain ownership of everything you upload.
- You grant us a non-exclusive, worldwide, royalty-free licence to
  process, store, and transmit your uploads to the necessary providers
  (Supabase, Groq, edge-tts) **only for the purpose of running the
  service for you**.
- We do **not** train any model on your data.
- We do **not** send your content to free-tier Gemini (its terms allow
  training).

## 5. Service availability

Audiobook-Assistant is hosted on free-tier infrastructure during v1 (build plan §3).
Expect:
- Cold starts after periods of inactivity (Hugging Face Spaces sleeps).
- Occasional rate limits when the daily Groq quota is exhausted.
- Scheduled 14-day data cleanup (DPDP-aligned default; opt-in to keep
  longer).

We make no SLA promises at v1.

## 6. Pricing

The service is **free at v1 scale (~50 daily users)**. We may introduce paid
tiers later; existing free use will continue under the same terms unless
explicitly changed with 30 days' notice.

## 7. Termination

You may delete your account at any time via `Account → Delete my account`.
We may terminate accounts that violate Section 3 with 7 days' notice
unless the violation is severe (CSAM, breach attempts), in which case
termination is immediate.

## 8. Limits of liability

The service is provided **AS IS, WITHOUT WARRANTY**. We are not liable for:
- Indirect or consequential damages.
- Loss of data caused by free-tier provider outages.
- AI hallucinations — every answer is a model's best guess; verify
  important claims via the cited source.

Maximum aggregate liability is capped at **₹0** (zero rupees) for free-
tier users, or the fees paid in the 12 months preceding the claim, for
paid users.

## 9. Governing law

These terms are governed by the laws of India. Disputes are subject to
the exclusive jurisdiction of the courts of Bengaluru.

## 10. Changes

Substantive changes will be announced 30 days before they take effect.
Continued use after the effective date constitutes acceptance.

---

DMCA / takedown notices → `docs/legal/dmca.md` (or same email above).
