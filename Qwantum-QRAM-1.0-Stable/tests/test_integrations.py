from fastapi.testclient import TestClient
from app.main import app
from app.integrations import IntegrationRegistry, ExperimentNotFound
from app.experiment_store import ExperimentStore
import tempfile

client = TestClient(app)


def test_capabilities_contracts_are_explicit():
    data = client.get("/api/integrations/capabilities").json()
    assert data["protocol_version"] == "1.0"
    assert data["integrations"]["qwp777"]["connected"] is False
    assert data["integrations"]["nebiru"]["connected"] is False


def test_create_and_get_experiment():
    created = client.post("/api/experiments", json={"qubits": 2, "shots": 64, "label": "hadamard_all"})
    assert created.status_code == 200
    record = created.json()
    assert record["status"] == "queued"
    fetched = client.get(f"/api/experiments/{record['experiment_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["experiment_id"] == record["experiment_id"]


def test_list_experiments():
    client.post("/api/experiments", json={"qubits": 1, "shots": 10})
    response = client.get("/api/experiments")
    assert response.status_code == 200
    assert isinstance(response.json()["experiments"], list)


def test_invalid_experiment_is_rejected():
    response = client.post("/api/experiments", json={"qubits": 13, "shots": 10})
    assert response.status_code == 422


def test_unknown_experiment_returns_404():
    assert client.get("/api/experiments/not-a-real-id").status_code == 404


def test_registry_rejects_invalid_values():
    registry = IntegrationRegistry(ExperimentStore(tempfile.mktemp(suffix=".db")))
    try:
        registry.create_experiment(0, 10)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid qubit count should fail")


def test_experiment_history_endpoint():
    created = client.post("/api/experiments", json={"qubits": 2, "shots": 16})
    assert created.status_code == 200
    experiment_id = created.json()["experiment_id"]
    response = client.get(f"/api/experiments/{experiment_id}/history")
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) >= 1
    assert events[0]["event_type"] == "created"
