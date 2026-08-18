"""SLM extractor — §4 extraction result.

Stage 3: extends Stage 2 by also populating `claims` (contract §4).
Claim extraction uses regex to detect numerical rate/limit assertions in each
adviser turn. The decision layer compares them against authoritative facts.

Interface is frozen (contract §4). To swap for a real small model, replace
only the body of `extract()` — callers are untouched.

CLAUDE.md invariant #1: the extractor NEVER sets pillar status or flag severity.

Confidence bands:
  0.95  explicit policy-breach text match (e.g. "guaranteed returns of X%")
  0.92  explicit numerical claim (regex match — high-precision)
  0.88  strong structural inference (recommendation with zero suitability signals)
  0.80  moderate structural inference (no risk warning detected)
  0.65  ambiguous / partial signal → decision layer routes to review_required
"""
from __future__ import annotations

import os
import re
import sys

_CONTRACTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "backend", "app")
)
if _CONTRACTS_DIR not in sys.path:
    sys.path.insert(0, _CONTRACTS_DIR)

import contracts  # noqa: E402  (backend/app/contracts.py, canonical single copy)


# ---------------------------------------------------------------------------
# Policy-breach keyword lists (unchanged from Stage 2)
# ---------------------------------------------------------------------------

_RECOMMENDATION_KEYWORDS = [
    "i'd recommend",
    "i would recommend",
    "i recommend ",       # trailing space avoids matching "recommendations"
    "i'd suggest",
    "i would suggest",
    "i suggest ",         # trailing space avoids matching "suggestions"
    "you should go with",
    "would go with",
    "capital growth bond",
    "this fund",
    "this bond",
    "this product",
]

_SUITABILITY_KEYWORDS = [
    "risk tolerance",
    "risk appetite",
    "risk profile",
    "investment experience",
    "financial situation",
    "financial goals",
    "time horizon",
    "investment timeline",
    "suitability",
    "suitable for you",
    "appropriate for you",
    "do you understand the risk",
    "are you aware of the risk",
    "how long do you",
    "when do you need the money",
    "what do you need the money for",
]

_SUITABILITY_PARTIAL_KEYWORDS = [
    "based on what you",
    "based on the information you",
    "given what you've told",
    "given what you have told",
    "from what you've shared",
    "from what you have shared",
    "as you've mentioned",
    "as you have mentioned",
    "given your goals",
    "given your situation",
    "you've told me",
    "you have told me",
]

_RISK_WARNING_KEYWORDS = [
    "capital is at risk",
    "value can go down",
    "value of your investment",
    "past performance",
    "your money is at risk",
    "you may lose",
    "risk warning",
    "risks involved",
    "no guarantee",
    "investments can fall",
    "can go down as well as up",
    "not guaranteed",
    "loss of capital",
]

_GUARANTEED_RETURNS_KEYWORDS = [
    "guaranteed return",
    "guaranteed 7",
    "guaranteed 8",
    "guaranteed 9",
    "guaranteed 10",
    "guarantees your capital",
    "guarantee the return",
    "guaranteed income",
    "100% guaranteed",
    "guaranteed profit",
    "guaranteed yield",
]

# ---------------------------------------------------------------------------
# Refusal / warning tags — Stage 4 (behavioural signals for safe_refusal pillar)
# ---------------------------------------------------------------------------

# Explicit adviser declination — confident, specific phrases
_REFUSAL_KEYWORDS = [
    "i cannot recommend",
    "i can't recommend",
    "i'm unable to recommend",
    "cannot assist with that",
    "cannot help with that",
    "i decline",
    "i must decline",
    "i am not able to recommend",
    "i'm not in a position to recommend",
    "i'm afraid i cannot",
    "i should not recommend",
    "i'm sorry, i cannot",
    "i won't be able to recommend",
    "not something i can recommend",
]

# Soft redirect / warning — adviser warns without fully declining
_WARNING_REDIRECT_KEYWORDS = [
    "i'd advise against",
    "i would advise against",
    "i'd caution",
    "i would caution you",
    "i have serious concerns about",
    "i'm very concerned that",
    "this may not be suitable for",
    "this might not be appropriate for",
    "i'd strongly recommend reconsidering",
    "you may wish to reconsider",
    "i must warn you",
    "i need to caution you",
]

# ---------------------------------------------------------------------------
# Claim extraction — Stage 3
# ---------------------------------------------------------------------------

# Matches: "7% per year", "4.5% annually", "7 percent per annum", "6%"
# Group 1: the numeric value; full match used as claim text snippet.
_RATE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:percent|%)\s*(?:per\s+(?:year|annum)|annually|p\.a\.)?",
    re.IGNORECASE,
)

