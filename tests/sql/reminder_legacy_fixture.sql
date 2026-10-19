-- Seed a task before the proposed reminder migration is applied.
-- This ensures the migration does not silently opt existing tasks into reminders.
WITH new_household AS (
  INSERT INTO public.saathi_households DEFAULT VALUES
  RETURNING id
)
INSERT INTO public.saathi_pending_tasks (
  household_id, title, status, missing_requirements, idempotency_key,
  scheduled_callback, timezone_name
)
SELECT
  id,
  'Legacy task must not be auto-enrolled',
  'pending',
  '{}',
  'legacy-reminder-opt-in-fixture',
  '2026-01-02 04:00:00+00',
  'Asia/Kolkata'
FROM new_household;
