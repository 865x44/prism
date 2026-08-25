# Pizm AUTO v1 Pipeline Contract

AUTO is an automated execution mode of Pizm that executes exactly one bounded path — Search(initial), Portfolio Judge, Deep on one nominated target, Critic review, optional LEVER — and then renders a deterministic final report plus a deterministic readable `run.md`.

## Explicit Delegation Requirement

AUTO executes ONLY via explicit `/pizm auto <task>` user delegation. Manual Pizm modes (`/pizm`, `normal`, `explore`, `rift`, `360`, `deep`, `/pizm lever`) NEVER trigger or emulate AUTO behavior. Discussing AUTO with the user remains possible without executing it.

AUTO enforces a strict single-target rule: exactly one nominated target (P or B) is deepened. There is no second Search pass, no second Deep, no alternative branch, no decide stage or inference, no secondary candidate concept, and no auto-360/RIFT/reroll/research loops.

---

## 1. Pipeline Execution Sequence

The AUTO pipeline proceeds through the following sequential stages in exact order:

```text
AUTO TASK → Search(initial) GENERATE → freeze explore pass + search-field manifest
→ PORTFOLIO JUDGE → freeze portfolio record (route AUTO; exactly one auto_target: P or B)
→ DEEP(target) DEVELOP (development-v2) → freeze
→ CRITIC REVIEW (deep-review-v2) → freeze
→ [conditional] same manual LEVER primitive (design + review)
→ deterministic FINAL assembly (zero model calls)
→ deterministic run.md rendering (zero model calls)
```

### Stage Execution Details:

1. **AUTO TASK**: Receive the user's task prompt via `/pizm auto <task>`.
2. **Search(initial)**: Run ONE initial Search pass adhering to `references/explore.md` (soft target 12–16 candidates when supported; hard bounds 1..20 candidates, ≤ 192 KiB total payload, ≤ 12 KiB per candidate). Freeze the raw pass and register it in the append-only search-field manifest exactly as `references/explore.md` prescribes. This is the only Search of the run: no residual Search, no second Search, and no re-judgment loop exists inside AUTO.
3. **PORTFOLIO JUDGE**: Reveal `references/explore-selector.md`. The judge evaluates the exact frozen field categorically and freezes one portfolio record conforming to `pizm-portfolio-selection-v1` with `route: "AUTO"` and exactly one `auto_target` (`{"target_type": "P"|"B", "target_id": ...}`), pointing either at a promoted perspective (`P<n>`) or at a proposed bundle (`B<n>`). The portfolio record is the sole routing authority; no secondary routing file is created. There is no ranked ordering and no alternative branch.
   - **Task orientation**: while judging, classify the task as `ANALYTICAL` or `ACTION_OR_DECISION`, reusing the existing bounded judgment already exercised in the conversation (no classifier call, no extra model turn, no new semantic abstraction). If genuinely ambiguous, default to `ANALYTICAL`. Orientation is conversational routing metadata; it adds no semantic stage.
4. **DEEP(target) DEVELOP**: Deepen exactly the nominated target following `references/deep.md` under the development-v2 contract. The developed artifact's target must equal the portfolio's `auto_target` verbatim: a promoted perspective (`P<n>`, identity lock preserving its `p_id`) or a proposed bundle (`B<n>`, identity lock freezing `member_refs`; one Bundle = one Deep, never per-member mini-Deeps). Single Deep only.
5. **Freeze Deep**: Freeze the development-v2 artifact before any review begins.
6. **CRITIC REVIEW**: Reveal `references/deep-reviewer.md`. The critic independently evaluates the frozen developed model and freezes a deep-review-v2 record whose `terminal_state` is one of `{"MODEL_READY", "NEED_EVIDENCE", "RETURN_TO_EXPLORE"}`.
7. **Conditional LEVER Primitive**:
   - If `terminal_state == "MODEL_READY"` AND `task_orientation == "ACTION_OR_DECISION"`:
     Execute the same manual LEVER primitive (`references/lever.md` and `references/lever-reviewer.md`) using identical prompts and review logic as `/pizm lever`, with zero duplication.
   - Otherwise (if `task_orientation == "ANALYTICAL"` or `terminal_state != "MODEL_READY"`):
     Do not invoke LEVER.
8. **FINAL Assembly + run.md**: Assemble the final output deterministically from frozen artifacts (Section 3). You must archive the run via `bin/pizm-session-bundle create` providing the required ephemeral accounting input (`--accounting`). Then render the readable `run.md` deterministically with the session-bundle tool (`bin/pizm-session-bundle render --run-dir <run-dir> --task "<original task>"`). The renderer reads ONLY frozen checkpoint artifacts, emits byte-identical output for identical inputs, and performs zero model calls.
   - **Artifact & Suffix Chain**: Checkpoint artifacts follow the standard freeze chain: `candidates.json` (or `candidates-pass01.json`), `search-field.json` (or `search-field-pass01.json`), `portfolio.json`, `development-v2.json`, `deep-review-v2.json` (and optional `design.json` / `review.json`).
   - **Ephemeral Accounting Contract**: `--accounting <path>` supplies caller-provided bounded non-derived counts (`host_inference_count`, `model_repair_count`, `checkpoint_retry_count`). The bundle computes and validates derived counts (`semantic_stage_count`, `candidate_bytes`, `development_bytes`). The archive manifest records the normalized six-counter object; the ephemeral accounting file is never archived into inputs.

