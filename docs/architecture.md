# Prism Architecture

Prism is a semantic exploration and model-development architecture designed for structured divergence, synthesis, adversarial evaluation, and actionable leverage.

This document describes the system architecture across four distinct layers:
1. **Semantic Capabilities**: Core reasoning primitives and logical contracts (Search, Portfolio, Deep Development, Critic Review, LEVER, Comparative Review). Logical contracts define semantic invariants and artifact schemas; they are not model calls, network APIs, or provider abstractions.
2. **Cumulative Manual Orchestration**: The reference interactive experience where human direction guides free-form exploration, preserves monotonic P-ID continuity, chooses what and when to deepen, and invokes manual LEVER on ready models.
3. **Dynamic AUTO Orchestration**: Automated execution of the same semantic capabilities with dynamic reasoning-budget forks (`DEEP`, `GATHER_INFORMATION`, `PRESERVE_ONLY`), compact live rival shadows, and honest non-ready stops.
4. **Execution & Performance Optimization**: Deterministic fail-closed payload ceilings, checkpoint seams, offline bundle accounting, and reader rendering. Context slicing and payload reduction operate as execution hypotheses, never as semantic invariants.

---

## 1. Search Policies & Candidate Generation

Search (invoked as Search or Explore) is the divergence primitive in Prism (Layer 1: Semantic Capability). It expands the space of materially distinct, grounded models of a problem before committing to any single branch. Candidate generation is an offline logical contract adhering to `pizm-candidates-v1`, not a dedicated provider call or mandatory execution wrapper.

### Information Gathering & Question Budget
Information Gathering unifies clarifying questions and probe-like decisions directly at the semantic interface, without introducing a standalone Probe subsystem, extra inference stage, or separate probe artifact:
- **0–3 Question Rule**: Permits 0–3 clarifying questions only when different answers would materially change search territory, constraints, evidence interpretation, or the next downstream reasoning spend.
- **Consumption Requirement**: Existing conversation context, source documents, and bounded reasoning checks must be fully consumed before asking questions; "more context would help" is strictly insufficient to trigger questions.
- **Grounding and Abstention**: When supplied source material cannot support materially distinct grounded models, Search limits candidate count or abstains honestly rather than manufacturing artificial breadth.

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

### Field Survival vs Reasoning Spend
Portfolio evaluation strictly separates field survival from downstream reasoning spend:
- **Field Survival**: Governed by categorical dispositions (`KEEP`, `BORDERLINE`, `MERGE`, `DROP`), which establish visible perspective identity ($P\langle n\rangle$) and open territory. Field survival does **not** force Deep development.
- **Reasoning Spend**: Governed by `next_reasoning_move` (`DEEP`, `GATHER_INFORMATION`, `PRESERVE_ONLY`), determining where computational or analytical effort is allocated next.

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

#### `pizm-portfolio-selection-v1` (Manual & AUTO)
Used in manual exploration and AUTO (`route: "MANUAL" | "AUTO"`).
- **In `MANUAL`**: `auto_target`, `next_reasoning_move`, `next_reasoning_rationale`, `information_request`, and `rival_shadow` are `null`. The user interactively decides which perspective or bundle to deepen in Layer 2 cumulative manual orchestration.
- **In `AUTO`**: `next_reasoning_move` is a required non-null enum (`DEEP | GATHER_INFORMATION | PRESERVE_ONLY`) with a non-empty `next_reasoning_rationale`:
  - `DEEP`: `auto_target` is a required non-null target (`{"target_type": "P" | "B", "target_id": "P<n>" | "B<n>"}`); `information_request` is `null`. `rival_shadow` is nullable. When a clear live rival exists in the portfolio, `rival_shadow` records:
    ```json
    {
      "target_type": "P | B",
      "target_id": "P<n> | B<n>",
      "core_claim": "non-empty string",
      "why_remains_live": "non-empty string",
      "differentiator_or_source_anchor": "non-empty string"
    }
    ```
    The rival ID must differ from `auto_target.target_id` and reference a promoted Perspective or defined Bundle (never synthesized).
  - `GATHER_INFORMATION`: Intentional completed terminal outcome. `auto_target` and `rival_shadow` are `null`. `information_request` contains:
    ```json
    {
      "mode": "USER_QUESTION | EXTERNAL_OBSERVATION",
      "missing_information": "non-empty string",
      "why_it_changes_route": "non-empty string",
      "questions": ["1–3 non-empty strings for USER_QUESTION; [] otherwise"],
      "suggested_observation": "non-empty string for EXTERNAL_OBSERVATION; null otherwise"
    }
    ```
  - `PRESERVE_ONLY`: Intentional completed terminal outcome. `auto_target`, `information_request`, and `rival_shadow` are all `null`. Preserves the current field without further reasoning spend.

