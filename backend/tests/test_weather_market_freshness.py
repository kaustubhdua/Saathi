import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.http_tools import DataGovMandiTool, OpenMeteoWeatherTool


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_weather_forecast_exposes_tomorrow_values(monkeypatch):
    import app.http_tools as module

    local_time = datetime.now(ZoneInfo("Asia/Kolkata")).replace(minute=0, second=0, microsecond=0)
    payload = {
        "timezone": "Asia/Kolkata",
        "current": {"time": local_time.isoformat(timespec="minutes"), "temperature_2m": 27, "precipitation": 0},
        "hourly": {"precipitation_probability": [10, 20, 30]},
        "daily": {
            "time": ["2026-10-11", "2026-10-12"],
            "precipitation_probability_max": [30, 75],
            "precipitation_sum": [1.2, 8.5],
        },
    }

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, *args, **kwargs):
            return FakeResponse(payload)

    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kwargs: Client())
    result = asyncio.run(OpenMeteoWeatherTool().forecast(latitude=28.99, longitude=77.02))
    assert result.ok
    assert result.data["tomorrow_date"] == "2026-10-12"
    assert result.data["tomorrow_rain_probability_pct"] == 75
    assert result.data["tomorrow_precipitation_mm"] == 8.5
    assert result.source is not None and result.source.observed_at is not None
    assert result.source.freshness_status == "current"


def test_mandi_prefers_newest_arrival_date_not_response_order(monkeypatch):
    import app.http_tools as module

    payload = {
        "records": [
            {
                "commodity": "Wheat", "state": "Haryana", "district": "Sonipat",
                "market": "Sonipat", "arrival_date": "09/10/2026", "Modal_Price": "2400",
            },
            {
                "commodity": "Wheat", "state": "Haryana", "district": "Sonipat",
                "market": "Sonipat", "arrival_date": "10/10/2026", "Modal_Price": "2450",
            },
        ]
    }

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, *args, **kwargs):
            return FakeResponse(payload)

    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kwargs: Client())
    result = asyncio.run(
        DataGovMandiTool(api_key="test", resource_id="resource").price(
            commodity="Wheat", state="Haryana", district="Sonipat", market="Sonipat"
        )
    )
    assert result.ok
    assert result.data["modal_price"] == 2450
    assert result.data["arrival_date"] == "10/10/2026"


def test_mandi_equal_match_and_date_stays_ambiguous(monkeypatch):
    import app.http_tools as module

    payload = {
        "records": [
            {
                "commodity": "Wheat", "state": "Haryana", "district": "Sonipat",
                "market": "Sonipat", "arrival_date": "10/10/2026", "Modal_Price": "2450",
            },
            {
                "commodity": "Wheat", "state": "Haryana", "district": "Sonipat",
                "market": "Sonipat", "arrival_date": "10/10/2026", "Modal_Price": "2475",
            },
        ]
    }

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, *args, **kwargs):
            return FakeResponse(payload)

    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kwargs: Client())
    result = asyncio.run(
        DataGovMandiTool(api_key="test", resource_id="resource").price(
            commodity="Wheat", state="Haryana", district="Sonipat", market="Sonipat"
        )
    )
    assert not result.ok
    assert result.error_code == "MANDI_AMBIGUOUS_MARKET"



def test_weather_freshness_classifies_current_stale_future_and_naive_times():
    from app.market_freshness import assess_weather_freshness

    now = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    assert assess_weather_freshness(datetime(2026, 10, 16, 11, 0, tzinfo=timezone.utc), now=now).status == "current"
    assert assess_weather_freshness(datetime(2026, 10, 16, 8, 0, tzinfo=timezone.utc), now=now).status == "stale"
    assert assess_weather_freshness(datetime(2026, 10, 16, 12, 10, tzinfo=timezone.utc), now=now).status == "future"
    assert assess_weather_freshness(datetime(2026, 10, 16, 11, 0), now=now).status == "unknown"
