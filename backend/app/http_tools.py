from datetime import datetime, timezone
from math import isfinite
from zoneinfo import ZoneInfo

import httpx

from .provenance import SourceRecord, ToolResult
from .market_freshness import assess_mandi_freshness, assess_weather_freshness


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _is_probability(value: object) -> bool:
    return _is_finite_number(value) and 0 <= value <= 100


def _is_nonnegative_number(value: object) -> bool:
    return _is_finite_number(value) and value >= 0


class OpenMeteoWeatherTool:
    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def forecast(self, *, latitude: float, longitude: float) -> ToolResult:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "time,temperature_2m,precipitation",
            "hourly": "precipitation_probability,temperature_2m",
            "daily": "precipitation_probability_max,precipitation_sum",
            "forecast_days": 2,
            "forecast_hours": 24,
            "timezone": "auto",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(OPEN_METEO_URL, params=params)
                response.raise_for_status()
                payload = response.json()

            if not isinstance(payload, dict):
                raise ValueError("weather_payload_not_object")
            current = payload.get("current")
            hourly = payload.get("hourly")
            timezone_name = payload.get("timezone")
            current_time = current.get("time") if isinstance(current, dict) else None
            if not isinstance(current, dict) or not isinstance(hourly, dict):
                raise ValueError("weather_payload_missing_current_or_hourly")
            if not isinstance(timezone_name, str) or not timezone_name.strip():
                raise ValueError("weather_payload_missing_timezone")
            if not isinstance(current_time, str) or not current_time.strip():
                raise ValueError("weather_payload_missing_observation_time")

            provider_timezone = ZoneInfo(timezone_name)
            observed_at = datetime.fromisoformat(current_time)
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=provider_timezone)
            observed_at = observed_at.astimezone(timezone.utc)

            temperature = current.get("temperature_2m")
            precipitation = current.get("precipitation")
            probabilities = hourly.get("precipitation_probability")
            if not _is_finite_number(temperature):
                raise ValueError("weather_payload_missing_valid_temperature")
            if not isinstance(probabilities, list) or not probabilities or any(not _is_probability(value) for value in probabilities):
                raise ValueError("weather_payload_missing_valid_hourly_probabilities")
            rain_probability = max(probabilities)
            if not _is_nonnegative_number(precipitation):
                precipitation = None

            daily = payload.get("daily")
            if not isinstance(daily, dict):
                daily = {}
            daily_dates = daily.get("time") if isinstance(daily.get("time"), list) else []
            daily_probabilities = daily.get("precipitation_probability_max") if isinstance(daily.get("precipitation_probability_max"), list) else []
            daily_precipitation = daily.get("precipitation_sum") if isinstance(daily.get("precipitation_sum"), list) else []
            tomorrow_date = daily_dates[1] if len(daily_dates) > 1 and isinstance(daily_dates[1], str) else None
            tomorrow_probability = daily_probabilities[1] if len(daily_probabilities) > 1 else None
            if not _is_probability(tomorrow_probability):
                tomorrow_probability = None
            tomorrow_precipitation = daily_precipitation[1] if len(daily_precipitation) > 1 else None
            if not _is_nonnegative_number(tomorrow_precipitation):
                tomorrow_precipitation = None

            freshness = assess_weather_freshness(observed_at)
            retrieved_at = datetime.now(timezone.utc)
            source = SourceRecord(
                name="Open-Meteo",
                url=OPEN_METEO_URL,
                retrieved_at=retrieved_at,
                observed_at=observed_at,
                freshness_status=freshness.status,
                freshness_note=(
                    f"LIVE Open-Meteo response; observation {observed_at.isoformat()} UTC-normalized; "
                    f"status={freshness.status}. Forecast values can change."
                ),
            )
            if freshness.status != "current":
                return ToolResult(
                    ok=False,
                    error_code=f"WEATHER_OBSERVATION_{freshness.status.upper()}",
                    retryable=True,
                    data={
                        "observed_at": observed_at.isoformat(),
                        "freshness_status": freshness.status,
                        "observation_age_minutes": freshness.age_minutes,
                    },
                    source=source,
                )

            return ToolResult(
                ok=True,
                data={
                    "latitude": latitude,
                    "longitude": longitude,
                    "temperature_c": temperature,
                    "precipitation_mm": precipitation,
                    "rain_probability_pct": rain_probability,
                    "next_24h_rain_probability_max": rain_probability,
                    "tomorrow_date": tomorrow_date,
                    "tomorrow_rain_probability_pct": tomorrow_probability,
                    "tomorrow_precipitation_mm": tomorrow_precipitation,
                    "observed_at": observed_at.isoformat(),
                    "timezone": timezone_name,
                    "freshness_status": freshness.status,
                    "observation_age_minutes": freshness.age_minutes,
                },
                source=source,
            )
        except (httpx.HTTPError, ValueError, TypeError, KeyError, OverflowError) as exc:
            return ToolResult(
                ok=False,
                error_code="WEATHER_PROVIDER_ERROR",
                retryable=True,
                data={"detail": type(exc).__name__, "latitude": latitude, "longitude": longitude},
            )


