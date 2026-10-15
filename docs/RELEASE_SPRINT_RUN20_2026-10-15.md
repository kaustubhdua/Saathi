# Saathi Release Sprint — Run 20

Date: 2026-10-15 (IST)  
Scope: evidence-only refresh; no merge, database mutation, provider activation, or deployment.

## Live GitHub state checked at run start

- Integrated PR #68 is open and draft, head `4b4cedb8b73cc645192cf0f616d109f792209543`, base `main` at `edd5164fc406b87a5ab811d9746ad21e7e4c1d1f`.
- Exact-head Actions run #921 for that SHA completed successfully: frontend lint/contract tests/TypeScript/build/dashboard smoke, backend tests/API smoke, dependency audit, Docker build, and Streamlit smoke all passed.
- Migration-safety PR #58 is open and draft, head `bb0b9c50dd3c0eb2d2d09dde5554d857b98088dd`. Exact-head Actions run #840 completed successfully across all five jobs.
- Accessibility PR #76 is closed without merge; its error/not-found implementation is included in PR #68. Do not reopen duplicate work unless the consolidated implementation regresses.

Evidence:
- PR #68: https://github.com/kaustubhdua/Saathi/pull/68
- CI #921: https://github.com/kaustubhdua/Saathi/actions/runs/38777005269
- PR #58: https://github.com/kaustubhdua/Saathi/pull/58
- CI #840: https://github.com/kaustubhdua/Saathi/actions/runs/38720431345
- PR #76: https://github.com/kaustubhdua/Saathi/pull/76

## Newly confirmed review concern

The current proposed enrollment implementation performs household creation and membership insertion as separate REST operations. Concurrent first-time setup for the same Auth identity can leave an unlinked household row if membership creation loses a uniqueness race. This is a data-integrity concern; it does not by itself establish cross-household access.

A local candidate patch exists in the Run 19 handoff. It moves enrollment into a proposed server-only PostgreSQL RPC, serializes enrollment by Auth user ID, revokes direct membership-table writes from `service_role`, grants RPC execution only to `service_role`, and adds contract assertions. It is **not published or CI-verified**. Before adopting it, review SECURITY DEFINER ownership/search_path/grants, conflict semantics, row-return behavior, and run deterministic concurrent-enrollment tests against an authorized isolated database. Do not activate or apply the proposed migration.

## Database safety gates (unchanged)

- Read-only checks found six Saathi migration records and eight RLS-enabled Saathi tables in the active Nihdhoom project; `saathi_household_memberships` is absent.
- The separate Saathi Supabase project in `ap-northeast-2` is inactive and its migration-history query timed out. Its history remains unverified.
- PR #58's current migration-history review says the two legacy versions are absent in the active project. The inactive environment is still unresolved. Keep PR #58 draft; do not apply the proposed indexes or run migrations.
- No DDL, migration push, inactive-project restoration, shared non-Saathi database change, or live provider test was performed.

## Release gates still open

1. Publish/review the atomic enrollment fix on the PR #68 branch and require exact-head CI.
2. Run isolated tests for simultaneous enrollment, PIN immutability, recycled phone numbers, two-household isolation, consent revocation races, and RLS/RPC permissions.
3. Verify live Supabase Phone OTP/SMS and server-only secret configuration only with explicit operator authorization.
4. Resolve the five high-severity frontend development-tool-chain advisories or document a reviewed, accepted risk; production-only npm audit currently passes.
5. Complete browser E2E coverage, WCAG 2.2 AA assessment, Lighthouse/Core Web Vitals, production smoke tests, and rollback evidence.
6. Reconcile migration history in every target environment before considering PR #58 or any proposed migration.
7. Keep automatic memory extraction, scheduled reminders, volunteer dispatch, and live phone calls disabled until implemented and verified.
8. Do not configure or deploy Vercel before 2026-10-24.

## Operating rule

PRs remain draft and unmerged. A green CI run establishes only the checks listed in that run, not live identity/provider/database readiness. Re-fetch branch heads and verify CI against the exact current SHA after every new commit.