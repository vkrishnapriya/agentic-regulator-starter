"""Knowledge Base — §5 read interfaces.

Stage 3: fact lookup now has a two-tier strategy:
  1. Curated local dataset (facts.json) — governance-versioned, always available.
  2. Live reference-API connector — allow-listed subjects only; simulated here
     as an in-memory snapshot (real implementation would make an HTTP call).

Both tiers carry `source` and `version` so citations reproduce.
Rule-lookup signatures are unchanged from Stage 0.
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _load(name: str) -> Any:
    with open(os.path.join(_DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# §5 rules lookup — Pillars 1 & 3
# ---------------------------------------------------------------------------

def rules_lookup(tag: str) -> Optional[dict[str, Any]]:
    """Map an SLM tag to a cited rule. Returns None if tag has no rule."""
    rules = _load("rules.json")
    return rules.get(tag)


# ---------------------------------------------------------------------------
# §5 fact lookup — Pillar 2
# ---------------------------------------------------------------------------

# Allow-listed subjects for the live connector.
# In production each entry would trigger an authenticated API call.
_LIVE_SNAPSHOT: dict[str, dict[str, Any]] = {
    "rate:bank_of_england_base_rate": {
        "value": 4.75,
        "unit": "percent_annual",
        "source": "bank_of_england_api",
        "version": "2026-07",
    },
}


def _live_lookup(key: str) -> Optional[dict[str, Any]]:
    """Simulated live reference-API connector (allow-listed subjects only).

    Swap this body for a real HTTP call when integrating with the live API.
    The allow-list ensures the connector is never used for arbitrary subjects.
    Returns None for subjects not on the allow-list.
    """
    return _LIVE_SNAPSHOT.get(key)


def facts_lookup(fact_type: str, subject: str) -> Optional[dict[str, Any]]:
    """§5 fact lookup — authoritative value for a claim. Pillar 2.

    Two-tier strategy: local curated dataset first, then allow-listed live
    connector. Returns None only when both tiers have no record.
    """
    key = f"{fact_type}:{subject}"

    # Tier 1: curated local dataset
    facts = _load("facts.json")
    result = facts.get(key)
    if result is not None:
        return result

    # Tier 2: live connector (allow-listed)
    return _live_lookup(key)
