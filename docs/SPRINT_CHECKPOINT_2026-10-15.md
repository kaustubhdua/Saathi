# Saathi completion sprint checkpoint — 15 October 2026

## Verified baseline

- Main SHA: `edd5164fc406b87a5ab811d9746ad21e7e4c1d1f`.
- Main GitHub Actions run [#818](https://github.com/kaustubhdua/Saathi/actions/runs/38718765777) passed all five jobs: frontend, backend, dependency-audit, docker-build, and streamlit-smoke.
- The frontend lockfile is merged; CI and the dependency-audit job use `npm ci`.
- PR #66 is merged. PR #64 is merged as `fb795e62f5dbaaf6d57ef150e2877382c8a32655`; run #796 passed all five jobs on its candidate head.
- No live database mutation, provider round-trip, or production deployment is verified by these CI results.

## Feature candidates and dependency warning

| Work | Exact head | Exact-head CI | State / gate |
|---|---|---|---|
| [PR #68 — phone OTP, household PIN and consent](https://github.com/kaustubhdua/Saathi/pull/68) | `ca19ba37e6e3b27fada7094388db110ba946a16e` | [#851](https://github.com/kaustubhdua/Saathi/actions/runs/38720886120), all five jobs passed | Draft; proposed membership migration and live Auth/SMS/database tests remain |
| [PR #71 — household tasks](https://github.com/kaustubhdua/Saathi/pull/71) | `f1a162e1c76c9579371371dca72b6b4bda5536a9` | [#857](https://github.com/kaustubhdua/Saathi/actions/runs/38721250337), all five jobs passed | Draft; based on closed/unmerged PR #70's branch, not PR #68 |
| [PR #72 — explicit household memory](https://github.com/kaustubhdua/Saathi/pull/72) | `974928dc794005d3b1883dffd735d982ffdb6f4a` | [#858](https://github.com/kaustubhdua/Saathi/actions/runs/38722014033), all five jobs passed | Draft; stacked on PR #71, so integrated auth compatibility remains unverified |
| [PR #58 — migration quarantine and indexes](https://github.com/kaustubhdua/Saathi/pull/58) | `bb0b9c50dd3c0eb2d2d09dde5554d857b98088dd` | [#840](https://github.com/kaustubhdua/Saathi/actions/runs/38720431345), all five jobs passed | Draft; do not merge/apply migrations until every relevant environment's migration history is reconciled |

The task/memory branches must not be treated as integrated merely because their individual CI is green. Port their changes onto the current PR #68 authentication candidate, preserve its security improvements, and rerun CI on the exact integrated head. Avoid wholesale stale-branch merges.

## Release controls

- Shared Nihdhoom Supabase project `igqgtlmnwssjaoxkkzbm` contains data for multiple products. Only Saathi-exclusive `saathi_*` schema objects may be changed.
- No live DB writes or migrations without explicit authorization. Reconcile both legacy unprefixed migrations against every target environment before any migration push.
- The shared Upstash limiter is code/CI verified, but real Upstash and trusted single-IP header behavior are not verified. Production requests must fail closed until configured and tested.
- Keep all service/provider credentials server-side; never put secrets in `NEXT_PUBLIC_*`.
- No Vercel deployment or configuration before **2026-10-24**. Passing CI does not waive the freeze.

## Remaining acceptance evidence

1. Real Supabase Phone Auth/SMS, PIN/session lifecycle, immutable user-to-household mapping, purpose-specific consent grant/revocation and concurrent revoke/write tests.
2. Two-household isolation tests for tasks and memory against an isolated non-production database.
3. Live Upstash/trusted-header verification, weather/OGD-AGMARKNET provenance, browser STT → tool → TTS, document AI lifecycle, and Exotel callback signature/WSS round-trip evidence.
4. Durable reminder/callback retries, quiet hours, idempotency, receipts and volunteer workflows.
5. WCAG-oriented device/browser checks, Lighthouse/Core Web Vitals, SEO/error states, monitoring, backup/restore and rollback rehearsal.
6. After the freeze only: exact deployed SHA and hosted smoke evidence.

## Evidence boundary

**Code + CI:** the main baseline and listed candidates pass their stated automated jobs.  
**Provider verified:** not established by the CI runs above.  
**Database verified:** no live DDL/write or full cross-environment migration reconciliation is claimed.  
**Production verified:** no deployment SHA or hosted acceptance evidence is established.
