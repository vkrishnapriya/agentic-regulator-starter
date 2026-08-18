"""Knowledge Base — §5 read interfaces.

STUB for Stage 0: returns canned rule/fact lookups from local versioned data.
Later stages replace the bodies with a real rules table and reference-API
connectors, but the two function signatures stay frozen.

Governance-owned. Every response carries a `version` so citations reproduce.
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _load(name: str) -> Any:
    with open(os.path.join(_DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def rules_lookup(tag: str) -> Optional[dict[str, Any]]:
    """§5 rules lookup — map an SLM tag to a cited rule. Pillars 1 & 3."""
    rules = _load("rules.json")
    return rules.get(tag)


def facts_lookup(fact_type: str, subject: str) -> Optional[dict[str, Any]]:
    """§5 fact lookup — authoritative value for a claim. Pillar 2."""
    facts = _load("facts.json")
    return facts.get(f"{fact_type}:{subject}")
