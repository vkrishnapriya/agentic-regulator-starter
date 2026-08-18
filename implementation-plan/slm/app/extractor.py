"""SLM extractor — §4 extraction result.

STUB for Stage 0: returns an empty extraction result. It is wired into the
pipeline but not yet consulted by the decision layer.

CRITICAL INVARIANT (all stages): the SLM extracts and tags ONLY. It never sets
a pillar status or a flag severity — that is the deterministic layer's job.
Stage 2 replaces the body with a rules-based fake extractor, later swapped for a
fine-tuned small model, both behind this exact signature.

The shared contract types live in backend/app/contracts.py. To keep a single
source of truth we import that module under its canonical name `contracts` by
putting backend/app on sys.path. Because it's imported (not re-exec'd), the
dataclasses are defined exactly once and shared with the backend.
"""
from __future__ import annotations

import os
import sys

_CONTRACTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "backend", "app")
)
if _CONTRACTS_DIR not in sys.path:
    sys.path.insert(0, _CONTRACTS_DIR)

import contracts  # noqa: E402  (backend/app/contracts.py, canonical single copy)


def extract(transcript):
    """Return tags + claims per turn. Stage 0 stub: empty extractions."""
    return contracts.ExtractionResult(run_id=transcript.run_id, extractions=[])
