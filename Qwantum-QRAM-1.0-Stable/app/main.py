import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.persistence import SQLiteStore
from app.schemas import MemoryWriteRequest, QuantumDemoRequest
from app.quantum_demo import hadamard_all_demo
from app.integrations import IntegrationRegistry, ExperimentNotFound
from app.experiment_store import ExperimentStore
from app.integration_schemas import ExperimentCreateRequest
from app.migrations import migrate_database, LATEST_SCHEMA_VERSION
from app.security import FixedWindowRateLimiter, configured_api_key, valid_api_key, rate_limit_value
from app.quantum_bridge import (
    QuantumBackendUnavailable,
    backend_status,
    run_circuit_demo,
)

APP_VERSION = "1.0.0"
CAPACITY = int(os.getenv("QRAM_CAPACITY", "1024"))
MAX_DEMO_QUBITS = int(os.getenv("QRAM_MAX_DEMO_QUBITS", "12"))
DATABASE_PATH = os.getenv("QRAM_DATABASE_PATH", "data/qram.db")

app = FastAPI(
    title="Qwantum QRAM API",
    version=APP_VERSION,
    description="Persistent QRAM-style memory simulator plus an optional Qiskit Aer circuit-simulation bridge.",
)
SCHEMA_VERSION = migrate_database(DATABASE_PATH)
memory = SQLiteStore(database_path=DATABASE_PATH, capacity=CAPACITY)
experiment_store = ExperimentStore(database_path=DATABASE_PATH)
registry = IntegrationRegistry(experiment_store)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
rate_limiter = FixedWindowRateLimiter()
PUBLIC_API_PATHS = {"/api/health", "/api/version"}


@app.middleware("http")
async def api_security_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and path not in PUBLIC_API_PATHS:
        # Count unauthorized calls too, so the API-key gate cannot be brute-forced without limit.
        client_id = request.client.host if request.client else "unknown"
        current_limit = rate_limit_value()
        allowed, retry_after = rate_limiter.check(client_id, current_limit)
        if not allowed:
            return JSONResponse(status_code=429, content={"detail": "API rate limit exceeded. Try again later."},
                                headers={"Retry-After": str(retry_after), "X-RateLimit-Limit": str(current_limit)})
        expected_key = configured_api_key()
        if expected_key and not valid_api_key(request.headers.get("X-API-Key"), expected_key):
            return JSONResponse(status_code=401, content={"detail": "A valid X-API-Key header is required."},
                                headers={"X-RateLimit-Limit": str(current_limit)})
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(current_limit)
        return response
    return await call_next(request)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "qwantum-qram",
        "version": APP_VERSION,
        "storage": "sqlite",
        "schema_version": SCHEMA_VERSION,
        "api_key_required": configured_api_key() is not None,
        "quantum_backend": backend_status(),
    }


@app.get("/api/version")
def version():
    return {
        "name": "Qwantum QRAM",
        "version": APP_VERSION,
        "capacity": CAPACITY,
        "storage": "sqlite",
        "revision_history": True,
        "schema_version": SCHEMA_VERSION,
        "api_key_required": configured_api_key() is not None,
        "quantum_backend": backend_status(),
    }


@app.get("/api/quantum/backend")
def quantum_backend():
    return backend_status()


@app.post("/api/quantum/circuit-demo")
def quantum_circuit_demo(request: QuantumDemoRequest, shots: int = Query(default=1024, ge=1, le=100000)):
    try:
        return run_circuit_demo(request.qubits, shots=shots)
    except QuantumBackendUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc




@app.get("/api/experiments/{experiment_id}/history")
def experiment_history(experiment_id: str, limit: int = Query(default=100, ge=1, le=500)):
    try:
        return {"experiment_id": experiment_id, "events": registry.experiment_history(experiment_id, limit)}
    except ExperimentNotFound as exc:
        raise HTTPException(status_code=404, detail="experiment not found") from exc


@app.get("/api/integrations/capabilities")
def integration_capabilities():
    return registry.capabilities()


@app.post("/api/experiments")
def create_experiment(request: ExperimentCreateRequest):
    try:
        return registry.create_experiment(request.qubits, request.shots, request.label)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/experiments")
def list_experiments(limit: int = Query(default=50, ge=1, le=200)):
    return {"experiments": registry.list_experiments(limit)}


@app.get("/api/experiments/{experiment_id}")
def get_experiment(experiment_id: str):
    try:
        return registry.get_experiment(experiment_id)
    except ExperimentNotFound as exc:
        raise HTTPException(status_code=404, detail="experiment not found") from exc


@app.post("/api/experiments/{experiment_id}/run")
def run_experiment(experiment_id: str):
    try:
        result = registry.run_experiment(experiment_id)
        if result["status"] == "unavailable":
            raise HTTPException(status_code=503, detail=result["error"])
        return result
    except ExperimentNotFound as exc:
        raise HTTPException(status_code=404, detail="experiment not found") from exc


@app.get("/api/memory")
def list_memory():
    return {"stats": memory.stats(), "cells": memory.list_cells()}


@app.post("/api/memory/write")
def write_memory(request: MemoryWriteRequest):
    try:
        return memory.write(request.address, request.value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/memory/read/{address}")
def read_memory(address: int):
    try:
        return memory.read(address)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/memory/history/{address}")
def memory_history(address: int, limit: int = Query(default=50, ge=1, le=200)):
    try:
        return {"address": address, "history": memory.history(address, limit=limit)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.delete("/api/memory")
def reset_memory():
    removed = memory.reset()
    return {"reset": True, "removed_cells": removed, "stats": memory.stats()}


@app.post("/api/quantum/demo")
def quantum_demo(request: QuantumDemoRequest):
    try:
        return hadamard_all_demo(request.qubits, MAX_DEMO_QUBITS)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
