-- Run only against an ephemeral CI PostgreSQL database.
DO $reminder_test$
DECLARE
  household_uuid uuid;
  task_uuid uuid;
  cancelled_task_uuid uuid;
  scheduled_at timestamptz;
  reminder_status_value text;
  delivered_count integer;
  notification_count integer;
BEGIN
  INSERT INTO public.saathi_households DEFAULT VALUES RETURNING id INTO household_uuid;

  INSERT INTO public.saathi_pending_tasks (
    household_id, title, status, missing_requirements, idempotency_key,
    scheduled_callback, timezone_name, reminder_status
  ) VALUES (
    household_uuid, 'Quiet-hour test reminder', 'pending', '{}',
    'reminder-quiet-' || gen_random_uuid()::text,
    '2026-01-01 16:00:00+00', 'Asia/Kolkata', 'scheduled'
  ) RETURNING id INTO task_uuid;

  SELECT count(*) INTO delivered_count
  FROM public.saathi_deliver_due_reminders(25, '2026-01-01 17:30:00+00');

  IF delivered_count <> 0 THEN
    RAISE EXCEPTION 'test_failed: reminder must be deferred during local quiet hours';
  END IF;

  SELECT scheduled_callback INTO scheduled_at
  FROM public.saathi_pending_tasks WHERE id = task_uuid;
  IF scheduled_at <> '2026-01-02 02:30:00+00'::timestamptz THEN
    RAISE EXCEPTION 'test_failed: quiet-hour reminder must move to 08:00 local time';
  END IF;

  SELECT count(*) INTO delivered_count
  FROM public.saathi_deliver_due_reminders(25, '2026-01-02 04:30:00+00');
  IF delivered_count <> 1 THEN
    RAISE EXCEPTION 'test_failed: due reminder should create one in-app notification';
  END IF;

  SELECT count(*) INTO notification_count
  FROM public.saathi_in_app_notifications WHERE task_id = task_uuid;
  IF notification_count <> 1 THEN
    RAISE EXCEPTION 'test_failed: one reminder must create exactly one notification';
  END IF;

  SELECT reminder_status INTO reminder_status_value
  FROM public.saathi_pending_tasks WHERE id = task_uuid;
  IF reminder_status_value <> 'delivered' THEN
    RAISE EXCEPTION 'test_failed: task reminder status must be delivered';
  END IF;

  SELECT count(*) INTO delivered_count
  FROM public.saathi_deliver_due_reminders(25, '2026-01-02 04:31:00+00');
  IF delivered_count <> 0 THEN
    RAISE EXCEPTION 'test_failed: a delivered reminder must not be duplicated';
  END IF;

  INSERT INTO public.saathi_pending_tasks (
    household_id, title, status, missing_requirements, idempotency_key,
    scheduled_callback, timezone_name, cancelled_at, reminder_status
  ) VALUES (
    household_uuid, 'Cancelled reminder', 'cancelled', '{}',
    'reminder-cancelled-' || gen_random_uuid()::text,
    '2026-01-02 02:00:00+00', 'Asia/Kolkata', '2026-01-02 01:00:00+00', 'cancelled'
  ) RETURNING id INTO cancelled_task_uuid;

  SELECT count(*) INTO delivered_count
  FROM public.saathi_deliver_due_reminders(25, '2026-01-02 04:30:00+00');
  IF delivered_count <> 0 THEN
    RAISE EXCEPTION 'test_failed: cancelled tasks must not be delivered';
  END IF;

  SELECT count(*) INTO notification_count
  FROM public.saathi_in_app_notifications WHERE task_id = cancelled_task_uuid;
  IF notification_count <> 0 THEN
    RAISE EXCEPTION 'test_failed: cancelled task must not create a notification';
  END IF;

  BEGIN
    PERFORM * FROM public.saathi_deliver_due_reminders(0, '2026-01-02 04:30:00+00');
    RAISE EXCEPTION 'test_failed: invalid batch size must be rejected';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM <> 'reminder_batch_size_out_of_range' THEN
      RAISE;
    END IF;
  END;

  -- Spring-forward DST: 03:00 local is still inside quiet hours, and the
  -- next allowed 08:00 local resolves to 12:00 UTC after the offset change.
  INSERT INTO public.saathi_pending_tasks (
    household_id, title, status, missing_requirements, idempotency_key,
    scheduled_callback, timezone_name, reminder_status
  ) VALUES (
    household_uuid, 'DST spring-forward reminder', 'pending', '{}',
    'reminder-dst-spring-' || gen_random_uuid()::text,
    '2026-03-08 06:30:00+00', 'America/New_York', 'scheduled'
  ) RETURNING id INTO task_uuid;

  SELECT count(*) INTO delivered_count
  FROM public.saathi_deliver_due_reminders(25, '2026-03-08 07:00:00+00');
  IF delivered_count <> 0 THEN
    RAISE EXCEPTION 'test_failed: reminder must defer during DST spring-forward quiet hours';
  END IF;

  SELECT scheduled_callback INTO scheduled_at
  FROM public.saathi_pending_tasks WHERE id = task_uuid;
  IF scheduled_at <> '2026-03-08 12:00:00+00'::timestamptz THEN
    RAISE EXCEPTION 'test_failed: DST quiet-hour deferral must resolve to 08:00 local after spring-forward';
  END IF;

  SELECT count(*) INTO delivered_count
  FROM public.saathi_deliver_due_reminders(25, '2026-03-08 12:00:00+00');
  IF delivered_count <> 1 THEN
    RAISE EXCEPTION 'test_failed: DST reminder must deliver at 08:00 local';
  END IF;

END;
$reminder_test$;
