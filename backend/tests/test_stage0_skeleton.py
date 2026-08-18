"""Stage 0 definition-of-done test: drive the full path end-to-end.

create run -> poll -> assert transcript + scorecard shape.

Updated at Stage 2: policy_breach is now a real evaluated pillar, so this
test no longer asserts "not_evaluated" for it. The first adviser in the
registry (CleanTestAdviser) produces a GREEN result, keeping this test
deterministic without depending on specific flag counts.
Hallucination and safe_refusal remain not_evaluated until Stages 3 and 4.

Run with:  pytest   (from backend/)
"""
from fastapi.testclient import TestClient

from app.main import app
from app.contracts import PILLARS

client = TestClient(app)

_VALID_STATUSES = {"green", "amber", "red", "review_required", "not_evaluated"}


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_scenarios_and_advisers_listed():
    scenarios = client.get("/scenarios").json()
    advisers = client.get("/advisers").json()
    assert len(scenarios) >= 1 and "scenario_id" in scenarios[0]
    assert len(advisers) >= 1 and "adviser_id" in advisers[0]


def test_full_run_path():
    scenario_id = client.get("/scenarios").json()[0]["scenario_id"]
    adviser_id = client.get("/advisers").json()[0]["adviser_id"]

    run_id = client.post(
        "/runs", json={"scenario_id": scenario_id, "adviser_id": adviser_id}
    ).json()["run_id"]
    assert run_id.startswith("run_")

    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "complete"

    # Transcript is real (a multi-turn exchange).
    assert run["transcript"]["run_id"] == run_id
    assert len(run["transcript"]["turns"]) >= 2

    # Scorecard has all three pillars with valid statuses and list flags.
    pillars = run["scorecard"]["pillars"]
    assert set(pillars.keys()) == set(PILLARS)
    for p in PILLARS:
        assert pillars[p]["status"] in _VALID_STATUSES
        assert isinstance(pillars[p]["flags"], list)

    # All three pillars are now real; each must have a valid status and flag list.


def test_unknown_run_returns_404():
    assert client.get("/runs/run_doesnotexist").status_code == 404
