from datetime import datetime, timezone


def assess_mandi_freshness(observation: datetime | None, *, now: datetime | None = None, max_age_days: int = 7) -> type("Freshness", (), {}):
    """Classify a government market observation date; never treat retrieval time as observation time."""
    class Freshness:
        def __init__(self, status: str, age_days: int | None):
            self.status = status
            self.age_days = age_days

    if observation is None or observation.year < 2000:
        return Freshness("unknown", None)
    now = now or datetime.now(timezone.utc)
    if observation.tzinfo is None:
        observation = observation.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    age = (now.date() - observation.astimezone(timezone.utc).date()).days
    if age < 0:
        return Freshness("future", age)
    if age > max_age_days:
        return Freshness("stale", age)
    return Freshness("current", age)
