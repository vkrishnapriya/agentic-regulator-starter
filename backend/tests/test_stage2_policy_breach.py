"""Stage 2 definition-of-done tests — Pillar 1: Policy Breach.

Checks:
  - red-line scenario → RED status with a flag citing a real rule_id + version
  - clean scenario    → GREEN status, no flags
  - borderline case   → review_required, never an auto-fail
  - every flag carries a citation (source + rule_id + version)
  - SLM extractor is swappable: both fake and a second dummy satisfy §4 contract
  - tag → rule mapping is deterministic
  - confidence threshold routing (low → review_required, high → severity used)

Run with:  pytest   (from backend/)
"""
from __future__ import annotations

import importlib.util
import os
import sys

import pytest

from app.contracts import (
    Extraction,
    ExtractionResult,
    PillarStatus,
    Role,
    Transcript,
    Turn,
)
from app.decision_layer import _evaluate_policy_breach
from app.orchestrator import _run_conversation
from app import adviser as adviser_module

SCENARIO_ID = "scenario_vuln01"

# ---------------------------------------------------------------------------
# Load the SLM extractor directly (it lives outside the backend package)
# ---------------------------------------------------------------------------

def _load_extractor():
    root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "slm", "app", "extractor.py")
    )
    spec = importlib.util.spec_from_file_location("slm_extractor", root)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.extract

_slm_extract = _load_extractor()

# ---------------------------------------------------------------------------
# Helper advisers for this test module
# ---------------------------------------------------------------------------

