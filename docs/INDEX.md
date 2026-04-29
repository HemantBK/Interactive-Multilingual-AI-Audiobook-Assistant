# Documentation index

Audience-segmented entry points. If you can answer "who am I" in one
sentence, the right doc is one click away.

## I'm a **first-time user** trying it locally

→ [QUICKSTART.md](QUICKSTART.md) — 5-min run

## I'm an **engineer** picking up the codebase

1. [ARCHITECTURE.md](ARCHITECTURE.md) — system context, sequence flows, data model
2. [adr/](adr) — why we picked the stack we picked (one ADR per decision)
3. [glossary.md](glossary.md) — terminology
4. [CONTRIBUTING.md](CONTRIBUTING.md) — branching, PR process, ADR template

## I'm **on-call** for an incident

1. [RUNBOOK.md](RUNBOOK.md) — common scenarios, kill-switch procedure
2. [SLOs.md](SLOs.md) — what's broken depends on which budget is burning
3. [SECURITY.md](SECURITY.md) §Vulnerability disclosure — for security incidents

## I'm an **auditor / security reviewer**

1. [SECURITY.md](SECURITY.md) — threat model + controls + reporting
2. [security/day-26-review.md](security/day-26-review.md) — most recent full pass
3. [security/rls-checklist.md](security/rls-checklist.md) — manual RLS verification
4. [legal/privacy.md](legal/privacy.md), [legal/terms.md](legal/terms.md), [legal/dmca.md](legal/dmca.md)

## I'm **shipping a deploy**

1. [DEPLOY.md](DEPLOY.md) — CI gates + environments + rollback
2. [SLOs.md](SLOs.md) — verify error budget allows
3. [RUNBOOK.md](RUNBOOK.md) §Rollback if it goes wrong

## I'm **labeling the eval set** on Kaggle

→ [../eval/README.md](../eval/README.md) — golden-set methodology, schema, status

## I'm reviewing **UX / accessibility**

1. [ui-states.md](ui-states.md) — every fetch's empty/loading/error state
2. [a11y-test-plan.md](a11y-test-plan.md) — NVDA + VoiceOver + axe-core scenarios

## I'm checking **what we've shipped each day**

→ [../CHANGELOG.md](../CHANGELOG.md)

## I'm reviewing the **plan**

→ [../build plan.md](../build%20plan.md) — the only active plan
