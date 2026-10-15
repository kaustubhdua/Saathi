from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class MandiFreshness:
    status: str
    age_days: int | None


def assess_mandi_freshness(observation: datetime | None, *, now: datetime | None = None, max_age_days: int = 7) -> MandiFreshness:
    """Classify a market observation date; retrieval time is never substituted for it."""
    if observation is None or observation.year < 2000:
        return MandiFreshness("unknown", None)
    now = now or datetime.now(timezone.utc)
    if observation.tzinfo is None:
        observation = observation.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    age = (now.astimezone(timezone.utc).date() - observation.astimezone(timezone.utc).date()).days
    if age < 0:
        return MandiFreshness("future", age)
    if age > max_age_days:
        return MandiFreshness("stale", age)
    return MandiFreshness("current", age)


@dataclass(frozen=True)
class WeatherFreshness:
    status: str
    age_minutes: int | None


def assess_weather_freshness(
    observation: datetime | None,
    *,
    now: datetime | None = None,
    max_age_hours: int = 3,
    future_tolerance_minutes: int = 5,
) -> WeatherFreshness:
    """Classify provider observation time, never the later retrieval time."""
    if observation is None or observation.tzinfo is None:
        return WeatherFreshness("unknown", None)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    age_seconds = (now.astimezone(timezone.utc) - observation.astimezone(timezone.utc)).total_seconds()
    age_minutes = int(age_seconds // 60)
    if age_seconds < -(future_tolerance_minutes * 60):
        return WeatherFreshness("future", age_minutes)
    if age_seconds > max_age_hours * 60 * 60:
        return WeatherFreshness("stale", age_minutes)
    return WeatherFreshness("current", max(0, age_minutes))
