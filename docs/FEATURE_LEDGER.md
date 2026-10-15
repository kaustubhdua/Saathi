# Saathi Release Feature Ledger

Last verified: 2026-10-15 UTC

- Main baseline for this branch: `edd5164fc406b87a5ab811d9746ad21e7e4c1d1f` after PR #66.
- P0/P1 API proxy and source freshness: [PR #57](https://github.com/kaustubhdua/Saathi/pull/57), merged.
- Household identity fail-closed guard: [PR #59](https://github.com/kaustubhdua/Saathi/pull/59), merged.
- Telephony callback lifecycle and live-call safety gate: [PR #61](https://github.com/kaustubhdua/Saathi/pull/61), merged.
- Dashboard keyboard accessibility and truthful status labels: [PR #63](https://github.com/kaustubhdua/Saathi/pull/63), merged.
- Shared production rate limiting: [PR #64](https://github.com/kaustubhdua/Saathi/pull/64), merged; production requires configured Upstash Redis and a trusted single-IP header.
- Phone OTP, household PIN, purpose-specific consent, household tasks and explicit memory: [PR #68](https://github.com/kaustubhdua/Saathi/pull/68), draft. Exact-head CI run #894 passed all five jobs on `ae17c5e1f7b5daa6f0fce6a60228c79292f87f5c`, including the active memory-consent lock/trigger regression test. Live Auth/SMS, migration-history and provider gates remain.
- Migration quarantine/index proposal: [PR #58](https://github.com/kaustubhdua/Saathi/pull/58), draft; do not merge until all environments' migration histories are reconciled.
- [Release acceptance matrix](RELEASE_ACCEPTANCE_MATRIX.md)
- [Provider verification plan](PROVIDER_VERIFICATION.md)
- Deployment policy: no Vercel production deployment before 2026-10-24.

## Verified

- Read-only verification of the Nihdhoom project on 2026-10-15 confirms eight `saathi_*` tables with RLS enabled, six recorded Saathi migrations including `saathi_memory_consent_locking`, and no `saathi_household_memberships` table. The two legacy unprefixed migration versions/tables remain absent in this project. No live DDL or production deployment was performed; other target environments still need migration-history reconciliation.
- A separate Supabase project named `Saathi` in `ap-northeast-2` is `INACTIVE`; its read-only migration-history query timed out. It was not restored. That environment remains unverified, and restoration must not be attempted without explicit operator approval.
- PR #57 merged as `e8a13bdd0022f33707e6a9338d3cc7fcdf039615`; exact-head CI run #770 passed all five jobs, and main run #771 passed.
- PR #59 merged as `d048170180a24a36280c557150753c687139d9d7`; exact-head CI run #774 passed all five jobs.
- PR #61 merged after exact-head CI run #782 passed all five jobs. Callback state processing is implemented, but live calls remain disabled until the real provider authentication contract is verified.
- PR #63 merged after frontend accessibility contract tests and full CI passed.
- PR #64 merged after CI run #796 passed. Production API requests now fail closed unless shared Upstash rate limiting and a trusted single-IP header are configured. The Upstash credentials and hosting-header behavior have not been verified in a live deployment.

## Partial — PR #68 integrated auth, consent, tasks and explicit memory

- Supabase SSR phone OTP login routes and an accessible login page are added. SMS delivery requires enabling Supabase Phone Auth and configuring the SMS provider in the project dashboard.
- The server verifies the Supabase user and confirmed E.164 phone, then maps the immutable Supabase Auth user ID through the proposed `saathi_household_memberships` table. A phone number alone never grants access, avoiding recycled-number takeover.
- New household rows start with memory and outbound-call consent disabled. Purpose-specific consent status/update endpoints and UI controls are added.
- The proxy injects verified identity/household headers only from the server-side session resolver; the backend validates both UUIDs and rejects client-supplied household IDs.
- Memory consent is explicitly described as permission for future storage because automatic conversation-memory writes are not yet connected.
- The membership migration remains proposed outside active discovery until PR #58's migration-history reconciliation is approved. Until that table exists, household-specific requests fail closed. Enrollment now creates a separate phone-unlinked household if a concurrent unique-phone insert conflicts; it never adopts a household by looking up the conflicting phone number.
- The feature requires public `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (or the existing public anon key), plus server-only `SUPABASE_URL` and `SUPABASE_SECRET_KEY`. Never expose the secret key through `NEXT_PUBLIC_*`.
- The authentication rate limiter rejects missing, malformed or comma-separated trusted client IP values in production before any Upstash request; development retains a local fallback and caps bucket storage at 5,000 entries. The household enrollment flow also isolates concurrent phone-number uniqueness conflicts rather than adopting an existing household. Both fixes and regression tests are committed to this auth branch; exact-head CI run #894 passed all five jobs on `ae17c5e1f7b5daa6f0fce6a60228c79292f87f5c`.

## Candidate integration — household tasks and explicit memory

- Task and memory API/UI changes from PRs #71/#72 have been ported onto the current authentication branch. The task/memory patches are included in the consolidated auth candidate; exact-head CI run #894 passed all five jobs on `ae17c5e1f7b5daa6f0fce6a60228c79292f87f5c`. This remains a draft branch, not main or production.
- Task list/create/status routes use verified household context; idempotency-conflict recovery is additionally household-filtered and rejects mismatched rows. Automatic reminder dispatch and callback delivery remain disabled.
- Memory list/write/delete routes require current persisted memory consent and explicit user input; automatic conversation extraction is not connected. Database trigger behavior and revocation races still require isolated live-database acceptance.

## Other partial implementation

- Scheme catalogue data carries reviewed/stale/unknown freshness rather than a false live retrieval timestamp. Eligibility and deadlines still need official portal verification.
- Mandi records with invalid, future-dated or over-seven-day observations are withheld from current-price claims. Live OGD record selection, market ambiguity and units still need provider-backed verification.
- Household task list/create/status endpoints and dashboard actions now persist through household-scoped repositories. Scheduled reminder delivery and automatic callbacks remain disabled.
- User-entered memory list/save/delete is consent-gated, expiry-filtered and household-scoped. Automatic conversation-memory extraction remains disabled; deletion stays available when consent is off.
- The active migration `supabase/migrations/20261014222432_saathi_memory_consent_locking.sql` uses `SELECT ... FOR UPDATE` to serialize memory writes against revocation. A regression test verifies the lock and trigger attachment; a read-only SQL query also confirmed the live Nihdhoom function has the row lock and the trigger is attached to `saathi_household_memories`. A concurrent revoke/write integration test is still needed in an isolated environment. No duplicate migration is needed.
- PR #58 quarantines two unprefixed legacy migrations outside active discovery, adds a namespace guard covering DDL/DML/read references, and proposes three Saathi-only indexes. CI run #840 passed all five jobs on `bb0b9c50dd3c0eb2d2d09dde5554d857b98088dd`; keep it draft until migration history is reconciled across every relevant environment.

## Blocked / not tested

- No real Open-Meteo, OGD/AGMARKNET, Sarvam STT/TTS, document AI or Exotel round-trip test is claimed.
- Exotel callback authentication remains unverified: the current webhook requires an HMAC over the raw body, and official callback docs do not establish that Exotel supplies the custom HMAC header. Keep `TELEPHONY_CALLBACK_SIGNATURE_VERIFIED=false` until verified with the actual provider or trusted signer.
- Upstash shared rate limiting and the hosting platform's trusted-IP header must be configured/tested before production traffic; code intentionally fails closed otherwise.
- PR #66 added the frontend lockfile and switched CI to `npm ci`; PR #68 regenerated the lockfile for the Supabase dependencies. Exact-head CI run #848 passed all five jobs, including `npm ci`, lint, Node tests, TypeScript, build, backend pytest/API smoke, dependency audit, Docker build and Streamlit smoke. Mobile/browser screen-reader tests, full WCAG 2.2 AA audit, reduced-motion/contrast checks, Lighthouse/Core Web Vitals, SEO, monitoring, rollback evidence and deployed SHA remain outstanding.
- Vercel deployment/configuration remains deferred until 2026-10-24.

## Next actions

1. Keep PR #68 draft until migration history, live Auth/SMS, household isolation and provider acceptance gates are satisfied; exact-head CI is green but is not production acceptance. Configure Supabase Phone Auth/SMS and server-only secrets, then test OTP, household PIN, task isolation and consent in an isolated environment.
2. Configure Supabase Phone Auth and SMS delivery, then verify OTP, session refresh, sign-out, first-household creation, phone-number recycling isolation and consent behavior against an isolated test household.
3. Confirm the existing `saathi_memory_consent_locking` migration is present in each target environment, reconcile migration history, and verify concurrent memory write/revocation against an isolated database. Keep automatic extraction disabled.
4. Keep PR #58 draft until migration history is reconciled across environments; do not apply live DDL before approval.
5. Configure/test Upstash and the hosting platform's trusted IP header before enabling production API traffic.
6. Test real providers with authorized credentials and attach redacted evidence. Keep phone AI unavailable until callback signature verification is proven.
7. Complete durable reminder dispatch and volunteer queue, real provider tests, accessibility/performance checks, monitoring and rollback evidence.
8. Deploy only after 2026-10-24 and only after the release matrix's required gates are satisfied.