#### `pizm-portfolio-selection-v2` (BONK)
Used in BONK (`route: "BONK"`). Specifies `competition_status`: either `TWO_DEFENSIBLE_BUNDLES` with `recommended_competition` (`left_bundle_id`, `right_bundle_id`, `competition_axis`, `discriminating_observation`) or `NO_SECOND_DEFENSIBLE_BUNDLE` with `single_target`.

---

## 3. Deep Model Development (v2)

Deep develops a selected perspective ($P\langle n\rangle$), composed bundle ($B\langle n\rangle$), or direct seed into a mature, testable causal model conforming to `pizm-development-v2`.

### Development Contract

- **Target Scope**: Exactly one target per development artifact. For a bundle target ($B\langle n\rangle$), one bundle equals one Deep pass (never split into per-member mini-Deeps).
- **Identity Lock**: Strictly preserves semantic identity (`p_id` or bundle `member_refs`). Fail-closed against silent topic drift.
- **Analytical Depth**: Comprehensive prose synthesis (~900–1600 words for single perspectives, ~1400–2400 words for bundles).
- **Required Model Structure**: Core thesis, mechanism chain, generative dynamics, boundary conditions, load-bearing claims census ($2..5$ claims with epistemic statuses: `SUPPORTED`, `INFERRED`, `SPECULATIVE`, `UNKNOWN`), break conditions, unresolved tensions, and observable predictions.

### Comparative Standing (`comparative_standing`)
When Portfolio nominates a live `rival_shadow`, Deep receives it without executing an additional inference stage and records `developed_model.comparative_standing`:
- `rival_ref`: Reference to the rival perspective or bundle (`"P<n>"` or `"B<n>"`).
- `material_difference`: Structural or causal difference between the two models.
- `selected_target_advantage`: Where the selected target is stronger or more parsimonious.
- `rival_advantage_or_parity`: Where the rival is stronger or on equal footing (wording explicitly permits the rival to remain equal or stronger).
- `unresolved_competition`: What empirical or conceptual uncertainty remains live between them.
If no rival shadow was nominated in Portfolio, `comparative_standing` is `null`.

### Development Delta & Provenance (`development_delta`)
Every development artifact records a compact provenance summary in `developed_model.development_delta`:
- `summary`: Non-empty string summarizing the delta or explicitly stating that no material delta occurred.
- `new_load_bearing_claims`: List of new load-bearing claims introduced during development.
- `strengthened_claims`: List of claims strengthened by new evidence or analysis.
- `new_causal_arrows_or_mechanisms`: List of newly articulated causal links or mechanisms.
- `material_imports`: List of concepts or structures imported from outside the seed.
- `scope_expansions`: List of scope expansions beyond original seed boundaries.
All five list keys are required and may be empty (`[]`). This provides an auditable delta record without requiring a heavy graph representation.

---

## 4. Critic & Comparative Review

The Critic provides independent adversarial reassessment of frozen development models. The developer role is blind to the critic rubric until the development artifact freezes.

### Single-Model Critic (`pizm-deep-review-v2`)

The critic inspects the model independently without adopting developer self-assessments:
- **Mandatory Checks**: Identity verification, cross-field contradictions, independent audit of load-bearing claims (`load_bearing_reassessment`), detection of unsupported specificity, exposure of epistemic laundering, independent countermodel generation, break condition validity, member ablation (for bundles), cost relocation analysis, round-trip structural skeleton extraction, and identification of the cheapest discriminating test.
- **Delta-Aware Audit**: The critic uses `development_delta` to identify where load-bearing structures shifted. Whole-model re-evaluation is invoked when new or strengthened claims, mechanisms, imports, or scope changes alter what carries the model; ordinary uncertainty remains recorded evidence debt rather than contradiction.

