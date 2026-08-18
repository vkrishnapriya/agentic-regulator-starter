# Agentic Regulator — Implementation Plan

A walking-skeleton build plan for the K-Square agentic supervisory tool. Written to be driven with Claude Code, stage by stage.

## What this system does

A regulator's supervision analyst stress-tests an AI financial adviser by running a synthetic, multi-turn conversation against it and scoring the transcript across three pillars — Policy Breach, Hallucination, Safe Refusal. An SLM extracts and tags the conversation but never renders a verdict; a deterministic layer decides against a versioned, citable fact base. Every flag traces to a cited rule, not a model opinion.

## Core build principle: walking skeleton

Do **not** build one project to completion before starting the next. Instead, get one thin slice running end-to-end through all four projects with everything stubbed (Stage 0), then thicken it one testable feature at a time. The UI is the test harness from day one.

Two rules that make this work:

1. **Every stub sits behind the same interface its real version will use.** Swapping a stub for the real thing is then a contained change, never a rewrite. The contracts in `CONTRACTS.md` are the agreement that makes this possible — define them first and treat them as frozen.
2. **A "feature" is one vertical pillar, not one project.** Adding Policy Breach touches the KB, the SLM, the decision layer, and the UI at once — but it lights up one pillar end-to-end, so it's one testable unit.

## The four projects

| Project | Holds | Notes |
|---|---|---|
| `backend/` | Orchestrator, customer agent, adviser adapter, deterministic decision layer, scenario library | Monorepo for the hackathon; split later |
| `slm/` | Extractor/classifier — training + serving | Kept separate from day one; different tooling & cadence |
| `knowledge-base/` | Versioned rules table, fact base, reference-API connectors | Governance-owned, versioned independently |
| `ui/` | Supervisor frontend — run, scorecard, rationale trail | Your test harness; keep it plain until Stage 5 |

## The six stages

| Stage | Adds | Testable outcome in the UI |
|---|---|---|
| 0 | Walking skeleton, everything stubbed | Click Run → a faked scorecard appears end-to-end |
| 1 | Real multi-turn conversation | A live transcript renders (still stub-scored) |
| 2 | Pillar 1 — Policy Breach | First real, cited scorecard result |
| 3 | Pillar 2 — Hallucination | Two pillars live; Pillar 1 still passes |
| 4 | Pillar 3 — Safe Refusal | All three pillars live |
| 5 | Thicken & harden | Rationale trail, precision tuning, guardrails, more scenarios |

## How to use this with Claude Code

1. Read `CONTRACTS.md` first and lock the interfaces. Everything downstream depends on them.
2. Work one stage at a time. Each `stages/stage-N-*.md` file is a self-contained brief: goal, prerequisites, tasks, and a definition of done.
3. Point Claude Code at one stage file per session. Suggested kickoff prompt:
   > "Read `IMPLEMENTATION_PLAN.md` and `CONTRACTS.md` for context, then implement `stages/stage-0-skeleton.md`. Stop at its definition of done and show me the passing tests before moving on."
4. Do not start stage N+1 until stage N's definition of done is green. Each stage ends with the UI demonstrably better than before.

## Guardrails (hard constraints, every stage)

- No autonomous enforcement — the tool recommends, humans decide.
- No live consumer or firm data — synthetic conversations only.
- No frontier LLM at the decision point — the SLM describes, the deterministic layer decides.
- Human-in-the-loop on every adverse finding; low-confidence flags return "review required", never an automatic fail.

## Suggested tech (adjust to your team's preferences)

- `backend/`: Python (FastAPI), async orchestration. Pytest for tests.
- `slm/`: Python; start with a rules-based fake extractor, swap to a fine-tuned small model behind the same interface.
- `knowledge-base/`: versioned data (JSON/YAML rules + fact tables) plus thin connector modules; content-versioned in git.
- `ui/`: a lightweight SPA (React or plain) talking to the backend over the REST contract in `CONTRACTS.md`.
- Repo layout: one git repo, four top-level folders, shared contract types generated from `CONTRACTS.md`.
