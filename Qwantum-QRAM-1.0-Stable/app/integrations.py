"""Integration registry and experiment coordinator for QRAM 1.0.0."""
from __future__ import annotations
from typing import Any
import uuid
from app.quantum_bridge import backend_status, run_circuit_demo, QuantumBackendUnavailable
from app.experiment_store import ExperimentStore, ExperimentNotFound


class IntegrationRegistry:
    def __init__(self, experiment_store: ExperimentStore):
        self.store = experiment_store

    def capabilities(self) -> dict[str, Any]:
        backend = backend_status()
        return {
            "service": "qwantum-qram", "protocol_version": "1.0",
            "integrations": {
                "qwp777": {"status": "adapter-contract", "connected": False,
                           "note": "No physical QWP-777 transport is configured."},
                "nebiru": {"status": "adapter-contract", "connected": False,
                           "note": "No Nebiru endpoint is configured."},
                "qiskit_aer": {"status": "available" if backend.get("available") else "optional-dependency-missing",
                                "connected": bool(backend.get("available")), "mode": backend.get("mode")},
            },
        }

    def create_experiment(self, qubits: int, shots: int, label: str = "hadamard_all") -> dict[str, Any]:
        if isinstance(qubits, bool) or not isinstance(qubits, int) or not 1 <= qubits <= 12:
            raise ValueError("qubits must be an integer between 1 and 12")
        if isinstance(shots, bool) or not isinstance(shots, int) or not 1 <= shots <= 100_000:
            raise ValueError("shots must be an integer between 1 and 100000")
        if label != "hadamard_all":
            raise ValueError("only the hadamard_all experiment is supported in 1.0.0")
        return self.store.create(str(uuid.uuid4()), label, qubits, shots)

    def run_experiment(self, experiment_id: str) -> dict[str, Any]:
        record = self.store.get(experiment_id)
        if record["status"] in {"completed", "unavailable", "failed", "running"}:
            return record
        claimed = self.store.start_if_queued(experiment_id)
        if claimed["status"] != "running":
            return claimed
        try:
            result = run_circuit_demo(record["qubits"], record["shots"])
            return self.store.update(experiment_id, status="completed", result=result,
                                     backend=result.get("backend"),
                                     metadata={"operation": result.get("operation"), "qubits": record["qubits"], "shots": record["shots"]})
        except QuantumBackendUnavailable as exc:
            return self.store.update(experiment_id, status="unavailable", error=str(exc),
                                     metadata={"qubits": record["qubits"], "shots": record["shots"]})
        except Exception as exc:
            return self.store.update(experiment_id, status="failed", error=str(exc),
                                     metadata={"qubits": record["qubits"], "shots": record["shots"]})

    def get_experiment(self, experiment_id: str) -> dict[str, Any]:
        return self.store.get(experiment_id)

    def list_experiments(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.store.list(limit)

    def experiment_history(self, experiment_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return self.store.history(experiment_id, limit)