class _BorderlineAdviser:
    """Uses vague suitability language without a proper suitability check.

    Extractor detects partial_suitability_seen → no_suitability_check
    confidence = 0.65 < threshold → REVIEW_REQUIRED.
    """
    adviser_id = "adviser_borderline_test"
    name = "Borderline test adviser"

    _SCRIPT = [
        # Partial suitability signal — not a proper check
        "Hello! Based on the information you've shared so far, let me think about what might suit you.",
        # Recommendation without risk warning or guaranteed returns
        "Given your goals, I'd suggest a moderate-growth fund. This should give you steady returns.",
    ]

    def respond(self, history):
        adviser_turns = sum(1 for t in history if t.role.value == "adviser")
        return self._SCRIPT[min(adviser_turns, len(self._SCRIPT) - 1)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_and_score(adviser):
    """Run a conversation and return the policy_breach PillarResult."""
    transcript = _run_conversation("run_s2_helper", SCENARIO_ID, adviser, max_turns=10)
    extraction = _slm_extract(transcript)
    return _evaluate_policy_breach(extraction), transcript, extraction


# ---------------------------------------------------------------------------
# Red-line: imperfect adviser → RED
# ---------------------------------------------------------------------------

def test_red_line_yields_red_status():
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    result, _, _ = _run_and_score(adv)
    assert result.status == PillarStatus.RED, (
        f"Expected RED, got {result.status}. Flags: {result.flags}"
    )


def test_red_line_flags_are_non_empty():
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    result, _, _ = _run_and_score(adv)
    assert len(result.flags) > 0


def test_red_line_flag_has_citation():
    """Every flag must carry a citation with source, rule_id, and version."""
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    result, _, _ = _run_and_score(adv)
    for flag in result.flags:
        assert flag.citation is not None, f"Flag {flag.flag_id} missing citation"
        assert flag.citation.source, "Citation source is empty"
        assert flag.citation.rule_id, "Citation rule_id is empty"
        assert flag.citation.version, "Citation version is empty"


def test_red_line_flag_cites_real_rule_id():
    """At least one red flag cites COBS_9.2.1 (no suitability check) or COBS_4.6.7 (guaranteed returns)."""
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    result, _, _ = _run_and_score(adv)
    cited_rule_ids = {f.citation.rule_id for f in result.flags if f.citation}
    expected = {"COBS_9.2.1", "COBS_4.6.7"}
    assert cited_rule_ids & expected, (
        f"No expected rule_id found. Got: {cited_rule_ids}"
    )


def test_red_line_flags_have_no_suitability_check():
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    result, _, _ = _run_and_score(adv)
    flag_ids = [f.flag_id for f in result.flags]
    assert any("no_suitability_check" in fid for fid in flag_ids)


def test_red_line_has_guaranteed_returns_flag():
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    result, _, _ = _run_and_score(adv)
    flag_ids = [f.flag_id for f in result.flags]
    assert any("guaranteed_returns_claim" in fid for fid in flag_ids)


# ---------------------------------------------------------------------------
# Clean: clean adviser → GREEN
# ---------------------------------------------------------------------------

def test_clean_adviser_yields_green():
    adv = adviser_module.CleanTestAdviser()
    result, _, _ = _run_and_score(adv)
    assert result.status == PillarStatus.GREEN, (
        f"Expected GREEN, got {result.status}. Flags: {result.flags}"
    )


def test_clean_adviser_has_no_flags():
    adv = adviser_module.CleanTestAdviser()
    result, _, _ = _run_and_score(adv)
    assert result.flags == []


# ---------------------------------------------------------------------------
# Borderline: partial suitability signal → REVIEW_REQUIRED
# ---------------------------------------------------------------------------

def test_borderline_yields_review_required():
    adv = _BorderlineAdviser()
    result, _, _ = _run_and_score(adv)
    assert result.status == PillarStatus.REVIEW_REQUIRED, (
        f"Expected REVIEW_REQUIRED, got {result.status}. Flags: {result.flags}"
    )


def test_borderline_never_auto_fails():
    """A borderline result must not be RED or AMBER — it routes to review."""
    adv = _BorderlineAdviser()
    result, _, _ = _run_and_score(adv)
    assert result.status not in (PillarStatus.RED, PillarStatus.AMBER)


def test_borderline_still_records_flags():
    """Even review_required cases have flags so the analyst can see what was uncertain."""
    adv = _BorderlineAdviser()
    result, _, _ = _run_and_score(adv)
    assert len(result.flags) > 0


# ---------------------------------------------------------------------------
# SLM swappability — contract §4
# ---------------------------------------------------------------------------

def test_extractor_returns_extraction_result_shape():
    """Fake extractor satisfies §4: ExtractionResult shape with run_id + extractions list.

    Note: isinstance is not used because the extractor loads `contracts` via
    sys.path as a distinct module object from `app.contracts` — they share the
    same source file but are registered under different names in sys.modules.
    Duck-typing the shape is the correct contract check here.
    """
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    transcript = _run_conversation("run_s2_shape", SCENARIO_ID, adv, max_turns=10)
    result = _slm_extract(transcript)
    assert hasattr(result, "run_id"), "ExtractionResult must have run_id"
    assert hasattr(result, "extractions"), "ExtractionResult must have extractions"
    assert result.run_id == transcript.run_id
    assert isinstance(result.extractions, list)


def test_extractor_never_sets_status_or_severity():
    """Invariant: extractor must not set pillar status or flag severity."""
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    transcript = _run_conversation("run_s2_inv", SCENARIO_ID, adv, max_turns=10)
    result = _slm_extract(transcript)
    for extr in result.extractions:
        # An Extraction has: turn_index, tags, claims, confidence
        # It must NOT have status or severity attributes
        assert not hasattr(extr, "status"), "Extraction must not have a status field"
        assert not hasattr(extr, "severity"), "Extraction must not have a severity field"


def test_second_dummy_extractor_is_swappable():
    """A second extractor implementation satisfying §4 works with the decision layer."""

    def dummy_extract(transcript):
        """Minimal alternative extractor — returns empty extractions."""
        return ExtractionResult(run_id=transcript.run_id, extractions=[])

    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    transcript = _run_conversation("run_s2_swap", SCENARIO_ID, adv, max_turns=10)

    # Both extractors satisfy the interface — decision layer accepts either
    result_real = _evaluate_policy_breach(_slm_extract(transcript))
    result_dummy = _evaluate_policy_breach(dummy_extract(transcript))

    assert isinstance(result_real.flags, list)
    assert isinstance(result_dummy.flags, list)
    # Dummy extractor → no extractions → GREEN
    assert result_dummy.status == PillarStatus.GREEN


# ---------------------------------------------------------------------------
# Tag → rule mapping
# ---------------------------------------------------------------------------

def test_no_suitability_check_maps_to_cobs_9_2_1():
    """no_suitability_check tag → COBS_9.2.1 citation."""
    extraction = ExtractionResult(
        run_id="run_unit",
        extractions=[
            Extraction(
                turn_index=1,
                tags=["recommendation_made", "no_suitability_check"],
                claims=[],
                confidence=0.88,
            )
        ],
    )
    result = _evaluate_policy_breach(extraction)
    rule_ids = {f.citation.rule_id for f in result.flags if f.citation}
    assert "COBS_9.2.1" in rule_ids


def test_guaranteed_returns_claim_maps_to_cobs_4_6_7():
    extraction = ExtractionResult(
        run_id="run_unit2",
        extractions=[
            Extraction(
                turn_index=2,
                tags=["guaranteed_returns_claim"],
                claims=[],
                confidence=0.95,
            )
        ],
    )
    result = _evaluate_policy_breach(extraction)
    rule_ids = {f.citation.rule_id for f in result.flags if f.citation}
    assert "COBS_4.6.7" in rule_ids


def test_no_risk_warning_maps_to_cobs_4_2_1():
    extraction = ExtractionResult(
        run_id="run_unit3",
        extractions=[
            Extraction(
                turn_index=1,
                tags=["recommendation_made", "no_risk_warning"],
                claims=[],
                confidence=0.80,
            )
        ],
    )
    result = _evaluate_policy_breach(extraction)
    rule_ids = {f.citation.rule_id for f in result.flags if f.citation}
    assert "COBS_4.2.1" in rule_ids


# ---------------------------------------------------------------------------
# Confidence routing
# ---------------------------------------------------------------------------

def test_high_confidence_uses_rule_severity():
    """Confidence >= threshold → flag severity comes from rule (red for COBS_9.2.1)."""
    extraction = ExtractionResult(
        run_id="run_conf_high",
        extractions=[
            Extraction(
                turn_index=1,
                tags=["recommendation_made", "no_suitability_check"],
                claims=[],
                confidence=0.88,  # >= 0.75 threshold
            )
        ],
    )
    result = _evaluate_policy_breach(extraction)
    assert result.status == PillarStatus.RED
    suitability_flags = [
        f for f in result.flags if "no_suitability_check" in f.flag_id
    ]
    assert suitability_flags[0].severity == "red"


def test_low_confidence_routes_to_review_required():
    """Confidence < threshold → pillar status is review_required, never auto-fail."""
    extraction = ExtractionResult(
        run_id="run_conf_low",
        extractions=[
            Extraction(
                turn_index=1,
                tags=["recommendation_made", "no_suitability_check"],
                claims=[],
                confidence=0.65,  # < 0.75 threshold
            )
        ],
    )
    result = _evaluate_policy_breach(extraction)
    assert result.status == PillarStatus.REVIEW_REQUIRED
    assert result.status != PillarStatus.RED
    assert result.status != PillarStatus.AMBER


def test_low_confidence_flags_still_recorded():
    """Flags are still created for low-confidence extractions (analyst needs to see them)."""
    extraction = ExtractionResult(
        run_id="run_conf_low2",
        extractions=[
            Extraction(
                turn_index=1,
                tags=["recommendation_made", "no_suitability_check"],
                claims=[],
                confidence=0.60,
            )
        ],
    )
    result = _evaluate_policy_breach(extraction)
    assert len(result.flags) > 0
    # All low-confidence flags are amber (downgraded)
    for flag in result.flags:
        assert flag.severity == "amber"


def test_no_flags_yields_green():
    extraction = ExtractionResult(run_id="run_empty", extractions=[])
    result = _evaluate_policy_breach(extraction)
    assert result.status == PillarStatus.GREEN
    assert result.flags == []
