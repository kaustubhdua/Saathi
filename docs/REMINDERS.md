# In-app reminders — implementation and acceptance

## Scope

The proposed reminder path is **in-app only**. It persists a notification row for a scheduled household task and shows it in the dashboard. It does not send SMS, browser push, outbound calls or telephony. Those channels remain separate and disabled until their own consent/provider acceptance gates pass.

## Feature gates

Both flags must be enabled, and a configured Supabase URL/service secret must exist, before the worker runs:

- `SAATHI_HOUSEHOLD_FEATURES_ENABLED=true`
- `SAATHI_REMINDERS_ENABLED=true`
- `SUPABASE_URL=...`
- `SUPABASE_SECRET_KEY=...` (server-side only)

All flags default to disabled. Do not enable them against the live/shared project. The reminder migration remains in `docs/proposed-migrations/` until migration-history reconciliation and isolated database acceptance are approved.

## Worker

From the backend environment, after the approved migration is applied to the intended isolated database:

```bash
python -m app.reminder_worker
```

The worker calls `saathi_deliver_due_reminders` every 30 seconds by default. The SQL function performs notification insertion and task-state update in one transaction, locks due rows with `SKIP LOCKED`, and uses a unique task ID to prevent duplicate notifications after restarts or duplicate workers. Database errors roll back the transaction so a later tick can retry. Logs contain counts and bounded error codes, not task titles or household identifiers.

## Quiet hours and cancellation

- Quiet hours are 21:00–08:00 in the task's IANA timezone; invalid stored timezone values fall back to Asia/Kolkata.
- A due reminder during quiet hours is moved to the next local 08:00.
- The worker only processes pending/scheduled, not-cancelled tasks with `reminder_status='scheduled'`.
- Task cancellation updates the cancellation timestamp and, when the reminder migration is enabled, marks its reminder cancelled. The database row lock makes a cancellation-vs-delivery race deterministic.
- Marking a notification read is household-scoped by the backend API and same-origin proxy.

## Acceptance evidence and remaining limitations

CI applies the proposed migration only to a disposable PostgreSQL 17 database and tests quiet-hour deferral, idempotent delivery, cancelled-task exclusion, batch bounds, household membership and role access. This is not proof that the inactive/shared Supabase project is restored, that the live migration history is reconciled, or that production RLS is correct. Those gates must pass before the feature flags are enabled. Browser-push notifications, phone calls, quiet-hour user settings, and full multi-household end-to-end acceptance are not included in this implementation.