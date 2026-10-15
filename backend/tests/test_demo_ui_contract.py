from pathlib import Path


def test_dashboard_exposes_purpose_specific_persisted_consent_controls():
    source = Path(__file__).parents[2].joinpath("frontend/app/dashboard/page.tsx").read_text(encoding="utf-8")
    assert "Consent is separate by purpose" in source
    assert "The conversation workflow does not yet write memories automatically" in source
    assert 'updateConsent("memory", true)' in source
    assert 'updateConsent("memory", false)' in source
    assert 'updateConsent("outbound_calls", true)' in source
    assert 'updateConsent("outbound_calls", false)' in source
    # No UI toggle should claim that consent automatically enables an unfinished feature.
    assert "simulateThreeDaysLater" not in source
    assert "memoryConsent" not in source
    assert "setMemoryConsent" not in source
