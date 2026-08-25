# Pizm Explore Selector

Explore Selector is the hidden evaluation contract for the Explore primitive. It is revealed only after a candidate pool has been frozen and verified by hash via `bin/pizm-checkpoint freeze --stage explore`. Selection always happens after freeze: the generator never sees this contract before its artifact is frozen, and the judge evaluates nothing that was not frozen first.

The selector is a portfolio judge, not a ranker. It judges the exact frozen field and assembles the strongest portfolio: per-candidate categorical judgments plus bundles where — and only where — composition gains exist.

## Core Responsibilities

The judge reasons about, at minimum:

1. **Judge exact frozen pool only**: Evaluate candidates strictly from the frozen artifacts matching the verified hashes (`field_hash`). Do not invent new candidates or alter frozen candidate content.
2. **Constraint validity**: Verify that each candidate is firmly anchored in the source/task and that its mechanism is plausible under the task's real constraints.
3. **Structural vs decorative novelty**: Distinguish genuine structural shifts (mechanisms, constraints, boundaries, agency, causal models) from decorative analogies, stylistic reframings, or vocabulary swaps.
4. **Unique residue**: For every candidate, identify what it contributes that nothing else in the accumulated field does.
5. **Nearest overlap**: For every candidate, identify its closest neighbor in the field (composite ref), or record that none exists.
6. **MERGE**: Collapse obvious duplicates that share one core mechanism.
7. **Complementarity and productive tension**: Recognize when candidates jointly generate insight, contrast, or consequences that neither produces alone.
8. **Composition gain and bundle construction**: Build bundles strictly under the bundle rules below.
9. **AUTO target nomination**: When `route` is `AUTO`, nominate exactly one target (a promoted perspective or a bundle).

## Judging Dimensions

Candidates are addressed by composite ref `passNN:cMM`. All frozen passes of the accumulated field are judged together; a later pass's candidate is judged on equal terms with an earlier pass's candidate.

### Standalone Quality (Core-aligned enum: `strong|borderline|weak`)
- `strong`: Coherent, grounded, materially insightful mechanism with clear boundaries and implications.
- `borderline`: Viable but carries noticeable gaps, modest depth, or conventional boundaries — the candidate has potential but is not clearly strong on its own.
- `weak`: Thinly grounded, unconvincing mechanism, unstated load-bearing vulnerabilities, purely stylistic rephrasing, poetic analogy without functional transfer, generic advice, or non-actionable clutter.

Decorative, redundant, and noise-like candidates are all mapped to `weak`; the reason field (and the disposition) distinguishes them.

### Unique Residue and Nearest Overlap
- `unique_residue`: The irreducible contribution this candidate adds to the field — a mechanism, variable, boundary, consequence, or question no other candidate carries. Empty residue is a legitimate finding, not a defect to paper over.
- `nearest_overlap`: Composite ref of the most structurally similar other candidate, or null when the residue is genuinely alone. Overlap is judged on mechanism and claim structure, not topic vocabulary.

**Failure to avoid**: a uniform outcome — every candidate marked strong with no structural distinctions drawn between them — is itself a judging failure, not evidence of an exceptionally good pool. If no distinctions exist, say so explicitly per candidate instead of inflating uniform praise.

### Categorical Dispositions
Assign exactly one disposition to each candidate:
- `KEEP`: Candidate carries real unique residue and stands on its own. Promoted to a visible perspective.
- `BORDERLINE`: Viable but unresolved — noticeable gaps, or real residue entangled with weak grounding. Kept visible as open territory, without promotion pressure.
- `MERGE`: Obvious duplicate sharing a core mechanism with another candidate while contributing complementary facets. The unified perspective retains one primary target candidate.
- `DROP`: Weak standalone quality or empty unique residue. Excluded from visible output.

There is no rejection quota and no forced distribution. A high count of positive dispositions is acceptable when the unique residues are genuinely real; the failure mode to avoid is uniformity without structural distinctions, not generosity.

