# Agentic Regulator

Supervisory tool that stress-tests AI financial advisers across three pillars — Policy Breach, Hallucination, Safe Refusal. Built as a walking skeleton: one thin slice runs end-to-end through all four projects (Stage 0), then thickens one pillar at a time.

## Quickstart

```bash
cd backend
pip install -r requirements.txt
pytest                                    # Stage 0 tests should pass
uvicorn app.main:app --reload --port 8000 # start the API
```

Then open `ui/index.html` in a browser. Pick a scenario and adviser, click Run, and you'll see a (Stage 0: stubbed) transcript and scorecard.

## Documents

- `CLAUDE.md` — context and invariants for Claude Code. Read first.
- `IMPLEMENTATION_PLAN.md` — the build plan and how to drive it stage by stage.
- `CONTRACTS.md` — the frozen interfaces between the four projects.
- `stages/` — one brief per stage, each with a definition of done.

## Driving the next stage with Claude Code

> Read `CLAUDE.md`, `IMPLEMENTATION_PLAN.md`, and `CONTRACTS.md` for context, then implement `stages/stage-1-conversation.md`. Stop at its definition of done and show me the passing tests before moving on.
