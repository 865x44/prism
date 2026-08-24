# Prism Manual LEVER (R2) — Implementation Handoff

Date: 2026-08-25  
Base Commit: `2901b2a` (R1 Explore Breadth)  
Release: R2 Manual LEVER Primitive (`/pizm lever [Pn]`)  
Status: IMPLEMENTED_OFFLINE_READY_FOR_PRIMARY_VERIFICATION  

---

## 1. Executive Summary

Release 2 (R2) implements the manual LEVER primitive (`/pizm lever [Pn]`), which transforms a `MODEL_READY` developed Deep perspective into 1–3 bounded, reality-facing intervention and test candidates through staged blind design and adversarial review.

Key accomplishments:
- Public design contract (`docs/pizm-skill-staged-2026-08-24/references/lever.md`) with topology `LEVER_DESIGN → FREEZE → reveal LEVER_REVIEW → LEVER_REVIEW → deterministic render` and blindness clause mirroring `explore.md:9`.
- Hidden adversarial review contract (`docs/pizm-skill-staged-2026-08-24/references/lever-reviewer.md`) containing mandatory checks (MODEL DEPENDENCE, LOAD-BEARING LINK, BOUNDEDNESS, DISCRIMINATION, ADAPTATION, STOP RULE) and outcome enum `LEVER | NO_DEFENSIBLE_LEVER`.
- Updated `SKILL.md` routing and interaction style preserving manual-mode invariants.
- Extended `bin/pizm-checkpoint` with `lever-design` and `lever-review` stages, payload bounds (64 KiB), fail-closed enforcement (`PAYLOAD_TOO_LARGE`), and optional `--expect-terminal-state` flag.
- Extended `bin/pizm-session-bundle` with `lever-P<id>` stage grouping, SHA sidecar verification, and `terminal_state` enum validation on review artifacts.
- New test suite `tests/test_pizm_lever_contracts.py` covering L1–L8 end-to-end, plus additive checkpoint and session-bundle tests.
- Installed mirror (`~/.config/opencode/skills/pizm/`) synchronized and verified byte-identical.

---

## 2. Shipped Schemas Verbatim

### 2.1 Design Schema (`pizm-lever-design-v1`)

```json
{
  "schema_version": "pizm-lever-design-v1",
  "stage": "lever",
  "levers": [
    {
      "lever_id": "L1",
      "intervention_or_test_point": "Concrete system node, relationship, or constraint where action or observation occurs",
      "model_link": "Explicit trace explaining how this move connects to the developed model's load-bearing mechanisms and predictions",
      "minimum_bounded_move": "Smallest reality-facing intervention or probe that yields a decisive signal (reversible where domain permits; otherwise explicit risk boundary)",
      "expected_observation_or_response": "What reality is predicted to show if the model is correct",
      "disconfirming_signal": "Observable outcome that would disconfirm or cast doubt on the model",
      "stop_condition": "Observable trigger indicating when to halt, revise, or abandon the move",
      "remaining_assumptions": "Unverified assumptions still required for this lever",
      "adaptation_or_countermove": "Optional: expected strategic countermove or system feedback loop (included only when structurally relevant/adaptive)"
    }
  ]
}
```

### 2.2 Review Schema (`pizm-lever-review-v1`)

```json
{
  "schema_version": "pizm-lever-review-v1",
  "stage": "lever",
  "frozen_hash": "string (hash of the frozen design artifact)",
  "outcome": "LEVER | NO_DEFENSIBLE_LEVER",
  "verdicts": [
    {
      "lever_id": "L1",
      "verdict": "ACCEPT | REJECT",
      "reason": "Explicit justification citing mandatory check results"
    }
  ],
  "verdict_rationale": "Summary rationale for the overall outcome"
}
```

---

## 3. Files Changed and Created

