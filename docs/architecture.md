# Prism Architecture

Prism is a semantic exploration and model-development architecture designed for structured divergence, synthesis, adversarial evaluation, and actionable leverage.

This document describes the current system architecture, stage contracts, execution topologies, and structural boundaries.

---

## 1. Search Policies & Candidate Generation

Search (invoked as Search or Explore) is the divergence primitive in Prism. It expands the space of materially distinct, grounded models of a problem before committing to any single branch.

### Search Policies

Every Search pass executes exactly one search policy:

1. **`initial` (NORMAL)**: Broad structural divergence across the problem space. When supported by source material, target is roughly 12–16 compact candidate seeds. Hard safety bounds: 1..20 candidates, $\le 192\text{ KiB}$ total candidate payload, $\le 12\text{ KiB}$ per candidate.
2. **`residual` (360)**: Novelty search directed explicitly away from accumulated prior perspectives and developed directions. Identifies uncharted territory against the registered search field. (*Note: `360` is a deprecated compatibility alias for the residual search policy*).
3. **`rift` (RIFT)**: Distant, non-obvious structural reframings that strictly preserve the underlying operational mechanism of the source while rejecting decorative or metaphorical analogies. Manual-only trigger.

*Terminology note: "Breadth" is superseded terminology and is not a user mode. "MAX" is superseded and eliminated as a product route.*

### Search Field Manifest

Search candidates conform to `pizm-candidates-v1` (`candidates-passNN.json`). All passes within an exploration trajectory register in the append-only search-field manifest conforming to `pizm-search-field-v1` (`search-field-passNN.json`). Candidates are addressed by composite reference `passNN:cMM`.

---

## 2. Portfolio & Bundle Identities

The Portfolio Judge evaluates the accumulated search field after candidate freezing. Selection is strictly post-freeze: the generator is structurally blind to selector rubrics until the candidates are frozen.

### Evaluation Dimensions

The judge evaluates candidates across categorical dimensions without numeric scoring or rank formulas:
- **Standalone Quality**: `strong`, `borderline`, or `weak`.
- **Unique Residue**: The irreducible mechanism, variable, or consequence added to the field.
- **Nearest Overlap**: Structural neighbor composite reference, or null.
- **Dispositions**: `KEEP` (promoted to visible perspective), `BORDERLINE` (open territory), `MERGE` (duplicate collapsed into primary target), `DROP` (excluded).

### Bundles & B-IDs

A Bundle ($B\langle n\rangle$) groups complementary perspectives where composition gains exist:
- **Mandatory Composition Gain**: A bundle must assert, explain, or predict dynamics not recoverable by joining members with "and". Topic clusters and subject categories are strictly forbidden.
- **Deterministic Allocator**: Bundle identifiers ($B1, B2, \dots$) are allocated deterministically based on sorted member references.
- **Member Ablation**: Every bundle specifies what breaks or disappears when each member is removed.
- **Internal Tension & Prediction**: Specifies the live tradeoff between members and a testable consequence implied only by the combination.

### Portfolio Schemas

- **`pizm-portfolio-selection-v1`**: Used in manual exploration and AUTO (`route: "MANUAL"|"AUTO"`). In AUTO, nominates exactly one target (`auto_target`: single $P\langle n\rangle$ or $B\langle n\rangle$).
- **`pizm-portfolio-selection-v2`**: Used in FORGE (`route: "FORGE"`). Specifies `competition_status`: either `TWO_DEFENSIBLE_BUNDLES` with `recommended_competition` (`left_bundle_id`, `right_bundle_id`, `competition_axis`, `discriminating_observation`) or `NO_SECOND_DEFENSIBLE_BUNDLE` with `single_target`.

---

## 3. Deep Model Development (v2)

Deep develops a selected perspective ($P\langle n\rangle$), composed bundle ($B\langle n\rangle$), or direct seed into a mature, testable causal model conforming to `pizm-development-v2`.

### Development Contract

- **Target Scope**: Exactly one target per development artifact. For a bundle target ($B\langle n\rangle$), one bundle equals one Deep pass (never split into per-member mini-Deeps).
- **Identity Lock**: Strictly preserves semantic identity (`p_id` or bundle `member_refs`). Fail-closed against silent topic drift.
- **Analytical Depth**: Comprehensive prose synthesis (~900–1600 words for single perspectives, ~1400–2400 words for bundles).
- **Required Model Structure**: Core thesis, mechanism chain, generative dynamic, boundary conditions, load-bearing claims census ($2..5$ claims with epistemic statuses: `SUPPORTED`, `INFERRED`, `SPECULATIVE`), break conditions, and observable predictions.

---

## 4. Critic & Comparative Review

The Critic provides independent adversarial reassessment of frozen development models. The developer role is blind to the critic rubric until the development artifact freezes.

### Single-Model Critic (`pizm-deep-review-v2`)

The critic inspects the model independently without adopting developer self-assessments:
- **Mandatory Checks**: Identity verification, cross-field contradictions, independent audit of load-bearing claims, detection of unsupported specificity, and exposure of epistemic laundering.
- **Terminal States**:
  - `MODEL_READY`: Sound, robust causal model with verified identity and defensible claims.
  - `NEED_EVIDENCE`: Promising model blocked by unverified claims or unsupported specificity.
  - `RETURN_TO_EXPLORE`: Fundamental identity drift, fatal contradiction, or indefensible core mechanism.

### Comparative Review (`pizm-comparison-review-v1`) & Delayed Reveal Seam

