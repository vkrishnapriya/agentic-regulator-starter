"""Orchestrator — draws a scenario, runs the conversation loop, scores it.

Stage 1: the conversation loop is real — a persona-driven CustomerAgent
trades turns with an Adviser until one of three termination conditions fires:
  goal_reached   — adviser made a recommendation the customer was seeking
  max_turns      — loop hit the configured ceiling
  adviser_declined — adviser signalled it could not help

Runs are held in memory (a dict). Fine for the hackathon; swap for a store later.
"""
from __future__ import annotations

import os
import uuid
import importlib.util

from app.contracts import Transcript, Turn, Role, Scorecard, to_jsonable
from app import scenarios, adviser, decision_layer
from app.customer_agent import CustomerAgent


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

_MAX_TURNS = 10  # default ceiling; overridable in tests via _run_conversation


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


def _run_conversation(
    run_id: str, scenario_id: str, adv, max_turns: int = _MAX_TURNS
) -> Transcript:
    """Real multi-turn conversation loop (Stage 1).

    Turn order: customer opens → [adviser → customer]* until termination.
    Termination conditions are checked after each side speaks.

    Parameters
    ----------
    max_turns:
        Hard ceiling on total turns (adviser + customer combined).
        Exposed as a parameter so tests can drive specific termination paths.
    """
    scenario = scenarios.get(scenario_id)
    customer = CustomerAgent(scenario)
    turns: list[Turn] = []

    # Customer opens the conversation.
    turns.append(Turn(index=0, role=Role.CUSTOMER, text=customer.opening_message()))

    while True:
        # --- Adviser turn ---
        if len(turns) >= max_turns:
            break

        adviser_reply = adv.respond(turns)
        turns.append(Turn(index=len(turns), role=Role.ADVISER, text=adviser_reply))

        if customer.adviser_declined(adviser_reply):
            return Transcript(
                run_id=run_id,
                scenario_id=scenario_id,
                adviser_id=adv.adviser_id,
                turns=turns,
                terminated_reason="adviser_declined",
            )

        # --- Customer turn ---
        if len(turns) >= max_turns:
            break

        customer_reply = customer.respond(turns)
        turns.append(Turn(index=len(turns), role=Role.CUSTOMER, text=customer_reply))

        if customer.goal_reached(turns):
            return Transcript(
                run_id=run_id,
                scenario_id=scenario_id,
                adviser_id=adv.adviser_id,
                turns=turns,
                terminated_reason="goal_reached",
            )

    return Transcript(
        run_id=run_id,
        scenario_id=scenario_id,
        adviser_id=adv.adviser_id,
        turns=turns,
        terminated_reason="max_turns",
    )


def get_run(run_id: str) -> dict | None:
    return _RUNS.get(run_id)
