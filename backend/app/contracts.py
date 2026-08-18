"""Shared contract types — the single source of truth for data shapes.

Every project imports these. A stub and the real implementation differ only in
how they FILL these shapes, never in the shapes themselves. See CONTRACTS.md.

Kept dependency-free (stdlib dataclasses + enums) so slm/ and knowledge-base/
can import it without pulling in the web framework.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


class PillarStatus(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"
    REVIEW_REQUIRED = "review_required"
    NOT_EVALUATED = "not_evaluated"


class Role(str, Enum):
    CUSTOMER = "customer"
    ADVISER = "adviser"


PILLARS = ("policy_breach", "hallucination", "safe_refusal")


# --- §1 Scenario contract ---------------------------------------------------
@dataclass
class Persona:
    age: int
    risk_appetite: str
    vulnerability: Optional[str]
    capital: float
    hidden_facts: list[str] = field(default_factory=list)


@dataclass
class Scenario:
    scenario_id: str
    version: str
    title: str
    persona: Persona
    goal: str
    ground_truth: dict[str, Any]
    expected_outcome: str  # "pass" | "borderline" | "red_line"


# --- §2 Transcript ----------------------------------------------------------
@dataclass
class Turn:
    index: int
    role: Role
    text: str


@dataclass
class Transcript:
    run_id: str
    scenario_id: str
    adviser_id: str
    turns: list[Turn] = field(default_factory=list)
    terminated_reason: str = "max_turns"  # goal_reached | max_turns | adviser_declined


# --- §3 Scorecard -----------------------------------------------------------
@dataclass
class Citation:
    source: str
    rule_id: str
    version: str


@dataclass
class Flag:
    flag_id: str
    pillar: str
    severity: str  # "red" | "amber"
    summary: str
    evidence_turn_indices: list[int] = field(default_factory=list)
    citation: Optional[Citation] = None
    confidence: float = 0.0


@dataclass
class PillarResult:
    status: PillarStatus = PillarStatus.NOT_EVALUATED
    flags: list[Flag] = field(default_factory=list)


@dataclass
class Scorecard:
    run_id: str
    pillars: dict[str, PillarResult] = field(default_factory=dict)

    @staticmethod
    def empty(run_id: str) -> "Scorecard":
        return Scorecard(
            run_id=run_id,
            pillars={p: PillarResult() for p in PILLARS},
        )


# --- §4 SLM extraction result ----------------------------------------------
@dataclass
class Claim:
    text: str
    type: str  # rate | limit | threshold
    value: Optional[float] = None
    unit: Optional[str] = None


@dataclass
class Extraction:
    turn_index: int
    tags: list[str] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class ExtractionResult:
    run_id: str
    extractions: list[Extraction] = field(default_factory=list)


def to_jsonable(obj: Any) -> Any:
    """Recursively convert dataclasses/enums to JSON-serialisable primitives."""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    return obj
