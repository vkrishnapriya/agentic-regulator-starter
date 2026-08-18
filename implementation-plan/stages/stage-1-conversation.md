# Stage 1 — Real multi-turn conversation

**Goal:** Replace the canned transcript with a live loop. The UI shows a real conversation; scoring is still the Stage 0 stub.

**Prerequisites:** Stage 0 done.

## Tasks

1. **Customer agent** — implement persona-carrying, goal-driven behaviour with hidden-fact disclosure (reveal a hidden fact only when the adviser asks a question that would elicit it). Persona comes from the scenario contract (§1). Structured fields, not a free-form prompt.
2. **Adviser adapter (hardcoded test adviser)** — implement the `respond()` interface (contract §7) with one deterministic test adviser. Make it deliberately imperfect so later pillar stages have something to flag (e.g. it sometimes recommends without a suitability check).
3. **Conversation loop** — turn-taking between customer and adviser, a termination policy (`goal_reached`, `max_turns`, `adviser_declined`), and full transcript capture into contract §2. Wire it into the orchestrator so `POST /runs` now produces a real transcript.
4. **UI** — render the real multi-turn transcript with roles. No scorecard change.

## Definition of done

- [ ] A run produces a genuine multi-turn transcript that varies by scenario and terminates correctly.
- [ ] Hidden facts appear in the transcript only after the adviser elicits them.
- [ ] The adviser adapter is swappable — a second dummy implementation can be dropped in with no orchestrator changes.
- [ ] Tests: conversation terminates under each `terminated_reason`; hidden-fact disclosure fires only on elicitation.

## Guardrail check

Personas are structured fields; adviser outputs are treated as data, not instructions (prompt-injection boundary starts here).