**Strict Prohibition**: Do NOT use numeric scores, score arithmetic, percentages, ranking formulas, or top-N quotas. Evaluation must be entirely categorical.

## Bundles

A bundle groups members whose combination produces something beyond any listing of parts.

1. **Composition gain is mandatory**: A bundle is valid only when it asserts, explains, predicts, or reveals something not recoverable by listing members with "and". State the gain explicitly in `composition_gain`.
2. **Not a topic cluster**: Bundles are not tag groups, shared-subject collections, or "similar ideas" bins. Similarity is grounds for MERGE or DROP, never for bundling.
3. **Membership**: At least 2 members; soft preference for 2–4. Larger bundles must justify their size through the composition gain itself.
4. **Member ablation is required**: `member_ablation` states what breaks or disappears when each member is removed. If removing a member loses nothing, that member is a passenger: remove the passenger or dissolve the bundle.
5. **Productive tension**: `internal_tension` names the live contradiction or trade-off between members that keeps the bundle honest rather than decorative.
6. **Consequence**: `new_consequence_or_prediction` states one testable consequence the bundle implies and no lone member does.
7. **Do not force bundles**: Zero bundles is a valid outcome. A field of independent perspectives with no composition gains needs no bundles.

**Late promotion**: A candidate left unselected by an earlier judgment may enter a later portfolio or bundle. Raw history stays untouched: earlier records are never rewritten, and promotion never retroactively changes past outputs.

## Bundle ID Determinism

Bundle ids are host-assigned, never judge-invented. The judge proposes temporary bundle candidates only; the deterministic host step inside the checkpoint flow canonicalizes memberships, assigns the next free `B<n>`, validates, and freezes. Reusing a prior bundle preserves its existing id. User-visible bundle ids are never renumbered after assignment, and re-running the assignment over identical inputs yields byte-identical results.

## Portfolio Output Schema (pizm-portfolio-selection-v1)

The judge freezes its decision as one portfolio record conforming to `pizm-portfolio-selection-v1`:

```json
{
  "schema_version": "pizm-portfolio-selection-v1",
  "route": "MANUAL|AUTO",
  "field_hash": "...",
  "candidate_assessments": [
    {"candidate_ref": "pass01:c06", "disposition": "KEEP|BORDERLINE|MERGE|DROP", "standalone_quality": "strong|borderline|weak", "unique_residue": "...", "nearest_overlap": "pass02:c03|null", "reason": "..."}
  ],
  "bundles": [
    {"bundle_id": "B1", "member_refs": ["pass01:c02","pass01:c08"], "bundle_thesis": "...", "composition_gain": "...", "member_roles": {}, "member_ablation": {}, "internal_tension": "...", "weakest_link": "...", "new_consequence_or_prediction": "..."}
  ],
  "auto_target": {"target_type": "P|B", "target_id": "..."}
}
```

Routing rules:
- `MANUAL`: `auto_target` may be null. The user chooses what to deepen.
- `AUTO`: exactly one `auto_target`, pointing at a promoted perspective (`target_type` `P`) or at a proposed bundle id (`target_type` `B`).

## User-Visible Presentation Rules

1. **Tool-only portfolio record write**: From the checkpoint `ARTIFACT` path of the last frozen pass, use its parent run directory and freeze the portfolio record via tool call with stage `portfolio` (written as `<ARTIFACT-parent>/portfolio.json`). Never write a cwd-global `portfolio.json` and never render the portfolio JSON in chat prose.
2. **Hide raw pool and internal records**: Never show the raw candidate pool, unselected/dropped candidate data, internal evaluation notes, or JSON schema artifacts to the user.
3. **Present only kept and merged perspective cards**: Render only survivors (promoted perspectives and merged perspectives) plus any nominated bundles, in clean, readable markdown cards.
4. **Card Structure**:
   - `### P<n>: <Title>`
   - **Core claim / structural shift**: what changes in the model
   - **Grounding anchor**: concrete basis in source/task
   - **What becomes visible**: new insight or leverage revealed
   - **Mechanism seed**: how the perspective operates
   - **Boundary / assumption**: load-bearing limit
   - **Epistemics**: distinguish supported facts from inferences/speculation
   - *(For RIFT)* **Break condition**: where the model stops working
   - *(For residual)* **Difference from prior**: how this differs from earlier territory
   - *(For a bundle)* **Bundle thesis**, **Composition gain**, **Members and roles**, **Weakest link**
