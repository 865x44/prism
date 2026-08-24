# Prism Single-Branch AUTO v0 (R3) — Implementation Handoff

Date: 2026-08-25  
Base Commit: `7e94078` (R2 Manual LEVER)  
Release: R3 Single-Branch AUTO v0 (`/pizm auto <task>`)  
Status: IMPLEMENTED_OFFLINE_READY_FOR_PRIMARY_VERIFICATION  

---

## 1. Executive Summary

Release 3 (R3) implements Single-Branch AUTO v0 (`/pizm auto <task>`), automating exactly one bounded path through Explore, single nominated Deep, and optional LEVER intervention (only when `MODEL_READY` ∧ `ACTION_OR_DECISION`) before rendering a deterministic FINAL report.

Key accomplishments:
- Public pipeline contract (`docs/pizm-skill-staged-2026-08-24/references/auto.md`) establishing the exact stage execution sequence, honest-stop rules, deterministic FINAL assembly template (zero model turns, zero tool calls), operational cost ceilings, and fail-closed budget enforcement.
- AUTO mode selection extension appended to `docs/pizm-skill-staged-2026-08-24/references/explore-selector.md` defining `pizm-auto-selection-v1` (`auto_primary_candidate_id` and `task_orientation`), establishing `selection.json` as sole routing authority (no `route.json`).
- Updated `SKILL.md` routing (`/pizm auto <task> → read references/auto.md`) and delegation clause while preserving manual-mode invariants verbatim.
- Extended `bin/pizm-session-bundle` with deterministic validation for `pizm-auto-selection-v1` (enforcing valid non-empty primary in `kept` with disposition `KEEP`, valid `task_orientation` enum, and rejecting forbidden multi-branch/fallback keys with `BAD_AUTO_SELECTION`).
- New test suite `tests/test_pizm_auto_contracts.py` covering A1 through A10 end-to-end, plus additive session-bundle tests in `tests/test_pizm_session_bundle.py`.
- Installed mirror (`~/.config/opencode/skills/pizm/`) synchronized across all 9 mirrored files and verified byte-identical.

---

## 2. Pipeline Verbatim

```text
AUTO TASK → EXPLORE GENERATE → freeze → AUTO SELECT (dispositions + nomination) → DEEP primary DEVELOP → freeze → DEEP_REVIEW → if terminal_state=MODEL_READY ∧ task_orientation=ACTION_OR_DECISION → same manual LEVER primitive (identical prompts/logic as /pizm lever, zero duplication) → FINAL
```

### Honest-Stop Rules
If Deep review produces `terminal_state == "NEED_EVIDENCE"` or `terminal_state == "RETURN_TO_EXPLORE"`:
- Execution stops honestly at that point with the stated reason from the review verdict.
- No other search or refinement primitive starts afterward (no second Deep, no alternative branch, no reroll, no auto-recovery).
- The pipeline proceeds directly to FINAL assembly to render the honest-stop report.

### Deterministic FINAL Assembly
- Rendered directly from frozen structured artifacts (`candidates.json`, `selection.json`, `development.json`, `review.json`, and `lever/*` if present).
- Increments neither `semantic_stage_count` nor `host_inference_count` and performs ZERO tool-call model turns.

---

## 3. Shipped Schemas Verbatim

### AUTO Selection Schema (`pizm-auto-selection-v1`)

```json
{
  "schema_version": "pizm-auto-selection-v1",
  "stage": "explore",
  "mode": "NORMAL|360|RIFT",
  "frozen_hash": "string",
  "dispositions": [
    {
      "candidate_id": "string",
      "disposition": "KEEP|BORDERLINE|MERGE|DROP",
      "standalone_quality": "strong|borderline|weak",
      "marginal_contribution": "high|medium|low|none",
      "reason": "string (compact)"
    }
  ],
  "kept": ["candidate_id"],
  "merged": [{"target": "candidate_id", "sources": ["candidate_id"]}],
  "next_free_p": "P<n>",
  "auto_primary_candidate_id": "string (member of kept with disposition KEEP)",
  "task_orientation": "ANALYTICAL | ACTION_OR_DECISION"
}
```

---

## 4. Operational Ceilings Table