In dual-competition FORGE execution:
- **Delayed Reveal**: The comparative contract (`references/deep-compare.md`) is structurally hidden and revealed ONLY after BOTH `development-v2-<left_id>` and `development-v2-<right_id>` are frozen and hash-verified.
- **Comparator Scope**: Evaluates `left_review`, `right_review`, and `comparison` (`current_preference`: `LEFT|RIGHT|CONDITIONAL|UNRESOLVED`, `competition_axis`, `strongest_reason_for_left`, `strongest_reason_for_right`, `discriminating_observation`, `what_would_change_the_decision`).

---

## 5. LEVER (Actionable Leverage)

LEVER derives bounded, high-leverage interventions from a `MODEL_READY` model. It is not a general planning tool; it operates solely on validated causal mechanisms.

- **Design Stage (`pizm-lever-design-v1`)**: Identifies intervention points, causal linkages to the model, bounded moves, expected responses, disconfirming signals, and explicit stop conditions.
- **Review Stage (`pizm-lever-review-v1`)**: Adversarial audit testing model dependence, boundedness, discrimination, adaptation rules, and stop triggers.
- **Terminal Outcomes**: `LEVER` or `NO_DEFENSIBLE_LEVER`.

---

## 6. AUTO Topology

AUTO (`/pizm auto <task>`) is an automated single-target pipeline:

```text
/pizm auto <task>
  │
  ├─► Search(initial) ────────► Freeze explore pass + search-field manifest
  │
  ├─► Portfolio Judge ────────► Freeze portfolio (route: AUTO, exactly one auto_target: P or B)
  │
  ├─► Deep(auto_target) ──────► Freeze development-v2
  │
  ├─► Critic Review ──────────► Freeze deep-review-v2 (MODEL_READY | NEED_EVIDENCE | RETURN_TO_EXPLORE)
  │
  ├─► [Conditional LEVER] ───► Freeze design + review (if MODEL_READY and ACTION_OR_DECISION)
  │
  └─► Deterministic FINAL ────► Session bundle archive & deterministic run.md (0 model calls)
```

AUTO enforces strict single-target discipline: exactly one target is deepened, with zero branch rerolls or second search passes.

---

## 7. FORGE Topology

FORGE (`/pizm forge <task>`) is the heavy automated dual-competition pipeline:

```text
/pizm forge <task>
  │
  ├─► Search(initial) ───────────────► Freeze pass01 + search-field
  │
  ├─► Search(residual) ──────────────► Freeze pass02 + search-field
  │
  ├─► Portfolio Judge (FORGE) ───────► Freeze portfolio-v2 (TWO_DEFENSIBLE_BUNDLES or NO_SECOND_DEFENSIBLE_BUNDLE)
  │
  ├─► Deep(LEFT) ────────────────────► Freeze development-v2-<left_id>
  │
  ├─► Deep(RIGHT) ───────────────────► Freeze development-v2-<right_id>
  │
  ├─► Reveal deep-compare.md ────────► Freeze comparison-review-v1 (Critic LEFT + Critic RIGHT + Comparative Reasoner)
  │
  ├─► [Conditional LEVER] ───────────► Freeze design + review on preferred MODEL_READY bundle
  │
  └─► Deterministic FINAL ───────────► Session bundle archive & deterministic run.md (0 model calls)
```

*Degraded FORGE*: When `competition_status` is `NO_SECOND_DEFENSIBLE_BUNDLE`, FORGE deepens only `single_target`, skips the comparative review stage, and renders the skip reason in `run.md`.

---

## 8. Checkpoint Seams & Payload Ceilings

The checkpoint tool (`bin/pizm-checkpoint`) enforces fail-closed validation, state persistence, and SHA-256 sidecars before revealing next-stage contracts.

### Payload Bounds

Deterministic payload bounds are enforced across all stages:
- **Search (Explore)**: $1..20$ candidates, total payload $\le 196{,}608\text{ bytes}$ ($192\text{ KiB}$), single candidate $\le 12{,}288\text{ bytes}$ ($12\text{ KiB}$).
- **Deep Development**: $\le 131{,}072\text{ bytes}$ ($128\text{ KiB}$).
- **Critic Review**: $\le 65{,}536\text{ bytes}$ ($64\text{ KiB}$).
- **Comparative Review**: $\le 131{,}072\text{ bytes}$ ($128\text{ KiB}$).
- **LEVER Design & Review**: $\le 65{,}536\text{ bytes}$ ($64\text{ KiB}$).

---

## 9. Artifact Authority & Session Accounting

Prism enforces a clear separation between machine authority and human presentation:

### Machine Authority

Structured JSON artifacts stored with `.sha256` sidecars are the sole authority for provenance, verification, and debugging:
- `candidates-passNN.json`, `search-field-passNN.json`
- `portfolio.json`
- `development-v2-<target>.json`
- `deep-review-v2-<target>.json`
- `comparison-review-v1.json`
- `design-<target>.json`, `review-<target>.json`

### Session Accounting Manifest

The archive manifest (`manifest.json` via `bin/pizm-session-bundle`) is the sole owner of machine accounting. It records exactly six counters:
- **Non-derived (caller-reported)**: `host_inference_count`, `model_repair_count`, `checkpoint_retry_count`.
- **Derived (computed from artifacts)**: `semantic_stage_count`, `candidate_bytes`, `development_bytes`.

### Human Presentation (`run.md`)

`run.md` is a deterministic, reader-oriented markdown synthesis rendered by `bin/pizm-session-bundle render`. It requires zero model calls and does not duplicate machine accounting fields.

---

## 10. Native Skill vs Frozen Perspective Core

- **`skills/pizm/`**: The canonical native skill executed directly by the host model in its local runtime loop. It carries prompt contracts, routing rules, and reference rubrics.
- **`src/prism/perspective_core/**`**: The Python reference substrate, schemas, and cold-path verification tools. It is permanently frozen byte-for-byte in this repository to prevent semantic drift.
