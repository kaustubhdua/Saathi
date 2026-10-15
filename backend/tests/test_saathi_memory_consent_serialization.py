from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROPOSED = ROOT / "docs" / "proposed-migrations" / "20261015090000_saathi_memory_consent_serialization.sql.proposed"
ACTIVE = ROOT / "supabase" / "migrations"


def test_memory_consent_guard_locks_household_before_authorizing_write():
    sql = PROPOSED.read_text(encoding="utf-8")
    assert "FOR UPDATE;" in sql
    assert "current_memory_consent IS DISTINCT FROM TRUE" in sql
    assert "current_memory_consent_at IS NULL" in sql
    assert "current_memory_consent_revoked_at >= current_memory_consent_at" in sql
    assert "household_memory_consent_required" in sql
    assert "GRANT EXECUTE ON FUNCTION public.saathi_enforce_memory_consent() TO service_role" in sql


def test_consent_serialization_migration_stays_out_of_active_discovery():
    assert PROPOSED.exists()
    assert not (ACTIVE / PROPOSED.name).exists()
    assert "PROPOSED ONLY" in PROPOSED.read_text(encoding="utf-8")
