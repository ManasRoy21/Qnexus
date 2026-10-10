from fastapi.testclient import TestClient
from qnexus.app import app

client = TestClient(app)


def test_complete_workflow_and_tampering():
    config = {"pulse_count": 2000, "distance_km": 0, "detector_efficiency": 1, "baseline_qber": 0}
    response = client.post("/api/material", json=config)
    assert response.status_code == 200
    material = response.json()
    identifier = material["simulation_id"]
    signed = client.post("/api/sign", json={"simulation_id": identifier, "message": "demo"})
    assert signed.status_code == 200
    signature = signed.json()["signature"]
    verified = client.post("/api/verify", json={"simulation_id": identifier, "message": "demo", "signature": signature})
    assert verified.json()["bob_accepts"]
    changed = client.post("/api/verify", json={"simulation_id": identifier, "message": "changed", "signature": signature})
    assert not changed.json()["message_intact"]
    attacked = client.post("/api/attack", json={"simulation_id": identifier, "intensity": 1})
    assert attacked.status_code == 200 and attacked.json()["abort"]
    report = client.get(f"/api/report/{identifier}").json()
    assert report["signing_complete"] and report["attack"]
    assert "key" not in report
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200


def test_input_validation_and_missing_session():
    assert client.post("/api/material", json={"pulse_count": -1}).status_code == 422
    assert client.post("/api/material", json={"authentication_threshold": .2, "verification_threshold": .1}).status_code == 422
    assert client.post("/api/attack", json={"simulation_id": "missing", "intensity": 1}).status_code == 404
    assert client.post("/api/sweep", json={"step": .001}).status_code == 422
    assert client.post("/api/bounds", json={"n": 0, "epsilon": .035}).status_code == 422
    assert client.post("/api/verify", json={"simulation_id": "missing", "message": "demo", "signature": "非ASCII"}).status_code == 422


def test_sweep_includes_endpoints_and_executes_circuits():
    response = client.post("/api/sweep", json={"config": {"pulse_count": 2000, "distance_km": 0, "detector_efficiency": 1, "baseline_qber": 0}, "step": .5})
    assert response.status_code == 200
    points = response.json()["points"]
    assert [p["intensity"] for p in points] == [0, .5, 1]
    assert points[0]["qber"] == 0
    assert points[-1]["qber"] > .15
