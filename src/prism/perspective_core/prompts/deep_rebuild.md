# Deep Rebuild Prompt

## Purpose

Rebuild a developed perspective to address specific review feedback. This is a
bounded single call that returns both a rebuilt development and a terminal review.

This is the final semantic stage. There is no fourth call. If the rebuild itself
requests another rebuild, the system resolves this to RETURN_TO_EXPLORE.

## Input

- Source material
- Session objective
- Immutable identity core (must be echoed exactly)
- Active constraints
- Previous development
- Review feedback with specific rebuild instructions

## Output Schema: DeepRebuildResult

```json
{
  "development": {
    "p_id": "string",
    "semantic_lock_echo": "object — exact copy of identity core",
    "developed_model": "string — rebuilt model",
    "what_became_more_precise": ["list"],
    "assumptions": ["list"],
    "supporting_basis": ["list"],
    "evidence_missing": ["list"],
    "unknowns": ["list"],
    "strongest_countermodel": "string or null",
    "break_conditions": ["list"],
    "downstream_implications": ["list"],
    "optional_analysis": "object or null"
  },
  "final_review": {
    "identity_preserved": "boolean",
    "identity_drift": ["list"],
    "load_bearing_claim": "string",
    "strongest_objection": "string",
    "objection_target": "string",
    "objection_is_load_bearing": "boolean",
    "counterevidence": ["list"],
    "evidence_debt": ["list — must carry forward prior evidence debt"],
    "rebuild_required": false,
    "rebuild_instructions": [],
    "terminal_state": "MODEL_READY | NEED_EVIDENCE | RETURN_TO_EXPLORE",
    "rationale": "string"
  }
}
```

## Invariants

1. The identity core MUST be preserved exactly in `semantic_lock_echo`.
2. Evidence debt from the original development MUST be carried forward unless
   explicitly resolved by the rebuild.
3. `rebuild_required` in `final_review` MUST be false — no recursive rebuild.
4. This is the terminal gate; the final_review determines the terminal state.
