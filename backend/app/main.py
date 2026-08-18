"""Backend REST API — §6, the contract the UI calls.

Endpoints (frozen across all stages; only what fills them gets more real):
  POST /runs           -> { run_id }
  GET  /runs/{run_id}  -> { status, transcript?, scorecard? }
  GET  /scenarios      -> [ { scenario_id, title } ]
  GET  /advisers       -> [ { adviser_id, name } ]

Run with:  uvicorn app.main:app --reload --port 8000   (from backend/)
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import orchestrator, scenarios, adviser

app = FastAPI(title="Agentic Regulator — Backend")

# Open CORS so the static UI (opened from file:// or any port) can call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    scenario_id: str
    adviser_id: str


@app.post("/runs")
def create_run(req: RunRequest):
    run_id = orchestrator.start_run(req.scenario_id, req.adviser_id)
    return {"run_id": run_id}


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    run = orchestrator.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@app.get("/scenarios")
def list_scenarios():
    return [{"scenario_id": s.scenario_id, "title": s.title} for s in scenarios.list_all()]


@app.get("/advisers")
def list_advisers():
    return [{"adviser_id": a.adviser_id, "name": a.name} for a in adviser.REGISTRY.values()]


@app.get("/health")
def health():
    return {"status": "ok"}
