# Saathi Release Feature Ledger

Last verified: 2026-10-15 UTC

- Main baseline for this branch: `468a11bd7247f9a0a9121a8daa0f20a7ca42654f` after PR #57, #59, #61 and #63.
- P0/P1 API proxy and freshness: [PR #57](https://github.com/kaustubhdua/Saathi/pull/57), merged.
- Household identity fail-closed guard: [PR #59](https://github.com/kaustubhdua/Saathi/pull/59), merged.
- Telephony callback lifecycle and live-call safety gate: [PR #61](https://github.com/kaustubhdua/Saathi/pull/61), merged.
- Dashboard keyboard accessibility and truthful status labels: [PR #63](https://github.com/kaustubhdua/Saathi/pull/63), merged.
- Phone OTP identity and purpose-specific household consent: [PR #65](https://github.com/kaustubhdua/Saathi/pull/65), draft pending CI and migration dependency.
- Shared production rate limiting: [PR #64](https://github.com/kaustubhdua/Saathi/pull/64), pending CI.
- Migration quarantine/index proposal: [PR #58](https://github.com/kaustubhdua/Saathi/pull/58), draft; do not merge until all environments' migration histories are reconciled.
- [Release acceptance matrix](RELEASE_ACCEPTANCE_MATRIX.md)
- [Provider verification plan](PROVIDER_VERIFICATION.md)
- Deployment policy: no Vercel production deployment before 2026-10-24.

## Verified

- The Nihdhoom project was reviewed read-only and contained eight Saathi-prefixed tables with RLS enabled and browser-role access denied. No live database migration or production deployment was performed.
- PR #57 merged as `e8a13bdd0022f33707e6a9338d3cc7fcdf039615`; exact-head CI run #770 passed all five jobs, and main run #771 passed.
- PR #59 merged as `d048170180a24a36280c557150753c687139d9d7`; exact-head CI run #774 passed all five jobs. Production text/voice routes reject caller-supplied household UUIDs unless verified identity context is supplied by the trusted server proxy.
- PR #61 merged after exact-head CI run #782 passed all five jobs. Webhook processing uses body-derived idempotency, monotonic call-state transitions and a server-configured callback URL. Live outbound calls fail closed until the actual callback authentication contract is verified.
- PR #63 merged after CI passed. Scenario tabs support keyboard navigation; voice/API/answer state is announced; the UI no longer claims consent was collected before it is.

## Partial — PR #65 pending CI, migration and provider configuration

- Supabase SSR phone OTP login routes and a login page are added. SMS delivery still requires enabling Supabase Phone Auth and configuring the SMS provider in the project dashboard.
- The server verifies the Supabase user and confirmed E.164 phone, then maps the immutable Supabase Auth user ID through the proposed `saathi_household_memberships` table; a phone number alone never grants access. First-login household rows start with memory and outbound-call consent disabled. The membership migration remains proposed until PR #58 migration-history reconciliation is approved.
- The public proxy injects verified identity/household headers only from the server-side session resolver. The backend rejects client-supplied household IDs and requires both verified headers for household-specific routes.
- Purpose-specific memory and outbound-call consent status/update endpoints and UI controls are added. Memory consent is explicitly described as permission for future storage because automatic conversation-memory writes are not yet connected.
- The proxy exposes only readiness, agent, voice and purpose-specific consent routes. Outbound call APIs and task APIs remain unavailable to the browser.
- These changes require server-only `SUPABASE_URL` and `SUPABASE_SECRET_KEY` on the frontend host, public `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, configured SMS delivery, and live OTP/consent tests. The secret key must never use a `NEXT_PUBLIC_*` variable.

## Other partial implementation

- Scheme catalogue data carries reviewed/stale/unknown freshness rather than a false live retrieval timestamp. Current eligibility and deadlines still need official portal verification.
- Mandi records with invalid, future-dated or over-seven-day observations are withheld from current-price claims. Live OGD record selection, market ambiguity and units still need provider-backed verification.
- Consent and task repository/schema foundations exist, but automatic memory writes, durable reminder dispatch, volunteer assignment/resolution and cross-household integration tests remain incomplete.
- PR #58 quarantines two unprefixed legacy migrations outside active discovery, adds a namespace test, and proposes three Saathi-only indexes. Keep it draft until migration history is reconciled across every relevant environment.

## Blocked / not tested

- No real Open-Meteo, OGD/AGMARKNET, Sarvam STT/TTS, document AI or Exotel round-trip test is claimed.
- Exotel callback authentication remains unverified: the current webhook requires an HMAC over the raw body, and official callback docs do not establish that Exotel supplies the custom HMAC header. Keep `TELEPHONY_CALLBACK_SIGNATURE_VERIFIED=false` until verified with the actual provider or trusted signer.
- A reviewed frontend lockfile and `npm ci`, mobile/browser screen-reader tests, full WCAG 2.2 AA audit, reduced-motion/contrast checks, Lighthouse/Core Web Vitals, SEO, monitoring, rollback evidence and deployed SHA remain outstanding.
- Vercel deployment/configuration remains deferred until 2026-10-24.

## Next actions

1. Finish CI on PR #65; fix any frontend TypeScript/build, backend, or proxy test failures before review. Keep it draft until the proposed membership migration can be safely activated after PR #58.
2. Configure Supabase Phone Auth and SMS delivery, then verify OTP, session refresh, sign-out, first-household creation and purpose-specific consent against an isolated test household.
3. Prove memory consent/revocation through the actual repository and database trigger; connect memory writes only after identity and consent tests pass.
4. Keep PR #58 draft until migration history is reconciled across environments; do not apply live DDL before approval.
5. Test real providers with authorized credentials and attach redacted evidence. Keep phone AI unavailable until callback signature verification is proven.
6. Complete durable reminder/volunteer workflows, reproducible frontend builds, accessibility/performance checks, monitoring and rollback evidence.
7. Deploy only after 2026-10-24 and only after the release matrix's required gates are satisfied.
