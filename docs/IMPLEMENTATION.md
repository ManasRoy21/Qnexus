# Implementation details

## Public model and circuits

The experiment prepares one-qubit states in two bases: Z (`|0>`, `|1>`) and X (`|+>`, `|->`). X chooses the sender bit; H chooses the X basis. A receiver applies H before measurement for the X basis. Matching-basis detections are retained.

This is a BB84-inspired channel experiment that illustrates disturbance relevant to quantum communication. It is not a coherent-state Practical QDS construction or a complete quantum signing protocol.

`circuits.py` constructs real `QuantumCircuit` objects. `simulation.py` executes them on `qiskit_aer.AerSimulator`, with `method="stabilizer"`, simulator seeds, and shot memory enabled. Preparation, measurement, and depolarizing noise are simulated; results are not hard-coded.

For interception, Eve chooses Z or X uniformly, rotates into her basis, measures, then rotates back. This leaves the same collapsed state as an ideal measurement-and-resend process in this single-qubit model. Bob then measures in his selected basis.

The circuit has two classical bits: `c[0]` is Eve, `c[1]` is the receiver. Qiskit count strings display the receiver first. An unused Eve bit stays zero.

Identical bit/basis/attack configurations are grouped. Each variant executes for the largest group size; only the required shot count for each group is retained. `executed_shots` can exceed `conclusive_bits` because extra batching shots are discarded. They never count as additional signals.

## Losses and measurement material

Independent seeded detection draws use:

```text
transmission = 10 ^ (−fiber_loss_db_per_km × distance_km / 10)
detection_probability = transmission × detector_efficiency
```

This approximates link losses, not a complete photon/detector model. Bob and Charlie have separate seeded channel and simulator draws. They share the sender bit and basis arrays.

Matching-basis detections are split into test and untested samples. `qber` is the test mismatch fraction. `verification_qber` is the unused-material mismatch fraction. A missing sample is `null` and produces insufficient-data status, never zero errors. Test and untested counts sum to the conclusive count.

`simulated_overall_qber` is a simulator diagnostic of all retained bits, not information available to every participant in a real protocol.

## Expected intercept-resend disturbance

On sifted signals, Eve uses the wrong basis half the time. A wrong-basis measurement induces a receiver error half the time. Full random-basis interception therefore has expected QBER 1/4 when baseline noise is zero.

For baseline error `e0` and interception fraction `gamma`:

```text
e_expected = e0 + (gamma / 4) × (1 − 2 e0)
```

The Aer depolarizing strength is `2 × e0`, which gives error probability `e0` in either basis. Finite samples fluctuate. An abort occurs if either recipient's test error rate exceeds the authentication threshold. Noise can also trigger an abort, so this does not uniquely attribute an attack.

The standalone circuit fixes Eve to the wrong basis and expects approximately 50% errors. The random-basis full-interception sweep expects approximately 25% at zero baseline noise.

## Message demonstration

HMAC-SHA256 signs canonical JSON containing the exact message and experiment ID. The demo key hashes the sender's seeded simulation bits. Verification uses constant-time HMAC comparison, then checks Bob and Charlie's untested mismatch rates against their thresholds. A failed channel test or insufficient material prevents acceptance.

This is a **classical teaching wrapper**. All roles run in one local process, the seed is not secret, and the key is unsuitable for production. It does not establish QDS transferability, unforgeability, or non-repudiation. Complete QDS needs a specified distribution, recipient symmetrisation, signing construction, and security analysis.

## Sampling calculation

For independent Bernoulli samples:

```text
P(|sample mean − expected mean| >= epsilon) <= 2 exp(−2 n epsilon^2)
```

The endpoint returns the raw expression, an upper bound capped at 1, and coverage lower bound `1 − min(1, expression)`. A raw bound at least 1 is uninformative. For example, `n=162`, `epsilon=0.035` gives no useful coverage assurance. The displayed error rate ± tolerance interval must be interpreted with the accompanying bound and independence assumptions. This is not a protocol forging or repudiation probability.

## API

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Project and local runtime status |
| GET | `/api/circuit` | Execute a fixed 1,024-shot Aer circuit |
| POST | `/api/material` | Generate a seeded experiment |
| POST | `/api/sign` | Create a classical demo message token |
| POST | `/api/verify` | Check integrity and receiver thresholds |
| POST | `/api/attack` | Re-run saved settings with interception |
| POST | `/api/sweep` | Execute up to 21 intensities |
| POST | `/api/bounds` | Compute the sampling estimate |
| GET | `/api/report/{simulation_id}` | Export results without the demo key |

Pydantic validates sample sizes, probabilities, and threshold ordering. Sessions are bounded to 100 in memory and protected with locks. Attack runs are separate from baseline material. New material clears previous signing/results in the dashboard. The public API is intended for local execution, not multi-user deployment.

## Reproducibility and validation

The sample output records library versions. Identical seed, configuration, versions, and platform reproduce simulation data; API UUIDs intentionally change. Cross-version simulator RNG behaviour is not guaranteed. Tests execute actual Aer jobs and check expected disturbance ranges, sample accounting, changed messages, empty data, and the API sequence.
