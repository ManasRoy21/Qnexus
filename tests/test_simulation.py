from qnexus.circuits import circuit_demo, prepare_and_measure, simulator
from qnexus.models import Experiment
from qnexus.security import hoeffding_bound, sign_message, verify_message
from qnexus.simulation import run_experiment


def ideal_config(**kwargs):
    return Experiment(pulse_count=6000, distance_km=0, detector_efficiency=1,
                      baseline_qber=0, **kwargs)


def test_matching_basis_preparations_have_no_errors():
    circuits = [prepare_and_measure(bit, basis, basis) for bit in (0, 1) for basis in (0, 1)]
    result = simulator().run(circuits, shots=128, memory=True, seed_simulator=42).result()
    for i, (bit, _) in enumerate((bit, basis) for bit in (0, 1) for basis in (0, 1)):
        assert all(int(memory[0]) == bit for memory in result.get_memory(i))


def test_channel_baseline_and_attack_match_physical_model():
    config = ideal_config()
    clean, key = run_experiment(config)
    repeated, repeated_key = run_experiment(config)
    attacked, _ = run_experiment(config, 1)
    assert clean == repeated and key == repeated_key
    assert clean["pooled_test_qber"] == 0
    assert not clean["abort"]
    assert 0.20 < attacked["pooled_test_qber"] < 0.30
    assert attacked["abort"]
    assert attacked["expected_sifted_qber"] == 0.25
    for label in ("bob", "charlie"):
        recipient = clean[label]
        assert recipient["conclusive_bits"] == recipient["tested_bits"] + recipient["untested_bits"]
        assert recipient["executed_circuits"] > 0


def test_classical_wrapper_rejects_tampered_message_and_session():
    material, key = run_experiment(ideal_config())
    signed = sign_message(key, "session-a", "hello")
    good = verify_message(key, "session-a", "hello", signed["signature"], material)
    tampered = verify_message(key, "session-a", "changed", signed["signature"], material)
    wrong_session = verify_message(key, "session-b", "hello", signed["signature"], material)
    assert good["message_intact"] and good["bob_accepts"] and good["charlie_accepts"]
    assert not tampered["message_intact"] and not tampered["bob_accepts"]
    assert not wrong_session["message_intact"]


def test_small_sample_bound_does_not_claim_confidence():
    loose = hoeffding_bound(162, .035)
    tighter = hoeffding_bound(10_000, .035)
    assert loose["failure_probability_upper_bound"] == 1
    assert loose["coverage_lower_bound"] == 0
    assert not loose["informative"]
    assert tighter["informative"]
    assert tighter["failure_probability_upper_bound"] < 1e-8


def test_wrong_basis_circuit_has_half_errors():
    result = circuit_demo(shots=2048)
    assert 0.45 < result["qber"] < 0.55
    assert sum(result["counts"].values()) == 2048


def test_channel_with_no_detected_data_is_not_accepted():
    result, key = run_experiment(Experiment(pulse_count=200, distance_km=100,
                                          fiber_loss_db_per_km=1, detector_efficiency=.001))
    signed = sign_message(key, "empty", "hello")
    verified = verify_message(key, "empty", "hello", signed["signature"], result)
    assert result["insufficient_data"]
    assert result["pooled_test_qber"] is None
    assert not verified["bob_accepts"] and not verified["charlie_accepts"]
