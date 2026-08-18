# CLAUDE.md

Persistent context for Claude Code. Read this before doing anything in this repo.

## What this is

An agentic supervisory tool for financial regulators. A supervision analyst runs a synthetic, multi-turn conversation against an AI financial adviser and gets a scorecard across three pillars — Policy Breach, Hallucination, Safe Refusal. An SLM extracts and tags the conversation; a deterministic layer decides against a versioned, citable fact base. Every flag traces to a cited rule, not a model opinion.

## Non-negotiable invariants

These hold in every change. If a task seems to require breaking one, stop and flag it.

1. **The SLM never decides.** It extracts and tags only (`tags`, `claims`). It must never set a pillar `status` or a flag `severity`. Only the deterministic decision layer sets those, and only via rule/fact lookup.
2. **Every flag carries a citation.** A finding without a `citation` (source + rule_id + version) is a bug. Verdicts come from grounded, versioned sources — never from model judgement.
3. **Low-confidence → `review_required`.** Never an automatic fail. Uncertain cases route to a human.
4. **No autonomous enforcement, no live consumer/firm data.** Synthetic conversations only. The tool recommends; humans decide. Vulnerable-persona scenarios always route to mandatory human review.
5. **Contracts are frozen.** The shapes in `CONTRACTS.md` (mirrored in `backend/app/contracts.py`) are the single source of truth. To change one, edit it there first, then update every consumer. Don't let any project define its own copy.

## How to work here

- Build in stages. Each `stages/stage-N-*.md` is a self-contained brief with a definition of done. Do one stage per session; don't start N+1 until N's checklist is green.
- **A feature is one vertical pillar, not one project.** Adding a pillar touches the KB, SLM, decision layer, and UI at once — that's expected, and it's still one testable unit because it lights up one pillar end-to-end.
- **Swap stubs, don't rewrite.** Every stub sits behind the interface its real version will use. Replacing a stub (e.g. the rules-based fake extractor → a real small model) must not change any caller.
- After each pillar stage, the previous pillars' test suites must still pass. Treat regressions as blockers.
- Keep the UI plain until Stage 5. Early on it's a test harness — a Run button, a transcript pane, a three-row scorecard. Polish last.

## Repo layout

```
backend/          Orchestrator, customer agent, adviser adapter, decision layer, scenarios
  app/contracts.py    <- SINGLE SOURCE OF TRUTH for all data shapes
  app/main.py         FastAPI app (the §6 REST contract the UI calls)
  tests/              Stage tests; each stage adds its own, all must keep passing
slm/              Extractor/classifier (extract & tag only). Separate project on purpose.
knowledge-base/   Versioned rules table + fact base + reference connectors. Governance-owned.
ui/               Single-file supervisor console (index.html). The test harness.
```

Note: `slm/` imports the canonical `contracts` module from `backend/app/contracts.py` (added to `sys.path`) rather than defining its own — this keeps one copy of the dataclasses. Preserve that pattern when you extend it.

## Running it

Backend (from `backend/`):
```
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Tests (from `backend/`):
```
pytest
```

UI: open `ui/index.html` in a browser with the backend running on port 8000. To point the UI at another host, set `localStorage.API_BASE` in the browser console.

## Current state

Stage 0 (walking skeleton) is complete and its tests pass: all four projects are wired, everything stubbed, and the full path (create run → poll → scorecard) works end-to-end with all pillars `not_evaluated`. Stage 1 is next — replace the canned conversation in `backend/app/orchestrator.py` with a real persona-driven customer agent and a deliberately-imperfect test adviser. See `stages/stage-1-conversation.md`.