class DataGovMandiTool:
    """AGMARKNET-backed OGD adapter.

    The OGD resource id and API key are configuration, not source-code constants.
    This keeps demo builds deterministic while allowing a real government resource
    to be enabled without changing orchestration code.
    """

    def __init__(
        self,
        *,
        api_key: str,
        resource_id: str,
        api_base: str = "https://api.data.gov.in/resource",
        timeout_seconds: float = 8.0,
    ) -> None:
        self.api_key = api_key
        self.resource_id = resource_id
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def price(self, *, commodity: str, state: str, district: str | None = None, market: str | None = None) -> ToolResult:
        url = f"{self.api_base}/{self.resource_id}"
        filters = {"state.keyword": state, "commodity": commodity}
        if district:
            filters["district"] = district
        if market:
            filters["market"] = market

        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": 25,
            "sort[arrival_date]": "desc",
            **{f"filters[{key}]": value for key, value in filters.items()},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()

            records = payload.get("records") or []
            if not records:
                return ToolResult(
                    ok=False,
                    error_code="MANDI_NO_RECORDS",
                    retryable=False,
                    data={"commodity": commodity, "state": state, "district": district},
                    source=SourceRecord(
                        name="Government OGD / AGMARKNET",
                        url=url,
                        retrieved_at=datetime.now(timezone.utc),
                        freshness_note="Government dataset queried; no matching record returned.",
                        freshness_status="unknown",
                    ),
                )

            def norm(value: object) -> str:
                return " ".join(str(value or "").casefold().split())

            def record_field(record: dict, *keys: str):
                for key in keys:
                    if record.get(key) not in (None, ""):
                        return record[key]
                return None

            requested_commodity = norm(commodity)
            requested_state = norm(state)
            requested_district = norm(district)
            requested_market = norm(market)

            def score(record: dict) -> int:
                score = 0
                if norm(record_field(record, "commodity", "Commodity")) == requested_commodity:
                    score += 4
                if norm(record_field(record, "state", "State")) == requested_state:
                    score += 3
                if requested_district and norm(record_field(record, "district", "District")) == requested_district:
                    score += 3
                if requested_market and norm(record_field(record, "market", "Market")) == requested_market:
                    score += 5
                return score

            def arrival_date(record: dict) -> datetime:
                value = record_field(record, "arrival_date", "Arrival_Date", "arrival date")
                if not value:
                    return datetime.min.replace(tzinfo=timezone.utc)
                text = str(value).strip()
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
                    try:
                        return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
                    except ValueError:
                        continue
                return datetime.min.replace(tzinfo=timezone.utc)

            # Prefer the strongest entity match, then the newest dated record.
            # Never let upstream response ordering decide which market/date is shown.
            scored_records = sorted(
                ((score(record), arrival_date(record), record) for record in records),
                key=lambda item: (item[0], item[1]),
                reverse=True,
            )
            best_score, best_date, record = scored_records[0]
            if best_score < 7:

                return ToolResult(
                    ok=False,
                    error_code="MANDI_ENTITY_MISMATCH",
                    retryable=False,
                    data={"commodity": commodity, "state": state, "district": district, "market": market},
                    source=SourceRecord(
                        name="Government OGD / AGMARKNET",
                        url=url,
                        retrieved_at=datetime.now(timezone.utc),
                        freshness_note="Government dataset returned records, but none matched the requested commodity/location strongly enough.",
                        freshness_status="unknown",
                    ),
                )

            tied_best = [
                item for item in scored_records
                if item[0] == best_score and item[1] == best_date
            ]
            if len(tied_best) > 1:
                return ToolResult(
                    ok=False,
                    error_code="MANDI_AMBIGUOUS_MARKET",
                    retryable=False,
                    data={"commodity": commodity, "state": state, "district": district, "market": market},
                    source=SourceRecord(
                        name="Government OGD / AGMARKNET",
                        url=url,
                        retrieved_at=datetime.now(timezone.utc),
                        freshness_note="Multiple records tied on entity match and arrival date; no price was selected.",
                        freshness_status="unknown",
                    ),
                )

            freshness = assess_mandi_freshness(best_date)
            if freshness.status != "current":
                error_code = {
                    "unknown": "MANDI_OBSERVATION_DATE_UNKNOWN",
                    "future": "MANDI_OBSERVATION_DATE_INVALID",
                    "stale": "MANDI_STALE_RECORD",
                }.get(freshness.status, "MANDI_OBSERVATION_DATE_UNKNOWN")
                note = {
                    "unknown": "The matching government record has no valid arrival date; no price is presented as current.",
                    "future": "The matching government record has a future arrival date; no price is presented as current.",
                    "stale": "The matching government record is older than the seven-day freshness window; no price is presented as current.",
                }.get(freshness.status, "Observation date could not be verified.")
                return ToolResult(
                    ok=False,
                    error_code=error_code,
                    retryable=False,
                    data={"commodity": commodity, "state": state, "district": district, "market": market,
                          "arrival_date": record.get("arrival_date") or record.get("Arrival_Date") or record.get("arrival date")},
                    source=SourceRecord(
                        name="Government OGD / AGMARKNET",
                        url=url,
                        retrieved_at=datetime.now(timezone.utc),
                        freshness_note=note,
                        freshness_status=freshness.status,
                    ),
                )

            def field(*keys: str):
                for key in keys:
                    if record.get(key) not in (None, ""):
                        return record[key]
                return None

            def number(*keys: str) -> float | None:
                for key in keys:
                    value = record.get(key)
                    if value in (None, ""):
                        continue
                    try:
                        return float(str(value).replace(",", "").strip())
                    except ValueError:
                        continue
                return None

            modal = number("Modal_Price", "Modal Price", "modal_price", "Modal_x0020_Price")
            minimum = number("Min_Price", "Min Price", "min_price", "Min_x0020_Price")
            maximum = number("Max_Price", "Max Price", "max_price", "Max_x0020_Price")
            if modal is None:
                return ToolResult(
                    ok=False,
                    error_code="MANDI_INVALID_RECORD",
                    retryable=False,
                    data={"record": record},
                    source=SourceRecord(
                        name="Government OGD / AGMARKNET",
                        url=url,
                        retrieved_at=datetime.now(timezone.utc),
                        freshness_note="Government dataset returned a record without a usable modal price.",
                        freshness_status="unknown",
                    ),
                )

            return ToolResult(
                ok=True,
                data={
                    "commodity": field("commodity", "Commodity") or commodity,
                    "market": field("market", "Market") or market or district or state,
                    "district": field("district", "District") or district,
                    "state": field("state", "State") or state,
                    "arrival_date": field("arrival_date", "Arrival_Date", "arrival date"),
                    "min_price": minimum,
                    "modal_price": modal,
                    "max_price": maximum,
                    "unit": "INR/quintal",
                    "raw_record": record,
                },
                source=SourceRecord(
                    name="Government OGD / AGMARKNET",
                    url=url,
                    retrieved_at=datetime.now(timezone.utc),
                    freshness_note="LIVE government market-price response; selected record observation date is within the seven-day display window.",
                    freshness_status="live",
                ),
            )
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            return ToolResult(
                ok=False,
                error_code="MANDI_PROVIDER_ERROR",
                retryable=True,
                data={"detail": type(exc).__name__},
            )
