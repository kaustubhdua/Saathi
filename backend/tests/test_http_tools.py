import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.http_tools import OpenMeteoWeatherTool

class FakeResponse:
    def __init__(self, payload=None):
        local_time = datetime.now(ZoneInfo("Asia/Kolkata")).replace(minute=0, second=0, microsecond=0)
        self.payload = payload or {
            "timezone": "Asia/Kolkata",
            "current": {"time": local_time.isoformat(timespec="minutes"), "temperature_2m": 27, "precipitation": 0},
            "hourly": {"precipitation_probability": [10, 20, 30]},
        }

    def raise_for_status(self): pass
    def json(self): return self.payload


class FakeClient:
    def __init__(self, response=None): self.response = response or FakeResponse()
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def get(self, *args, **kwargs): return self.response


def test_open_meteo_mapping(monkeypatch):
    import app.http_tools as module
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    result = asyncio.run(OpenMeteoWeatherTool().forecast(latitude=28.99, longitude=77.02))
    assert result.ok
    assert result.data["next_24h_rain_probability_max"] == 30
    assert result.data["freshness_status"] == "current"
    assert result.source is not None
    assert result.source.observed_at is not None
    assert result.source.observed_at.tzinfo is not None
    assert result.source.retrieved_at is not None
    assert result.source.retrieved_at >= result.source.observed_at
    assert "observation" in (result.source.freshness_note or "").lower()


def test_open_meteo_rejects_missing_observation_time(monkeypatch):
    import app.http_tools as module
    payload = FakeResponse().json()
    payload["current"].pop("time")
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kwargs: FakeClient(FakeResponse(payload)))
    result = asyncio.run(OpenMeteoWeatherTool().forecast(latitude=28.99, longitude=77.02))
    assert not result.ok
    assert result.error_code == "WEATHER_PROVIDER_ERROR"


def test_open_meteo_rejects_invalid_hourly_probabilities(monkeypatch):
    import app.http_tools as module
    payload = FakeResponse().json()
    payload["hourly"]["precipitation_probability"] = ["unknown"]
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kwargs: FakeClient(FakeResponse(payload)))
    result = asyncio.run(OpenMeteoWeatherTool().forecast(latitude=28.99, longitude=77.02))
    assert not result.ok
    assert result.error_code == "WEATHER_PROVIDER_ERROR"


def test_open_meteo_withholds_stale_observation(monkeypatch):
    import app.http_tools as module
    payload = FakeResponse().json()
    old_time = datetime.now(ZoneInfo("Asia/Kolkata")) - timedelta(hours=5)
    payload["current"]["time"] = old_time.replace(minute=0, second=0, microsecond=0).isoformat(timespec="minutes")
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kwargs: FakeClient(FakeResponse(payload)))
    result = asyncio.run(OpenMeteoWeatherTool().forecast(latitude=28.99, longitude=77.02))
    assert not result.ok
    assert result.error_code == "WEATHER_OBSERVATION_STALE"
    assert result.source is not None
    assert result.source.freshness_status == "stale"
    assert "temperature_c" not in result.data


class MandiResponse:
    def raise_for_status(self): pass
    def json(self):
        return {
            "records": [{
                "commodity": "Rice",
                "state": "Haryana",
                "district": "Sonipat",
                "market": "Sonipat",
                "Modal_Price": "2400",
            }]
        }


class MandiClient:
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def get(self, *args, **kwargs): return MandiResponse()


def test_mandi_rejects_entity_mismatch(monkeypatch):
    import app.http_tools as module
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kwargs: MandiClient())
    from app.http_tools import DataGovMandiTool
    result = asyncio.run(
        DataGovMandiTool(api_key="test", resource_id="resource").price(
            commodity="Wheat",
            state="Haryana",
            district="Sonipat",
        )
    )
    assert not result.ok
    assert result.error_code == "MANDI_ENTITY_MISMATCH"
