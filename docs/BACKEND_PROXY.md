# Server-side API proxy

The dashboard uses same-origin `/backend/*` routes. The Next.js Node route forwards only the allowlisted readiness, agent-text and voice-turn endpoints and injects `X-Saathi-API-Key` from server-only `SAATHI_API_AUTH_TOKEN`.

## Required configuration

- `BACKEND_API_URL`: HTTPS origin of FastAPI in deployed environments.
- `SAATHI_API_AUTH_TOKEN`: high-entropy value of at least 32 characters matching backend `API_AUTH_TOKEN`.
- Keep both variables server-side. Never expose the token through `NEXT_PUBLIC_*`.
- A localhost fallback exists only when `NODE_ENV=development`.

## Boundaries

- Only `GET /health/ready`, `GET /health/live`, `POST /api/v1/agent`, `POST /api/v1/voice/turn`, and authenticated `GET/POST /api/v1/household/consent` are exposed.
- The proxy rejects browser-supplied household identifiers, checks mutation origins when present, bounds request-body size and read time, rejects redirects, uses no-store responses, and includes a best-effort per-process rate limit.
- Text requests are limited to 64 KiB; voice uploads are limited to 10 MiB. Upstream calls have bounded timeouts.
- The host must overwrite `X-Real-IP`. The local limiter is not shared across instances and must be supplemented by an edge/shared limiter in production.
- Phone OTP login uses Supabase Auth SSR cookies. For signed-in users, the server verifies the Supabase user and requires a confirmed E.164 phone, then resolves the household through `saathi_household_memberships.auth_user_id`. A phone number alone never grants access, which avoids household takeover if a phone number is recycled. The proposed membership migration is outside active migration discovery until PR #58 is reconciled.
- The proxy injects `X-Saathi-Verified-Identity` and `X-Saathi-Verified-Household` only after that verification; the backend validates both UUIDs and rejects client-supplied household IDs. The browser cannot select a household by UUID.
- The consent API exposes only memory and outbound-call purpose booleans. Both start false; revoking memory relies on the existing database trigger to purge stored memory.
- Task APIs and outbound-call operations remain unavailable through the public proxy. Phone OTP and consent remain unavailable until Supabase Auth/SMS and server-only secrets are configured and tested.
- Production readiness reports `not_ready` when required API operator authentication is missing.

## Verification

CI runs `node --test tests/backend-proxy.test.mjs` plus lint, TypeScript and the Next.js build. These tests stub the upstream; they do not prove live provider or deployment behavior.

## Household identity fail-closed behavior

The backend rejects a client-supplied household identifier on text and voice interaction routes outside local demo mode. A household UUID is not an identity credential. Until a verified end-user identity provider and identity-to-household ownership check are integrated, production requests must omit household IDs; household-specific memory, tasks and consent APIs must not be exposed through the public proxy. This intentionally blocks household-personalized production workflows rather than silently trusting a client-supplied UUID.


## Additional server-only configuration

- `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` are public Auth client configuration.
- `SUPABASE_URL` and `SUPABASE_SECRET_KEY` are server-only. The secret key must never use a `NEXT_PUBLIC_*` name and must never be serialized to a browser response.
- Enable Supabase Phone Auth and configure SMS delivery in the project dashboard. This code cannot provision the provider or prove delivery.
