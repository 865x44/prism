# Deep Review Prompt

## Purpose

Critically review a developed perspective. The review evaluates identity preservation,
load-bearing objections, counterevidence, evidence debt, and whether a bounded rebuild
is needed. The review assigns a terminal state.

## Input

- Source material
- Session objective
- Immutable identity core
- Developed model (from DEEP_DEVELOP)
- Identity echo mismatch flag (if any)

## Output Schema: DeepReview

```json
{
  "identity_preserved": "boolean — does the development preserve the identity core?",
  "identity_drift": ["list of specific drift points if any"],
  "load_bearing_claim": "string — the central claim being evaluated",
  "strongest_objection": "string — the strongest objection to the model",
  "objection_target": "string — what the objection targets",
  "objection_is_load_bearing": "boolean — does the objection undermine the central mechanism?",
  "counterevidence": ["list of contradicting evidence"],
  "evidence_debt": ["list of evidence still missing after development"],
  "rebuild_required": "boolean — does the development need a bounded rebuild?",
  "rebuild_instructions": ["list of specific rebuild instructions"],
  "terminal_state": "MODEL_READY | NEED_EVIDENCE | RETURN_TO_EXPLORE",
  "rationale": "string — justification for the terminal state"
}
```

## Terminal State Semantics

- **MODEL_READY**: The developed model is sound, identity is preserved, and no
  load-bearing objections remain unaddressed. Evidence debt is acknowledged but
  does not block the model.
- **NEED_EVIDENCE**: The model is structurally sound but critical evidence gaps
  prevent a definitive assessment. The model cannot proceed without evidence
  resolution.
- **RETURN_TO_EXPLORE**: The model has fundamental issues — identity drift,
  load-bearing objection that cannot be resolved by rebuild, or the perspective
  itself may need to be reconsidered from the explore phase.

## Invariants

1. If identity_echo_mismatch is true, `identity_preserved` MUST be false.
2. A load-bearing objection (`objection_is_load_bearing: true`) that cannot be
   addressed by rebuild should result in RETURN_TO_EXPLORE.
3. `rebuild_required: true` means a single bounded rebuild may resolve issues.
4. `rebuild_required` must be false if terminal_state is RETURN_TO_EXPLORE.
