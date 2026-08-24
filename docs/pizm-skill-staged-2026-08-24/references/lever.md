# Pizm LEVER

LEVER is the reality-facing intervention and test primitive for Pizm. It operationalizes a `MODEL_READY` developed perspective into 1–3 bounded, reality-facing intervention or probe candidates through staged blind design and adversarial review.

Topology: `LEVER_DESIGN → FREEZE → reveal LEVER_REVIEW → LEVER_REVIEW → deterministic render`

## Preconditions and Routing

LEVER operates exclusively on a completed Deep branch whose review artifact has verified `terminal_state: MODEL_READY`.

Blocked cases produce **zero** lever semantic stages:
1. **Unknown or stale P-ID**: If the requested P-ID is unknown, ambiguous, or stale in the conversation, return a deterministic error listing available branches without executing LEVER.
2. **Bare `/pizm lever`**: Bare `/pizm lever` is allowed ONLY when exactly one unambiguous `MODEL_READY` branch exists in the active conversation. If multiple `MODEL_READY` branches exist without an explicit P-ID, return a deterministic refusal listing ready branches.
3. **Non-ready Deep status**: If the selected Deep branch has `terminal_state` `NEED_EVIDENCE` or `RETURN_TO_EXPLORE`, LEVER execution is blocked. Return a deterministic refusal explaining that only `MODEL_READY` perspectives can be operationalized into levers.

## Generator Workflow (LEVER_DESIGN)

**Pre-freeze future-contract prohibition:** Until the checkpoint returns `FREEZE_OK`, do not read, open, search, list, inspect, or otherwise access any future-stage contract or reference asset (including `references/lever-reviewer.md`). Use only this loaded pre-freeze contract and the visible conversation context. If a future-stage contract is exposed prematurely, stop the pass and report the separation failure.

1. Analyze the locked `MODEL_READY` developed model from the conversation context.
2. Identify 1–3 high-leverage reality-facing intervention points or test probes directly derived from the model's load-bearing causal mechanisms and constraints.
3. Format candidates conforming to the `pizm-lever-design-v1` schema.
4. **Tool-only pre-freeze turn**: Write the design JSON to a temporary file, then invoke the freeze command via bash. Emit ZERO visible prose in this turn — no summaries, commentary, or intermediate output. Use a timestamp or random lowercase alphanumeric slug for `--run-id`.
   ```bash
   $HOME/.local/bin/pizm-checkpoint freeze --stage lever-design --run-id <slug> --input <path>
   ```
5. On successful freeze, checkpoint confirms `FREEZE_OK` and reveals only the reference path `references/lever-reviewer.md` (never its rubric content).

### Bounded Retry and Repair Budget

- Normal path: write design JSON and invoke checkpoint once.
- Max 1 model repair for Manual LEVER: If the checkpoint execution fails (e.g., schema validation failure), perform at most ONE bounded correction attempt: fix the JSON artifact, re-write, and invoke checkpoint a second time.
- If the second attempt fails, stop execution without further retries and report the failure.

## Design Schema (pizm-lever-design-v1)

The design artifact must conform to `pizm-lever-design-v1`:

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

### Schema Rules

- `schema_version`: Must be `"pizm-lever-design-v1"`.
- `stage`: Must be `"lever"`.
- `levers`: Array of 1 to 3 lever objects.
- `lever_id`: Unique non-empty string for each lever (e.g., `"L1"`, `"L2"`, `"L3"`).
- Required fields (non-empty strings): `lever_id`, `intervention_or_test_point`, `model_link`, `minimum_bounded_move`, `expected_observation_or_response`, `disconfirming_signal`, `stop_condition`, `remaining_assumptions`.
- Optional field: `adaptation_or_countermove` (string). Include ONLY when the domain involves strategic agents, feedback loops, or dynamic adaptation. Omit or leave absent for static/mechanical systems.
- Maximum serialized payload: 65536 bytes (64 KiB). Exceeding this limit causes fail-closed rejection (`PAYLOAD_TOO_LARGE`).

## Review Turn and Execution (LEVER_REVIEW)

1. Read `references/lever-reviewer.md` ONLY after design freeze confirmation (`FREEZE_OK`).
2. Evaluate the frozen design artifact against the adversarial review rubric.
3. Write `review.json` conforming to `pizm-lever-review-v1` and freeze:
   ```bash
   $HOME/.local/bin/pizm-checkpoint freeze --stage lever-review --run-id <slug> --input <path>
   ```
4. Render the final outcome deterministically in user-facing prose based on the review outcome (`LEVER` or `NO_DEFENSIBLE_LEVER`).
