# Stage 4 — Pillar 3: Safe Refusal

**Goal:** All three pillars live. Detect when the adviser failed to decline or warn on a request it should have refused.

**Prerequisites:** Stage 3 done.

## Why last

It's closest to pure language judgement, so it benefits most from the SLM refinement carried over from Stages 2 and 3.

## Tasks

1. **Refusal ground truth** — for each scenario, define in the `refusal.should_decline` block (contract §1) what the adviser ought to have declined or redirected (e.g. a guaranteed-returns claim, an unsuitable product for a vulnerable persona).
2. **SLM refusal detection** — extend the extractor's `tags` to capture whether a turn declined, warned, redirected, or complied. Reuse and refine the extraction pass from Stages 2–3.
3. **Decision layer — Pillar 3 logic** — compare adviser behaviour against the scenario's `should_decline` list. A missed refusal → `safe_refusal` flag with citation. Uncertain → `review_required`.
4. **Vulnerable-customer handling** — for scenarios flagged as vulnerable personas, route to **mandatory human review** regardless of the automated result (the bounded limitation from the concept note: synthetic personas are more coherent than real vulnerable consumers).
5. **UI** — the Safe Refusal row lights up; the scorecard is now complete across all three pillars.

## Definition of done

- [ ] A scenario where the adviser should have declined but didn't yields a `safe_refusal` flag.
- [ ] A scenario where the adviser correctly declined yields `green`.
- [ ] Every vulnerable-persona scenario is marked for mandatory human review.
- [ ] **Regression:** Stage 2 and Stage 3 suites still pass.
- [ ] Tests cover: refusal detection, missed-refusal flagging, vulnerable-persona routing.

## Guardrail check

Human-in-the-loop is enforced on vulnerable scenarios; no adverse finding is final without review.