### Decoupling Readiness Blockers from Logical Contradictions
Prism separates logical contradiction from epistemic and structural readiness blockers:
- **`findings.unresolved_load_bearing_contradiction`**: Strictly boolean, reserved solely for actual, irreconcilable logical contradictions within the model.
- **`findings.readiness_blockers`**: Explicit list of structural blockers drawn from:
  1. `B1_SPECULATIVE_DEPENDENCY`: Central explanatory mechanism or causal chain materially depends on claims marked `SPECULATIVE` or `UNKNOWN`.
  2. `B2_STRONGER_COUNTERMODEL`: Reviewer constructs an independent countermodel explaining the phenomenon materially better with lower assumption burden.
  3. `B3_THESIS_LAUNDERING`: Synthesis or thesis presents central claims with settled certainty while underlying census is speculative.
  4. `B4_COVERAGE_MISMATCH`: Model asserts global explanatory scope while empirical or mechanism support covers only a local slice.
- **`findings.readiness_blocker_details`**: Object mapping each active blocker to its detailed evidence.
- **Coupling Rule**: Any active readiness blocker strictly forbids `MODEL_READY` on its own merits, without falsely setting `unresolved_load_bearing_contradiction: true`. An actual logical contradiction also independently forbids `MODEL_READY`.
- **Soft Warnings**: Peripheral uncertainty, minor missing secondary predictions, or non-central evidence debt do not set readiness blockers and do not forbid `MODEL_READY`.

### Terminal States

The critic returns exactly one of three terminal states:
- **`MODEL_READY`**: Sound, robust causal model with verified identity, defensible claims, zero unresolved contradictions, and zero active readiness blockers.
- **`NEED_EVIDENCE`**: Model is structurally promising but blocked by unverified claims, unsupported specificity, or readiness blockers. Requires a non-null `inquiry_program`:
  ```json
  {
    "current_leading_models": ["one or more non-empty strings"],
    "unresolved_questions": ["one or more non-empty strings"],
    "strongest_live_rival": "non-empty string or null",
    "result_that_would_change_model": "non-empty string",
    "stop_rule": "non-empty string"
  }
  ```
  Accompanied by non-empty `evidence_debt` and `cheapest_discriminating_test` (which may specify empirical, conceptual, interpretive, or creative tests).
- **`RETURN_TO_EXPLORE`**: Fundamental identity drift, composition collapse, fatal logical contradiction, or defeated core mechanism. Requires a precise break point statement. Does not auto-loop back to Search.

### Comparative Review (`pizm-comparison-review-v1`) & Delayed Reveal Seam

In dual-competition BONK execution:
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

AUTO (`/pizm auto <task>`) is an automated pipeline that orchestrates the underlying semantic capabilities through dynamic reasoning-budget forks (Layer 3: Dynamic AUTO Orchestration):

```text
/pizm auto <task>
  │
  ├─► Search(initial) ────────► Freeze explore pass + search-field manifest
  │
  ├─► Portfolio Judge ────────► Freeze portfolio (route: AUTO)
  │     │
  │     ├─► [next_reasoning_move: DEEP]
  │     │     ├─► Deep(auto_target) ──► Freeze development-v2 (with delta & rival standing)
  │     │     ├─► Critic Review ──────► Freeze deep-review-v2 (MODEL_READY | NEED_EVIDENCE | RETURN_TO_EXPLORE)
  │     │     └─► [Conditional LEVER] ► Freeze design + review (if MODEL_READY and ACTION_OR_DECISION)
  │     │
  │     ├─► [next_reasoning_move: GATHER_INFORMATION]
  │     │     └─► Intentional terminal stop (freeze information request; 0 Deep/Critic/LEVER files)
  │     │
  │     └─► [next_reasoning_move: PRESERVE_ONLY]
  │           └─► Intentional terminal stop (freeze preserved field; 0 Deep/Critic/LEVER files)
  │
  └─► Deterministic FINAL ────► Session bundle archive & deterministic run.md (0 model calls)
```

