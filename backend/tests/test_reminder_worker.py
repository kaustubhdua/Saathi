import asyncio

from app import reminder_worker


def test_reminder_worker_stays_closed_without_both_feature_flags(monkeypatch):
    monkeypatch.setenv("SAATHI_HOUSEHOLD_FEATURES_ENABLED", "false")
    monkeypatch.setattr(reminder_worker.get_settings(), "saathi_reminders_enabled", True)
    monkeypatch.setattr(reminder_worker.get_settings(), "supabase_url", "https://supabase.example.test")
    monkeypatch.setattr(reminder_worker.get_settings(), "supabase_secret_key", "test-secret")
    monkeypatch.setattr(reminder_worker.get_settings(), "supabase_url", "https://supabase.example.test")
    monkeypatch.setattr(reminder_worker.get_settings(), "supabase_secret_key", "test-secret")
    called = False

    class FakeRepository:
        async def deliver_due(self, *, batch_size):
            nonlocal called
            called = True
            return [{"task_id": "not-logged"}]

    monkeypatch.setattr(reminder_worker, "SupabaseReminderRepository", FakeRepository)
    assert asyncio.run(reminder_worker.run_once()) == 0
    assert called is False


def test_reminder_worker_reports_count_without_logging_task_content(monkeypatch):
    monkeypatch.setenv("SAATHI_HOUSEHOLD_FEATURES_ENABLED", "true")
    monkeypatch.setattr(reminder_worker.get_settings(), "saathi_reminders_enabled", True)
    monkeypatch.setattr(reminder_worker.get_settings(), "supabase_url", "https://supabase.example.test")
    monkeypatch.setattr(reminder_worker.get_settings(), "supabase_secret_key", "test-secret")
    events = []

    class FakeRepository:
        async def deliver_due(self, *, batch_size):
            assert batch_size == 25
            return [{"task_id": "private-id", "title": "private-title"}, {"task_id": "other-id"}]

    monkeypatch.setattr(reminder_worker, "SupabaseReminderRepository", FakeRepository)
    monkeypatch.setattr(reminder_worker, "emit_event", lambda name, **fields: events.append((name, fields)))
    assert asyncio.run(reminder_worker.run_once()) == 2
    assert events == [("reminder_worker.tick_completed", {"delivered_count": 2})]


def test_reminder_worker_fails_closed_on_persistence_errors(monkeypatch):
    monkeypatch.setenv("SAATHI_HOUSEHOLD_FEATURES_ENABLED", "true")
    monkeypatch.setattr(reminder_worker.get_settings(), "saathi_reminders_enabled", True)
    monkeypatch.setattr(reminder_worker.get_settings(), "supabase_url", "https://supabase.example.test")
    monkeypatch.setattr(reminder_worker.get_settings(), "supabase_secret_key", "test-secret")
    events = []

    class FakeRepository:
        async def deliver_due(self, *, batch_size):
            raise reminder_worker.SupabaseRepositoryError("supabase_persistence_http_503")

    monkeypatch.setattr(reminder_worker, "SupabaseReminderRepository", FakeRepository)
    monkeypatch.setattr(reminder_worker, "emit_event", lambda name, **fields: events.append((name, fields)))
    assert asyncio.run(reminder_worker.run_once()) == 0
    assert events == [("reminder_worker.tick_failed", {"error_code": "supabase_persistence_http_503"})]



def test_reminder_worker_keeps_running_and_rechecks_flags_each_tick(monkeypatch):
    """A disabled worker must remain alive, then honor a deliberate later enable."""
    monkeypatch.setenv("SAATHI_HOUSEHOLD_FEATURES_ENABLED", "false")
    settings = reminder_worker.get_settings()
    monkeypatch.setattr(settings, "saathi_reminders_enabled", True)
    monkeypatch.setattr(settings, "supabase_url", "https://supabase.example.test")
    monkeypatch.setattr(settings, "supabase_secret_key", "test-secret")
    ticks = []
    sleeps = 0

    async def run_once():
        ticks.append(reminder_worker._enabled())
        return 0

    async def fake_sleep(_interval):
        nonlocal sleeps
        sleeps += 1
        if sleeps == 1:
            monkeypatch.setenv("SAATHI_HOUSEHOLD_FEATURES_ENABLED", "true")
            return
        raise RuntimeError("stop-test-loop")

    monkeypatch.setattr(reminder_worker, "run_once", run_once)
    monkeypatch.setattr(reminder_worker.asyncio, "sleep", fake_sleep)

    try:
        asyncio.run(reminder_worker.run_forever())
    except RuntimeError as exc:
        assert str(exc) == "stop-test-loop"
    else:
        raise AssertionError("test loop should have been stopped by its sentinel")

    assert ticks == [False, True]
    assert sleeps == 2


def test_reminder_worker_retries_on_next_tick_after_persistence_failure(monkeypatch):
    """A transient database error must not mark work delivered or stop later ticks."""
    monkeypatch.setenv("SAATHI_HOUSEHOLD_FEATURES_ENABLED", "true")
    settings = reminder_worker.get_settings()
    monkeypatch.setattr(settings, "saathi_reminders_enabled", True)
    monkeypatch.setattr(settings, "supabase_url", "https://supabase.example.test")
    monkeypatch.setattr(settings, "supabase_secret_key", "test-secret")
    attempts = 0

    class FlakyRepository:
        async def deliver_due(self, *, batch_size):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise reminder_worker.SupabaseRepositoryError("supabase_persistence_http_503")
            return [{"task_id": "private-id"}]

    monkeypatch.setattr(reminder_worker, "SupabaseReminderRepository", FlakyRepository)
    assert asyncio.run(reminder_worker.run_once()) == 0
    assert asyncio.run(reminder_worker.run_once()) == 1
    assert attempts == 2