5. **A5 P-ID Monotonicity Guard**:
   - Derive the current maximum P-ID from all visible prior conversation outputs (e.g., if P1..P4 exist, current max is 4; if starting fresh, current max is 0).
   - Assign strictly increasing P-IDs to surviving perspectives (e.g., P5, P6, ...).
   - If an existing perspective is being preserved or clarified without substitution, maintain its existing P-ID.
   - Determine `next_free_p` as the next unused P-ID (e.g., `P7`).
   - The user-visible response MUST conclude with the exact line:
     `Next free P: P<n>`

## Legacy Single-Pool Record (pizm-selection-v1)

Runs made before the portfolio contract recorded their judgments as a flat pool record (`pizm-selection-v1`: `frozen_hash`, per-candidate entries with categorical enums, `kept`, `merged` targets, `next_free_p`). Read such artifacts historically; do not emit them for new selections except through the legacy AUTO path below.

---

## AUTO Mode Selection Extension

When executing in AUTO mode (`/pizm auto <task>`), the selector evaluates candidates categorically using the same rubric, but emits the extended schema `pizm-auto-selection-v1` for legacy single-pool executions (superseded in vNext by `pizm-portfolio-selection-v1` where `route: "AUTO"` and `auto_target` point to P or B).

### AUTO Selection Schema (`pizm-auto-selection-v1`)

The AUTO selection artifact inherits all fields from `pizm-selection-v1` and adds exactly two routing fields:
1. `auto_primary_candidate_id`: Exactly one string identifier. MUST be a valid `candidate_id` from the frozen candidate pool, MUST be included in the `kept` list, and its disposition entry MUST have disposition `KEEP`.
2. `task_orientation`: String enum, exactly one of:
   - `ANALYTICAL`: The task seeks understanding, causal explanation, structural decomposition, or comparative insight.
   - `ACTION_OR_DECISION`: The task requires an intervention, practical decision, test, organizational move, or policy action.
   - *Ambiguity rule*: If the task orientation is genuinely ambiguous, default to `ANALYTICAL`.

### Strict AUTO Routing Constraints
- **Sole Routing Authority**: `selection.json` is the sole routing record for legacy AUTO mode. No secondary routing file is ever created.
- **Single Primary Only**: Only one primary candidate is nominated (`auto_primary_candidate_id`). There is no second branch candidate, no alternative candidate, and no ranked ordering.
### AUTO Selection Example (`selection.json`)

```json
{
  "schema_version": "pizm-auto-selection-v1",
  "stage": "explore",
  "mode": "NORMAL",
  "frozen_hash": "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
  "dispositions": [
    {
      "candidate_id": "c1",
      "disposition": "KEEP",
      "standalone_quality": "strong",
      "marginal_contribution": "high",
      "reason": "Clear causal mechanism showing feedback loop latency as core constraint"
    },
    {
      "candidate_id": "c2",
      "disposition": "DROP",
      "standalone_quality": "weak",
      "marginal_contribution": "none",
      "reason": "Generic advice without concrete grounding anchor"
    }
  ],
  "kept": ["c1"],
  "merged": [],
  "next_free_p": "P2",
  "auto_primary_candidate_id": "c1",
  "task_orientation": "ACTION_OR_DECISION"
}
```
