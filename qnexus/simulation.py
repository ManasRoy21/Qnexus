"""Seeded losses and basis choices; outcomes sampled from executable circuits."""
from collections import defaultdict
from hashlib import sha256
import importlib.metadata

import numpy as np

from .circuits import prepare_and_measure, simulator
from .models import Experiment


def _recipient(config, sender_bits, sender_bases, label, attack_intensity, offset):
    rng = np.random.default_rng(config.seed + offset)
    count = config.pulse_count
    transmission = 10 ** (-config.fiber_loss_db_per_km * config.distance_km / 10)
    detected = rng.random(count) < transmission * config.detector_efficiency
    bases = rng.integers(0, 2, count)
    intercepted = rng.random(count) < attack_intensity
    eve_bases = rng.integers(0, 2, count)
    # Retain matching-basis detections. We simulate their measurement outcomes.
    indices = np.flatnonzero(detected & (bases == sender_bases))
    groups = defaultdict(list)
    for index in indices:
        key = (int(sender_bits[index]), int(sender_bases[index]), int(bases[index]),
               int(eve_bases[index]) if intercepted[index] else None)
        groups[key].append(int(index))
    outcomes = {}
    circuit_count = executed_shots = 0
    if groups:
        keys = list(groups)
        circuits = [prepare_and_measure(*key, baseline_qber=config.baseline_qber) for key in keys]
        # Equal-shot batching keeps one Aer job per receiver. Unneeded shots are
        # discarded, never counted as extra pulses or conclusive measurements.
        shots = max(len(groups[key]) for key in keys)
        result = simulator().run(circuits, shots=shots, memory=True,
                                 seed_simulator=config.seed + offset).result()
        if not result.success:
            raise RuntimeError("Qiskit Aer simulation failed")
        for i, key in enumerate(keys):
            for index, memory in zip(groups[key], result.get_memory(i)):
                outcomes[index] = int(memory.replace(" ", "")[0])
        circuit_count, executed_shots = len(circuits), shots * len(circuits)
    test_count = min(len(indices) - 1, max(1, int(len(indices) * config.test_fraction))) if len(indices) > 1 else 0
    test_indices = set(map(int, rng.choice(indices, test_count, replace=False))) if test_count else set()
    untested = [int(index) for index in indices if index not in test_indices]
    test_mismatches = sum(outcomes[i] != int(sender_bits[i]) for i in test_indices)
    remaining_mismatches = sum(outcomes[i] != int(sender_bits[i]) for i in untested)
    total_mismatches = test_mismatches + remaining_mismatches
    qber = test_mismatches / test_count if test_count else None
    verification_qber = remaining_mismatches / len(untested) if untested else None
    summary = {
        "recipient": label, "detected_pulses": int(detected.sum()),
        "conclusive_bits": len(indices), "tested_bits": test_count,
        "untested_bits": len(untested), "test_mismatches": int(test_mismatches),
        "qber": qber, "verification_qber": verification_qber,
        "simulated_overall_qber": total_mismatches / len(indices) if len(indices) else None,
        "usable_fraction": len(untested) / config.pulse_count,
        "executed_circuits": circuit_count, "executed_shots": executed_shots,
        "register_preview": "".join(str(outcomes[i]) for i in untested[:64]),
    }
    return summary


def run_experiment(config: Experiment, attack_intensity: float = 0):
    if not 0 <= attack_intensity <= 1:
        raise ValueError("Attack intensity must be between 0 and 1")
    rng = np.random.default_rng(config.seed)
    bits = rng.integers(0, 2, config.pulse_count)
    bases = rng.integers(0, 2, config.pulse_count)
    bob = _recipient(config, bits, bases, "Bob", attack_intensity, 101)
    charlie = _recipient(config, bits, bases, "Charlie", attack_intensity, 202)
    samples = [r for r in (bob, charlie) if r["tested_bits"]]
    tested = sum(r["tested_bits"] for r in samples)
    mismatches = sum(r["test_mismatches"] for r in samples)
    pooled_qber = mismatches / tested if tested else None
    return {
        "config": config.model_dump(), "attack_intensity": attack_intensity,
        "bob": bob, "charlie": charlie, "tested_bits": tested,
        "pooled_test_qber": pooled_qber,
        "abort": any(r["qber"] is not None and r["qber"] > config.authentication_threshold for r in (bob, charlie)),
        "insufficient_data": not all(r["tested_bits"] and r["untested_bits"] for r in (bob, charlie)),
        "expected_sifted_qber": config.baseline_qber + attack_intensity * 0.25 * (1 - 2 * config.baseline_qber),
        "backend": "Qiskit Aer stabilizer simulator",
        "versions": {name: importlib.metadata.version(name) for name in ("qiskit", "qiskit-aer")},
        "model": "BB84-inspired four-state educational channel; not a complete QDS protocol",
    }, sha256(bits.tobytes()).digest()
