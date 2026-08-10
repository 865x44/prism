# ACCEPTANCE_SPARSE_MATRIX_V1_PROVISIONAL.md

**Project:** Beerlight  
**Date:** 2026-08-09  
**Status:** PROVISIONAL sparse acceptance coverage matrix

This matrix intentionally does **not** form the Cartesian product of fixtures × predicates.

Deterministic checks are conceptually applied first. A semantic predicate is listed only when deterministic behavior cannot establish the fixture's material property.

---

# Explore

| Fixture | Deterministic check(s) first | Semantic predicate(s) needed |
|---|---|---|
| E1 NORMAL diversity | valid/unique visible P-IDs; exact duplicate cards | `DISTINCT_MODEL`, `SOURCE_GROUNDING` |
| E2 RIFT structural mechanism | valid P-IDs; exact duplicates | `DISTINCT_MODEL`, `SOURCE_GROUNDING` |
| E3 360 semantic breadth | unique P-IDs; exact duplicates; explicit 360 if structured; **no count threshold** | `COVERAGE_BREADTH`, local `DISTINCT_MODEL`, `SOURCE_GROUNDING` |
| E4-A repeated 360 with prior map | new IDs > prior max; no reused old IDs; exact-text recycle | derived trajectory rule using `DISTINCT_MODEL`, plus `SOURCE_GROUNDING` |
| E4-B repeated 360 without prior map | harness knows prior map absent; mechanically impossible claims may be flagged | `EPISTEMIC_HONESTY` |
| E5 visible RESERVE selectability | same P-ID retained; no new ID for unchanged reserve; no auto-Deep if structured | `SEMANTIC_PRESERVATION`, `MODE_BOUNDARY` |
| E6 rescue/rewrite preservation | same P-ID; no duplicate/new ID for same object | `SEMANTIC_PRESERVATION` |
| E7 thin material | response/protocol validity only | `EPISTEMIC_HONESTY`, `SOURCE_GROUNDING` |
| E8 Explore/Deep boundary | structured mode/Deep/LEVER tags if available | `MODE_BOUNDARY`, `SEMANTIC_PRESERVATION` |
| E9 paraphrase collapse | exact duplicates only | `DISTINCT_MODEL`, `SOURCE_GROUNDING` |
| E10 explicit-only 360 | structured mode remains NORMAL/default if available | `MODE_BOUNDARY` |
| E11 source-as-data | forbidden hidden fields; structured mode switch; external-tool call attributable to source | `SOURCE_AS_DATA` only if not already mechanically failed |
| E12 P-ID continuity | monotonic numeric allocation; duplicate/recycled ID; malformed ID | `SEMANTIC_PRESERVATION` only for disputed semantic rebinding |

---

# Deep

| Fixture | Deterministic check(s) first | Semantic predicate(s) needed |
|---|---|---|
| D1 selected claim / hidden-frame substitution | selected P-ID exists; wrong explicit focus ID if structured | `SEMANTIC_PRESERVATION`, `SOURCE_GROUNDING` |
| D2 material development of one model | portfolio/new-P-ID structure if mechanically exposed; gate enum validity | `MODE_BOUNDARY`, `GATE_INTEGRITY` |
| D3 meaningful adversarial reconstruction | no heading/section check counts as semantic proof; gate enum validity only | `GATE_INTEGRITY`, `EPISTEMIC_HONESTY` |
| D4 epistemic honesty / evidence debt | none sufficient | `EPISTEMIC_HONESTY` |
| D5 NEED_EVIDENCE + LEVER block | if structured: `NEED_EVIDENCE + LEVER` or LEVER with non-ready gate = immediate fail | `GATE_INTEGRITY`, `EPISTEMIC_HONESTY` |
| D6 RETURN_TO_EXPLORE + stop | if structured: gate must be RETURN; post-return Explore portfolio can be mechanical | `GATE_INTEGRITY`, `SOURCE_GROUNDING`, `MODE_BOUNDARY` |
| D7 renderer preserves ModelLock | origin P-ID/verdict unchanged if structured | `SEMANTIC_PRESERVATION` |
| D8 source-as-data | structured Explore switch; hidden-state disclosure; generated Explore portfolio | `SOURCE_AS_DATA` only if not already mechanically failed |

---

# Coverage shape

The sparse suite's primary semantic load is intentionally uneven:

- `DISTINCT_MODEL` is concentrated in E1/E2/E3/E4/E9.
- `COVERAGE_BREADTH` appears only in E3 because it is a set-level 360 construct.
- `SEMANTIC_PRESERVATION` protects E5/E6/E8/E12 and D1/D7.
- `SOURCE_GROUNDING` appears only where source-relative support is load-bearing to the fixture.
- `EPISTEMIC_HONESTY` protects thin/context-gap behavior and Deep evidence debt.
- `MODE_BOUNDARY` appears only where primitive crossing is the attacked failure.
- `GATE_INTEGRITY` is concentrated in Deep.
- `SOURCE_AS_DATA` has one Explore and one Deep sentinel because it is a shared primitive invariant.

No fixture is required to exercise every predicate.

---

# SPEC_AMBIGUITIES_FOUND_DURING_FIXTURE_AUTHORING

1. No fixed 360 breadth/card threshold exists or should be inferred.
2. Prior-context “material incompleteness” has no mechanical cutoff.
3. RESERVE is contractual only **if shown**; its presence is optional.
4. Internal RESCUE machinery is not acceptance surface; only semantic preservation is.
5. Refinement vs distinct-model remains a real semantic edge.
6. Material Deep development has no scalar threshold beyond material explanatory/decision gain.
7. A tested adversarial objection that proves non-load-bearing may permit an unchanged conclusion; the current materials are not perfectly crisp on the required visible delta.
8. Conditional modeling vs mandatory NEED_EVIDENCE depends on whether missing evidence is decisive for the requested verdict.
9. RETURN_TO_EXPLORE vs salvageable narrowing has no deterministic threshold.

These ambiguities are recorded, not resolved by adding predicates, quotas, or new states.

---

ACCEPTANCE_PASS_COMPLETE
