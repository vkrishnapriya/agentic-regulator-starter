# Stage 0 — Walking skeleton

**Goal:** Click "Run" in the UI and watch a faked scorecard appear, having travelled end-to-end through all four projects. Nothing is real; every pipe is connected.

**Prerequisites:** `CONTRACTS.md` interfaces locked.

## Why this stage first

This is the highest-risk integration done cheapest. By connecting all four projects while each is trivial, you turn the big-bang integration risk into a Stage 0 task. Everything after this is thickening, not wiring.

## Tasks

1. **Repo scaffold** — one git repo, four folders (`backend/`, `slm/`, `knowledge-base/`, `ui/`). Add the shared contract types (from `CONTRACTS.md`) as a generated or hand-written module each project imports.
2. **Backend orchestrator (stub)** — implement `POST /runs`, `GET /runs/{run_id}`, `GET /scenarios`, `GET /advisers` per contract §6. On a run, return a hardcoded two-turn transcript (contract §2) and immediately mark the run complete.
3. **Decision layer (stub)** — a function that takes a transcript and returns a fixed scorecard (contract §3) with all three pillars `not_evaluated`, empty flags.
4. **KB (stub)** — the two read endpoints (contract §5) returning canned responses. Not called yet, but stand them up so the shape exists.
5. **SLM (stub)** — an extractor function returning an empty extraction result (contract §4). Not called yet.
6. **UI** — one screen: a scenario dropdown, an adviser dropdown, a Run button, a transcript pane, and a three-row scorecard bound to contract §3. Poll `GET /runs/{run_id}` until complete, then render. Keep it plain — no styling effort yet.

## Definition of done

- [ ] `POST /runs` then polling `GET /runs/{run_id}` returns a complete run with the canned transcript and the all-`not_evaluated` scorecard.
- [ ] The UI shows the two-turn transcript and three scorecard rows after clicking Run.
- [ ] A single integration test drives the full path (create run → poll → assert scorecard shape).
- [ ] All four folders import the shared contract types; no project defines its own copy.

## Guardrail check

Synthetic transcript only; no external calls; nothing decides anything yet.
