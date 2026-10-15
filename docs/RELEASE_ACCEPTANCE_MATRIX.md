# Saathi release acceptance matrix

Last updated: 2026-10-16 UTC

This is an evidence ledger, not a declaration that release gates have passed. Automated CI and manual/live-provider acceptance are tracked separately. A checked item must link to reproducible evidence for the exact candidate SHA.

## Current baseline

- Main baseline for this branch: `edd5164fc406b87a5ab811d9746ad21e7e4c1d1f` after PR #66.
- PR #57 (API proxy/source freshness), #59 (identity fail-closed guard), #61 (telephony callback state handling), #63 (dashboard accessibility) and #64 (shared production rate limiting) are merged.
- PR #68 contains phone OTP, household PIN, consent, household task APIs, explicit user-entered memory, accessible error states, atomic household enrollment through a proposed server-only RPC, and bounded streaming JSON parsing for auth mutations. The enrollment RPC uses a fixed `pg_catalog` search path, serializes by Auth user ID, and has contract assertions for grants and conflict handling. Exact-tree CI run #945 passed all five jobs on `0d8a68aaa471370d4aed065b7b1b238726c50c12`; live Auth/SMS and isolated database acceptance remain outstanding.
- Trusted-IP validation, bounded development limiter storage, phone-enrollment collision isolation, and bounded auth request bodies (size + read deadline) have regression coverage. Live Auth/SMS and migration activation remain outstanding.
- Read-only live verification found six recorded Saathi migrations, including `saathi_memory_consent_locking`, eight Saathi tables with RLS enabled, and no `saathi_household_memberships` table. Authenticated household actions therefore remain fail-closed until the membership migration is approved and applied safely.
- A separate Supabase project named `Saathi` in `ap-northeast-2` is inactive and its migration-history query timed out. It was not restored; do not restore it without explicit operator approval. Migration reconciliation remains incomplete until this environment is safely inspected.
- PR #58 remains draft because other environments' migration histories are not verified; its latest exact-head CI run #840 passed all five jobs.
- Production Vercel configuration/deployment remains deferred until 2026-10-24.
- No live provider test, live database DDL, or production deployment is claimed here.

## Manual release gates

