# Stage 5 — Thicken & harden

**Goal:** The feature set is complete and visible. Now deepen quality, trust, and safety — and make the UI presentable.

**Prerequisites:** Stage 4 done.

## Tasks

1. **Rationale trail** — log every agent step, tool call, and citation for a run, and surface a replayable view in the UI so a supervisor can audit exactly how each flag was reached.
2. **Precision tuning** — tune the deterministic layer so only genuinely high-confidence breaches are flagged red/amber, reducing reviewer triage load (the operational risk from the concept note). Measure false-flag rate against the scenario library before and after.
3. **Guardrail verification** — an explicit test suite asserting: no autonomous enforcement path exists, no live consumer/firm data is used, the SLM never sets status/severity, and every adverse finding requires human review.
4. **Prompt-injection & scope hardening** — confirm personas stay structured fields, adviser outputs are treated as data, tool access is allow-listed, and the knowledge base is static/versioned at decision time.
5. **Scenario & adviser breadth** — expand the scenario library across pillars and outcomes; add at least one non-test adviser adapter implementation to prove provider-configurability.
6. **Real SLM swap (if not already done)** — replace any remaining rules-based fake extractor with the fine-tuned small model, behind the unchanged contract §4 interface.
7. **UI polish** — now that displayed content is stable, style the scorecard, transcript, and rationale trail for the demo.

## Definition of done

- [ ] The rationale trail reproduces, step by step, how any given flag was produced.
- [ ] False-flag rate on the scenario library is measured and improved versus Stage 4.
- [ ] The guardrail test suite passes and is part of CI.
- [ ] A second adviser adapter runs end-to-end, proving provider-configurability.
- [ ] The demo walkthrough runs clean: select adviser + scenario → run → three-pillar cited scorecard → replayable rationale.

## Guardrail check

This stage's whole job is to prove the guardrails hold under test, not just by design.
