# Pizm Single-Branch AUTO v0 Pipeline Contract

AUTO is an automated execution mode of Pizm that executes exactly one bounded path through Explore, Deep, and an optional LEVER intervention before rendering a deterministic final report.

## Explicit Delegation Requirement

AUTO executes ONLY via explicit `/pizm auto <task>` user delegation. Manual Pizm modes (`/pizm`, `normal`, `explore`, `rift`, `360`, `deep`, `/pizm lever`) NEVER trigger or emulate AUTO behavior. Discussing AUTO with the user remains possible without executing it.

AUTO enforces a strict single-Deep-only rule: exactly one branch is deepened. There is no second Deep, no alternative branch, no decide stage or inference, no secondary candidate concept, and no auto-360/RIFT/reroll/research loops.

---

## 1. Pipeline Execution Sequence

The AUTO pipeline proceeds through the following sequential stages in exact order:

```text
AUTO TASK → EXPLORE GENERATE → freeze → AUTO SELECT (dispositions + nomination) → DEEP primary DEVELOP → freeze → DEEP_REVIEW → if terminal_state=MODEL_READY ∧ task_orientation=ACTION_OR_DECISION → same manual LEVER primitive (identical prompts/logic as /pizm lever, zero duplication) → FINAL
```

### Stage Execution Details:
1. **AUTO TASK**: Receive the user's task prompt via `/pizm auto <task>`.
2. **EXPLORE GENERATE**: Run Explore generation adhering to `references/explore.md`. Generate 12–16 candidate seeds (bounded to 1..20 candidates, ≤ 192 KiB total payload).
3. **Freeze Explore**: Run `bin/pizm-checkpoint freeze --stage explore --run-id <run-id> --input <candidates.json>`.
4. **AUTO SELECT**: Reveal `references/explore-selector.md` (AUTO mode). The selector evaluates candidates categorically and writes `selection.json` adhering to `pizm-auto-selection-v1`, assigning categorical dispositions, designating exactly one `auto_primary_candidate_id` (which MUST be present in frozen candidates and have disposition `KEEP`), and classifying `task_orientation` as `ANALYTICAL` or `ACTION_OR_DECISION` (if genuinely ambiguous, default to `ANALYTICAL`). `selection.json` is the sole routing authority; no secondary routing file is created.
5. **DEEP Primary DEVELOP**: Deepen the single nominated perspective (`auto_primary_candidate_id`) following `references/deep.md`. Assign its visible P-ID (e.g., P1). Single Deep only.
6. **Freeze Deep**: Run `bin/pizm-checkpoint freeze --stage deep-P<n> --run-id <run-id> --input <development.json>`.
7. **DEEP_REVIEW**: Reveal `references/deep-reviewer.md`. The reviewer evaluates the developed model and writes `review.json` with `terminal_state` in `{"MODEL_READY", "NEED_EVIDENCE", "RETURN_TO_EXPLORE"}`.
8. **Conditional LEVER Primitive**:
   - If `terminal_state == "MODEL_READY"` AND `task_orientation == "ACTION_OR_DECISION"`:
     Execute the same manual LEVER primitive (`references/lever.md` and `references/lever-reviewer.md`) using identical prompts and review logic as `/pizm lever`, with zero duplication.
   - Otherwise (if `task_orientation == "ANALYTICAL"` or `terminal_state != "MODEL_READY"`):
     Do not invoke LEVER.
9. **FINAL Assembly**: Assemble and present the final output using the deterministic template.

---

## 2. Honest-Stop Rules

If Deep review produces `terminal_state == "NEED_EVIDENCE"` or `terminal_state == "RETURN_TO_EXPLORE"`:
- Execution MUST stop honestly at that point with the stated reason from the review verdict.
- No other search or refinement primitive starts afterward (no second Deep, no alternative branch, no reroll, no auto-recovery).
- The pipeline proceeds directly to FINAL assembly to render the honest-stop report.

---

## 3. Deterministic FINAL Assembly

