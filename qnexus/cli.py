"""Terminal demo that executes real Aer circuits and saves reproducible outputs."""
import argparse
import json
from pathlib import Path

from .circuits import circuit_demo
from .models import Experiment
from .security import hoeffding_bound, sign_message, verify_message
from .simulation import run_experiment


def main():
    parser = argparse.ArgumentParser(description="QNexus public Qiskit demo")
    parser.add_argument("--pulses", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("examples/generated/demo.json"))
    args = parser.parse_args()
    config = Experiment(pulse_count=args.pulses, seed=args.seed, distance_km=0,
                        detector_efficiency=1, baseline_qber=0)
    clean, key = run_experiment(config)
    attacked, _ = run_experiment(config, attack_intensity=1)
    message, identifier = "QNexus hackathon demonstration", "cli-demo"
    signed = sign_message(key, identifier, message)
    sweep = []
    for intensity in (0, 0.25, 0.5, 0.75, 1):
        result, _ = run_experiment(config, intensity)
        sweep.append({"intensity": intensity, "qber": result["pooled_test_qber"]})
    output = {"scope": "Public educational MVP, not a complete QDS implementation",
              "circuit_execution": circuit_demo(seed=args.seed),
              "clean_channel": clean, "intercept_resend": attacked,
              "signing": signed,
              "verification": verify_message(key, identifier, message, signed["signature"], clean),
              "tampered_verification": verify_message(key, identifier, message + " changed", signed["signature"], clean),
              "sweep": sweep,
              "sampling_bound": hoeffding_bound(clean["tested_bits"], 0.035, clean["pooled_test_qber"])}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(output["circuit_execution"]["circuit"])
    print(f"Clean QBER: {clean['pooled_test_qber']:.2%}")
    print(f"Full intercept-resend QBER: {attacked['pooled_test_qber']:.2%}")
    print(f"Changed message passes integrity check: {output['tampered_verification']['message_intact']}")
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
