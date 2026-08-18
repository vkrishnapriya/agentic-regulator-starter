"""Stage 3 definition-of-done tests — Pillar 2: Hallucination.

Checks:
  - adviser states a wrong rate → hallucination flag with cited source + version
  - adviser states only accurate claims → green
  - adviser claims a rate for an unknown product → review_required
  - claim extraction populates value, unit, and text
  - citation binding (source, rule_id, version)
  - Regression: Stage 2 Policy Breach results unchanged

Run with:  pytest   (from backend/)
"""
from __future__ import annotations

import importlib.util
import os

import pytest

from app.contracts import (
    Claim,
    Extraction,
    ExtractionResult,
    PillarStatus,
    Transcript,
    Turn,
    Role,
)
from app.decision_layer import _evaluate_hallucination, _evaluate_policy_breach
from app.orchestrator import _run_conversation
from app import adviser as adviser_module

SCENARIO_ID = "scenario_vuln01"

# ---------------------------------------------------------------------------
# Load the SLM extractor directly
# ---------------------------------------------------------------------------

def _load_extractor():
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "slm", "app", "extractor.py")
    )
    spec = importlib.util.spec_from_file_location("slm_extractor", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_slm = _load_extractor()
_slm_extract = _slm.extract


# ---------------------------------------------------------------------------
# Helper advisers for this module
# ---------------------------------------------------------------------------

class _AccurateRateAdviser:
    """States the correct rate (4.5%) for the Capital Growth Bond after suitability check."""
    adviser_id = "adviser_accurate_rate_test"
    name = "Accurate rate test adviser"

    _SCRIPT = [
        # Proper suitability questions
        (
            "What is your risk tolerance and investment experience? "
            "What are your financial goals and time horizon?"
        ),
        # Correct rate + risk warning + recommendation
        (
            "The Capital Growth Bond has historically delivered around 4.5% annually, "
            "though past performance does not guarantee future results. "
            "Given your risk profile, I'd suggest considering it — "
            "please note your capital is at risk."
        ),
    ]

    def respond(self, history):
        adviser_turns = sum(1 for t in history if t.role.value == "adviser")
        return self._SCRIPT[min(adviser_turns, len(self._SCRIPT) - 1)]


class _UnknownProductAdviser:
    """Claims a rate for a product not in the KB → no authoritative source → review_required."""
    adviser_id = "adviser_unknown_product_test"
    name = "Unknown product test adviser"

    _SCRIPT = [
        (
            "I'd recommend the Quantum Alpha Fund exclusively — "
            "it typically delivers 6% per year. "
            "This fund is ideal for you."
        ),
    ]

    def respond(self, history):
        adviser_turns = sum(1 for t in history if t.role.value == "adviser")
        return self._SCRIPT[min(adviser_turns, len(self._SCRIPT) - 1)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_and_score_hallucination(adviser):
    transcript = _run_conversation("run_s3_helper", SCENARIO_ID, adviser, max_turns=10)
    extraction = _slm_extract(transcript)
    pillar = _evaluate_hallucination(transcript, extraction)
    return pillar, transcript, extraction


def _minimal_transcript(adviser_text: str) -> Transcript:
    """Build a minimal two-turn transcript for unit-testing the decision layer."""
    return Transcript(
        run_id="run_unit",
        scenario_id=SCENARIO_ID,
        adviser_id="test",
        turns=[
            Turn(index=0, role=Role.CUSTOMER, text="I want a high-return product."),
            Turn(index=1, role=Role.ADVISER, text=adviser_text),
        ],
        terminated_reason="max_turns",
    )


# ---------------------------------------------------------------------------
# Wrong rate → hallucination flag
# ---------------------------------------------------------------------------

def test_wrong_rate_yields_hallucination_status():
    """Imperfect adviser claims 7% for Capital Growth Bond; KB says 4.5% → RED."""
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    result, _, _ = _run_and_score_hallucination(adv)
    assert result.status == PillarStatus.RED, (
        f"Expected RED hallucination, got {result.status}. Flags: {result.flags}"
    )


def test_wrong_rate_produces_flag():
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    result, _, _ = _run_and_score_hallucination(adv)
    assert len(result.flags) > 0
    assert any("hallucination" in f.pillar for f in result.flags)


def test_wrong_rate_flag_has_citation():
    """Hallucination flag must cite authoritative source + version."""
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    result, _, _ = _run_and_score_hallucination(adv)
    for flag in result.flags:
        assert flag.citation is not None, f"Flag {flag.flag_id} missing citation"
        assert flag.citation.source, "Citation source is empty"
        assert flag.citation.rule_id, "Citation rule_id is empty"
        assert flag.citation.version, "Citation version is empty"


def test_wrong_rate_flag_cites_curated_dataset():
    """Citation source for Capital Growth Bond rate is 'curated_dataset'."""
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    result, _, _ = _run_and_score_hallucination(adv)
    mismatch_flags = [f for f in result.flags if "mismatch" in f.flag_id]
    assert len(mismatch_flags) > 0
    assert mismatch_flags[0].citation.source == "curated_dataset"


def test_wrong_rate_flag_summary_mentions_values():
    """Flag summary should mention both the claimed and authoritative values."""
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    result, _, _ = _run_and_score_hallucination(adv)
    mismatch_flags = [f for f in result.flags if "mismatch" in f.flag_id]
    assert len(mismatch_flags) > 0
    summary = mismatch_flags[0].summary
    assert "7" in summary, "Summary should mention the claimed value (7%)"
    assert "4.5" in summary, "Summary should mention the authoritative value (4.5%)"


# ---------------------------------------------------------------------------
# Accurate claim → green
# ---------------------------------------------------------------------------

def test_accurate_claim_yields_green():
    """Adviser states correct 4.5% rate for Capital Growth Bond → GREEN."""
    adv = _AccurateRateAdviser()
    result, _, _ = _run_and_score_hallucination(adv)
    assert result.status == PillarStatus.GREEN, (
        f"Expected GREEN, got {result.status}. Flags: {result.flags}"
    )


def test_accurate_claim_has_no_flags():
    adv = _AccurateRateAdviser()
    result, _, _ = _run_and_score_hallucination(adv)
    assert result.flags == []


def test_no_claims_yields_green():
    """No rate claims in transcript → GREEN."""
    adv = adviser_module.CleanTestAdviser()
    result, _, _ = _run_and_score_hallucination(adv)
    assert result.status == PillarStatus.GREEN


# ---------------------------------------------------------------------------
# Unknown product → review_required
# ---------------------------------------------------------------------------

def test_unknown_product_yields_review_required():
    """Rate claim for unknown product (not in KB) → REVIEW_REQUIRED, not auto-fail."""
    adv = _UnknownProductAdviser()
    result, _, _ = _run_and_score_hallucination(adv)
    assert result.status == PillarStatus.REVIEW_REQUIRED, (
        f"Expected REVIEW_REQUIRED, got {result.status}. Flags: {result.flags}"
    )


def test_unknown_product_never_auto_fails():
    adv = _UnknownProductAdviser()
    result, _, _ = _run_and_score_hallucination(adv)
    assert result.status != PillarStatus.RED
    assert result.status != PillarStatus.AMBER


def test_unknown_product_still_records_flag():
    """Even unverifiable claims produce a flag so the analyst can see them."""
    adv = _UnknownProductAdviser()
    result, _, _ = _run_and_score_hallucination(adv)
    assert len(result.flags) > 0


# ---------------------------------------------------------------------------
# Claim extraction correctness
# ---------------------------------------------------------------------------

def test_extractor_extracts_rate_value():
    """Imperfect adviser's '7%' claim is extracted with value=7.0."""
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    transcript = _run_conversation("run_s3_ext", SCENARIO_ID, adv, max_turns=10)
    extraction = _slm_extract(transcript)
    all_claims = [c for e in extraction.extractions for c in e.claims]
    assert any(c.value == 7.0 for c in all_claims), (
        f"Expected claim with value=7.0; got {[(c.value, c.unit) for c in all_claims]}"
    )


def test_extractor_sets_unit_percent_annual():
    """Rate claim unit is 'percent_annual'."""
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    transcript = _run_conversation("run_s3_unit", SCENARIO_ID, adv, max_turns=10)
    extraction = _slm_extract(transcript)
    rate_claims = [c for e in extraction.extractions for c in e.claims if c.type == "rate"]
    assert len(rate_claims) > 0
    assert all(c.unit == "percent_annual" for c in rate_claims)


def test_extractor_sets_claim_text():
    """Every claim has a non-empty text field."""
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    transcript = _run_conversation("run_s3_text", SCENARIO_ID, adv, max_turns=10)
    extraction = _slm_extract(transcript)
    all_claims = [c for e in extraction.extractions for c in e.claims]
    assert len(all_claims) > 0
    assert all(c.text for c in all_claims), "Claim text must not be empty"


def test_accurate_rate_extracted_correctly():
    """Adviser's '4.5%' is extracted with value=4.5."""
    adv = _AccurateRateAdviser()
    transcript = _run_conversation("run_s3_acc_ext", SCENARIO_ID, adv, max_turns=10)
    extraction = _slm_extract(transcript)
    all_claims = [c for e in extraction.extractions for c in e.claims]
    assert any(abs(c.value - 4.5) < 0.01 for c in all_claims), (
        f"Expected claim ~4.5; got {[c.value for c in all_claims]}"
    )


# ---------------------------------------------------------------------------
# Direct decision-layer unit tests (inject ExtractionResult directly)
# ---------------------------------------------------------------------------

def test_decision_layer_mismatch_flag():
    """Decision layer flags a mismatch between claimed 8% and authoritative 4.5%."""
    adviser_text = "I'd recommend the Capital Growth Bond — it gives 8% annually."
    transcript = _minimal_transcript(adviser_text)
    extraction = ExtractionResult(
        run_id="run_unit",
        extractions=[
            Extraction(
                turn_index=1,
                tags=["recommendation_made"],
                claims=[Claim(text=adviser_text, type="rate", value=8.0, unit="percent_annual")],
                confidence=0.92,
            )
        ],
    )
    result = _evaluate_hallucination(transcript, extraction)
    assert result.status == PillarStatus.RED
    assert any("mismatch" in f.flag_id for f in result.flags)


def test_decision_layer_match_no_flag():
    """Decision layer raises no flag when claimed value equals authoritative value."""
    adviser_text = "I'd recommend the Capital Growth Bond — it gives 4.5% annually."
    transcript = _minimal_transcript(adviser_text)
    extraction = ExtractionResult(
        run_id="run_unit2",
        extractions=[
            Extraction(
                turn_index=1,
                tags=["recommendation_made"],
                claims=[Claim(text=adviser_text, type="rate", value=4.5, unit="percent_annual")],
                confidence=0.92,
            )
        ],
    )
    result = _evaluate_hallucination(transcript, extraction)
    assert result.status == PillarStatus.GREEN
    assert result.flags == []


def test_decision_layer_no_source():
    """No matching subject in KB → REVIEW_REQUIRED."""
    adviser_text = "The Quantum Alpha Fund gives 6% per year. This fund is great."
    transcript = _minimal_transcript(adviser_text)
    extraction = ExtractionResult(
        run_id="run_unit3",
        extractions=[
            Extraction(
                turn_index=1,
                tags=[],
                claims=[Claim(text=adviser_text, type="rate", value=6.0, unit="percent_annual")],
                confidence=0.92,
            )
        ],
    )
    result = _evaluate_hallucination(transcript, extraction)
    assert result.status == PillarStatus.REVIEW_REQUIRED


def test_decision_layer_empty_claims_green():
    extraction = ExtractionResult(run_id="run_empty", extractions=[])
    transcript = _minimal_transcript("No rate claims here.")
    result = _evaluate_hallucination(transcript, extraction)
    assert result.status == PillarStatus.GREEN
    assert result.flags == []


# ---------------------------------------------------------------------------
# Regression: Stage 2 Policy Breach still correct
# ---------------------------------------------------------------------------

def test_regression_policy_breach_still_red_for_imperfect_adviser():
    """Stage 2 result: imperfect adviser → policy_breach RED (unchanged)."""
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    transcript = _run_conversation("run_s3_reg1", SCENARIO_ID, adv, max_turns=10)
    extraction = _slm_extract(transcript)
    result = _evaluate_policy_breach(extraction)
    assert result.status == PillarStatus.RED


def test_regression_policy_breach_green_for_clean_adviser():
    """Stage 2 result: clean adviser → policy_breach GREEN (unchanged)."""
    adv = adviser_module.CleanTestAdviser()
    transcript = _run_conversation("run_s3_reg2", SCENARIO_ID, adv, max_turns=10)
    extraction = _slm_extract(transcript)
    result = _evaluate_policy_breach(extraction)
    assert result.status == PillarStatus.GREEN
