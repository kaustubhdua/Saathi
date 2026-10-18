"""Durable in-app reminder worker.

The worker writes notifications to the database only. It does not send SMS,
browser push, or phone calls. Feature flags default off; while disabled, the
process stays healthy and idle so a separately deployed worker does not crash
or enter a restart loop before the feature is approved.
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
    settings = get_settings()
    return bool(
        settings.saathi_reminders_enabled
        and household_enabled
        and settings.supabase_url
        and settings.supabase_secret_key
    )


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
    # Keep the deployment alive while flags are off. run_once() fails closed,
    # and checks the flags on every tick so operators can enable it deliberately.
    while True:
        settings = get_settings()
        interval = max(5, min(int(settings.reminder_worker_interval_seconds), 300))
        await run_once()
        await asyncio.sleep(interval)


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