### Dynamic Reasoning-Budget Branches
- **`DEEP`**: Deepens exactly the nominated target (`auto_target`: single $P$ or $B$). If a live rival shadow is present, Deep records comparative standing against it. Proceeds through Deep Developer, Critic Review, and conditional LEVER.
- **`GATHER_INFORMATION`**: Intentional completed terminal outcome. Freezes an information request (1–3 questions or external observation) and stops immediately without invoking Deep, Critic, or LEVER.
- **`PRESERVE_ONLY`**: Intentional completed terminal outcome. Preserves the candidate field without further reasoning spend and stops immediately without invoking Deep, Critic, or LEVER.

### Honest-Stop Discipline
- **Portfolio Terminals**: `GATHER_INFORMATION` and `PRESERVE_ONLY` are completed run outcomes, not resumable partial states. They freeze current artifacts and never auto-resume. Continuation requires an explicit fresh user command or a fresh run; prior runs remain immutable.
- **Critic Terminals**: If Critic returns `NEED_EVIDENCE` (with inquiry program) or `RETURN_TO_EXPLORE`, execution stops honestly at Critic. No secondary Deep, reroll, or branch recovery is attempted.
- **Final Assembly**: Pipeline proceeds directly to deterministic FINAL assembly and `run.md` rendering.

### Execution vs Semantic Invariants
AUTO enforces strict single-target discipline: exactly one target is deepened, with zero branch rerolls or second search passes. Context slicing, payload pruning, and token reduction operate as execution optimization hypotheses, not as semantic invariants of the reasoning model.

---

## 7. BONK Topology

BONK (`/pizm bonk <task>`) is the heavy automated dual-competition pipeline:

```text
/pizm bonk <task>
  │
  ├─► Search(initial) ───────────────► Freeze pass01 + search-field
  │
  ├─► Search(residual) ──────────────► Freeze pass02 + search-field
  │
  ├─► Portfolio Judge (BONK) ───────► Freeze portfolio-v2 (TWO_DEFENSIBLE_BUNDLES or NO_SECOND_DEFENSIBLE_BUNDLE)
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

*Degraded BONK*: When `competition_status` is `NO_SECOND_DEFENSIBLE_BUNDLE`, BONK deepens only `single_target`, skips the comparative review stage, and renders the skip reason in `run.md`.

---

## 8. Checkpoint Seams & Payload Ceilings

The checkpoint tool (`bin/pizm-checkpoint`) enforces fail-closed validation, state persistence, and SHA-256 sidecars before revealing next-stage contracts (Layer 4: Execution & Performance Optimization).

### Optimization Hypotheses & Invariants
Context slicing and payload bounds serve as execution and performance optimizations:
- Deterministic payload bounds fail closed to prevent context bloat and runaway token consumption.
- Context minimization across stage boundaries is an execution hypothesis designed to maximize reasoning density; it does not alter the underlying semantic contracts.

### Payload Bounds

Deterministic payload bounds are enforced across all stages:
- **Search (Explore)**: $1..20$ candidates, total payload $\le 196{,}608\text{ bytes}$ ($192\text{ KiB}$), single candidate $\le 12{,}288\text{ bytes}$ ($12\text{ KiB}$).
- **Deep Development**: $\le 196{,}608\text{ bytes}$ ($192\text{ KiB}$).
- **Critic Review**: $\le 131{,}072\text{ bytes}$ ($128\text{ KiB}$).
- **Comparative Review**: $\le 131{,}072\text{ bytes}$ ($128\text{ KiB}$).
- **LEVER Design & Review**: $\le 65{,}536\text{ bytes}$ ($64\text{ KiB}$).

---

## 9. Artifact Authority & Session Accounting

Prism enforces a clear separation between machine authority, session accounting, and human presentation (Layer 4: Execution & Performance Optimization):

### Logical Contracts vs Model Invocations
Logical stage contracts (Search, Portfolio, Deep, Critic, LEVER, Final Assembly) define schema validation rules, invariant bounds, and deterministic transitions. They are distinct from raw model invocations or host turns. A logical stage is not a 1:1 network call or provider abstraction.

### Machine Authority

Structured JSON artifacts stored with `.sha256` sidecars are the sole authority for provenance, verification, and debugging:
- `candidates-passNN.json`, `search-field-passNN.json`
- `portfolio.json`
- `development-v2-<target>.json`
- `deep-review-v2-<target>.json`
- `comparison-review-v1.json`
- `design.json`, `review.json` (legacy `lever-design.json` / `lever-review.json` aliases also accepted)

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
