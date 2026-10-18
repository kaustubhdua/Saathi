from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.domain import Task, TaskStatus
from app.main import app


HOUSEHOLD_ID = "22222222-2222-4222-8222-222222222222"
IDENTITY_ID = "11111111-1111-4111-8111-111111111111"
TASK_ID = "33333333-3333-4333-8333-333333333333"


def configure_production(monkeypatch):
    monkeypatch.setenv("SAATHI_HOUSEHOLD_FEATURES_ENABLED", "true")
    monkeypatch.setattr(
        "app.main.settings",
        SimpleNamespace(app_env="production", demo_mode=False, api_auth_token="server-token", saathi_reminders_enabled=False),
    )


def headers():
    return {
        "X-Saathi-API-Key": "server-token",
        "X-Saathi-Verified-Identity": IDENTITY_ID,
        "X-Saathi-Verified-Household": HOUSEHOLD_ID,
    }


def test_task_list_requires_verified_household(monkeypatch):
    configure_production(monkeypatch)
    response = TestClient(app).get("/api/v1/household/tasks", headers={"X-Saathi-API-Key": "server-token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "verified_phone_identity_required"


def test_task_create_scopes_household_and_idempotency_to_verified_identity(monkeypatch):
    configure_production(monkeypatch)
    captured = {}

    async def create(self, task):
        captured["task"] = task
        return task.model_copy(update={"task_id": TASK_ID})

    monkeypatch.setattr("app.main.SupabaseTaskRepository.create", create)
    response = TestClient(app).post(
        "/api/v1/household/tasks",
        headers=headers(),
        json={"title": "  Call the agriculture office  ", "missing_items": [" land record ", ""], "idempotency_key": "client-request-1"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "task_id": TASK_ID,
        "title": "Call the agriculture office",
        "status": "pending",
        "missing_items": ["land record"],
        "scheduled_callback": None,
        "timezone_name": "Asia/Kolkata",
    }
    assert captured["task"].household_id == HOUSEHOLD_ID
    assert captured["task"].status == TaskStatus.PENDING
    assert captured["task"].idempotency_key == f"{HOUSEHOLD_ID}:client-request-1"


def test_task_create_rejects_client_supplied_household_id(monkeypatch):
    configure_production(monkeypatch)
    response = TestClient(app).post(
        "/api/v1/household/tasks",
        headers=headers(),
        json={"title": "Private task", "household_id": "44444444-4444-4444-8444-444444444444"},
    )
    assert response.status_code == 422


def test_task_status_update_is_scoped_to_verified_household(monkeypatch):
    configure_production(monkeypatch)
    captured = {}

    async def set_status(self, *, household_id, task_id, status):
        captured.update(household_id=household_id, task_id=task_id, status=status)
        return Task(
            task_id=task_id,
            household_id=household_id,
            title="Call the agriculture office",
            status=status,
        )

    monkeypatch.setattr("app.main.SupabaseTaskRepository.set_status", set_status)
    response = TestClient(app).post(
        "/api/v1/household/tasks/status",
        headers=headers(),
        json={"task_id": TASK_ID, "status": "completed"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert captured == {"household_id": HOUSEHOLD_ID, "task_id": TASK_ID, "status": TaskStatus.COMPLETED}


def test_task_status_update_returns_not_found_for_other_household(monkeypatch):
    configure_production(monkeypatch)

    async def set_status(self, *, household_id, task_id, status):
        assert household_id == HOUSEHOLD_ID
        raise KeyError("task_not_found")

    monkeypatch.setattr("app.main.SupabaseTaskRepository.set_status", set_status)
    response = TestClient(app).post(
        "/api/v1/household/tasks/status",
        headers=headers(),
        json={"task_id": TASK_ID, "status": "cancelled"},
    )
    assert response.status_code == 404

def test_household_features_are_disabled_without_explicit_flag(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.delenv("SAATHI_HOUSEHOLD_FEATURES_ENABLED", raising=False)
    response = TestClient(app).get("/api/v1/household/tasks", headers=headers())
    assert response.status_code == 503
    assert response.json()["detail"] == "household_features_disabled"


def test_task_schedule_is_disabled_until_reminder_migration_is_approved(monkeypatch):
    configure_production(monkeypatch)
    called = False

    async def create(self, task):
        nonlocal called
        called = True
        return task

    monkeypatch.setattr("app.main.SupabaseTaskRepository.create", create)
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    response = TestClient(app).post(
        "/api/v1/household/tasks",
        headers=headers(),
        json={"title": "Submit form", "scheduled_callback": future, "timezone_name": "Asia/Kolkata"},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "reminders_disabled"
    assert called is False


def test_task_schedule_is_normalized_and_scoped_when_feature_enabled(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.setattr("app.main.settings.saathi_reminders_enabled", True)
    captured = {}

    async def create(self, task):
        captured["task"] = task
        return task.model_copy(update={"task_id": TASK_ID})

    monkeypatch.setattr("app.main.SupabaseTaskRepository.create", create)
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    response = TestClient(app).post(
        "/api/v1/household/tasks",
        headers=headers(),
        json={
            "title": "Submit form",
            "scheduled_callback": future.isoformat(),
            "timezone_name": "Asia/Kolkata",
            "idempotency_key": "scheduled-task-1",
        },
    )
    assert response.status_code == 200
    assert captured["task"].scheduled_callback.tzinfo is not None
    assert captured["task"].timezone_name == "Asia/Kolkata"
    assert captured["task"].household_id == HOUSEHOLD_ID
    assert response.json()["scheduled_callback"] is not None


def test_task_schedule_rejects_invalid_timezone(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.setattr("app.main.settings.saathi_reminders_enabled", True)
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    response = TestClient(app).post(
        "/api/v1/household/tasks",
        headers=headers(),
        json={"title": "Submit form", "scheduled_callback": future, "timezone_name": "Not/A_Timezone"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_task_timezone"


def test_notification_list_is_household_scoped(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.setattr("app.main.settings.saathi_reminders_enabled", True)
    captured = {}

    async def list_for_household(self, *, household_id, limit=20):
        captured["household_id"] = household_id
        return [{"notification_id": "55555555-5555-4555-8555-555555555555", "task_id": TASK_ID, "title": "Reminder", "body": "Submit form", "created_at": "2026-10-17T10:00:00Z", "read_at": None}]

    monkeypatch.setattr("app.main.SupabaseReminderRepository.list_for_household", list_for_household)
    response = TestClient(app).get("/api/v1/household/notifications", headers=headers())
    assert response.status_code == 200
    assert captured["household_id"] == HOUSEHOLD_ID
    assert response.json()["notifications"][0]["task_id"] == TASK_ID


def test_notification_read_is_household_scoped(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.setattr("app.main.settings.saathi_reminders_enabled", True)
    captured = {}

    async def mark_read(self, *, household_id, notification_id):
        captured.update(household_id=household_id, notification_id=notification_id)
        return True

    monkeypatch.setattr("app.main.SupabaseReminderRepository.mark_read", mark_read)
    notification_id = "55555555-5555-4555-8555-555555555555"
    response = TestClient(app).post(
        "/api/v1/household/notifications/read",
        headers=headers(),
        json={"notification_id": notification_id},
    )
    assert response.status_code == 200
    assert response.json() == {"notification_id": notification_id, "read": True}
    assert captured == {"household_id": HOUSEHOLD_ID, "notification_id": notification_id}


def test_notification_read_returns_not_found_for_another_household(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.setattr("app.main.settings.saathi_reminders_enabled", True)

    async def mark_read(self, *, household_id, notification_id):
        # Repository updates include both notification ID and verified household.
        assert household_id == HOUSEHOLD_ID
        assert notification_id == "55555555-5555-4555-8555-555555555555"
        return False

    monkeypatch.setattr("app.main.SupabaseReminderRepository.mark_read", mark_read)
    response = TestClient(app).post(
        "/api/v1/household/notifications/read",
        headers=headers(),
        json={"notification_id": "55555555-5555-4555-8555-555555555555"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "household_notification_not_found"


def test_notification_read_requires_verified_household(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.setattr("app.main.settings.saathi_reminders_enabled", True)
    response = TestClient(app).post(
        "/api/v1/household/notifications/read",
        headers={"X-Saathi-API-Key": "server-token"},
        json={"notification_id": "55555555-5555-4555-8555-555555555555"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "verified_phone_identity_required"



def test_task_schedule_rejects_time_too_close_to_now(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.setattr("app.main.settings.saathi_reminders_enabled", True)
    called = False

    async def create(self, task):
        nonlocal called
        called = True
        return task

    monkeypatch.setattr("app.main.SupabaseTaskRepository.create", create)
    almost_now = (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat()
    response = TestClient(app).post(
        "/api/v1/household/tasks",
        headers=headers(),
        json={"title": "Submit form", "scheduled_callback": almost_now, "timezone_name": "Asia/Kolkata"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "reminder_must_be_at_least_one_minute_in_future"
    assert called is False


def test_task_schedule_rejects_time_beyond_one_year(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.setattr("app.main.settings.saathi_reminders_enabled", True)
    called = False

    async def create(self, task):
        nonlocal called
        called = True
        return task

    monkeypatch.setattr("app.main.SupabaseTaskRepository.create", create)
    too_far = (datetime.now(timezone.utc) + timedelta(days=366)).isoformat()
    response = TestClient(app).post(
        "/api/v1/household/tasks",
        headers=headers(),
        json={"title": "Submit form", "scheduled_callback": too_far, "timezone_name": "Asia/Kolkata"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "reminder_too_far_in_future"
    assert called is False


def test_notification_list_requires_verified_household(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.setattr("app.main.settings.saathi_reminders_enabled", True)
    response = TestClient(app).get(
        "/api/v1/household/notifications",
        headers={"X-Saathi-API-Key": "server-token"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "verified_phone_identity_required"


def test_notification_read_rejects_malformed_notification_id(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.setattr("app.main.settings.saathi_reminders_enabled", True)
    response = TestClient(app).post(
        "/api/v1/household/notifications/read",
        headers=headers(),
        json={"notification_id": "not-a-uuid"},
    )
    assert response.status_code == 422


def test_task_cancellation_marks_scheduled_reminder_cancelled_when_enabled(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.setattr("app.main.settings.saathi_reminders_enabled", True)
    captured = {}

    async def set_status(self, *, household_id, task_id, status):
        captured.update(household_id=household_id, task_id=task_id, status=status)
        return Task(
            task_id=task_id,
            household_id=household_id,
            title="Submit form",
            status=status,
        )

    monkeypatch.setattr("app.main.SupabaseTaskRepository.set_status", set_status)
    response = TestClient(app).post(
        "/api/v1/household/tasks/status",
        headers=headers(),
        json={"task_id": TASK_ID, "status": "cancelled"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert captured == {
        "household_id": HOUSEHOLD_ID,
        "task_id": TASK_ID,
        "status": TaskStatus.CANCELLED,
    }


def test_notification_read_returns_service_error_without_leaking_database_details(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.setattr("app.main.settings.saathi_reminders_enabled", True)

    async def mark_read(self, *, household_id, notification_id):
        raise SupabaseRepositoryError("supabase_persistence_http_503_secret-value")

    from app.supabase_repositories import SupabaseRepositoryError
    monkeypatch.setattr("app.main.SupabaseReminderRepository.mark_read", mark_read)
    response = TestClient(app).post(
        "/api/v1/household/notifications/read",
        headers=headers(),
        json={"notification_id": "55555555-5555-4555-8555-555555555555"},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "household_notification_update_failed"
    assert "secret-value" not in response.text
