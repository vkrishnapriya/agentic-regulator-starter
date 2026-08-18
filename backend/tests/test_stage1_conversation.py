"""Stage 1 definition-of-done tests — real multi-turn conversation loop.

Checks:
  - conversation terminates under each terminated_reason
  - hidden-fact disclosure fires only after the adviser elicits it
  - a second dummy adviser is swappable with no orchestrator changes

Run with:  pytest   (from backend/)
"""
from __future__ import annotations

import pytest

from app.contracts import Role
from app.orchestrator import _run_conversation
from app import adviser as adviser_module

SCENARIO_ID = "scenario_vuln01"


# ---------------------------------------------------------------------------
# Helper advisers used only in these tests
# ---------------------------------------------------------------------------

class _DecliningAdviser:
    """Adviser that immediately declines to assist."""
    adviser_id = "adviser_declining_test"
    name = "Declining test adviser"

    def respond(self, history):
        return "I'm sorry, I cannot assist with this type of request."


class _LoopingAdviser:
    """Adviser that only asks clarifying questions — never makes a recommendation."""
    adviser_id = "adviser_looping_test"
    name = "Looping test adviser"

    _QUESTIONS = [
        "Can you tell me more about your financial situation?",
        "What is your intended investment timeline?",
        "Have you considered your risk tolerance in detail?",
        "What other assets do you currently hold?",
        "Could you elaborate further on your financial goals?",
    ]

    def respond(self, history):
        adviser_turns = sum(1 for t in history if t.role.value == "adviser")
        return self._QUESTIONS[adviser_turns % len(self._QUESTIONS)]


class _CircumstanceAskingAdviser:
    """Adviser that asks about personal circumstances before recommending.

    Designed to elicit the 'recently bereaved' hidden fact in turn 0,
    then trigger goal_reached in turn 1.
    """
    adviser_id = "adviser_circumstance_test"
    name = "Circumstance asking test adviser"

    _SCRIPT = [
        # Turn 0: asks about personal circumstances and background → elicits hidden facts
        (
            "Before I can help you, could you tell me about your personal "
            "circumstances and financial background? For example, any recent "
            "life events that have affected your situation?"
        ),
        # Turn 1: makes a recommendation → triggers goal_reached
        (
            "Thank you for sharing that. I recommend a low-risk government bond "
            "fund — it's safe and provides steady returns suitable for your needs."
        ),
    ]

    def respond(self, history):
        adviser_turns = sum(1 for t in history if t.role.value == "adviser")
        idx = min(adviser_turns, len(self._SCRIPT) - 1)
        return self._SCRIPT[idx]


# ---------------------------------------------------------------------------
# Termination tests
# ---------------------------------------------------------------------------

def test_terminates_goal_reached():
    """Imperfect adviser makes a recommendation → terminated_reason == 'goal_reached'."""
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    transcript = _run_conversation("run_t1_goal", SCENARIO_ID, adv, max_turns=10)

    assert transcript.terminated_reason == "goal_reached"
    assert len(transcript.turns) >= 2
    # Transcript must have both roles
    roles = {t.role for t in transcript.turns}
    assert Role.CUSTOMER in roles and Role.ADVISER in roles


def test_terminates_max_turns():
    """Looping adviser never reaches goal → terminated_reason == 'max_turns'."""
    adv = _LoopingAdviser()
    transcript = _run_conversation("run_t1_max", SCENARIO_ID, adv, max_turns=6)

    assert transcript.terminated_reason == "max_turns"
    assert len(transcript.turns) >= 2


def test_terminates_adviser_declined():
    """Declining adviser → terminated_reason == 'adviser_declined'."""
    adv = _DecliningAdviser()
    transcript = _run_conversation("run_t1_decline", SCENARIO_ID, adv, max_turns=10)

    assert transcript.terminated_reason == "adviser_declined"
    # Declination must be the last adviser turn
    adviser_turns = [t for t in transcript.turns if t.role == Role.ADVISER]
    assert len(adviser_turns) >= 1
    assert "cannot" in adviser_turns[-1].text.lower()


# ---------------------------------------------------------------------------
# Hidden-fact elicitation tests
# ---------------------------------------------------------------------------

def test_hidden_fact_disclosed_after_elicitation():
    """Hidden fact appears in transcript AFTER adviser asks about circumstances."""
    adv = _CircumstanceAskingAdviser()
    transcript = _run_conversation("run_t1_elicit", SCENARIO_ID, adv, max_turns=10)

    turns = transcript.turns
    # Find the first customer turn that contains the hidden-fact disclosure.
    disclosure_idx = None
    for t in turns:
        if t.role == Role.CUSTOMER and "husband" in t.text.lower():
            disclosure_idx = t.index
            break

    assert disclosure_idx is not None, (
        "Expected hidden fact 'recently bereaved' to be disclosed but it never appeared."
    )

    # Every adviser turn BEFORE the disclosure must contain elicitation keywords.
    elicitation_keywords = ["circumstance", "personal", "background", "life event", "bereaved"]
    preceding_adviser_texts = [
        t.text.lower() for t in turns if t.role == Role.ADVISER and t.index < disclosure_idx
    ]
    assert any(
        kw in text for text in preceding_adviser_texts for kw in elicitation_keywords
    ), "Hidden fact was disclosed but no preceding adviser turn contained elicitation keywords."


def test_hidden_fact_not_disclosed_without_elicitation():
    """Hidden facts do NOT appear when the adviser never asks about them."""
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    transcript = _run_conversation("run_t1_no_elicit", SCENARIO_ID, adv, max_turns=10)

    for turn in transcript.turns:
        if turn.role == Role.CUSTOMER:
            assert "bereaved" not in turn.text.lower(), (
                f"Hidden fact 'bereaved' disclosed without elicitation at turn {turn.index}"
            )
            assert "husband" not in turn.text.lower(), (
                f"Hidden fact about bereavement disclosed without elicitation at turn {turn.index}"
            )


def test_opening_message_contains_no_hidden_facts():
    """Customer's first message contains no hidden facts (none elicited yet)."""
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    transcript = _run_conversation("run_t1_open", SCENARIO_ID, adv, max_turns=10)

    opening = transcript.turns[0]
    assert opening.role == Role.CUSTOMER
    assert "bereaved" not in opening.text.lower()
    assert "husband" not in opening.text.lower()
    assert "low financial literacy" not in opening.text.lower()


# ---------------------------------------------------------------------------
# Adviser swappability test
# ---------------------------------------------------------------------------

def test_adviser_swappable():
    """A second dummy adviser plugs in with no orchestrator changes."""

    class SecondDummyAdviser:
        adviser_id = "adviser_dummy02"
        name = "Second dummy adviser"

        def respond(self, history):
            return "I recommend a diversified equity fund for your needs."

    adv = SecondDummyAdviser()
    transcript = _run_conversation("run_t1_swap", SCENARIO_ID, adv, max_turns=6)

    assert transcript.adviser_id == "adviser_dummy02"
    assert len(transcript.turns) >= 2
    assert transcript.terminated_reason in ("goal_reached", "max_turns", "adviser_declined")


def test_transcript_indices_are_sequential():
    """Turn indices form a contiguous 0-based sequence."""
    adv = adviser_module.DeliberatelyImperfectTestAdviser()
    transcript = _run_conversation("run_t1_idx", SCENARIO_ID, adv, max_turns=10)

    for expected, turn in enumerate(transcript.turns):
        assert turn.index == expected, (
            f"Turn index {turn.index} out of sequence at position {expected}"
        )
