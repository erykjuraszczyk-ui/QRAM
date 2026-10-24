import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# Import app with an isolated SQLite database so tests don't alter user data.
_TEST_DB = tempfile.mktemp(prefix="qram-test-", suffix=".db")
os.environ["QRAM_DATABASE_PATH"] = _TEST_DB

from app.main import app, memory  # noqa: E402

client = TestClient(app)


def setup_function():
    memory.reset()


def test_health_and_version():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    version = client.get("/api/version").json()
    assert version["version"] == "1.0.0"
    assert version["storage"] == "sqlite"
    assert version["schema_version"] == 3


def test_write_then_read_and_revision():
    first = client.post("/api/memory/write", json={"address": 4, "value": "alpha"})
    second = client.post("/api/memory/write", json={"address": 4, "value": "beta"})
    assert first.status_code == second.status_code == 200
    assert first.json()["revision"] == 1
    assert second.json()["revision"] == 2
    assert client.get("/api/memory/read/4").json()["value"] == "beta"


def test_data_persists_in_database_store():
    client.post("/api/memory/write", json={"address": 7, "value": "persistent"})
    assert client.get("/api/memory/read/7").json()["value"] == "persistent"


def test_history_tracks_writes_and_deletes():
    client.post("/api/memory/write", json={"address": 2, "value": "one"})
    client.post("/api/memory/write", json={"address": 2, "value": "two"})
    history = client.get("/api/memory/history/2").json()["history"]
    assert [item["operation"] for item in history] == ["write", "write"]
    assert [item["revision"] for item in history] == [2, 1]


def test_empty_address_returns_404():
    assert client.get("/api/memory/read/8").status_code == 404


def test_invalid_address_returns_422():
    assert client.post("/api/memory/write", json={"address": -1, "value": "x"}).status_code == 422


def test_empty_value_rejected():
    assert client.post("/api/memory/write", json={"address": 1, "value": ""}).status_code == 422


def test_list_and_reset():
    client.post("/api/memory/write", json={"address": 2, "value": "x"})
    assert client.get("/api/memory").json()["stats"]["used"] == 1
    reset = client.delete("/api/memory")
    assert reset.json()["removed_cells"] == 1
    assert client.get("/api/memory").json()["cells"] == []
    history = client.get("/api/memory/history/2").json()["history"]
    assert history[0]["operation"] == "delete"


def test_quantum_demo_probabilities():
    result = client.post("/api/quantum/demo", json={"qubits": 2, "operation": "hadamard_all"})
    assert result.status_code == 200
    assert result.json()["dimension"] == 4
    assert abs(result.json()["probability_sum"] - 1.0) < 1e-9
    assert len(result.json()["preview"]) == 4


def test_quantum_demo_limit():
    assert client.post("/api/quantum/demo", json={"qubits": 13}).status_code == 422