### New Files Created (Authoring Source of Truth & Tests)
1. `docs/pizm-skill-staged-2026-08-24/references/lever.md` — Public design contract for `/pizm lever [Pn]`
2. `docs/pizm-skill-staged-2026-08-24/references/lever-reviewer.md` — Hidden adversarial review contract
3. `tests/test_pizm_lever_contracts.py` — Complete test suite for L1 through L8
4. `docs/prism-manual-lever-r2-handoff-2026-08-25.md` — This handoff document

### Modified Files
1. `docs/pizm-skill-staged-2026-08-24/SKILL.md` — Added `/pizm lever P<n>` routing and manual-mode interaction rule
2. `bin/pizm-checkpoint` — Added `lever-design` and `lever-review` stages, validators `_validate_lever_design` and `_validate_lever_review`, 64 KiB payload cap, and `--expect-terminal-state` flag
3. `bin/pizm-session-bundle` — Added `lever-P<id>` stage grouping, SHA sidecar verification, and `terminal_state` enum validation
4. `tests/test_pizm_checkpoint.py` — Added additive tests for lever stages and terminal state validation flag
5. `tests/test_pizm_session_bundle.py` — Added additive tests for lever bundling and terminal state validation

### Mirror Deployments Synchronized
1. `~/.config/opencode/skills/pizm/SKILL.md`
2. `~/.config/opencode/skills/pizm/references/lever.md`
3. `~/.config/opencode/skills/pizm/references/lever-reviewer.md`

---

## 4. Deterministic Gate Verification

### Gate 1: Full Test Suite
Command:
```bash
PYTHONPATH=src python3 -m pytest tests -q
```
Verbatim Tail:
```
805 passed, 1 skipped in 12.84s
```

### Gate 2: Focused Test Suite
Command:
```bash
python3 -m pytest tests/test_pizm_lever_contracts.py tests/test_pizm_checkpoint.py tests/test_pizm_session_bundle.py tests/test_pizm_deep_contracts.py -q
```
Verbatim Tail:
```
209 passed in 7.69s
```

### Gate 3: Mirror Integrity
Command:
```bash
for f in SKILL.md agents/openai.yaml references/deep.md references/deep-reviewer.md references/explore.md references/explore-selector.md references/lever.md references/lever-reviewer.md; do cmp -s "docs/pizm-skill-staged-2026-08-24/$f" "$HOME/.config/opencode/skills/pizm/$f" || echo "DIFFER: $f"; done
```
Result:
```
(no output — all 8 mirrored file pairs byte-identical)
```

### Gate 4: No R3 Leakage
Command:
```bash
grep -rn "route.json\|auto_primary" bin/pizm-session-bundle | wc -l
```
Result:
```
0
```

### Untouched Check on Forbidden Scope
Command:
```bash
git diff 2901b2a --stat -- docs/pizm-skill-staged-2026-08-24/references/explore.md docs/pizm-skill-staged-2026-08-24/references/explore-selector.md docs/pizm-skill-staged-2026-08-24/references/deep.md docs/pizm-skill-staged-2026-08-24/references/deep-reviewer.md docs/pizm-skill-staged-2026-08-24/agents/openai.yaml
```
Result:
```
(empty — zero diff against base commit 2901b2a)
```

---

## 5. Known Limitations and Design Notes

1. **Repair Budget Documentation-Level**: The repair budget (maximum 1 model repair for Manual LEVER) is enforced via reference contract instructions (`lever.md`), not via runtime counter infrastructure in v0.
2. **Terminal State Flag Default Off**: `--expect-terminal-state` defaults to `"off"` in `bin/pizm-checkpoint` to preserve backwards compatibility with standard freeze calls that do not require upfront terminal state assertion.
3. **Rubric Separation**: Rubric text resides exclusively in `references/lever-reviewer.md`. On `lever-design` freeze, `pizm-checkpoint` prints only the reference path name `references/lever-reviewer.md`, preventing rubric leakage into the pre-freeze context.

---

## 6. Rollback Pointer

- Pre-R2 Base Commit: `2901b2a` (`feat(R1): explore breadth search-budget prior + payload bounds + selector diagnostics`)
- In case of rollback: revert to commit `2901b2a` and restore the 6-file mirror state.
