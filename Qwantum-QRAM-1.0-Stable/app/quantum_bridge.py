"""Educational adapter to a real circuit simulator (Qiskit Aer when installed).

The adapter does not claim to implement physical QRAM. It provides reproducible
small-circuit simulation and keeps this separate from the SQLite memory store.
"""
from __future__ import annotations

from typing import Any


class QuantumBackendUnavailable(RuntimeError):
    pass


def backend_status() -> dict[str, Any]:
    try:
        import qiskit  # noqa: F401
        from qiskit_aer import AerSimulator  # noqa: F401
        return {
            "available": True,
            "backend": "qiskit-aer",
            "mode": "local-circuit-simulation",
            "note": "Classical simulation of quantum circuits; not quantum hardware.",
        }
    except ImportError:
        return {
            "available": False,
            "backend": None,
            "mode": "unavailable",
            "note": "Install the optional qiskit and qiskit-aer packages to enable circuit simulation.",
        }


def run_circuit_demo(qubits: int = 2, shots: int = 1024) -> dict[str, Any]:
    if isinstance(qubits, bool) or not isinstance(qubits, int) or not 1 <= qubits <= 12:
        raise ValueError("qubits must be an integer between 1 and 12")
    if isinstance(shots, bool) or not isinstance(shots, int) or not 1 <= shots <= 100_000:
        raise ValueError("shots must be an integer between 1 and 100000")

    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit_aer import AerSimulator
    except ImportError as exc:
        raise QuantumBackendUnavailable(
            "Qiskit Aer is not installed. Install optional dependencies with: "
            "pip install 'qiskit>=1.2,<3' 'qiskit-aer>=0.15,<1'"
        ) from exc

    circuit = QuantumCircuit(qubits, qubits)
    circuit.h(range(qubits))
    circuit.measure(range(qubits), range(qubits))
    simulator = AerSimulator()
    compiled = transpile(circuit, simulator)
    result = simulator.run(compiled, shots=shots).result()
    counts = result.get_counts(compiled)
    probabilities = {state: count / shots for state, count in sorted(counts.items())}
    return {
        "backend": "qiskit-aer",
        "mode": "local-circuit-simulation",
        "qubits": qubits,
        "shots": shots,
        "operation": "hadamard_all_then_measure",
        "counts": counts,
        "probabilities": probabilities,
        "circuit_qasm": circuit.draw(output="text").__str__(),
        "note": "Measurement samples one bitstring per shot. This is a classical simulation, not physical quantum hardware.",
    }
