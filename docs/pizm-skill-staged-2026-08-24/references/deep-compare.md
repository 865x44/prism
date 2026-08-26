# Pizm Comparative Reviewer

In FORGE execution with two defensible Bundles, the comparative reviewer executes adversarial comparison ONLY after BOTH `development-v2-<left_target_id>` and `development-v2-<right_target_id>` artifacts have been frozen and verified by hash.

---

## Comparator Role

The comparator acts simultaneously as:
1. **Critic of LEFT**: independent reassessment of the LEFT candidate using the 8-move Critic arsenal.
2. **Critic of RIGHT**: independent reassessment of the RIGHT candidate using the 8-move Critic arsenal.
3. **Comparative Reasoner**: evaluating the load-bearing competition axis, identifying discriminating observations, and determining relative explanatory power without manufactured winners.

---

## Comparison Output Schema (pizm-comparison-review-v1)

```json
{
  "schema_version": "pizm-comparison-review-v1",
  "stage": "comparison-review-v1",
  "task_summary": "Summary of the original task",
  "left_target_id": "B3",
  "right_target_id": "B7",
  "left_review": {
    "target_id": "B3",
    "development_ref": "development-v2-B3.json",
    "frozen_hash": "<sha256>",
    "terminal_state": "MODEL_READY|NEED_EVIDENCE|RETURN_TO_EXPLORE",
    "findings": {
      "unresolved_load_bearing_contradiction": false,
      "unsupported_specificity": ["..."],
      "epistemic_laundering": ["..."]
    },
    "load_bearing_reassessment": [
      {
        "claim": "...",
        "critic_epistemic_status": "SUPPORTED|INFERRED|SPECULATIVE|UNKNOWN"
      }
    ],
    "independent_countermodel": "critic countermodel against LEFT",
    "evidence_debt": ["..."],
    "verdict_rationale": "..."
  },
  "right_review": {
    "target_id": "B7",
    "development_ref": "development-v2-B7.json",
    "frozen_hash": "<sha256>",
    "terminal_state": "MODEL_READY|NEED_EVIDENCE|RETURN_TO_EXPLORE",
    "findings": {
      "unresolved_load_bearing_contradiction": false,
      "unsupported_specificity": ["..."],
      "epistemic_laundering": ["..."]
    },
    "load_bearing_reassessment": [
      {
        "claim": "...",
        "critic_epistemic_status": "SUPPORTED|INFERRED|SPECULATIVE|UNKNOWN"
      }
    ],
    "independent_countermodel": "critic countermodel against RIGHT",
    "evidence_debt": ["..."],
    "verdict_rationale": "..."
  },
  "comparison": {
    "current_preference": "LEFT|RIGHT|CONDITIONAL|UNRESOLVED",
    "competition_axis": "Load-bearing axis where the models diverge",
    "strongest_reason_for_left": "Why LEFT may be correct",
    "strongest_reason_for_right": "Why RIGHT may be correct",
    "shared_evidence_debt": ["Unresolved empirical questions affecting both models"],
    "discriminating_observation": "The observation or test that would discriminate LEFT from RIGHT",
    "what_would_change_the_decision": "What specific evidence would reverse or resolve the preference"
  }
}
```

---

## Comparative Decision Rules

- **No Forced Winner:** `CONDITIONAL` and `UNRESOLVED` are first-class terminal states.
- **Blocking Preference:** If the LEFT review has an unresolved load-bearing contradiction (`unresolved_load_bearing_contradiction: true`) or `terminal_state: "RETURN_TO_EXPLORE"`, `current_preference: "LEFT"` is rejected. The same applies symmetrically to RIGHT.
- **Discriminating Observation Required:** `discriminating_observation` and `what_would_change_the_decision` must be non-empty strings.
- **Payload Ceiling:** Maximum serialized payload 131072 bytes (128 KiB); exceeding it causes fail-closed rejection.
- **Freeze Command:**
  ```bash
  $HOME/.local/bin/pizm-checkpoint freeze --stage comparison-review-v1 --run-id <slug> --input <pending-json-path>
  ```

---

## External State Prohibition

The reviewer must never reference any external state, registry, or persistent storage. All inputs come from the frozen artifact hash and the visible conversation context only.