---

## 2. Honest-Stop Rules

If the Critic produces `terminal_state == "NEED_EVIDENCE"` or `terminal_state == "RETURN_TO_EXPLORE"`:
- Execution MUST stop honestly at that point with the stated reason from the review verdict.
- No other search or refinement primitive starts afterward (no second Deep, no alternative branch, no reroll, no auto-recovery).
- The pipeline proceeds directly to FINAL assembly to render the honest-stop report and its `run.md`.

---

## 3. Deterministic FINAL Assembly

`FINAL` is a DETERMINISTIC ASSEMBLY rendered directly from frozen structured artifacts (`candidates.json`, the search-field manifest, `portfolio.json`, `development.json`, `deep-review-v2.json`, and `design.json` / lever `review.json` if LEVER was executed).

- **Zero Model Invocations**: FINAL increments neither `semantic_stage_count` nor `host_inference_count` and performs ZERO tool-call model turns. The subsequent `run.md` rendering is equally deterministic: byte-identical output for identical frozen inputs, zero model calls.
- **Contract Prohibition**: If an implementation ever requires an additional model turn or tool call for FINAL or for `run.md` rendering, STOP and replan the budget/contract instead of hiding it.
- **Fixed Assembly Template**: The final response is formatted strictly using the fixed deterministic template below:

### Fixed FINAL Assembly Template

```markdown
# Pizm AUTO Analysis: <Task Title / Summary>

## 1. Nominated Perspective
- **Target**: <P<n> | B<n>> — <Title>
- **Source**: <auto_target nominated by the frozen portfolio record>
- **Task Orientation**: <ANALYTICAL | ACTION_OR_DECISION>
- **Core Claim / Shift**: <identity_lock claim / structural_shift>
- **Grounding Anchor**: <identity_lock grounding basis>
- **Boundary**: <identity_lock boundary>

## 2. Developed Model Summary
- **Thesis**: <developed_model.thesis>
- **Primary Mechanism**: <mechanism_chain or identity_lock mechanism>
- **Load-Bearing Claims**: <census claims with epistemic statuses>
- **Key Predictions**: <predictions_or_observables>
- **Evidence Debt**: <evidence_debt>

## 3. Deep Review Verdict
- **Terminal State**: <MODEL_READY | NEED_EVIDENCE | RETURN_TO_EXPLORE>
- **Review Rationale**: <verdict_rationale from the deep-review-v2 record>
<!-- IF terminal_state != "MODEL_READY": -->
- **Stop Reason**: Honest stop triggered due to non-ready status (<terminal_state>). No further primitives executed.
<!-- END IF -->

<!-- IF LEVER executed (task_orientation == "ACTION_OR_DECISION" AND terminal_state == "MODEL_READY"): -->
## 4. Reality-Facing Levers
<!-- For each accepted lever from the lever review: -->
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

After presenting FINAL, render `run.md` for the reading record: all candidate ideas appear compactly, the developed model and critic verdict are rendered fully enough for normal reading, and machine bookkeeping (hashes, schema strings, byte counts, repair/host counters) stays out of the readable document.

---

## 4. Operational Cost Accounting and Ceilings

### Semantic Stage Budget

- Base AUTO path: Generate + Portfolio + Deep + Critic = 4 semantic stages.
- Optional LEVER: Design + Review add 2 semantic stages = 6 semantic stages total.
- FINAL assembly and `run.md` rendering are deterministic: they add zero semantic stages.

### Accounting and Counters

The bundle archive manifest records all six normalized counters:
1. `semantic_stage_count` (derived from stage collection)
2. `host_inference_count` (caller-supplied non-derived counter)
3. `model_repair_count` (caller-supplied non-derived counter)
4. `checkpoint_retry_count` (caller-supplied non-derived counter)
5. `candidate_bytes` (derived from frozen candidate JSON byte sizes)
6. `development_bytes` (derived from frozen development JSON byte sizes)

### Repair Accounting

- Repairs and tool-loop continuations are accounted separately from the semantic stage budget.
- max 1 model repair per stage.
- max 2 model repairs across the entire AUTO run.
- No unbounded retries.
### Fail-Closed Budget Enforcement

If semantic stage or model repair ceilings are exhausted at any point:
- The run immediately terminates with `BUDGET_EXHAUSTED`.
- Fail-closed rule: Do not reveal unreached future-stage contracts or rubrics.
- Archive failure evidence and report `BUDGET_EXHAUSTED` with the exact stage reached.

---

## 5. Known Limitation Note (OBSERVE_IN_DOGFOOD)

In same-host execution, the Portfolio Judge and Deep DEVELOP see earlier stage context (generator prose, selector rubric) in conversation history. This is accepted as `OBSERVE_IN_DOGFOOD` per W0 reconciliation Risk 1:
- The judged field is always the hash-frozen artifact set, never loose conversation content.
- Deep DEVELOP remains structurally blind to its own Critic rubric until after the development-v2 artifact is frozen.
