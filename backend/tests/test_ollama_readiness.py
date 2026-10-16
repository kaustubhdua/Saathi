import httpx

from app import main


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    payload = {"models": [{"name": "qwen2.5:7b"}]}

    def __init__(self, timeout, trust_env):
        assert timeout == 1.5
        assert trust_env is False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url):
        assert url == "http://127.0.0.1:11434/api/tags"
        return FakeResponse(self.payload)


def test_ollama_readiness_requires_exact_model_to_be_pulled(monkeypatch):
    monkeypatch.setattr(main.httpx, "Client", FakeClient)
    assert main._ollama_model_available("http://127.0.0.1:11434", "qwen2.5:7b") is True
    assert main._ollama_model_available("http://127.0.0.1:11434", "qwen2.5:3b") is False


def test_ollama_readiness_fails_closed_on_unreachable_server(monkeypatch):
    class UnreachableClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url):
            raise httpx.ConnectError("offline")

    monkeypatch.setattr(main.httpx, "Client", UnreachableClient)
    assert main._ollama_model_available("http://127.0.0.1:11434", "qwen2.5:7b") is False


def test_ollama_readiness_rejects_url_with_embedded_credentials():
    assert main._ollama_model_available("http://user:pass@127.0.0.1:11434", "qwen2.5:7b") is False


def test_non_demo_readiness_is_not_ready_without_local_model(monkeypatch):
    monkeypatch.setattr(main.settings, "demo_mode", False)
    monkeypatch.setattr(main.settings, "app_env", "production")
    monkeypatch.setattr(main.settings, "api_auth_token", "server-test-token")
    monkeypatch.setattr(main.settings, "llm_provider", "ollama")
    monkeypatch.setattr(main.settings, "ollama_base_url", "http://127.0.0.1:11434")
    monkeypatch.setattr(main.settings, "llm_model", "qwen2.5:7b")
    monkeypatch.setattr(main, "_ollama_model_available", lambda *_args: False)

    body = main.readiness()
    assert body["status"] == "not_ready"
    assert "local_reasoning_model" in body["missing_requirements"]
    assert body["provider_contracts"]["reasoning"] is False
