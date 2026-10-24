from fastapi.testclient import TestClient
from app.main import app
from app.quantum_bridge import run_circuit_demo, QuantumBackendUnavailable

client = TestClient(app)


def test_backend_status_shape():
    response = client.get("/api/quantum/backend")
    assert response.status_code == 200
    data = response.json()
    assert "available" in data
    assert "mode" in data


def test_circuit_demo_validates_qubit_range():
    try:
        run_circuit_demo(0, 10)
    except ValueError as exc:
        assert "between 1 and 12" in str(exc)
    else:
        raise AssertionError("invalid qubit count should fail")


def test_circuit_demo_validates_shots():
    try:
        run_circuit_demo(2, 0)
    except ValueError as exc:
        assert "between 1 and 100000" in str(exc)
    else:
        raise AssertionError("invalid shots should fail")


def test_endpoint_returns_result_or_clear_missing_dependency():
    response = client.post("/api/quantum/circuit-demo?shots=32", json={"qubits": 2, "operation": "hadamard_all"})
    assert response.status_code in (200, 503)
    if response.status_code == 200:
        body = response.json()
        assert body["backend"] == "qiskit-aer"
        assert sum(body["counts"].values()) == 32
    else:
        assert "qiskit" in response.json()["detail"].lower()
