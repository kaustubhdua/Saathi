import asyncio

from fastapi.testclient import TestClient

from app.main import app


def test_voice_turn_timeout_cancels_provider_and_returns_gateway_timeout(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", True)
    monkeypatch.setattr(main.settings, "app_env", "development")
    monkeypatch.setattr(main, "VOICE_TURN_TIMEOUT_SECONDS", 0.01)
    cancelled = False

    async def stalled_provider(*args, **kwargs):
        nonlocal cancelled
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            cancelled = True
            raise

    monkeypatch.setattr(main.voice_gateway, "handle", stalled_provider)
    response = TestClient(app).post(
        "/api/v1/voice/turn",
        files={"audio": ("recording.webm", bytes([0x1A, 0x45, 0xDF, 0xA3]) + bytes(8), "audio/webm")},
        data={"language": "hi"},
    )

    assert response.status_code == 504
    assert response.json() == {"detail": "voice_request_timeout"}
    assert cancelled