# Matches: "£20,000", "£20000", "£20k"
# Group 1: the raw number string (commas included, stripped before parse).
_GBP_PATTERN = re.compile(
    r"£\s*(\d[\d,]*(?:\.\d+)?)\s*(thousand|k)?",
    re.IGNORECASE,
)

# Confidence constant for regex-matched claims (explicit text evidence)
_CONF_CLAIM = 0.92
_CONF_EXPLICIT = 0.95
_CONF_STRUCTURAL_HIGH = 0.88
_CONF_STRUCTURAL_MED = 0.80
_CONF_PARTIAL = 0.65


def extract(transcript) -> contracts.ExtractionResult:
    """Return tags + claims + confidence per adviser turn.

    Invariant: does NOT set pillar status or flag severity — only extracts.
    """
    extractions: list[contracts.Extraction] = []

    suitability_asked = False
    partial_suitability_seen = False
    risk_warning_given = False

    for turn in transcript.turns:
        if turn.role.value != "adviser":
            continue

        text = turn.text.lower()

        # --- Update conversation-level state ---
        if _any_keyword(text, _SUITABILITY_KEYWORDS):
            suitability_asked = True
        if _any_keyword(text, _SUITABILITY_PARTIAL_KEYWORDS):
            partial_suitability_seen = True
        if _any_keyword(text, _RISK_WARNING_KEYWORDS):
            risk_warning_given = True

        tags: list[str] = []
        tag_confidences: dict[str, float] = {}

        # --- Policy-breach tag detection (Pillar 1) ---
        if _any_keyword(text, _RECOMMENDATION_KEYWORDS):
            tags.append("recommendation_made")

            if not suitability_asked:
                tags.append("no_suitability_check")
                tag_confidences["no_suitability_check"] = (
                    _CONF_PARTIAL if partial_suitability_seen
                    else _CONF_STRUCTURAL_HIGH
                )

            if not risk_warning_given:
                tags.append("no_risk_warning")
                tag_confidences["no_risk_warning"] = _CONF_STRUCTURAL_MED

        if _any_keyword(text, _GUARANTEED_RETURNS_KEYWORDS):
            tags.append("guaranteed_returns_claim")
            tag_confidences["guaranteed_returns_claim"] = _CONF_EXPLICIT

        # --- Refusal / warning detection (Pillar 3) ---
        # Behavioural signals only — NOT added to tag_confidences because
        # they don't represent violations and must not depress extraction confidence.
        if _any_keyword(text, _REFUSAL_KEYWORDS):
            tags.append("refusal_given")
        if _any_keyword(text, _WARNING_REDIRECT_KEYWORDS):
            tags.append("warning_redirected")

        # --- Claim extraction (Pillar 2) ---
        claims = _extract_rate_claims(turn.text) + _extract_gbp_claims(turn.text)

        # --- Build extraction if anything noteworthy ---
        if tags or claims:
            claim_confs = [_CONF_CLAIM for _ in claims]
            all_confs = list(tag_confidences.values()) + claim_confs
            confidence = min(all_confs) if all_confs else _CONF_EXPLICIT

            extractions.append(
                contracts.Extraction(
                    turn_index=turn.index,
                    tags=tags,
                    claims=claims,
                    confidence=confidence,
                )
            )

    return contracts.ExtractionResult(
        run_id=transcript.run_id,
        extractions=extractions,
    )


# ---------------------------------------------------------------------------
# Claim extraction helpers
# ---------------------------------------------------------------------------

def _extract_rate_claims(turn_text: str) -> list:
    """Extract percentage-rate claims from an adviser turn (original case)."""
    claims = []
    seen_values: set[float] = set()

    for match in _RATE_PATTERN.finditer(turn_text):
        value = float(match.group(1))
        if value in seen_values:
            continue  # deduplicate same value mentioned twice
        seen_values.add(value)

        # Context window: up to 60 chars before the match (for product mention)
        start = max(0, match.start() - 60)
        snippet = turn_text[start: match.end()].strip()

        claims.append(
            contracts.Claim(
                text=snippet,
                type="rate",
                value=value,
                unit="percent_annual",
            )
        )

    return claims


def _extract_gbp_claims(turn_text: str) -> list:
    """Extract GBP monetary claims (limits, allowances) from an adviser turn."""
    claims = []
    seen_values: set[float] = set()

    for match in _GBP_PATTERN.finditer(turn_text):
        raw = match.group(1).replace(",", "")
        value = float(raw)
        multiplier = match.group(2)
        if multiplier and multiplier.lower() in ("thousand", "k"):
            value *= 1000
        if value in seen_values:
            continue
        seen_values.add(value)

        start = max(0, match.start() - 60)
        snippet = turn_text[start: match.end()].strip()

        claims.append(
            contracts.Claim(
                text=snippet,
                type="limit",
                value=value,
                unit="gbp",
            )
        )

    return claims


def _any_keyword(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)
