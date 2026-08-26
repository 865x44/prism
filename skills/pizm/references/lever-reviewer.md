# Pizm LEVER Reviewer

LEVER Reviewer is the hidden adversarial review contract for the LEVER primitive. It is revealed only after a lever design artifact has been frozen and verified by hash via `bin/pizm-checkpoint freeze --stage lever-design`.

## Input

The reviewer receives exactly:
1. **Frozen design artifact**: the exact JSON artifact matching the verified hash from the checkpoint output.
2. **Locked developed model**: the visible `MODEL_READY` developed model (title, core claim, mechanism, constraints, predictions) from the active conversation.
3. **Current context**: source materials and conversation context already accessible to the host.

Do NOT use, reference, or construct external registries, persistent storage, or external tools.

## Mandatory Checks and Reject Rules

Evaluate each candidate lever in `levers` against the mandatory criteria below. If any mandatory check fails for a candidate, reject that candidate with an explicit reason.

### 1. MODEL DEPENDENCE
- Core question: **"If the developed model disappeared, could essentially the same recommendation be written? YES → reject"**
- The lever must directly require the developed model's specific causal claims or structural shifts. Generic business advice, best-practice platitudes, or universal heuristics that do not depend on the specific model must be rejected.

### 2. LOAD-BEARING LINK
- The move must touch a variable, relationship, constraint, or prediction that is load-bearing for the developed model.
- If the move only affects peripheral or cosmetic factors without engaging the core mechanism, reject.

### 3. BOUNDEDNESS AND RISK HONESTY
- The move must be the minimal bounded action or probe that yields a decisive signal.
- Reversible where domain permits; otherwise explicit risk/boundary statement instead of fake reversibility. Do not accept claims of "low-risk reversibility" when the domain is intrinsically irreversible; require an honest risk boundary instead.

### 4. DISCRIMINATION
- The expected observation and disconfirming signal must genuinely discriminate between the model being right vs. wrong.
- If observing the outcome would teach nothing decision-relevant or model-relevant, reject.

### 5. ADAPTATION (Conditional)
- Check `adaptation_or_countermove` only when structurally relevant (e.g., adaptive agents, competitive dynamics, game-theoretic interactions).
- For static, mechanical, or physical domains where countermoves do not exist, omit or accept absence without penalty.

### 6. OBSERVABLE STOP RULE
- The `stop_condition` must define concrete, observable triggers to continue, revise, or abandon the move.
- Vague or unobservable stop criteria must be rejected.

### 7. GOAL AND LEVEL ALIGNMENT
- Check the goal reading and structural level reading embedded in `model_link`: does the move target what participants actually enact (STATED GOAL vs ENACTED GOAL), and the structural relation that generates the outcome rather than its visible knob (APPARENT LEVER vs ACTUAL STRUCTURAL LEVEL)? A lever that pushes the INTUITIVE direction while the model's structure implies the opposite push, without acknowledging the divergence, must be rejected.

### 8. CONTROL ZONE HONESTY
- Each accepted lever's intervention point must carry an honest control-zone classification: `CAN_CHANGE` (directly actionable), `CAN_INFLUENCE` (indirectly movable), or `MUST_ACCOUNT_FOR` (fixed constraint). Misclassifying a fixed constraint as changeable — or an influenceable node as directly changeable — rejects the candidate.

## Anti-Cargo-Cult Clause

The lenses above are analytic aids for evaluation, not quotas. There is no required number of lens applications per lever and no required vocabulary in the design artifact. If the developed model genuinely supports no useful application of any candidate, `NO_DEFENSIBLE_LEVER` is the correct outcome — do not manufacture levers to appear thorough. These extensions introduce no new agents, modes, or stages.

## Top-Level Outcomes

Return exactly one of two top-level outcomes:
- `LEVER`: At least one candidate lever satisfies all mandatory checks and is accepted.
- `NO_DEFENSIBLE_LEVER`: All candidate levers failed one or more mandatory checks, and no defensible reality-facing move can be derived from the current model.

## Review Output Schema (pizm-lever-review-v1)

The reviewer produces a compact JSON record conforming to `pizm-lever-review-v1`:

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

## User-Visible Presentation Rules

1. **Tool-only review.json write**: Write the review JSON to the run directory and freeze via checkpoint tool call. Never render raw JSON in chat prose.
2. **Hide raw artifacts**: Never show raw design JSON, review JSON, or internal evaluation notes to the user.
3. **Present defensible levers**: If `outcome == "LEVER"`, render accepted levers in clear, structured prose with their intervention point, minimal bounded move, expected observations, disconfirming signals, and stop conditions.
4. **Present honest stop**: If `outcome == "NO_DEFENSIBLE_LEVER"`, explain clearly why the current model does not support a defensible reality-facing intervention or probe without generic padding.