| Dimension | Analytical AUTO | With-LEVER AUTO | Enforcement |
|---|---|---|---|
| Base Semantic Stages | 4 (Explore 2 + Deep 2) | 6 (Explore 2 + Deep 2 + LEVER 2) | Pipeline orchestration |
| Host Inference Hard Ceiling | ≤ 8 host inferences | ≤ 10 host inferences | Fail-closed (`BUDGET_EXHAUSTED`) |
| Model Repair Budget | ≤ 1 Explore, ≤ 2 total | ≤ 1 Explore, ≤ 1 LEVER, ≤ 2 total | Fail-closed (`BUDGET_EXHAUSTED`) |
| Checkpoint Retries | ≤ 3 internal retries | ≤ 3 internal retries | Runtime fail-closed |
| Future Contract Disclosure | Prohibited before freeze | Prohibited before freeze | Tamper-evident hash commit |

---

## 5. Files Changed and Created

### New Files Created (Authoring Source of Truth & Tests)
1. `docs/pizm-skill-staged-2026-08-24/references/auto.md` — Public pipeline contract for `/pizm auto <task>`
2. `tests/test_pizm_auto_contracts.py` — Complete test suite for A1 through A10
3. `docs/prism-single-branch-auto-r3-handoff-2026-08-25.md` — This handoff document

### Modified Files
1. `docs/pizm-skill-staged-2026-08-24/SKILL.md` — Added `/pizm auto <task>` route and delegation rule
2. `docs/pizm-skill-staged-2026-08-24/references/explore-selector.md` — Appended AUTO Mode Selection Extension (`pizm-auto-selection-v1`)
3. `bin/pizm-session-bundle` — Added `pizm-auto-selection-v1` deterministic validation and `BAD_AUTO_SELECTION` fail-closed error
4. `tests/test_pizm_session_bundle.py` — Added additive tests in `TestAutoSelectionValidation`

### Mirror Deployments Synchronized (9-File Total Mirror)
1. `~/.config/opencode/skills/pizm/SKILL.md`
2. `~/.config/opencode/skills/pizm/references/explore-selector.md`
3. `~/.config/opencode/skills/pizm/references/auto.md`
(plus unchanged: `agents/openai.yaml`, `references/deep.md`, `references/deep-reviewer.md`, `references/explore.md`, `references/lever.md`, `references/lever-reviewer.md`)

---

## 6. Deterministic Gate Verification

### Gate 1: Full Test Suite
Command:
```bash
PYTHONPATH=src python3 -m pytest tests -q
```
Verbatim Tail:
```
826 passed, 1 skipped in 13.83s
```

### Gate 2: Focused Test Suite
Command:
```bash
python3 -m pytest tests/test_pizm_auto_contracts.py tests/test_pizm_session_bundle.py tests/test_pizm_explore_contracts.py -q
```
Verbatim Tail:
```
147 passed in 3.53s
```

### Gate 3: Mirror Integrity (9 Mirrored Files)
Command:
```bash
for f in SKILL.md agents/openai.yaml references/deep.md references/deep-reviewer.md references/explore.md references/explore-selector.md references/lever.md references/lever-reviewer.md references/auto.md; do cmp -s "docs/pizm-skill-staged-2026-08-24/$f" "$HOME/.config/opencode/skills/pizm/$f" || echo "DIFFER: $f"; done
```
Result:
```
(no output — all 9 mirrored file pairs byte-identical)
```

### Gate 4: Zero Route JSON Occurrences
Command:
```bash
grep -rn "route.json" docs/pizm-skill-staged-2026-08-24 bin/ tests/ | wc -l
```
Result:
```
0
```

### Untouched Check on Checkpoint Binary vs 7e94078
Command:
```bash
git diff 7e94078 -- bin/pizm-checkpoint
```
Result:
```
(empty — zero diff against base commit 7e94078)
```

---

## 7. Known Limitation Note (OBSERVE_IN_DOGFOOD)

In same-host execution, Deep DEVELOP sees the earlier Explore selector rubric in conversation context. This is accepted as `OBSERVE_IN_DOGFOOD` per W0 reconciliation Risk 1:
- The Explore selector rubric (standalone quality & marginal contribution) and Deep develop/review contracts are structurally orthogonal.
- Deep DEVELOP remains strictly blind to its own Deep reviewer rubric until after `development.json` is frozen.

---

## 8. Rollback Pointer

- Pre-R3 Base Commit: `7e94078` (`feat(R2): manual LEVER primitive with staged blind review`)
- In case of rollback: revert to commit `7e94078` and restore the 8-file mirror state.
