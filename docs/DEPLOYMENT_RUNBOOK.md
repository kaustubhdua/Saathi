# Deployment Runbook

This is the supported first deployment path for Saathi. It deliberately starts in demo-safe mode and enables live providers only after each provider has been tested. A successful cloud build is not evidence that live voice, mandi data, persistence, or telephony works.

## Recommended architecture

- **Frontend:** Vercel, from the `frontend/` directory.
- **API:** Render, from the repository's `render.yaml` blueprint (FastAPI/Docker).
- **Database:** Supabase is optional for the current demo; do not claim persistent memory until the Saathi schema is applied and tenant-isolation tests pass.
- **Fastest judge demo:** Streamlit Community Cloud using `streamlit_app/app.py`; this is a separate demo shell, not the Next.js production frontend.

## 1. Deploy the API on Render

1. Push/merge the release branch after CI passes.
2. In Render, create a Blueprint from `kaustubhdua/Saathi` and select the intended branch.
3. Confirm the service root is `backend`, runtime is Docker, and readiness path is `/health/ready`.
4. Keep `DEMO_MODE=true` for the first deploy. This is intentional: a deploy with missing credentials must not imply that external data is live.
5. Set `CORS_ORIGINS` to the exact frontend origin, for example `https://your-app.vercel.app` (no trailing slash; comma-separate additional trusted origins only).
6. Deploy and verify:
   - `/health/live` returns `{"status":"alive"}`
   - `/health/ready` returns a capability map
   - `/api/v1/agent` returns a clearly labelled demo response while demo mode is on.
7. Save the public HTTPS API URL.

Do not set real API keys in GitHub files, commit history, or client-side `NEXT_PUBLIC_*` variables.

## 2. Deploy the Next.js frontend on Vercel (after the deployment freeze and release gates)

1. Import `kaustubhdua/Saathi` into Vercel.
2. Set the project root directory to `frontend`.
3. Use the Node version specified by the repository README/runtime requirements.
4. Add server-side `BACKEND_API_URL` with the Render API origin (no trailing slash).
5. Add server-side `SAATHI_API_AUTH_TOKEN` and set the matching `API_AUTH_TOKEN` on the API service. Use a high-entropy value of at least 32 characters; never expose it through `NEXT_PUBLIC_*`.
6. Keep `DEMO_MODE=true` until proxy authentication and provider checks pass. The browser must call only the same-origin `/backend/*` proxy.
7. Deploy. Add the final Vercel origin to Render `CORS_ORIGINS` only if another trusted caller requires cross-origin access.
8. Open the deployed site and test the landing page, dashboard, a text request, mobile layout, and provider/capability labels.

**Deployment freeze:** do not configure or deploy Vercel before 24 October 2026. After that date, proceed only when the release acceptance matrix's P0 gates and exact-commit CI are satisfied.

The browser does not need a direct API URL; requests go through the same-origin `/backend/*` proxy. Provider credentials and the backend API token must remain server-side.

## 3. Configure verified phone identity and household consent

- Set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` on Vercel.
- Set `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `HOUSEHOLD_PIN_PEPPER` and `HOUSEHOLD_CONTEXT_SIGNING_SECRET` as **server-only** Vercel environment variables. Use random values of at least 32 characters for the pepper and signing secret. Never use a `NEXT_PUBLIC_*` name for any of these values.
- Enable Phone authentication in Supabase Auth and configure an SMS provider in the Supabase dashboard. This repository cannot configure the SMS provider or verify delivery without administrator access and provider credentials.
- Test request OTP, verify OTP, PIN setup and verification, session refresh, sign-out, concurrent first-login household creation, phone-number recycling isolation, and an invalid/unverified session.
- Phone OTP is followed by a separate eight-digit household PIN. The PIN is stored as a server-keyed HMAC hash, and a signed HttpOnly household-context cookie expires after one hour. A phone number alone never grants access, protecting against number recycling.
- The application maps a confirmed Supabase Auth user ID to a Saathi household through `saathi_household_memberships`. The membership table is currently a proposed migration outside active discovery and must not be applied until migration-history reconciliation is approved. New households start with memory and outbound-call consent disabled.
- The consent panel reads and writes purpose-specific consent through the authenticated same-origin proxy. Memory revocation is intended to purge stored memories.
- The active migration `supabase/migrations/20261014222432_saathi_memory_consent_locking.sql` uses `SELECT ... FOR UPDATE` to serialize memory writes against revocation. A regression test now verifies that lock and confirms the trigger is attached to `saathi_household_memories`. Before enabling persistent memory in any environment, confirm this migration is present in that environment's history and test concurrent write/revoke behavior against an isolated database; do not add a duplicate migration.
- Test the household workflow end-to-end: confirm consent defaults off; enable memory; save a user-selected memory; list and delete it; revoke consent; confirm stored memories are purged and a subsequent write is denied. Test a second household cannot read/update the first household's memories or tasks.
- Tasks currently support persistent create/list/complete/cancel only. Scheduled reminder delivery, automatic follow-up calls, and volunteer assignment are not enabled; do not claim they are working.
- If the membership migration, required secrets, shared rate limiter, or verified household session is unavailable, household-specific actions fail closed. Do not advertise personalized household workflows until live tests pass.

