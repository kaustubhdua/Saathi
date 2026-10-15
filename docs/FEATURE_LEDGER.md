# Saathi Release Feature Ledger

Last verified: 2026-10-15 UTC

- Main baseline for this branch: `edd5164fc406b87a5ab811d9746ad21e7e4c1d1f` after PR #66.
- P0/P1 API proxy and source freshness: [PR #57](https://github.com/kaustubhdua/Saathi/pull/57), merged.
- Household identity fail-closed guard: [PR #59](https://github.com/kaustubhdua/Saathi/pull/59), merged.
- Telephony callback lifecycle and live-call safety gate: [PR #61](https://github.com/kaustubhdua/Saathi/pull/61), merged.
- Dashboard keyboard accessibility and truthful status labels: [PR #63](https://github.com/kaustubhdua/Saathi/pull/63), merged.
- Shared production rate limiting: [PR #64](https://github.com/kaustubhdua/Saathi/pull/64), merged; production requires configured Upstash Redis and a trusted single-IP header.
- Phone OTP, household PIN and purpose-specific consent: [PR #68](https://github.com/kaustubhdua/Saathi/pull/68), draft; exact-head CI run #848 passed all five jobs on `5892a7321a509cff12471b147b4c7d3988ab1cd2`. Migration and live provider gates remain.
- Migration quarantine/index proposal: [PR #58](https://github.com/kaustubhdua/Saathi/pull/58), draft; do not merge until all environments' migration histories are reconciled.
- [Release acceptance matrix](RELEASE_ACCEPTANCE_MATRIX.md)
- [Provider verification plan](PROVIDER_VERIFICATION.md)
- Deployment policy: no Vercel production deployment before 2026-10-24.

## Verified

- The Nihdhoom project was reviewed read-only and contained eight Saathi-prefixed tables with RLS enabled and browser-role access denied. No live database migration or production deployment was performed.
- PR #57 merged as `e8a13bdd0022f33707e6a9338d3cc7fcdf039615`; exact-head CI run #770 passed all five jobs, and main run #771 passed.
- PR #59 merged as `d048170180a24a36280c557150753c687139d9d7`; exact-head CI run #774 passed all five jobs.
- PR #61 merged after exact-head CI run #782 passed all five jobs. Callback state processing is implemented, but live calls remain disabled until the real provider authentication contract is verified.
- PR #63 merged after frontend accessibility contract tests and full CI passed.
- PR #64 merged after CI run #796 passed. Production API requests now fail closed unless shared Upstash rate limiting and a trusted single-IP header are configured. The Upstash credentials and hosting-header behavior have not been verified in a live deployment.

## Partial — PR #68 CI green; migration and provider configuration pending

- Supabase SSR phone OTP login routes and an accessible login page are added. SMS delivery requires enabling Supabase Phone Auth and configuring the SMS provider in the project dashboard.
- The server verifies the Supabase user and confirmed E.164 phone, then maps the immutable Supabase Auth user ID through the proposed `saathi_household_memberships` table. A phone number alone never grants access, avoiding recycled-number takeover.
- New household rows start with memory and outbound-call consent disabled. Purpose-specific consent status/update endpoints and UI controls are added.
- The proxy injects verified identity/household headers only from the server-side session resolver; the backend validates both UUIDs and rejects client-supplied household IDs.
- Memory consent is explicitly described as permission for future storage because automatic conversation-memory writes are not yet connected.
- The membership migration remains proposed outside active discovery until PR #58's migration-history reconciliation is approved. Until that table exists, household-specific requests fail closed.
- The feature requires public `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (or the existing public anon key), plus server-only `SUPABASE_URL` and `SUPABASE_SECRET_KEY`. Never expose the secret key through `NEXT_PUBLIC_*`.

## Other partial implementation

- Scheme catalogue data carries reviewed/stale/unknown freshness rather than a false live retrieval timestamp. Eligibility and deadlines still need official portal verification.
- Mandi records with invalid, future-dated or over-seven-day observations are withheld from current-price claims. Live OGD record selection, market ambiguity and units still need provider-backed verification.
- Consent and task repository/schema foundations exist, but automatic memory writes, durable reminder dispatch, volunteer assignment/resolution and cross-household integration tests remain incomplete.
- PR #58 quarantines two unprefixed legacy migrations outside active discovery, adds a namespace guard covering DDL/DML/read references, and proposes three Saathi-only indexes. CI run #840 passed all five jobs on `bb0b9c50dd3c0eb2d2d09dde5554d857b98088dd`; keep it draft until migration history is reconciled across every relevant environment.

## Blocked / not tested

- No real Open-Meteo, OGD/AGMARKNET, Sarvam STT/TTS, document AI or Exotel round-trip test is claimed.
- Exotel callback authentication remains unverified: the current webhook requires an HMAC over the raw body, and official callback docs do not establish that Exotel supplies the custom HMAC header. Keep `TELEPHONY_CALLBACK_SIGNATURE_VERIFIED=false` until verified with the actual provider or trusted signer.
- Upstash shared rate limiting and the hosting platform's trusted-IP header must be configured/tested before production traffic; code intentionally fails closed otherwise.
- PR #66 added the frontend lockfile and switched CI to `npm ci`; PR #68 regenerated the lockfile for the Supabase dependencies. Exact-head CI run #848 passed all five jobs, including `npm ci`, lint, Node tests, TypeScript, build, backend pytest/API smoke, dependency audit, Docker build and Streamlit smoke. Mobile/browser screen-reader tests, full WCAG 2.2 AA audit, reduced-motion/contrast checks, Lighthouse/Core Web Vitals, SEO, monitoring, rollback evidence and deployed SHA remain outstanding.
- Vercel deployment/configuration remains deferred until 2026-10-24.

## Next actions

1. Keep PR #68 draft until the membership migration can be safely activated after PR #58 is reconciled. Configure Supabase Phone Auth/SMS and server-only secrets, then test the full identity/consent flow in an isolated environment.
2. Configure Supabase Phone Auth and SMS delivery, then verify OTP, session refresh, sign-out, first-household creation, phone-number recycling isolation and consent behavior against an isolated test household.
3. Prove memory consent/revocation through the actual repository and database trigger; connect memory writes only after identity and consent tests pass.
4. Keep PR #58 draft until migration history is reconciled across environments; do not apply live DDL before approval.
5. Configure/test Upstash and the hosting platform's trusted IP header before enabling production API traffic.
6. Test real providers with authorized credentials and attach redacted evidence. Keep phone AI unavailable until callback signature verification is proven.
7. Complete durable reminder/volunteer workflows, reproducible frontend builds, accessibility/performance checks, monitoring and rollback evidence.
8. Deploy only after 2026-10-24 and only after the release matrix's required gates are satisfied.
