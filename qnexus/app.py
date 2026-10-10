"""Local FastAPI dashboard and experiment API. Run with uvicorn qnexus.app:app."""
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .circuits import circuit_demo
from .models import AttackRequest, BoundRequest, Experiment, SignRequest, SweepRequest, VerifyRequest
from .security import hoeffding_bound, sign_message, verify_message
from .simulation import run_experiment

app = FastAPI(title="QNexus Public MVP", version="0.1.0",
              description="Executable Qiskit channel experiments and a simplified signing workflow. Not a full QDS protocol.")
WEB = Path(__file__).resolve().parent.parent / "web"
app.mount("/static", StaticFiles(directory=WEB), name="static")


@dataclass
class Session:
    material: dict
    key: bytes
    signed: dict | None = None
    verification: dict | None = None
    attack: dict | None = None
    lock: RLock = field(default_factory=RLock)


sessions = OrderedDict()
sessions_lock = RLock()


def get_session(identifier):
    with sessions_lock:
        session = sessions.get(identifier)
    if session is None:
        raise HTTPException(404, "Experiment not found. Generate material again; local sessions expire on restart or after 100 experiments.")
    return session


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "project": "QNexus", "team": "Schrödinger's Squad", "scope": "public educational MVP"}


@app.get("/api/circuit")
def execute_circuit():
    return circuit_demo()


@app.post("/api/material")
def material(config: Experiment):
    output, key = run_experiment(config)
    identifier = uuid4().hex
    output["simulation_id"] = identifier
    with sessions_lock:
        sessions[identifier] = Session(output, key)
        while len(sessions) > 100:
            sessions.popitem(last=False)
    return output


@app.post("/api/sign")
def sign(request: SignRequest):
    session = get_session(request.simulation_id)
    with session.lock:
        if session.material["insufficient_data"] or session.material["abort"]:
            raise HTTPException(409, "The channel check failed or produced insufficient data; generate suitable material first.")
        output = sign_message(session.key, request.simulation_id, request.message)
        session.signed = {**output, "message": request.message}
        session.verification = None
        return output


@app.post("/api/verify")
def verify(request: VerifyRequest):
    session = get_session(request.simulation_id)
    with session.lock:
        if session.signed is None:
            raise HTTPException(409, "Sign a message in this experiment first.")
        output = verify_message(session.key, request.simulation_id, request.message,
                                request.signature, session.material)
        session.verification = output
        return output


@app.post("/api/attack")
def attack(request: AttackRequest):
    session = get_session(request.simulation_id)
    output, _ = run_experiment(Experiment(**session.material["config"]), request.intensity)
    with session.lock:
        session.attack = output
    return output


@app.post("/api/sweep")
def sweep(request: SweepRequest):
    steps = int((request.maximum - request.minimum) / request.step + 1e-9)
    points = []
    for i in range(steps + 1):
        intensity = round(request.minimum + i * request.step, 10)
        output, _ = run_experiment(request.config, intensity)
        points.append({"intensity": intensity, "qber": output["pooled_test_qber"],
                       "expected_qber": output["expected_sifted_qber"],
                       "tested_bits": output["tested_bits"], "abort": output["abort"],
                       "insufficient_data": output["insufficient_data"]})
    return {"config": request.config.model_dump(), "points": points,
            "note": "Same seed and channel settings at every point; random finite-sample outcomes need not be monotonic. Only intercept-resend is implemented."}


@app.post("/api/bounds")
def bounds(request: BoundRequest):
    return hoeffding_bound(request.n, request.epsilon, request.observed_qber)


@app.get("/api/report/{simulation_id}")
def report(simulation_id: str):
    session = get_session(simulation_id)
    with session.lock:
        return {"project": "QNexus", "team": "Schrödinger's Squad",
                "scope": "Public educational implementation; independent of the deployed private backend.",
                "material": session.material, "signing_complete": session.signed is not None,
                "verification": session.verification, "attack": session.attack,
                "limitations": ["Not a complete QDS protocol or security proof.",
                                "All participants run inside one local server.",
                                "Seeded randomness is for reproduction, not cryptographic keys.",
                                "No hardware execution, optical coherent-state detector model, recipient symmetrisation, or QML."]}
