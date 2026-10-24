from fastapi.testclient import TestClient
from app.main import app, rate_limiter
from app.security import FixedWindowRateLimiter

client = TestClient(app)


def test_api_key_required_when_configured(monkeypatch):
    monkeypatch.setenv("QRAM_API_KEY", "test-secret-key")
    no_key = client.get("/api/quantum/backend")
    assert no_key.status_code == 401
    assert no_key.headers.get("X-RateLimit-Limit") is not None
    wrong = client.get("/api/quantum/backend", headers={"X-API-Key": "wrong"})
    assert wrong.status_code == 401
    right = client.get("/api/quantum/backend", headers={"X-API-Key": "test-secret-key"})
    assert right.status_code == 200
    monkeypatch.delenv("QRAM_API_KEY", raising=False)


def test_health_remains_public_with_api_key_enabled(monkeypatch):
    monkeypatch.setenv("QRAM_API_KEY", "test-secret-key")
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["api_key_required"] is True
    monkeypatch.delenv("QRAM_API_KEY", raising=False)


def test_fixed_window_limiter_blocks_and_resets():
    limiter = FixedWindowRateLimiter()
    assert limiter.check("test", 2, window_seconds=10, now=100)[0] is True
    assert limiter.check("test", 2, window_seconds=10, now=101)[0] is True
    allowed, retry = limiter.check("test", 2, window_seconds=10, now=102)
    assert allowed is False and retry >= 1
    assert limiter.check("test", 2, window_seconds=10, now=111)[0] is True