| # | Acceptance gate | Status | Evidence required |
|---|---|---|---|
| 1 | Browser API requests use the same-origin allowlisted proxy; server token never enters browser bundles | CODE + CI | PR #57 merged; inspect production build/environment and run hosted request tests |
| 2 | Production readiness fails when operator auth is absent | CODE + CI | Backend tests pass; verify real deployment configuration |
| 3 | Production API traffic uses shared rate limiting and trusted client IP | CODE; DEPLOYMENT BLOCKED | PR #64 merged; auth follow-up rejects missing/ambiguous IPs before Redis access; configure Upstash credentials and verify hosting overwrites the trusted single-IP header |
| 4 | Verified identity maps to a household; caller-supplied UUID cannot select another household | PARTIAL — PR #68 draft | Phone OTP and PIN code are code + CI validated; trusted-IP fail-closed, concurrent phone-collision isolation and anonymous chat/voice fallback are covered by regression tests. Review/apply auth-user membership migration only after PR #58 reconciliation, then test number-recycling isolation in an isolated environment |
| 5 | Consent grant/status/revocation are persisted and identity-bound | PARTIAL — PR #68 draft | CI covers API contracts; verify real Supabase Auth, household mapping and persisted grant/revoke behavior in an isolated test household |
| 6 | Memory reads/writes require current consent; revocation deletes memory | API + ACTIVE LOCKING MIGRATION; LIVE RACE TEST PENDING | PR #68 adds user-entered save/list/delete with persisted consent checks and database guard rejection handling. Active migration `20261014222432_saathi_memory_consent_locking.sql` uses `SELECT ... FOR UPDATE`; regression tests and read-only SQL confirm the lock and trigger binding. Test concurrent revoke/write in an isolated DB. Automatic extraction remains disabled. |
| 7 | Two households cannot read/update each other's tasks, memory or cases | CODE + UNIT TESTS; LIVE ISOLATION NOT VERIFIED | PR #68 scopes task/memory API and repository operations to the verified household; prove with two real identities and a non-production database before release |
| 8 | Live weather and mandi results have correct source and observation/retrieval timestamps | NOT VERIFIED | Authorized provider tests; validate units, location matching, freshness and failure cases |
| 9 | Browser voice completes real STT -> tool -> TTS with measured latency | NOT VERIFIED | Provider credentials, browser matrix, STT/TTS round-trip logs and p50/p95 latency |
| 10 | Outbound phone calls require persisted purpose-specific consent; webhooks update call lifecycle idempotently | PARTIAL / FAIL-CLOSED — CALLBACK AUTH CONTRACT UNVERIFIED | Current handler requires `X-Saathi-Signature`. Exotel's documented ExoML event endpoint uses configured `Authorization: Basic` and does not support custom headers; this does not prove the legacy `Calls/connect` `StatusCallback` contract. Confirm the actual provider mode, implement its matching auth/payload handler, and run an authorized provider test before enabling calls. [Official Exotel docs](https://docs.exotel.com/voice-apis/implementing-your-https-event-endpoint-for-real-time-call-events?open=browser) |
| 11 | Reminder/volunteer workflows persist, dispatch, retry, assign and resolve correctly | NOT COMPLETE | Durable dispatcher, atomic claims, retry/quiet-hour tests and operator queue evidence |
| 12 | Mobile, keyboard, screen-reader, reduced-motion and WCAG 2.2 AA-oriented checks pass | PARTIAL | PR #63 adds keyboard tab navigation and live regions; complete real-device/browser and accessibility audit |
| 13 | Core Web Vitals, SEO, responsive behavior and error states are measured and pass | PARTIAL — PR #68 DRAFT | Branded 404/route/global error boundaries and dashboard noindex metadata are included. Local build/smoke checks run in CI; Lighthouse/field data, hosted browser smoke and full accessibility audit remain outstanding. Use the latest exact-head run linked from PR #68. |
| 14 | Reproducible frontend build uses a reviewed lockfile and npm ci | CODE + CI PASS | Lockfile committed on main; run #818 passed all five CI jobs on `edd5164fc406b87a5ab811d9746ad21e7e4c1d1f`. `npm ci` full-tree audit reports five high-severity dev-only Next/ESLint-chain advisories, rooted in `braces@3.0.3` with no patched upstream version listed ([GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)). Production-only audit passes. The suggested `eslint-config-next@14.2.35` downgrade is a major-version mismatch for Next `16.3.8`; do not force it. Monitor upstream and re-audit |
| 15 | Exact release commit has complete CI, deployed SHA, smoke tests, monitoring and rollback evidence | NOT COMPLETE | All manual gates, deployment evidence, runbook and rollback rehearsal |

## Evidence links

- [PR #57](https://github.com/kaustubhdua/Saathi/pull/57) — API proxy and source freshness.
- [PR #59](https://github.com/kaustubhdua/Saathi/pull/59) — fail-closed household ID guard.
- [PR #61](https://github.com/kaustubhdua/Saathi/pull/61) — webhook state processing and live-call gate.
- [PR #63](https://github.com/kaustubhdua/Saathi/pull/63) — dashboard accessibility contracts and truthful labels.
- [PR #64](https://github.com/kaustubhdua/Saathi/pull/64) — shared production rate limiting.
- [PR #68](https://github.com/kaustubhdua/Saathi/pull/68) — phone OTP, household PIN, consent, tasks and explicit memory (draft; exact-tree run #945 green).
- [PR #58](https://github.com/kaustubhdua/Saathi/pull/58) — migration safety and Saathi-only indexes (draft).
- [Provider verification plan](PROVIDER_VERIFICATION.md).

## Release rule

Do not call Saathi production-complete while any P0 authorization, migration safety, provider authentication, or manual acceptance gate is unresolved. Never infer live-provider success from mocked tests or a green build.
