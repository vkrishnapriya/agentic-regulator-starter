# Stage 2 — Pillar 1: Policy Breach

**Goal:** The first real, cited scorecard result. The SLM and KB enter the pipeline for the first time, minimally.

**Prerequisites:** Stage 1 done.

## Why Policy Breach first

It's the clearest regulator-facing proof and it exercises the full real pipeline — extraction, rule lookup, deterministic decision, citation binding — so it de-risks the other two pillars.

## Tasks

1. **KB rules table (small)** — parse or hand-author 5–10 rules into the versioned rules table (contract §5 rules lookup). Each rule: `rule_id`, `version`, the required element it maps to, and a default severity. Do not attempt the whole handbook.
2. **SLM extraction for Pillar 1** — return `tags` for required-element presence/absence (e.g. `no_suitability_check`, `risk_warning_given`, `recommendation_made`) per contract §4. **Start with a rules-based fake extractor** behind the SLM interface; swap to a real small model later without touching callers.
3. **Decision layer — Pillar 1 logic** — take SLM tags, look up rules in the KB, and produce `policy_breach` flags with citations (contract §3 flag shape). Apply the confidence threshold: low-confidence → `review_required`, not an automatic fail.
4. **Scenario ground truth** — fill the `policy` block (contract §1) for a handful of scenarios spanning pass / borderline / red-line.
5. **UI** — the Policy Breach row now shows a real RAG status, and each flag displays its cited `rule_id` and version. Other two pillars still `not_evaluated`.

## Definition of done

- [ ] A red-line scenario yields a `red` Policy Breach status with a flag citing a real `rule_id` + version.
- [ ] A clean scenario yields `green`.
- [ ] A borderline / low-confidence case yields `review_required`, never an auto-fail.
- [ ] The SLM extractor is swappable (fake → real) with zero decision-layer changes — assert via a test that both implementations satisfy contract §4.
- [ ] Tests cover: tag→rule mapping, citation binding, confidence routing.

## Guardrail check

Every flag traces to a cited, versioned rule — not a model opinion. The SLM sets no status or severity.
