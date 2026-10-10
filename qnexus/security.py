"""Classical demo signing and IID sampling bounds, not a QDS security proof."""
import hashlib
import hmac
import json
import math


def sign_message(key: bytes, simulation_id: str, message: str):
    payload = json.dumps({"simulation_id": simulation_id, "message": message},
                         ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {"signature": hmac.new(key, payload, hashlib.sha256).hexdigest(),
            "message_digest": hashlib.sha256(message.encode()).hexdigest(),
            "algorithm": "HMAC-SHA256 classroom wrapper, not a quantum signature"}


def verify_message(key, simulation_id, message, signature, material):
    expected = sign_message(key, simulation_id, message)
    intact = hmac.compare_digest(expected["signature"], signature)
    bob, charlie = material["bob"], material["charlie"]
    config = material["config"]
    enough = not material["insufficient_data"]
    accepted_bob = (intact and enough and not material["abort"]
                    and bob["verification_qber"] <= config["authentication_threshold"])
    accepted_charlie = (intact and enough and not material["abort"]
                        and charlie["verification_qber"] <= config["verification_threshold"])
    return {"message_intact": intact, "bob_accepts": bool(accepted_bob),
            "charlie_accepts": bool(accepted_charlie),
            "insufficient_data": not enough, "message_digest": expected["message_digest"],
            "note": "Classical integrity check plus illustrative recipient thresholds. Does not establish QDS transferability or non-repudiation."}


def hoeffding_bound(n, epsilon, observed_qber=0):
    if n < 1 or not 0 < epsilon <= 1 or not 0 <= observed_qber <= 1:
        raise ValueError("Invalid Hoeffding inputs")
    raw = 2 * math.exp(-2 * n * epsilon**2)
    delta = min(1.0, raw)
    return {"n": n, "epsilon": epsilon, "observed_qber": observed_qber,
            "raw_bound": raw, "failure_probability_upper_bound": delta,
            "coverage_lower_bound": 1 - delta,
            "interval": [max(0, observed_qber - epsilon), min(1, observed_qber + epsilon)],
            "informative": raw < 1,
            "formula": "P(|sample mean - expected mean| >= epsilon) <= 2 exp(-2 n epsilon^2)",
            "assumptions": "Independent bounded Bernoulli observations. This is a sampling bound, not a protocol forging-security probability."}
