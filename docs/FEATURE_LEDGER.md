# Saathi Release Feature Ledger

Last verified: 2026-10-15 UTC

- Main baseline before this branch's merge: `e8a13bdd0022f33707e6a9338d3cc7fcdf039615`; PR #59 has since merged as `d048170180a24a36280c557150753c687139d9d7`.
- P0/P1 proxy and freshness: [PR #57](https://github.com/kaustubhdua/Saathi/pull/57), merged.
- Household identity fail-closed guard: [PR #59](https://github.com/kaustubhdua/Saathi/pull/59), merged.
- Telephony callback lifecycle and live-call safety gate: [PR #60](https://github.com/kaustubhdua/Saathi/pull/60), under CI review.
- Migration quarantine/index proposal: [PR #58](https://github.com/kaustubhdua/Saathi/pull/58), draft; do not merge until all environments' migration histories are reconciled.
- [Release acceptance matrix](RELEASE_ACCEPTANCE_MATRIX.md)
- [Provider verification plan](PROVIDER_VERIFICATION.md)
- Deployment policy: no Vercel production deployment before 2026-10-24.

Statuses are evidence-based. Database schema readiness does not imply that a user-facing workflow is integrated.

## PASS — verified

- **Shared database identity:** Supabase project `igqgtlmnwssjaoxkkzbm`, named `nihdhoom`, status `ACTIVE_HEALTHY` in the latest read-only review.
- **Namespaced schema:** eight Saathi-only tables were observed: `saathi_conversations`, `saathi_telephony_webhook_events`, `saathi_households`, `saathi_household_memories`, `saathi_pending_tasks`, `saathi_volunteer_cases`, `saathi_calls`, and `saathi_call_events`.
- **Client isolation:** all eight observed Saathi tables had RLS enabled and browser roles denied access. No live database write or migration was performed in this work.
- **Consent database foundation:** existing migrations define purpose-specific consent timestamps, a memory-write consent trigger, and memory purge on revocation. Full user-facing consent workflow and live integration tests remain incomplete.
- **API proxy and source freshness:** PR #57 merged. Its exact-head CI run #770 passed all five jobs; main push run #771 passed all five jobs on `e8a13bdd0022f33707e6a9338d3cc7fcdf039615`.
- **Household ID fail-closed behavior:** PR #59 merged after CI run #774 passed all five jobs on its exact head. Production text/voice requests cannot use a client-provided household UUID as proof of identity.
- **Release evidence ledger:** manual acceptance requirements are listed in `docs/RELEASE_ACCEPTANCE_MATRIX.md`; items are not marked passed without evidence.

## PARTIAL — implementation exists, integration remains

- **Frontend API security:** dashboard requests use a same-origin allowlisted server proxy; server-only token injection is required in production; production readiness fails closed when operator auth is missing. Hosted deployment behavior is not yet verified.
- **Household identity:** production household IDs fail closed until verified identity-to-household ownership exists. This is a protective denial, not an implemented login or identity provider.
- **Scheme freshness:** static catalogue responses no longer claim a live retrieval timestamp and carry reviewed/stale/unknown status. Eligibility and deadlines still need official portal verification.
- **Mandi freshness:** missing, invalid, future-dated or over-seven-day observations are withheld from current-price claims. Live OGD record selection and units still need provider-backed verification.
- **Migration reconciliation:** PR #58 quarantines two unprefixed legacy migrations outside active discovery, adds a namespace regression test, and proposes three Saathi-only indexes. Do not merge or apply until migration history is reconciled across environments.
- **Conversation metadata:** server adapter targets the namespaced table; real PostgREST writes require server-side Nihdhoom credentials.
- **Consent/task repositories:** server-side repository foundations and tests exist, but authenticated household/task routes are not yet connected to a verified user session.
- **Memory/tasks/volunteer cases:** schema and consent protections exist. End-to-end ownership, memory deletion UX, durable reminder dispatcher, assignment and resolution queue remain incomplete.
- **Webhook lifecycle (PR #60):** proposed code parses signed JSON/form callbacks, derives idempotency from the signed body, and applies monotonic call state transitions. This remains unmerged and uses mocked provider/database tests.
- **Telephony safety (PR #60):** live calls fail closed until a trusted public HTTPS callback URL and the real callback authentication contract have been verified. Exotel sandbox evidence is not available yet.

## BLOCKED / NOT TESTED

- **Vercel production deployment:** intentionally deferred until 2026-10-24.
- **Provider secrets and live tests:** no live Open-Meteo, OGD/AGMARKNET, Sarvam STT/TTS, document AI, or Exotel end-to-end run is claimed.
- **Exotel callback authentication:** current webhook requires an HMAC signature over the raw body; official callback docs alone do not prove the provider sends the custom HMAC header. Keep `TELEPHONY_CALLBACK_SIGNATURE_VERIFIED=false` until the deployed provider/signer contract is proven.
- **Browser household authentication:** verified login/session, household enrollment/ownership, consent grant/revocation endpoints, deletion and cross-household tests remain outstanding.
- **Build reproducibility:** CI still runs `npm install`; a reviewed frontend lockfile and `npm ci` are outstanding.
- **Browser QA:** mobile-device, keyboard, screen-reader, reduced-motion, WCAG 2.2 AA-oriented checks, Lighthouse/Core Web Vitals and SEO/production error states are not verified.
- **Production release evidence:** deployed URL/SHA, secret configuration, monitoring/alerting and rollback rehearsal are not verified.

## Shared Nihdhoom findings deliberately left untouched

The read-only advisor also flagged shared Telegram tables and SECURITY DEFINER functions, plus unused indexes on shared objects. These are not changed as part of Saathi. Keep all Saathi DDL scoped to `saathi_*` objects and do not drop shared indexes without separate ownership/workload review.

## Next actions

1. Complete CI on PR #60 and review the exact head; fix failures before merging.
2. Keep PR #58 draft until every relevant environment's migration history is reconciled.
3. Implement verified user identity and identity-to-household ownership before exposing household memory/task APIs; test cross-household denial, consent, revocation and deletion.
4. Run authorized live provider tests and save redacted evidence; do not equate adapters or mocked tests with provider verification.
5. Implement durable reminder dispatch and volunteer case workflows; complete callback-to-call-state tests using the actual provider authentication contract.
6. Add the frontend lockfile and use `npm ci`; complete accessibility, mobile, performance, SEO, monitoring and rollback evidence.
7. Keep Vercel deployment deferred until 2026-10-24; then deploy only after the release matrix's required gates are satisfied.
