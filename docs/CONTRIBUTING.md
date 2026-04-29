# Contributing

Thanks for considering it. This is a solo-operator project at v1, so
the workflow is light — but the gates are real.

## Before you open a PR

Read the relevant doc first:
- New surface or non-trivial change → [ARCHITECTURE.md](ARCHITECTURE.md) + the relevant ADR in [adr/](adr)
- New endpoint → [DEPLOY.md](DEPLOY.md) §CI gates and [ui-states.md](ui-states.md)
- Touching auth, RLS, or any user-data table → [SECURITY.md](SECURITY.md) + [security/rls-checklist.md](security/rls-checklist.md)
- Adding a dependency → [adr/0001-stack-choice.md](adr/0001-stack-choice.md) §License-clean tree

## Branching

```
main                  always green; deploys automatically
└── feat/<short>      feature branches off main
└── fix/<issue#>      bugfixes
└── docs/<topic>      doc-only changes (skip eval gate)
```

Squash + merge. Conventional Commit prefix in the merge title:
`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.

## CI gates that block merge

13 jobs in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). Full
list in [DEPLOY.md](DEPLOY.md) §CI gates. The ones that bite contributors most:

- `lint-frontend` — eslint + prettier. Run `npm run format:write` locally.
- `backend-lint` — ruff. Run `ruff check backend/` locally.
- `migration-safety` — every `*.sql` in `infra/supabase/migrations/` applies
  cleanly against a vanilla pgvector + auth/storage stub.
- `no-client-side-ai` — no AI provider SDKs / VITE_*_KEY / direct provider URLs in `frontend/`.

## Adding a migration

1. New file: `infra/supabase/migrations/<NNNN>_<slug>.sql` (numeric prefix sorted).
2. Include both `-- Up` and `-- Down` blocks (required from `0002` onward).
3. Don't reference Supabase platform schemas (`auth.*`, `storage.*`) in ways the test stub at [`infra/supabase/test_helpers/auth_stub.sql`](../infra/supabase/test_helpers/auth_stub.sql) doesn't model — extend the stub if you do.
4. CI's `migration-safety` job applies your migration to a real Postgres + pgvector container; failures point at the syntax issue.

## Adding a dependency

1. **Backend**: append to `backend/requirements.txt` with a minor-version pin.
2. **Frontend**: `npm install --save <pkg>` then commit `package.json` (we don't commit `package-lock.json`; lockfile churn isn't worth the merge pain at this scale).
3. CI's license guards must stay green. AGPL/SSPL/Commons-Clause are blocked.
4. CI's audit jobs (`pip-audit`, `npm audit --audit-level=high`) must stay green.
5. If the dep is heavy (>5 MB) or pulls a vendor-locked SaaS, file a tiny ADR explaining why.

## ADR process

For non-trivial decisions (new vendor, swap a library, change a load-bearing pattern):

1. Copy `adr/0001-stack-choice.md` as `adr/<NNNN>-<slug>.md`.
2. Fill in: Date, Status, Deciders, Context, Decision, Consequences, Alternatives considered.
3. Status options: `Proposed → Accepted → Superseded by NNNN | Deprecated`.
4. Once accepted, the ADR is **immutable** — to change a decision, write a new ADR and mark the old one Superseded.

## Testing

| Level | What to add |
|---|---|
| Pure-function | Always. ~135 unit tests today (build plan §14). |
| HTTP-level smoke | At minimum: 401 without token + 422 on bad payload. |
| Contract (schemathesis) | Auto-runs against your new endpoint via `test_contract.py`; declare 401 / 422 in `responses=` to keep the fuzzer green. |
| Integration | Marker `@pytest.mark.integration`; runs only with `RUN_INTEGRATION=1`. |

## What NOT to do

- Don't add `dangerouslySetInnerHTML` (CI fails the build).
- Don't add an AI provider SDK to the frontend (CI fails).
- Don't store provider API keys in `VITE_*` env vars (CI fails).
- Don't touch `audit_log` writes without re-running the [security/rls-checklist.md](security/rls-checklist.md).
- Don't merge during a Sentry-paged incident — wait for the all-clear.

## Reporting a security issue

Email `hemantkumar.bk@gmail.com` with subject `SECURITY`. **Don't open a public issue.** We aim to triage within 72h.
