"""Deterministic decision layer — produces the scorecard.

STUB for Stage 0: returns a fixed scorecard with all three pillars
`not_evaluated` and no flags. It receives the transcript and (later) the SLM
extraction, but decides nothing yet.

This is the heart of the system's core claim: the SLM describes, THIS layer
decides — against versioned, cited sources. Every real flag added in Stages 2-4
must carry a citation and route low-confidence cases to `review_required`.
"""
from __future__ import annotations

from app.contracts import Transcript, ExtractionResult, Scorecard


def evaluate(transcript: Transcript, extraction: ExtractionResult) -> Scorecard:
    """Score a transcript across the three pillars. Stage 0 stub: empty scorecard."""
    return Scorecard.empty(transcript.run_id)
