-- Seed a task before the proposed reminder migration is applied.
-- This ensures the migration does not silently opt existing tasks into reminders.
INSERT INTO public.saathi_households DEFAULT VALUES;

INSERT INTO public.saathi_pending_tasks (
  household_id, title, status, missing_requirements, idempotency_key,
  scheduled_callback, timezone_name
)
SELECT
  h.id,
  'Legacy task must not be auto-enrolled',
  'pending',
  '{}',
  'legacy-reminder-opt-in-fixture',
  '2026-01-02 04:00:00+00',
  'Asia/Kolkata'
FROM public.saathi_households h
ORDER BY h.created_at DESC NULLS LAST, h.id DESC
LIMIT 1;
