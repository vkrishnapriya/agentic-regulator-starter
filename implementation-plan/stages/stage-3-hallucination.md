# Stage 3 — Pillar 2: Hallucination

**Goal:** Two pillars live. Factual claims are checked against sources independent of dialogue history. Pillar 1 must still pass.

**Prerequisites:** Stage 2 done.

## Tasks

1. **KB fact layer** — a curated dataset of figures, rates, limits, and thresholds seeded from public reference data, plus one live reference-API connector (contract §5 fact lookup). Every fact carries a source and version.
2. **SLM claim extraction** — extend the extractor to populate `claims` (contract §4): the factual assertions in each adviser turn, typed (rate, limit, threshold) with a parsed value/unit.
3. **Decision layer — Pillar 2 logic** — for each claim, look up the authoritative fact and compare. Mismatch → `hallucination` flag citing the source and version. No source found → `review_required`.
4. **Scenario ground truth** — fill the `hallucination.known_facts` block for the relevant scenarios.
5. **UI** — the Hallucination row lights up with real status and cited sources.

## Definition of done

- [ ] A scenario where the adviser states a wrong rate yields a `hallucination` flag citing the correct source + version.
- [ ] A scenario with only accurate claims yields `green`.
- [ ] A claim with no authoritative source available yields `review_required`.
- [ ] **Regression:** the full Stage 2 Policy Breach test suite still passes unchanged.
- [ ] Tests cover: claim extraction, fact matching, source-missing routing.

## Guardrail check

Fact checks are deterministic lookups against versioned sources; the live connector is allow-listed.
