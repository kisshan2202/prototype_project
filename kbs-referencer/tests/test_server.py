import asyncio

import pytest
from fastapi.testclient import TestClient

import server


@pytest.fixture
def client():
    server.limiter.limit = 0  # off for tests
    return TestClient(server.app)


def test_health(client):
    assert client.get("/health").json()["ok"] is True


def test_slow_request_times_out_with_clear_message(client, monkeypatch):
    async def hang(**kwargs):
        await asyncio.sleep(5)
        yield  # pragma: no cover

    monkeypatch.setattr(server, "REQUEST_TIMEOUT", 0.2)
    monkeypatch.setattr(server.runner, "run_async", hang)
    r = client.post("/api/reference", json={"url": "https://example.org/a"})
    assert r.status_code == 504 and "too long" in r.json()["detail"]


def test_rate_limit_returns_429(client):
    server.limiter.limit = 1
    server.limiter.hits.clear()
    try:
        client.post("/api/reference", json={"url": "notaurl"})  # 422 before the limiter
        assert client.post("/api/reference", json={"url": "https://example.org"}).status_code != 429
        assert client.post("/api/reference", json={"url": "https://example.org"}).status_code == 429
    finally:
        server.limiter.limit = 0
