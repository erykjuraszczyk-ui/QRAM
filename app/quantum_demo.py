import math


def hadamard_all_demo(qubits: int, max_qubits: int = 12) -> dict:
    """
    Educational state-vector demo. Starts in |0...0> and applies H to all qubits.
    Amplitudes are all 1/sqrt(2**qubits); probabilities are uniform.
    """
    if not isinstance(qubits, int) or isinstance(qubits, bool):
        raise ValueError("qubits must be an integer")
    if qubits < 1 or qubits > max_qubits:
        raise ValueError(f"qubits must be between 1 and {max_qubits}")

    dimension = 1 << qubits
    amplitude = 1 / math.sqrt(dimension)
    probabilities = [amplitude * amplitude for _ in range(dimension)]
    # Keep response compact for the UI while giving full outcome count.
    preview = [
        {"basis_state": format(i, f"0{qubits}b"), "probability": probabilities[i]}
        for i in range(min(dimension, 32))
    ]
    return {
        "qubits": qubits,
        "dimension": dimension,
        "operation": "hadamard_all",
        "amplitude_magnitude": amplitude,
        "outcome_count": dimension,
        "probability_sum": sum(probabilities),
        "preview": preview,
        "note": "Simulation only. A measurement returns one sampled outcome; it does not expose all outcomes at once.",
    }
