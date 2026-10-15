from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.supabase_repositories import SupabaseRepositoryError


HOUSEHOLD_ID = "22222222-2222-4222-8222-222222222222"
IDENTITY_ID = "11111111-1111-4111-8111-111111111111"
CASE_ID = "33333333-3333-4333-8333-333333333333"


def configure_production(monkeypatch):
    monkeypatch.setattr(
        "app.main.settings",
        SimpleNamespace(app_env="production", demo_mode=False, api_auth_token="server-token"),
    )


def headers():
    return {
        "X-Saathi-API-Key": "server-token",
        "X-Saathi-Verified-Identity": IDENTITY_ID,
        "X-Saathi-Verified-Household": HOUSEHOLD_ID,
    }


def test_help_case_list_requires_verified_household(monkeypatch):
    configure_production(monkeypatch)
    response = TestClient(app).get("/api/v1/household/help-cases", headers={"X-Saathi-API-Key": "server-token"})
    assert response.status_code == 401


def test_help_case_creation_is_household_scoped_and_does_not_claim_assignment(monkeypatch):
    configure_production(monkeypatch)
    captured = {}

    async def create(self, *, household_id, summary):
        captured.update(household_id=household_id, summary=summary)
        return {
            "case_id": CASE_ID,
            "status": "open",
            "priority": "normal",
            "summary": summary,
            "created_at": "2026-10-15T10:00:00+00:00",
            "updated_at": "2026-10-15T10:00:00+00:00",
            "resolved_at": None,
        }

    monkeypatch.setattr("app.main.SupabaseVolunteerCaseRepository.create", create)
    response = TestClient(app).post(
        "/api/v1/household/help-cases",
        headers=headers(),
        json={"summary": "  Please help me understand this application  "},
    )
    assert response.status_code == 200
    assert response.json()["volunteer_assignment_enabled"] is False
    assert response.json()["status"] == "open"
    assert captured == {"household_id": HOUSEHOLD_ID, "summary": "Please help me understand this application"}


def test_help_case_create_rejects_client_supplied_household_id(monkeypatch):
    configure_production(monkeypatch)
    response = TestClient(app).post(
        "/api/v1/household/help-cases",
        headers=headers(),
        json={"summary": "Help needed", "household_id": "44444444-4444-4444-8444-444444444444"},
    )
    assert response.status_code == 422


def test_help_case_close_is_scoped_to_verified_household(monkeypatch):
    configure_production(monkeypatch)
    captured = {}

    async def close(self, *, household_id, case_id):
        captured.update(household_id=household_id, case_id=case_id)
        return True

    monkeypatch.setattr("app.main.SupabaseVolunteerCaseRepository.close", close)
    response = TestClient(app).post(
        "/api/v1/household/help-cases/close",
        headers=headers(),
        json={"case_id": CASE_ID},
    )
    assert response.status_code == 200
    assert response.json() == {"case_id": CASE_ID, "status": "closed"}
    assert captured == {"household_id": HOUSEHOLD_ID, "case_id": CASE_ID}


def test_help_case_close_returns_not_found_for_another_household(monkeypatch):
    configure_production(monkeypatch)

    async def close(self, *, household_id, case_id):
        assert household_id == HOUSEHOLD_ID
        return False

    monkeypatch.setattr("app.main.SupabaseVolunteerCaseRepository.close", close)
    response = TestClient(app).post(
        "/api/v1/household/help-cases/close",
        headers=headers(),
        json={"case_id": CASE_ID},
    )
    assert response.status_code == 404
