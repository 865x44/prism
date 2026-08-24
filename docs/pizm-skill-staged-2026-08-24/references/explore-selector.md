# Pizm Explore Selector

Explore Selector is the hidden evaluation contract for the Explore primitive. It is revealed only after a candidate pool has been frozen and verified by hash via `bin/pizm-checkpoint freeze --stage explore`.

## Core Responsibilities

1. **Judge exact frozen pool only**: Evaluate candidates strictly from the frozen artifact matching the verified hash. Do not invent new candidates or alter frozen candidate content.
2. **Enforce task constraints and grounding**: Verify that each candidate is firmly anchored in the source/task and that its mechanism is plausible.
3. **Detect structural vs decorative novelty**: Distinguish genuine structural shifts (mechanisms, constraints, boundaries, agency, causal models) from decorative analogies, stylistic reframings, or vocabulary swaps.
4. **Detect redundancy**: Identify paraphrases, overlapping mechanisms, or generic platitudes across candidates.
5. **Construct strong survivor set with adaptive count**: Retain only candidates that offer distinct value. There is no fixed quota; select fewer when candidate quality is low and more only when candidates are genuinely independent.

## Categorical Evaluation Rubric

Every candidate must receive categorical judgments on two orthogonal dimensions:

### Standalone Quality (Core-aligned enum: `strong|borderline|weak`)
- `strong`: Coherent, grounded, materially insightful mechanism with clear boundaries and implications.
- `borderline`: Viable but carries noticeable gaps, modest depth, or conventional boundaries — the candidate has potential but is not clearly strong on its own.
- `weak`: Thinly grounded, unconvincing mechanism, unstated load-bearing vulnerabilities, purely stylistic rephrasing, poetic analogy without functional transfer, generic advice, or non-actionable clutter.

Decorative, redundant, and noise-like candidates are all mapped to `weak`; the reason field (and the disposition) distinguishes them.

### Marginal Contribution (Core-aligned enum: `high|medium|low|none`)
- `high`: Explores genuinely new semantic territory or an independent causal mechanism not covered by others.
- `medium`: Adds meaningful variation, nuance, or complementary facet to another candidate without fully overlapping it.
- `low`: Minor incremental variation or localized refinement that mostly duplicates another candidate's core claim or mechanism.
- `none`: Substantially duplicates another candidate, adds confusion, ungrounded speculation, or non-actionable clutter.

Redundant and noise-like candidates receive `low` or `none`; the reason field (and the disposition) disambiguates.

### Categorical Dispositions
Assign exactly one disposition to each candidate:
- `KEEP`: Candidate has `strong` standalone quality and `high` or `medium` marginal contribution. Promoted to a visible perspective.
- `BORDERLINE`: Candidate has `borderline` standalone quality, or `strong` quality with only `low` marginal contribution. Kept only if the pool lacks better coverage in that territory.
- `MERGE`: Combines with one or more related candidates when they share a core mechanism but offer complementary facets (typically `medium` marginal contribution but overlapping core claims). The unified perspective retains one primary `target` candidate.
- `DROP`: Candidate has `weak` standalone quality or `none` marginal contribution. Excluded from visible output.

**Strict Prohibition**: Do NOT use numeric scores, score arithmetic, percentages, ranking formulas, or top-N quotas. Evaluation must be entirely categorical.

## Mode-Specific Selection Criteria

### NORMAL
- Filter for practically useful, materially distinct perspectives that shift the user's framing.
- Drop generic advice, superficial summaries, and platitudes.
- Merge perspectives that describe the same core mechanism under different angles.

### 360
- Explicitly judge novelty relative to prior visible territory and reconstructed prior semantic cores.
- Verify `difference_from_prior`: reject candidates that merely re-hash previously explored perspectives under new names.
- Ensure survivors represent distinct outer-shell semantic territories.

### RIFT
- Evaluate actual functional transfer and structural shift from the donor domain, not just vocabulary or poetic analogy.
- Verify that `functional_mapping` and `return_path` hold under scrutiny.
- Ensure the `break_condition` identifies the genuine failure boundary of the analogy/shift.

## Selection Output Schema (selection.json)

The selector produces a compact JSON record conforming to `pizm-selection-v1`:

```json
{
  "schema_version": "pizm-selection-v1",
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
  "next_free_p": "P<n>"
}
```

## User-Visible Presentation Rules

1. **Tool-only selection.json write**: From the checkpoint `ARTIFACT` path, use its parent run directory and write `<ARTIFACT-parent>/selection.json` via tool call (not visible to user). Never write a cwd-global `selection.json` and never render the selection JSON in chat prose.
2. **Hide raw pool and internal records**: Never show the raw candidate pool, unselected/dropped candidate data, internal evaluation notes, or JSON schema artifacts to the user.
3. **Present only kept and merged perspective cards**: Render only survivors (KEPT and MERGED perspectives) in clean, readable markdown cards.
4. **Card Structure**:
   - `### P<n>: <Title>`
   - **Core claim / structural shift**: what changes in the model
   - **Grounding anchor**: concrete basis in source/task
   - **What becomes visible**: new insight or leverage revealed
   - **Mechanism seed**: how the perspective operates
   - **Boundary / assumption**: load-bearing limit
   - **Epistemics**: distinguish supported facts from inferences/speculation
   - *(For RIFT)* **Break condition**: where the model stops working
   - *(For 360)* **Difference from prior**: how this differs from earlier territory
5. **A5 P-ID Monotonicity Guard**:
   - Derive the current maximum P-ID from all visible prior conversation outputs (e.g., if P1..P4 exist, current max is 4; if starting fresh, current max is 0).
   - Assign strictly increasing P-IDs to surviving perspectives (e.g., P5, P6, ...).
   - If an existing perspective is being preserved or clarified without substitution, maintain its existing P-ID.
   - Determine `next_free_p` as the next unused P-ID (e.g., `P7`).
   - The user-visible response MUST conclude with the exact line:
     `Next free P: P<n>`