## 4. Configure live providers one at a time

Keep demo mode on until you have set the appropriate server-side credentials and successfully exercised each path.

- **Weather:** Open-Meteo is used by the backend; verify a live request and inspect source/retrieval provenance.
- **Mandi:** set `MANDI_API_KEY` and the confirmed `MANDI_RESOURCE_ID`; test commodity, district, market, observation date, price unit, and source. A retrieval timestamp is not the observation date.
- **Browser voice:** set `SARVAM_API_KEY`; test real microphone capture, transcription, tool result, and returned audio. Record latency and provider errors.
- **Reasoning model:** set `GEMINI_API_KEY` only if the selected orchestration path needs it; the deterministic routing baseline should remain available.
- **Phone calls:** configure Exotel only after the API is deployed on public HTTPS/WSS and the complete call has been tested. Required values include account SID, API key/token, virtual number, public WSS stream URL, `TELEPHONY_CALLBACK_URL` set to the public HTTPS webhook endpoint, webhook secret, and a strong call API token. The callback URL is server-configured; client-provided callback URLs are ignored. Live outbound calls fail closed unless `TELEPHONY_CALLBACK_SIGNATURE_VERIFIED=true` is set after a provider-sandbox test proves the deployed callback path authenticates the exact raw request body and processes terminal states. The current HMAC endpoint requires a trusted signer; do not set this flag merely because Exotel credentials exist. See [the provider verification plan](PROVIDER_VERIFICATION.md). Do not expose call credentials to the browser.
- **Supabase:** leave persistence disabled until migrations, Auth/JWT verification, row-level security, and cross-household tests are complete.

After a provider is tested, turn `DEMO_MODE=false` only when the enabled capability paths are ready for the audience. Verify that unavailable providers fail honestly rather than returning demo values as live facts.

## 5. Release smoke test

Run locally before release:

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Then:

```bash
cd frontend
npm ci
npm run lint
npx tsc --noEmit
npm run build
```

The repository now includes a reviewed `frontend/package-lock.json`; use `npm ci` for reproducible installation. CI already uses `npm ci`. If it fails, fix the failure before calling the release ready. The hosted provider tests still need to be run against the actual deployed URLs. The proxy regression suite runs in CI but does not replace browser end-to-end or live-provider verification.

## 6. Do not announce production readiness until these gates pass

- [ ] CI is green on the exact commit to deploy.
- [ ] The hosted frontend can reach the hosted API with the expected CORS policy.
- [ ] Live weather and live mandi queries return correct provenance and dates.
- [ ] Real browser voice completes STT → specialist tool → Hindi TTS.
- [ ] If phone AI is claimed, a real Exotel call completes the WSS audio round trip and interruption test.
- [ ] Authenticated user identity is verified server-side before storing or retrieving household data.
- [ ] Supabase RLS and cross-household tests pass before persistence is enabled.
- [ ] The membership migration is reviewed/applied only after migration-history reconciliation; confirm the active memory-consent locking migration is present in each environment and concurrent memory-write/revoke behavior passes in an isolated database.
- [ ] Household task and explicit-memory flows pass end-to-end with two isolated identities; reminders and automatic extraction remain disabled until separately implemented and tested.
- [ ] Webhook replay/idempotency survives process restarts before it is called durable.
- [ ] Rate limiting is shared across instances before multi-instance production claims.
- [ ] Privacy notice, consent withdrawal, retention, and deletion behavior match actual data handling.
- [ ] The exact deployed commit and smoke-test evidence are recorded.

## Rollback

If the deployed build fails its smoke test, roll back to the last known-good deployment in the hosting provider, verify `/health/ready`, and repeat the smoke test. Do not change multiple providers or credentials at once while diagnosing a failure.
