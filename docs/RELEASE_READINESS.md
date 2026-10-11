# Saathi release readiness

Last reviewed: 2026-10-11

## What is implemented and CI-verified

- FastAPI text, voice-turn and telephony webhook contracts.
- Deterministic intent routing, source/provenance metadata, confidence-based escalation policy and bounded provider adapters.
- Official-source PM-KISAN/PMFBY catalogue API, including source-check dates, caveats and detail lookup.
- Open-Meteo next-day forecast mapping and newest-arrival-date selection for OGD/AGMARKNET records, with ambiguity preserved.
- Synthetic Hindi/Hinglish/colloquial text regression benchmark. This is **not** a speech WER benchmark and does not prove Haryanvi speech quality.
- Demo/production boundary labels, operator API token policy and telephony stream admission token policy.
- Docker API image, Docker Compose local demo, deployment/local-demo documentation and CI for backend tests, frontend lint/typecheck/build, dependency audit, Docker build and Streamlit smoke checks.
- Browser voice fallback is a local demo capability, not provider-backed STT/TTS. Consent toggles are prototypes and do not persist data.

## Production launch blockers

These must remain open until the named evidence exists. A green CI run is not evidence that live credentials, database policies, telecom provider contracts or real speech quality have been verified.

| Area | Current implementation | Required before production |
| --- | --- | --- |
| Supabase restoration and RLS | Migrations and service-role metadata/webhook adapters exist; target project is inactive | Restore the intended project or change plan capacity, apply migrations in a reviewed window, inspect live RLS/grants, run household-isolation tests |
| Household memory and consent | Schema foundation and UI disclosure | Integrate authenticated household ownership, consent grant/revoke, retention/deletion, consent-gated writes and isolation tests; never treat the demo toggle as consent persistence |
| Durable tasks and callbacks | Task table and pure callback eligibility policy | Durable repository, scheduler/worker, atomic task claim, idempotent retries, timezone/quiet-hour/opt-out checks and audit trail |
| Volunteer escalation | Intent/policy can identify human-support requests | Persist cases, secure volunteer authentication/authorization, assignment, minimal context, resolution workflow and audit events |
| Document extraction | Provider capability is gated | Private upload/storage, malware/content validation, OCR/extraction confidence, expiry, consent, redaction and human review |
| Speech quality | Synthetic text intent/entity benchmark | Collect consented, non-sensitive representative audio; measure STT WER, intent/entity/tool accuracy, latency and escalation separately for Hindi/Hinglish/Haryanvi; review with native speakers |
| Telephony | HMAC webhook checks, event idempotency contract and WebSocket admission token | Validate exact provider signature/body contract and real inbound/outbound calls; verify retry semantics and end-to-end audio/interruptions against provider sandbox |
| Production identity | API operator token protects server-to-server endpoints | Public browser clients need a verified user-session/auth integration; never embed operator tokens in browser JavaScript |
| Shared rate limiting and observability | In-memory limiter and correlation/metrics contracts | Use a shared production limiter, redact sensitive logs, configure alerting and prove failure handling |
| Release and rollback | CI and deployment templates | Configure secrets in deployment platform, smoke-test live deployment, confirm health/readiness, rollback procedure and data backups |

## Safe operating rule

Run the demo without real household data or outbound calls. Do not enable production traffic merely because unit tests pass. Keep provider-backed functionality disabled until its exact credentials, consent contract, live persistence and end-to-end checks are verified.

## Issue tracking

The following repository issues track the remaining gates: #2, #11, #13, #16, #17, #19, #20, #21, #22 and #27. Do not close them solely because a schema, policy helper, synthetic benchmark or demo UI exists; close each only after its acceptance evidence is committed and verified.
