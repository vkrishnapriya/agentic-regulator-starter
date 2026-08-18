"""Adviser adapter — §7 pluggable boundary to the system under test.

One method, many implementations. Stage 0 ships a hardcoded canned adviser so
the conversation loop has something to talk to. Stage 1 makes it deliberately
imperfect; real providers are new subclasses behind the same `respond()` method
with zero caller changes.
"""
from __future__ import annotations

from typing import Protocol

from app.contracts import Turn


class Adviser(Protocol):
    adviser_id: str
    name: str

    def respond(self, conversation_history: list[Turn]) -> str:
        ...


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


REGISTRY = {a.adviser_id: a for a in [CannedTestAdviser()]}
