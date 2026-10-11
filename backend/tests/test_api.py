from fastapi.testclient import TestClient
from app.main import app

def test_agent_endpoint_returns_provenance():
    client=TestClient(app)
    response=client.post('/api/v1/agent',json={'message':'सोनीपत मंडी में गेहूं का भाव क्या है?','language':'hi'})
    assert response.status_code == 200
    data=response.json()
    assert data['intent']=='farming'
    assert data['source']['name']=='Saathi Demo Mandi'
    assert data['demo'] is True
    assert data['tool_name'] == 'get_mandi_price'
    assert isinstance(data['latency_ms'], (int, float)) and data['latency_ms'] >= 0

def test_liveness():
    assert TestClient(app).get('/health/live').json()['status']=='alive'


def test_agent_endpoint_exposes_all_sources_for_combined_request():
    client=TestClient(app)
    response=client.post(
        '/api/v1/agent',
        json={
            'message':'सोनीपत में गेहूं का मंडी भाव और अगले 24 घंटे में बारिश का chance?',
            'language':'hi',
            'location':{'latitude':28.9931,'longitude':77.0151,'label':'Sonipat'},
        },
    )
    assert response.status_code == 200
    data=response.json()
    assert data['tool_name']=='get_mandi_price+get_weather'
    assert len(data['sources']) == 2
    assert data['source']['name'] in {item['name'] for item in data['sources']}

def test_voice_response_schema_keeps_telemetry_fields():
    from app.schemas import VoiceTurnResponse
    payload=VoiceTurnResponse(status='ok',tool_name='get_weather',latency_ms=12.5)
    assert payload.tool_name == 'get_weather'
    assert payload.latency_ms == 12.5


def test_api_responses_disable_caching_and_expose_correlation_id():
    response = TestClient(app).post('/api/v1/agent', json={'message': 'नमस्ते', 'language': 'hi'})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers.get('x-correlation-id')


def test_operator_api_auth_can_be_enabled(monkeypatch):
    import app.main as module
    monkeypatch.setattr(module.settings, "demo_mode", False)
    monkeypatch.setattr(module.settings, "api_auth_token", "operator-secret")
    client = TestClient(module.app)
    denied = client.post("/api/v1/agent", json={"message": "नमस्ते", "language": "hi"})
    assert denied.status_code == 401
    allowed = client.post(
        "/api/v1/agent",
        headers={"X-Saathi-API-Key": "operator-secret"},
        json={"message": "नमस्ते", "language": "hi"},
    )
    assert allowed.status_code == 200
    monkeypatch.setattr(module.settings, "demo_mode", True)
    monkeypatch.setattr(module.settings, "api_auth_token", None)


def test_backend_security_headers_are_present(monkeypatch):
    import app.main as module
    monkeypatch.setattr(module.settings, "app_env", "production")
    response = TestClient(module.app).get("/health/live")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(), geolocation=(), microphone=()"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert "max-age=31536000" in response.headers["strict-transport-security"]
    monkeypatch.setattr(module.settings, "app_env", "development")


def test_cors_allows_operator_api_key_header():
    response = TestClient(app).options(
        "/api/v1/agent",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-saathi-api-key",
        },
    )
    assert response.status_code == 200
    assert "x-saathi-api-key" in response.headers["access-control-allow-headers"].lower()


def test_non_demo_api_fails_closed_when_auth_is_not_configured(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", False)
    monkeypatch.setattr(main.settings, "api_auth_token", None)
    response = TestClient(app).post("/api/v1/agent", json={"message": "नमस्ते"})
    assert response.status_code == 503
    assert response.json()["detail"] == "api_authentication_not_configured"


def test_non_demo_api_requires_a_matching_server_token(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", False)
    monkeypatch.setattr(main.settings, "api_auth_token", "test-only-secret")

    client = TestClient(app)
    denied = client.post("/api/v1/agent", json={"message": "नमस्ते"})
    assert denied.status_code == 401

    allowed = client.post(
        "/api/v1/agent",
        json={"message": "नमस्ते"},
        headers={"X-Saathi-API-Key": "test-only-secret"},
    )
    assert allowed.status_code == 200



def test_production_telephony_stream_auth_fails_closed_without_token(monkeypatch):
    import pytest
    from fastapi import HTTPException
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", False)
    monkeypatch.setattr(main.settings, "telephony_stream_token", None)
    with pytest.raises(HTTPException) as exc:
        main._authorize_telephony_stream(None)
    assert exc.value.status_code == 503
    assert exc.value.detail == "telephony_stream_auth_not_configured"


def test_telephony_stream_auth_rejects_wrong_token_and_accepts_matching_token(monkeypatch):
    import pytest
    from fastapi import HTTPException
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", False)
    monkeypatch.setattr(main.settings, "telephony_stream_token", "stream-test-secret")
    with pytest.raises(HTTPException) as exc:
        main._authorize_telephony_stream("wrong-secret")
    assert exc.value.status_code == 401
    main._authorize_telephony_stream("stream-test-secret")


def test_demo_telephony_stream_can_run_without_admission_token(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "demo_mode", True)
    monkeypatch.setattr(main.settings, "telephony_stream_token", None)
    main._authorize_telephony_stream(None)
