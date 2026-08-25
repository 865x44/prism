# Pizm FORGE Pipeline Contract

FORGE is the heavy automated path of Pizm that performs two-pass Search, judges the accumulated field for competing composite models, develops both models independently (Deep B1 and Deep B2), executes adversarial Critic and comparative reasoning, runs optional LEVER on a ready target, and renders a deterministic final report plus a readable `run.md`.

**Date:** 2026-08-25
**Prerequisite:** Plan 1 semantic primitives (Search Field v1, deterministic B-IDs, Deep v2, Critic v2, LEVER, atomic freeze checkpoints, deterministic session renderer).

---

## 1. Explicit Delegation Requirement

FORGE executes ONLY via explicit user delegation:

```text
/pizm forge <task>
```

Manual Pizm modes (`/pizm`, `normal`, `explore`, `rift`, `360`, `deep`, `/pizm lever`, `/pizm auto`) NEVER trigger or emulate FORGE behavior. Discussing FORGE with the user remains possible without executing it.

---

## 2. Target Topology & Execution Sequence

```text
Search(initial)
→ freeze explore pass 01 + search-field manifest

Search(residual)
→ freeze explore pass 02 + search-field manifest

Portfolio Judge over accumulated field
→ identify two defensible competing Bundles when possible (pizm-portfolio-selection-v2)

Deep(B1)
→ freeze development-v2-B1

Deep(B2)
→ freeze development-v2-B2

Critic + Compare(B1, B2)
→ freeze comparison-review-v1

[conditional] LEVER on preferred MODEL_READY model (design + review)

deterministic FINAL assembly (zero model calls)
deterministic run.md rendering (zero model calls)
```

---

## 3. Detailed Stage Contracts

### Stage 1: Search Pass 1 (initial)
- Run broad initial Search adhering to `references/explore.md` (soft target 12–16 candidates when supported; hard bounds 1..20 candidates, ≤ 192 KiB payload, ≤ 12 KiB per candidate).
- Freeze the raw pass as `pass01` via `bin/pizm-checkpoint freeze --stage explore --run-id <slug> --artifact-suffix pass01 --input <path>` -> creates `candidates-pass01.{json,sha256,meta.json}` (or unsuffixed `candidates.{json,sha256,meta.json}`).
- Register `pass01` in the append-only search-field manifest conforming to `pizm-search-field-v1` and freeze via `bin/pizm-checkpoint freeze --stage search-field --run-id <slug> --artifact-suffix pass01 --input <path>` -> creates `search-field-pass01.{json,sha256,meta.json}` (or `search-field.{json,sha256,meta.json}`).
- **No judging after Pass 1.** Do not filter, rank, or evaluate candidates at this stage.

### Stage 2: Search Pass 2 (residual)
- Pass 2 consumes the frozen accumulated field from Pass 1.
- Run residual Search following the `residual` policy in `references/explore.md`:
  - Reconstruct strongly covered semantic cores.
  - Notice redundant coverage.
  - Preserve seen-but-open directions.
  - Attack attractor lock (avoid returning to favored mechanisms, actor swaps, or stylistic reframings).
  - Seek new load-bearing dimensions, system boundaries, and causal families.
  - Allow honest exhaustion if no new structural territory exists (do not pad).
  - Soft ceiling: ~28 candidates across the accumulated field.
- Freeze raw `pass02` via `bin/pizm-checkpoint freeze --stage explore --run-id <slug> --artifact-suffix pass02 --input <path>` -> creates `candidates-pass02.{json,sha256,meta.json}`.
- Update the append-only search-field manifest (`pizm-search-field-v1`) naming `search-field-pass01.json` as `prior_ref` with its verified `prior_hash`, and freeze via `bin/pizm-checkpoint freeze --stage search-field --run-id <slug> --artifact-suffix pass02 --input <path>` -> creates `search-field-pass02.{json,sha256,meta.json}`.
- **No automatic third Search.** FORGE v1 executes exactly two automatic Search passes.

### Stage 3: Portfolio Judge over Accumulated Field
- Reveal `references/explore-selector.md`.
- Evaluate all accumulated candidates from both passes categorically and structurally.
- Freeze one portfolio record conforming to `pizm-portfolio-selection-v2`:
  - Enforce `field_ref` (pointing to the exact frozen search field JSON) and `field_hash` (matching its frozen SHA-256 sidecar).
  - Provide canonical `perspectives` mapping (`{"P1": "pass01:c01", "P2": "pass01:c02", "P3": "pass02:c01", ...}`) which strictly controls rendered perspective labels and continued P-IDs across passes.
  - Enforce `competition_status`: `"TWO_DEFENSIBLE_BUNDLES"` or `"NO_SECOND_DEFENSIBLE_BUNDLE"`.
  - When two defensible bundles exist:
    - `recommended_competition` specifies `bundle_a: "B1"`, `bundle_b: "B2"`, `competition_axis`, `discriminating_observation`, and optional `discriminating_question`.
    - Both B1 and B2 require genuine composition gain, bundle thesis, member ablation (no passengers), internal tension, and distinct explanatory programs.
    - Competing pair must differ on a load-bearing axis (e.g. primary mechanism, binding constraint, system boundary, agency location, time dynamics, causal direction, prediction, intervention implication).
  - When no second defensible bundle exists:
    - `competition_status = "NO_SECOND_DEFENSIBLE_BUNDLE"`.
    - `recommended_competition = null`.
    - Do not invent or force an artificial B2.
