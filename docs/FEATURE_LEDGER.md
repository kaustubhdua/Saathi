# Saathi Release Feature Ledger

Last verified: 2026-10-15 UTC

- Verified main baseline after PR #66: `edd5164fc406b87a5ab811d9746ad21e7e4c1d1f` (main push CI run #818 passed all five jobs).
- P0/P1 proxy and freshness: [PR #57](https://github.com/kaustubhdua/Saathi/pull/57), merged.
- Household identity fail-closed guard: [PR #59](https://github.com/kaustubhdua/Saathi/pull/59), merged.
- Telephony callback lifecycle and live-call safety gate: [PR #61](https://github.com/kaustubhdua/Saathi/pull/61), merged.
- Migration quarantine/index proposal: [PR #58](https://github.com/kaustubhdua/Saathi/pull/58), draft; do not merge until all environments' migration histories are reconciled.
- Shared production API rate limiting: [PR #64](https://github.com/kaustubhdua/Saathi/pull/64), merged as `fb795e62f5dbaaf6d57ef150e2877382c8a32655`.
- Verified phone OTP, household PIN and purpose-specific consent: [PR #68](https://github.com/kaustubhdua/Saathi/pull/68), draft; exact-head run #851 passed all five CI jobs on `ca19ba37e6e3b27fada7094388db110ba946a16e`. The membership migration remains proposed and live SMS/Auth/session tests are not verified.
- Persistent household tasks: [PR #71](https://github.com/kaustubhdua/Saathi/pull/71), exact-head run #857 passed all five jobs on `f1a162e1c76c9579371371dca72b6b4bda5536a9`.
- Explicit consent-gated household memory: [PR #72](https://github.com/kaustubhdua/Saathi/pull/72), exact-head run #858 passed all five jobs on `974928dc794005d3b1883dffd735d982ffdb6f4a`.
- **Stack blocker:** PRs #71/#72 are based on closed, unmerged PR #70, not current auth PR #68. Their green CI is code-candidate evidence only; do not merge them directly. Port their feature diffs onto #68 and rerun exact-head CI before considering merge.
- [Release acceptance matrix](RELEASE_ACCEPTANCE_MATRIX.md)
- [Provider verification plan](PROVIDER_VERIFICATION.md)
- Deployment policy: no Vercel production deployment before 2026-10-24.

## Verified

- The Nihdhoom project was reviewed read-only and contained eight Saathi-prefixed tables with RLS enabled and browser-role access denied.
- PR #57 merged as `e8a13bdd0022f33707e6a9338d3cc7fcdf039615`; exact-head CI run #770 passed all five jobs, and main run #771 passed.
- PR #59 merged as `d048170180a24a36280c557150753c687139d9d7`; exact-head CI run #774 passed all five jobs. Production text/voice routes reject caller-supplied household UUIDs until verified identity-to-household ownership exists.
- PR #64 merged as `fb795e62f5dbaaf6d57ef150e2877382c8a32655`; GitHub Actions run #796 passed all five jobs on PR head `b6820fae1e7fbf70cebc931eb3647abdf864a293` (frontend lint/tests/TypeScript/build/dashboard smoke, backend pytest/API smoke, dependency audit, Docker build, Streamlit smoke).
- Production proxy requests now require a configured shared Upstash limiter and trusted single-IP header; absent or invalid configuration fails closed. Live Upstash and hosting-header behavior remain unverified.
- No live database migration or production deployment was performed.

## Partial

- **Dashboard accessibility (PR #63):** scenario tabs use roving tabindex with arrow/Home/End keyboard navigation; API/voice/answer state announcements use live regions; microphone controls expose pressed state; the UI no longer claims consent was collected. This is a code-level contract check, not a full WCAG 2.2 AA audit.
- Frontend API calls use a same-origin allowlisted proxy; the server injects the API token and production readiness fails closed without operator auth.
- Scheme catalogue data carries reviewed/stale/unknown freshness rather than a false live retrieval timestamp. Mandi records with invalid, future or over-seven-day observations are withheld from current-price claims.
- PR #68 contains the current draft verified-phone/household-PIN and purpose-specific consent UI/API. PRs #71/#72 add task and explicit-memory journeys but are stacked on closed, unmerged PR #70; their code must be rebased/ported onto #68 before merge. Real SMS delivery, live Supabase ownership, two-household isolation, consent revocation races and provider round trips remain unverified.
- PR #61 merged signed form/JSON callback parsing, body-derived idempotency, monotonic call status transitions, server-configured public HTTPS callback URL, and a hard gate preventing live calls until the actual callback authentication contract is verified.
- PR #64 bounds the development limiter to 2,000 buckets and adds the atomic production shared limiter. Production still requires operator provisioning of Upstash and verification of the trusted IP header.

## Blocked / not tested

- PR #58 remains draft: reconcile migration histories in every relevant environment before merge or live DDL.
- No real Open-Meteo, OGD/AGMARKNET, Sarvam STT/TTS, document AI or Exotel round-trip test is claimed.
- Exotel callback authentication remains unverified: the current webhook requires an HMAC over the raw body, and official callback docs do not establish that Exotel supplies the custom HMAC header. Keep `TELEPHONY_CALLBACK_SIGNATURE_VERIFIED=false` until verified with the actual provider or trusted signer.
- PR #66 is merged. Main push run #818 passed all five jobs on `edd5164fc406b87a5ab811d9746ad21e7e4c1d1f`; run #810 passed all five jobs on the PR #66 candidate. CI uses `npm ci`, lint, tests, TypeScript, build, dashboard smoke and dependency audit. Mobile/browser accessibility checks, Lighthouse/Core Web Vitals, SEO, monitoring, rollback evidence and deployed SHA remain outstanding.
- Vercel deployment/configuration remains deferred until 2026-10-24.

## Next actions

1. Keep live telephony disabled until the provider's callback signature contract is proven in a sandbox.
2. Keep PR #58 draft until migration history is reconciled across environments.
3. Review PR #68's verified identity/consent code, then port PR #71/#72 task and memory diffs onto that current auth branch; keep the proposed membership migration inactive until PR #58 history reconciliation is complete.
4. Test real providers with authorized credentials and attach redacted evidence.
5. Complete durable reminder/volunteer workflows, accessibility/performance checks, reproducible builds and rollback evidence.
6. Deploy only after 2026-10-24 and only after the release matrix gates are satisfied.


## Merged change — PR #64

- [PR #64](https://github.com/kaustubhdua/Saathi/pull/64) adds a bounded 2,000-entry local development limiter and a production-only atomic Upstash Redis fixed-window limiter.
- Production requests fail closed when the shared store is absent/unavailable, the trusted single-IP header is missing/invalid, or Redis returns an invalid counter. The Redis key contains an HMAC digest rather than a raw IP address.
- Added regression tests for high-cardinality input, malformed IP values, invalid Upstash host/port, missing configuration, outage, response type validation, over-limit handling, and pseudonymous key construction.
- Status: **merged; exact-head CI passed**. Run #796 passed all five jobs on PR head `b6820fae1e7fbf70cebc931eb3647abdf864a293`. The local environment could not clone GitHub, so no local full build is claimed.
- Operational dependency: provision the shared Upstash REST store and verify the hosting proxy overwrites the configured IP header before production traffic is enabled. This change intentionally fails closed until configured.
