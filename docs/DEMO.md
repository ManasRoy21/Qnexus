# Public MVP walkthrough

Start the app using the README instructions. This guide refers to the code in this repository, not the separate deployed website.

1. **Protocol and Material:** Choose the implemented **Four-State Channel**, proceed to **02 Material**, and generate with the defaults. Pulse count means attempted signals per receiver. Distance and efficiency determine detections. Matching bases determine conclusive bits; some are tested and the rest retained. QBER is the test mismatch fraction. For an ideal baseline, set distance 0, efficiency 1, baseline QBER 0, and generate again.
2. **Signing:** Sign and verify the sample message. Then change the message and verify without re-signing. Integrity should fail. Explain that this is a classical demo wrapper, not a complete QDS algorithm.
3. **Attack:** Run full intercept-resend. In the ideal random-basis model the expected QBER is 25%; sampled results fluctuate. The default 6% test threshold should trigger an abort.
4. **Sweeps:** Run 0 to 1 in steps of 0.1 for eleven intensities. Navy is measured test QBER; mint is the model expectation. All points use the same settings and seed. Finite samples need not be monotonic.
5. **Bounds:** Compute the Hoeffding estimate. A small sample may give an uninformative bound; it does not certify QDS security.
6. **Circuit execution (header):** Run the 1,024-shot example. This fixed wrong-basis Eve circuit expects approximately 50% errors, whereas the random-basis attack sweep expects approximately 25% at full interception and zero baseline noise.
7. **Report:** Download JSON to inspect settings, versions, baseline, signing status, and attack measurements.

If an experiment is missing, generate material again. Restarting the server clears sessions. Increase sample count or detection efficiency if there is insufficient material. Re-sign only when you intend to accept a changed message. Inspect any failed threshold rather than presenting it as secure.

## Short explanation for judges

“This repository contains our runnable public educational MVP. We execute four-state channel circuits on Qiskit Aer, introduce intercept-resend interference, and inspect measured error rates. The message-signing part is a classical integrity demonstration. Our separate deployed research console is not reproduced here, and this MVP does not claim a complete QDS security proof.”