### Stage 4: Deep(B1) & Deep(B2)
- When two defensible bundles exist:
  - **Sequential execution:** Develop B1 → freeze → Develop B2 → freeze.
  - Each bundle receives a separate full development inference under the `pizm-development-v2` contract (`references/deep.md`).
  - Target identity locks freeze bundle membership (`member_refs`), thesis, mechanism, and boundaries.
  - Soft guidance: ~1400–2400 words per bundle when material supports it.
  - **Hard prohibitions:**
    - Do NOT Deep bundle members individually (one bundle = one Deep).
    - Do NOT combine B1 and B2 into a single joint development.
    - Do NOT critique B1 before developing B2.
  - Freeze `development-v2-B1` and `development-v2-B2` using `bin/pizm-checkpoint freeze --stage development-v2 --target B1 ...` and `--target B2 ...`.

### Stage 5: Critic and Comparative Review
- Revealed only after BOTH Deep B1 and Deep B2 are frozen and hash-verified.
- Execute adversarial critique and comparative reasoning under `pizm-comparison-review-v1` (`references/deep-reviewer.md`):
  - Declare explicit B1 and B2 development artifact references and verified frozen hashes (`review_B1.development_ref`, `review_B1.frozen_hash`, `review_B2.development_ref`, `review_B2.frozen_hash`), verifying target matching `B1` and `B2`.
  - Act as critic of B1, critic of B2, and comparative reasoner using the 8-move Critic arsenal.
  - Formulate independent countermodels, audit load-bearing claims, flag unsupported specificity and epistemic laundering, and identify shared evidence debt.
  - Determine `current_preference`: `B1 | B2 | CONDITIONAL | UNRESOLVED`.
  - **No forced winner:** `CONDITIONAL` and `UNRESOLVED` are first-class terminal states.
  - Specify `competition_axis`, `strongest_reason_for_B1`, `strongest_reason_for_B2`, `discriminating_observation`, and `what_would_change_the_decision`.
  - **Decision rule:** An unresolved load-bearing contradiction or `RETURN_TO_EXPLORE` state in a bundle's review blocks preference for that bundle.
- Freeze artifact via `bin/pizm-checkpoint freeze --stage comparison-review-v1 --run-id <slug> --input <path>`.
### Stage 6: Optional LEVER
- Automatically runs ONLY when:
  - Task orientation is `ACTION_OR_DECISION` (classified during judging).
  - AND the comparison identifies a suitable `MODEL_READY` target (or single-bundle degraded route is `MODEL_READY`).
- If `current_preference` is `CONDITIONAL` or `UNRESOLVED`: do NOT force LEVER; surface the discriminating observation as the recommended next step.
- If task orientation is `ANALYTICAL`: do not run LEVER.
- When executed, runs standard manual LEVER design and review (`references/lever.md` and `references/lever-reviewer.md`).

### Stage 7: Deterministic FINAL Assembly and run.md
- Assemble the final user-facing summary from frozen artifacts with zero model calls.
- You must archive the run via `bin/pizm-session-bundle create` providing the required ephemeral accounting input (`--accounting <path>`) and allowlisted stage labels:
  - `pass-01-normal` (or `pass-01-rift` / `pass-01-360`)
  - `pass-02-residual`
  - `search-field`
  - `portfolio`
  - `deep-B1`
  - `deep-B2`
  - `comparison-review`
- The bundle derives and verifies `semantic_stage_count`, `candidate_bytes`, and `development_bytes`; caller supplies bounded non-derived counts (`host_inference_count`, `model_repair_count`, `checkpoint_retry_count`). The archive manifest records the normalized six-counter object; the accounting file is ephemeral and never copied into inputs.
- Render the readable `run.md` deterministically using `bin/pizm-session-bundle render --run-dir <run-dir> --task "<task>"`.
- Output is a pure, byte-identical function of frozen inputs.
---

## 4. Degraded Path (Single Defensible Bundle)

If Portfolio records `competition_status: NO_SECOND_DEFENSIBLE_BUNDLE`:
1. Search Pass 1 (initial) and Pass 2 (residual) both execute and appear in the record.
2. Portfolio identifies B1 (or standalone P) and explicitly notes `NO_SECOND_DEFENSIBLE_BUNDLE`.
3. Compare stage is skipped without failing the run.
4. Deep develops B1.
5. Single-model Critic evaluates B1 (`pizm-deep-review-v2`).
6. Optional LEVER runs if task is `ACTION_OR_DECISION` and status is `MODEL_READY`.
7. Final report and `run.md` state `NO_SECOND_DEFENSIBLE_BUNDLE` and render single-model review.

---

## 5. Semantic Stage Budgets and Repairs

### Stage Budgets
- **Analytical FORGE (2 Bundles):** Pass 1 + Pass 2 + Portfolio + Deep B1 + Deep B2 + Critic/Compare = **6 semantic stages**.
- **Action FORGE with LEVER (2 Bundles):** 6 + Lever Design + Lever Review = **8 semantic stages**.
- **Degraded Single-Bundle Path:** 5 stages (analytical) or 7 stages (with LEVER).
- Final assembly and `run.md` rendering add **zero** semantic stages.

### Accounting and Counters
The archive manifest records all six normalized counters:
1. `semantic_stage_count` (derived from stage collection)
2. `host_inference_count` (caller-supplied non-derived counter)
3. `model_repair_count` (caller-supplied non-derived counter)
4. `checkpoint_retry_count` (caller-supplied non-derived counter)
5. `candidate_bytes` (derived from frozen candidate JSON byte sizes)
6. `development_bytes` (derived from frozen development JSON byte sizes)

### Bounded Repair Limits
- Max 1 model repair per stage.
- Max 2 model repairs across the entire FORGE run.
- If budget or repairs are exhausted, fail closed with `BUDGET_EXHAUSTED`.
