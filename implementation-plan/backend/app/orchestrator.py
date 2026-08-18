"""Orchestrator — draws a scenario, runs the conversation loop, scores it.

Stage 0: the customer side is a canned two-turn opener (no real customer agent
yet). Stage 1 replaces `_customer_opening`/loop with a real persona-driven
customer agent and proper termination logic.

Runs are held in memory (a dict). Fine for the hackathon; swap for a store later.
"""
from __future__ import annotations

import os
import uuid
import importlib.util

from app.contracts import Transcript, Turn, Role, Scorecard, to_jsonable
from app import scenarios, adviser, decision_layer


def _load_slm_extract():
    """Load slm/app/extractor.py by path — the slm project is a separate
    codebase with its own `app` package, so we import it explicitly rather than
    via `import app.extractor` (which would collide with the backend's own app)."""
    root = os.path.join(os.path.dirname(__file__), "..", "..")
    path = os.path.join(root, "slm", "app", "extractor.py")
    spec = importlib.util.spec_from_file_location("slm_extractor", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.extract


extract = _load_slm_extract()

_RUNS: dict[str, dict] = {}


def _new_id() -> str:
    return "run_" + uuid.uuid4().hex[:8]


def start_run(scenario_id: str, adviser_id: str) -> str:
    run_id = _new_id()
    _RUNS[run_id] = {"status": "running", "transcript": None, "scorecard": None}

    scenario = scenarios.get(scenario_id)
    adv = adviser.REGISTRY.get(adviser_id)
    if scenario is None or adv is None:
        _RUNS[run_id]["status"] = "complete"
        _RUNS[run_id]["scorecard"] = to_jsonable(Scorecard.empty(run_id))
        return run_id

    transcript = _run_conversation(run_id, scenario_id, adv)
    extraction = extract(transcript)
    scorecard = decision_layer.evaluate(transcript, extraction)

    _RUNS[run_id]["transcript"] = to_jsonable(transcript)
    _RUNS[run_id]["scorecard"] = to_jsonable(scorecard)
    _RUNS[run_id]["status"] = "complete"
    return run_id


def _run_conversation(run_id: str, scenario_id: str, adv) -> Transcript:
    """Stage 0: canned two-turn exchange. Stage 1 replaces with a real loop."""
    turns: list[Turn] = []
    turns.append(Turn(index=0, role=Role.CUSTOMER,
                      text="Hi, I'm looking for a safe investment with good returns."))
    adviser_reply = adv.respond(turns)
    turns.append(Turn(index=1, role=Role.ADVISER, text=adviser_reply))
    return Transcript(
        run_id=run_id,
        scenario_id=scenario_id,
        adviser_id=adv.adviser_id,
        turns=turns,
        terminated_reason="max_turns",
    )


def get_run(run_id: str) -> dict | None:
    return _RUNS.get(run_id)