`FINAL` is a DETERMINISTIC ASSEMBLY rendered directly from frozen structured artifacts (`candidates.json`, `selection.json`, `development.json`, `review.json`, and `lever/design.json` / `lever/review.json` if LEVER was executed).

- **Zero Model Invocations**: FINAL increments neither `semantic_stage_count` nor `host_inference_count` and performs ZERO tool-call model turns.
- **Contract Prohibition**: If an implementation ever requires an additional model turn or tool call for FINAL, STOP and replan the budget/contract instead of hiding it.
- **Fixed Assembly Template**: The final response is formatted strictly using the fixed deterministic template below:

### Fixed FINAL Assembly Template

```markdown
# Pizm AUTO Analysis: <Task Title / Summary>

## 1. Nominated Perspective
- **P-ID & Title**: P<n> — <Title>
- **Candidate ID**: <auto_primary_candidate_id>
- **Task Orientation**: <ANALYTICAL | ACTION_OR_DECISION>
- **Core Claim / Shift**: <semantic_core.claim>
- **Grounding Anchor**: <semantic_core.grounding_anchor>
- **Mechanism**: <semantic_core.mechanism>

## 2. Developed Model Summary
- **Primary Mechanism**: <developed model core mechanism>
- **Load-Bearing Constraints**: <key relations and constraints>
- **Key Predictions**: <observable predictions>
- **Boundary Conditions**: <where the model holds or breaks>

## 3. Deep Review Verdict
- **Terminal State**: <MODEL_READY | NEED_EVIDENCE | RETURN_TO_EXPLORE>
- **Review Rationale**: <summary rationale from review.json>
<!-- IF terminal_state != "MODEL_READY": -->
- **Stop Reason**: Honest stop triggered due to non-ready status (<terminal_state>). No further primitives executed.
<!-- END IF -->

<!-- IF LEVER executed (task_orientation == "ACTION_OR_DECISION" AND terminal_state == "MODEL_READY"): -->
## 4. Reality-Facing Levers
<!-- For each accepted lever from lever review: -->
### Lever <lever_id>: <intervention_or_test_point>
- **Model Link**: <model_link>
- **Minimum Bounded Move**: <minimum_bounded_move>
- **Expected Observation**: <expected_observation_or_response>
- **Disconfirming Signal**: <disconfirming_signal>
- **Stop Condition**: <stop_condition>
- **Remaining Assumptions**: <remaining_assumptions>
<!-- If adaptation_or_countermove present: -->
- **Adaptation / Countermove**: <adaptation_or_countermove>
<!-- End For -->
- **Lever Review Outcome**: <LEVER | NO_DEFENSIBLE_LEVER> (<verdict_rationale>)
<!-- END IF -->
```

---

## 4. Operational Cost Accounting and Ceilings

### Host Inference and Repair Ceilings
- **AUTO analytical** (Explore + Deep): ≤ 8 host inferences total.
- **AUTO with-LEVER** (Explore + Deep + LEVER): ≤ 10 host inferences total.
- **Repair budgets**:
  - Explore: max 1 model repair.
  - LEVER: max 1 model repair.
  - AUTO total: max 2 model repairs across the entire run.

### Fail-Closed Budget Enforcement
If host inference or model repair ceilings are exhausted at any point:
- The run immediately terminates with `BUDGET_EXHAUSTED`.
- Fail-closed rule: Do not reveal unreached future-stage contracts or rubrics.
- Archive failure evidence and report `BUDGET_EXHAUSTED` with the exact stage reached.

---

## 5. Known Limitation Note (OBSERVE_IN_DOGFOOD)

In same-host execution, Deep DEVELOP sees the earlier Explore selector rubric in conversation context. This is accepted as `OBSERVE_IN_DOGFOOD` per W0 reconciliation Risk 1:
- The Explore selector rubric (standalone quality & marginal contribution) and Deep develop/review contracts are structurally orthogonal.
- Deep DEVELOP remains strictly blind to its own Deep reviewer rubric until after `development.json` is frozen.
