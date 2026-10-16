"""Durable in-app reminder worker.

The worker writes notifications to the database only. It does not send SMS,
browser push, or phone calls. The migration and feature flags must be enabled
only after isolated database acceptance and owner approval.
"""
import asyncio
import os
from logging import getLogger

from .config import get_settings
from .observability import emit_event
from .supabase_repositories import SupabaseReminderRepository, SupabaseRepositoryError

logger = getLogger(__name__)


def _enabled() -> bool:
    household_enabled = os.getenv("SAATHI_HOUSEHOLD_FEATURES_ENABLED", "false").strip().casefold() in {"1", "true", "yes"}
    return bool(get_settings().saathi_reminders_enabled and household_enabled)


async def run_once() -> int:
    if not _enabled():
        emit_event("reminder_worker.disabled", reason="feature_gate_closed")
        return 0
    settings = get_settings()
    batch_size = max(1, min(int(settings.reminder_batch_size), 100))
    try:
        rows = await SupabaseReminderRepository().deliver_due(batch_size=batch_size)
    except (SupabaseRepositoryError, ValueError) as exc:
        # Never log task titles, household IDs, or database response bodies.
        emit_event("reminder_worker.tick_failed", error_code=str(exc)[:100])
        return 0
    emit_event("reminder_worker.tick_completed", delivered_count=len(rows))
    return len(rows)


async def run_forever() -> None:
    interval = max(5, min(int(get_settings().reminder_worker_interval_seconds), 300))
    while True:
        await run_once()
        await asyncio.sleep(interval)


def main() -> None:
    if not _enabled():
        raise SystemExit(
            "Reminder worker is disabled. Apply the approved reminder migration, "
            "then set SAATHI_HOUSEHOLD_FEATURES_ENABLED=true and SAATHI_REMINDERS_ENABLED=true."
        )
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
