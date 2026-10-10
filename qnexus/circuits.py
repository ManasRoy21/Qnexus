"""Executable BB84-inspired preparation and intercept/resend circuits.

This models a four-state channel, not a full Practical QDS construction.
"""
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import depolarizing_error


def prepare_and_measure(bit: int, basis: int, receiver_basis: int,
                        eve_basis: int | None = None, baseline_qber: float = 0.0):
    """Prepare |0>, |1>, |+> or |-> and measure in Z or X.

    c[0] records Eve, c[1] the receiver. After Eve's projective measurement,
    restoring her basis leaves the same state as ideal intercept-and-resend.
    A depolarizing channel of strength 2e induces error rate e in either basis.
    """
    if any(value not in (0, 1) for value in (bit, basis, receiver_basis)):
        raise ValueError("Bits and bases must be 0 (Z) or 1 (X)")
    if eve_basis not in (None, 0, 1) or not 0 <= baseline_qber <= 0.5:
        raise ValueError("Invalid Eve basis or baseline QBER")
    circuit = QuantumCircuit(1, 2, name=f"b{bit}_a{basis}_r{receiver_basis}_e{eve_basis}")
    if bit:
        circuit.x(0)
    if basis:
        circuit.h(0)
    circuit.barrier()
    if eve_basis is not None:
        if eve_basis:
            circuit.h(0)
        circuit.measure(0, 0)
        if eve_basis:
            circuit.h(0)
        circuit.barrier()
    if baseline_qber:
        circuit.append(depolarizing_error(2 * baseline_qber, 1).to_instruction(), [0])
    if receiver_basis:
        circuit.h(0)
    circuit.measure(0, 1)
    return circuit


def simulator():
    """Use real Aer simulation; limit thread count for small laptop workloads."""
    return AerSimulator(method="stabilizer", max_parallel_threads=2)


def circuit_demo(shots: int = 1024, seed: int = 42):
    circuit = prepare_and_measure(0, 0, 0, eve_basis=1)
    result = simulator().run(circuit, shots=shots, seed_simulator=seed).result()
    counts = result.get_counts()
    mismatches = sum(n for outcome, n in counts.items() if outcome.replace(" ", "")[0] == "1")
    return {"backend": "Qiskit Aer stabilizer simulator", "shots": shots,
            "counts": counts, "qber": mismatches / shots,
            "description": "Alice sends |0>; Eve measures in X; Bob measures in Z. Expect approximately 50% Bob errors for this fixed wrong-basis circuit.",
            "circuit": str(circuit.draw(output="text"))}
