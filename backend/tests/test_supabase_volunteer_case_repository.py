import asyncio

from app.supabase_repositories import SupabaseVolunteerCaseRepository


HOUSEHOLD_ID = "22222222-2222-4222-8222-222222222222"
CASE_ID = "33333333-3333-4333-8333-333333333333"


def test_list_active_cases_is_household_scoped(monkeypatch):
    repository = SupabaseVolunteerCaseRepository()
    captured = {}

    async def request(method, path, payload=None):
        captured.update(method=method, path=path)
        return []

    monkeypatch.setattr(repository, "_request", request)
    assert asyncio.run(repository.list_active_for_household(household_id=HOUSEHOLD_ID)) == []
    assert captured["method"] == "GET"
    assert f"household_id=eq.{HOUSEHOLD_ID}" in captured["path"]
    assert "status=in.(open,assigned,in_progress)" in captured["path"]


def test_create_case_defaults_to_open_normal_priority(monkeypatch):
    repository = SupabaseVolunteerCaseRepository()
    captured = {}

    async def request(method, path, payload=None):
        captured.update(method=method, path=path, payload=payload)
        return [{"id": CASE_ID, "status": "open", "priority": "normal", "summary": "Help", "created_at": None, "updated_at": None, "resolved_at": None}]

    monkeypatch.setattr(repository, "_request", request)
    result = asyncio.run(repository.create(household_id=HOUSEHOLD_ID, summary="Help"))
    assert captured["method"] == "POST"
    assert captured["payload"] == {"household_id": HOUSEHOLD_ID, "status": "open", "priority": "normal", "summary": "Help"}
    assert result["case_id"] == CASE_ID


def test_close_case_filters_by_household_and_only_active_statuses(monkeypatch):
    repository = SupabaseVolunteerCaseRepository()
    captured = {}

    async def request(method, path, payload=None):
        captured.update(method=method, path=path, payload=payload)
        return [{"id": CASE_ID}]

    monkeypatch.setattr(repository, "_request", request)
    assert asyncio.run(repository.close(household_id=HOUSEHOLD_ID, case_id=CASE_ID)) is True
    assert captured["method"] == "PATCH"
    assert f"id=eq.{CASE_ID}" in captured["path"]
    assert f"household_id=eq.{HOUSEHOLD_ID}" in captured["path"]
    assert "status=in.(open,assigned,in_progress)" in captured["path"]
    assert captured["payload"]["status"] == "closed"
