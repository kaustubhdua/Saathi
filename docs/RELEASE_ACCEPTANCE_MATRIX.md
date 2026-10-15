# Saathi release acceptance matrix

Last updated: 2026-10-15 UTC

This is an evidence ledger, not a declaration that release gates have passed. Automated CI and manual/live-provider acceptance are tracked separately. A checked item must link to reproducible evidence for the exact candidate SHA.

## Current baseline

- Main baseline for this branch: `edd5164fc406b87a5ab811d9746ad21e7e4c1d1f` after PR #66 (reproducible frontend lockfile and `npm ci`).
- PR #57 (API proxy/source freshness), #59 (identity fail-closed guard), #61 (telephony callback state handling), #63 (dashboard accessibility) and #64 (shared production rate limiting) are merged.
- PR #70 adds phone OTP, household PIN, user-to-household mapping and consent workflows. CI passed on the code candidate; migration activation and live Auth/SMS tests remain outstanding.
- PR #71 adds household-scoped task list/create/complete/cancel endpoints and dashboard controls. CI and live database tenant-isolation verification are tracked separately.
- PR #58 remains draft because other environments' migration histories are not verified.
- Production Vercel configuration/deployment remains deferred until 2026-10-24.
- No live provider test, live database DDL, or production deployment is claimed here.

## Manual release gates

| # | Acceptance gate | Status | Evidence required |
|---|---|---|---|
| 1 | Browser API requests use the same-origin allowlisted proxy; server token never enters browser bundles | CODE + CI | PR #57 merged; inspect production build/environment and run hosted request tests |
| 2 | Production readiness fails when operator auth is absent | CODE + CI | Backend tests pass; verify real deployment configuration |
| 3 | Production API traffic uses shared rate limiting and trusted client IP | CODE; DEPLOYMENT BLOCKED | PR #64 merged; configure Upstash credentials and verify hosting overwrites the trusted single-IP header |
| 4 | Verified identity maps to a household; caller-supplied UUID cannot select another household | PARTIAL — PR #70 draft | Phone OTP and household PIN code are present; review/apply auth-user membership migration after PR #58 reconciliation, then test number-recycling isolation |
| 5 | Consent grant/status/revocation are persisted and identity-bound | PARTIAL — PR #65 draft | Consent UI/API added in PR #70; verify real Supabase Auth, household mapping and persistence in an isolated test household |
| 6 | Memory writes require current consent; revocation deletes memory | PARTIAL — PR #72 | Manual save/list/delete endpoints require persisted consent; the database trigger re-checks consent while serializing writes against revocation and purges memory on revoke. Live DB race/isolation tests and automatic extraction remain outstanding |
| 7 | Two households cannot read/update each other's tasks, memory or cases | PARTIAL — PR #71 | Task endpoints scope reads/status changes to the verified household and prefix idempotency keys; verify with two real test identities. Memory and volunteer-case isolation remain unverified |
| 8 | Live weather and mandi results have correct source and observation/retrieval timestamps | NOT VERIFIED | Authorized provider tests; validate units, location matching, freshness and failure cases |
| 9 | Browser voice completes real STT -> tool -> TTS with measured latency | NOT VERIFIED | Provider credentials, browser matrix, STT/TTS round-trip logs and p50/p95 latency |
| 10 | Outbound phone calls require persisted purpose-specific consent; webhooks update call lifecycle idempotently | PARTIAL / FAIL-CLOSED | PR #61 adds state processing; keep live calls disabled until the real provider signature contract is proven and consent is checked on the actual call path |
| 11 | Reminder/volunteer workflows persist, dispatch, retry, assign and resolve correctly | NOT COMPLETE | Durable dispatcher, atomic claims, retry/quiet-hour tests and operator queue evidence |
| 12 | Mobile, keyboard, screen-reader, reduced-motion and WCAG 2.2 AA-oriented checks pass | PARTIAL | PR #63 adds keyboard tab navigation and live regions; complete real-device/browser and accessibility audit |
| 13 | Core Web Vitals, SEO, responsive behavior and error states are measured and pass | NOT VERIFIED | Lighthouse/field data, SEO checks and hosted browser smoke results |
| 14 | Reproducible frontend build uses a reviewed lockfile and npm ci | NOT COMPLETE | Generate and commit frontend/package-lock.json, switch CI to npm ci and verify exact SHA |
| 15 | Exact release commit has complete CI, deployed SHA, smoke tests, monitoring and rollback evidence | NOT COMPLETE | All manual gates, deployment evidence, runbook and rollback rehearsal |

## Evidence links

- [PR #57](https://github.com/kaustubhdua/Saathi/pull/57) — API proxy and source freshness.
- [PR #59](https://github.com/kaustubhdua/Saathi/pull/59) — fail-closed household ID guard.
- [PR #61](https://github.com/kaustubhdua/Saathi/pull/61) — webhook state processing and live-call gate.
- [PR #63](https://github.com/kaustubhdua/Saathi/pull/63) — dashboard accessibility contracts and truthful labels.
- [PR #64](https://github.com/kaustubhdua/Saathi/pull/64) — shared production rate limiting.
- [PR #65](https://github.com/kaustubhdua/Saathi/pull/65) — phone OTP, household mapping and consent (draft).
- [PR #58](https://github.com/kaustubhdua/Saathi/pull/58) — migration safety and Saathi-only indexes (draft).
- [Provider verification plan](PROVIDER_VERIFICATION.md).

## Release rule

Do not call Saathi production-complete while any P0 authorization, migration safety, provider authentication, or manual acceptance gate is unresolved. Never infer live-provider success from mocked tests or a green build.
