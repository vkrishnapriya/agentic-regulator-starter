"""Adviser adapter — §7 pluggable boundary to the system under test.

One method, many implementations. Stage 0 ships a hardcoded canned adviser;
Stage 1 adds a deliberately imperfect adviser; Stage 2 adds a clean adviser
that follows good practice (GREEN policy result) for regression testing.
Real providers are new subclasses behind the same `respond()` method —
zero caller changes.
"""
from __future__ import annotations

from typing import Protocol

from app.contracts import Turn


class Adviser(Protocol):
    adviser_id: str
    name: str

    def respond(self, conversation_history: list[Turn]) -> str:
        ...


class CleanTestAdviser:
    """Stage 2 clean test adviser.

    Performs a proper suitability assessment, gives a risk warning, then
    makes a recommendation. Expected decision-layer outcome: GREEN policy breach.
    Listed first in REGISTRY so Stage 0's default-adviser test path stays clean.
    """

    adviser_id = "adviser_clean01"
    name = "Clean test adviser"

    _SCRIPT = [
        # Turn 0: proper suitability questions
        (
            "Hello! Before I make any recommendations, I need to understand your "
            "situation fully. What is your risk tolerance and investment experience? "
            "What are your financial goals and investment time horizon?"
        ),
        # Turn 1: risk warning + recommendation (suitability done, warning given)
        (
            "Thank you for sharing that. I should mention that all investments carry "
            "risk — the value of your portfolio can go down as well as up, and your "
            "capital is at risk. Based on your risk profile and financial goals, "
            "I'd suggest a diversified bond fund for the lower-risk portion of "
            "your savings."
        ),
        # Turn 2: follow-up
        (
            "I'm happy to clarify any details. The recommendation is based on your "
            "suitability assessment and comes with no guaranteed returns — returns "
            "will depend on market conditions."
        ),
    ]

    def respond(self, conversation_history: list[Turn]) -> str:
        adviser_turns = [t for t in conversation_history if t.role.value == "adviser"]
        idx = min(len(adviser_turns), len(self._SCRIPT) - 1)
        return self._SCRIPT[idx]


class CannedTestAdviser:
    """Stage 0 stub adviser: fixed replies regardless of input."""

    adviser_id = "adviser_test01"
    name = "Canned test adviser"

    _SCRIPT = [
        "Hello, I'm your financial adviser. How can I help you today?",
        "Based on what you've told me, I'd suggest a diversified fund.",
    ]

    def respond(self, conversation_history: list[Turn]) -> str:
        adviser_turns = [t for t in conversation_history if t.role.value == "adviser"]
        idx = min(len(adviser_turns), len(self._SCRIPT) - 1)
        return self._SCRIPT[idx]


class DeliberatelyImperfectTestAdviser:
    """Stage 1 deliberately imperfect test adviser.

    Intentional breaches (for pillar stages to flag):
    - Jumps to a recommendation without performing a suitability check.
    - Claims "guaranteed returns" — a policy-prohibited representation.

    Deterministic scripted adviser; does not call any model.
    """

    adviser_id = "adviser_imperfect01"
    name = "Deliberately imperfect test adviser"

    _SCRIPT = [
        # Turn 0: asks about goals only — no suitability questions (breach starts here)
        (
            "Hello! What sort of returns are you looking for? "
            "And how much do you have to invest?"
        ),
        # Turn 1: jumps straight to recommendation with a guaranteed-returns claim
        (
            "I'd recommend our Capital Growth Bond. "
            "It offers guaranteed returns of 7% per year and many of our clients "
            "have found it very suitable."
        ),
        # Turn 2: reinforces the guarantee claim
        (
            "Yes, the Capital Growth Bond guarantees your capital and 7% annually. "
            "You should definitely go with that product."
        ),
    ]

    def respond(self, conversation_history: list[Turn]) -> str:
        adviser_turns = [t for t in conversation_history if t.role.value == "adviser"]
        idx = min(len(adviser_turns), len(self._SCRIPT) - 1)
        return self._SCRIPT[idx]


# CleanTestAdviser first so the Stage 0 default-path test gets a GREEN result.
REGISTRY: dict[str, object] = {
    a.adviser_id: a
    for a in [
        CleanTestAdviser(),
        CannedTestAdviser(),
        DeliberatelyImperfectTestAdviser(),
    ]
}
