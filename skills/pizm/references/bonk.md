# Pizm BONK v3 Pipeline Contract

BONK is the deep automated exploration route of Pizm. It executes one bounded path — Search(initial), Search(residual), Search(rift), Portfolio dual-development selection, Deep A, Deep B — and then renders a deterministic development handoff (`run.md`).

BONK does **not** judge, compare, or synthesize. It selects two strong, materially distinct model families, develops both honestly and deeply, and hands both to a stronger downstream reasoner or human.

**Date:** 2026-09-22
**Prerequisite:** Plan 1 semantic primitives (Search Field v1, deterministic B-IDs, Deep v2, atomic freeze checkpoints, deterministic session renderer).

---

## 1. Explicit Delegation Requirement

BONK executes ONLY via explicit user delegation:

```text
/pizm bonk <task>
```

Manual Pizm modes (`/pizm`, `normal`, `explore`, `rift`, `360`, `deep`, `/pizm critic`, `/pizm lever`, `/pizm auto`) NEVER trigger or emulate BONK behavior. Discussing BONK with the user remains possible without executing it.

## 2. Core Promise & Non-Claims

BONK is a development and handoff route, NOT an adjudication route.

BONK explicitly does not:
- select a winner;
- compare the two developed models for truth;
- synthesize a third model;
- issue a Critic readiness verdict (`MODEL_READY` or otherwise);
- validate either developed hypothesis.

The two targets are **not contestants**. They are two high-quality development targets with large useful structural distance. They are never presented to the user as LEFT/RIGHT, winner/rival, or ranked alternatives.

## 2b. Execution Scope & Root Contract

BONK's helper executables and skill root are location-dependent. Resolve them once, before the first freeze, and use the resolved values everywhere:

```text
$PIZM_CHECKPOINT       repo checkout: bin/pizm-checkpoint
                       installed host: $HOME/.local/bin/pizm-checkpoint
$PIZM_SESSION_BUNDLE   repo checkout: bin/pizm-session-bundle
                       installed host: $HOME/.local/bin/pizm-session-bundle
$PIZM_SKILL_ROOT       the directory containing the currently loaded Pizm SKILL.md
                       repo checkout: skills/pizm
                       installed host: $HOME/.claude/skills/pizm or $HOME/.config/opencode/skills/pizm
```

An installed host must use the helper and skill root deployed together by the supported installer, must not mix repo and installed locations, and the helpers and loaded skill root must belong to the same installed Pizm version. Every command recipe below is written with these variables: a displayed `bin/...` or `skills/pizm` path is the repo-checkout value of the same variable, never a separate command.

---

## Operational happy path

For normal successful BONK execution, follow the commands and artifact schemas in this contract and the currently loaded stage contract directly. Do not invoke Pizm CLI `--help`, inspect Pizm Python source, or read Pizm tests before attempting prescribed operations. If the prescribed command succeeds, continue immediately to the next pipeline step.

### Stage-contract loading order
- Stage 1–3: Load `references/explore.md` for Search Pass 1 (initial), Pass 2 (residual), and Pass 3 (rift).
- Stage 4: Reveal `references/explore-selector.md` only after the final Search Field freeze (`pass03`).
- Stage 5: Reveal `references/deep.md` for sequential Deep A and Deep B development. Deep A and Deep B are ordinary Deep passes under the current contract.
- Never load `references/deep-compare.md`, `references/deep-reviewer.md`, `references/lever.md`, or `references/lever-reviewer.md` during a BONK run. BONK v3 has no Critic, Compare, or LEVER stage.

### Freeze success and repair rules
- `FREEZE_OK` from the prescribed checkpoint command is authoritative for that freeze. After `FREEZE_OK`, do not reopen validator source/tests or re-read the just-frozen artifact solely to verify the successful freeze.
- Validator rejection is not permission for unrestricted repository archaeology. First repair directly from: (1) the surfaced validation error, (2) the current stage contract, and (3) the existing bounded repair budget. Inspect implementation files only if these are genuinely insufficient to continue.

---

## 3. Target Topology & Execution Sequence

```text
BONK TASK
→ Search(initial)   pass01 → freeze explore + search-field manifest
→ Search(residual)  pass02 → freeze explore + search-field manifest
→ Search(rift)      pass03 → freeze explore + search-field manifest
→ (only after pass03 freeze: reveal references/explore-selector.md)
→ Portfolio dual-development selection (pizm-portfolio-selection-v3, route BONK)
→ Deep A  → freeze development-v2-<A_target_id>
→ Deep B  → freeze development-v2-<B_target_id>
→ deterministic dual-development handoff (run.md)
→ STOP
```

No automatic Critic. No automatic Compare. No automatic LEVER. No winner. No synthesized third theory.

---

## 4. Detailed Stage Contracts

### Stage 0: Run Identity (before any freeze)
- Derive `subject_slug` from the task subject with the deterministic ASCII rule (`pizm_run_state.slugify_subject`: lowercase, Cyrillic transliterated, non-alphanumeric → hyphens). Mint one run-id `<subject_slug>-YYYYMMDDtHHMMSSz-<rand4>` (UTC timestamp + 4 lowercase-alphanumeric chars, same shape as `generate_run_id`). Use this run-id for every `--run-id` freeze below (run dir becomes `.ai/pizm/run-<run-id>/`) and for `--slug` at archive time, so run dir, bundle, and reader slug stay aligned. Never use a bare timestamp or short random id.

### Stage 1: Search Pass 1 (initial)
- Run broad initial Search adhering to `references/explore.md` (soft target 12–16 candidates when supported; hard bounds 1..20 candidates, ≤ 192 KiB payload, ≤ 12 KiB per candidate).
- Freeze the raw pass as `pass01` via `"$PIZM_CHECKPOINT" freeze --stage explore --run-id <slug> --artifact-suffix pass01 --input <path>` → creates `candidates-pass01.{json,sha256,meta.json}` (or unsuffixed `candidates.{json,sha256,meta.json}`).
- Register `pass01` in the append-only search-field manifest conforming to `pizm-search-field-v1` and freeze via `"$PIZM_CHECKPOINT" freeze --stage search-field --run-id <slug> --artifact-suffix pass01 --input <path>` → creates `search-field-pass01.{json,sha256,meta.json}`.
- **No judging after Pass 1.** Do not filter, rank, or evaluate candidates at this stage.

### Stage 2: Search Pass 2 (residual)
- Pass 2 consumes the frozen accumulated field from Pass 1.
- Run residual Search following the `residual` policy in `references/explore.md`:
  - Reconstruct strongly covered semantic cores; notice redundant coverage; preserve seen-but-open directions.
  - Attack attractor lock (avoid returning to favored mechanisms, actor swaps, or stylistic reframings).
  - Seek new load-bearing dimensions, system boundaries, and causal families.
  - Allow honest exhaustion if no new structural territory exists (do not pad): freeze `candidates: []` with a non-empty `exhaustion_reason`.
  - Freeze with the accepted residual mode string `360` (the accepted `mode` enum is `NORMAL|360|RIFT`; `RESIDUAL` is not accepted).
- Freeze raw `pass02` via `"$PIZM_CHECKPOINT" freeze --stage explore --run-id <slug> --artifact-suffix pass02 --input <path>`.
- Update the append-only search-field manifest naming `search-field-pass01.json` as `prior_ref` with its verified `prior_hash`, and freeze with `--artifact-suffix pass02`.

### Stage 3: Search Pass 3 (rift)
- Pass 3 consumes the accumulated field from Passes 1 and 2 and searches under the `rift` policy: distant structural shifts, reframed unit of analysis, different causal direction, system boundary, agency location, or time scale. An exhausted rift pass freezes `candidates: []` with a non-empty `exhaustion_reason` (mode `RIFT`) instead of a decorative analogy.
- Freeze raw `pass03` via `"$PIZM_CHECKPOINT" freeze --stage explore --run-id <slug> --artifact-suffix pass03 --input <path>`.
- Update the append-only search-field manifest naming `search-field-pass02.json` as `prior_ref` with its verified `prior_hash`, and freeze with `--artifact-suffix pass03` → creates `search-field-pass03.json`. This is the **final** search field.
- BONK v3 executes exactly three automatic Search passes. There is no fourth pass and no re-search after the portfolio.

### Stage 4: Portfolio Dual-Development Selection
- Reveal `references/explore-selector.md` only now, after `search-field-pass03.json` is frozen and hash-verified.
- Evaluate all accumulated candidates from the three passes categorically (`KEEP | BORDERLINE | MERGE | DROP`) and compose Bundles (`B1, B2, …`) from kept candidates.
- Freeze one portfolio record conforming to `pizm-portfolio-selection-v3`:
  - `route: "BONK"`, `stage: "portfolio"`.
  - `field_ref: "search-field-pass03.json"` and `field_hash` matching its frozen SHA-256 sidecar. The basename MUST be exactly `search-field-pass03.json`: the checkpoint fails closed on any other name, so a portfolio cannot be frozen before the third pass exists.
  - Canonical `perspectives` mapping (`{"P1": "pass01:c01", "P2": "pass01:c02", "P3": "pass02:c01", …}`) which strictly controls rendered perspective labels and continued P-IDs across passes.
  - `candidate_assessments`, `bundles`, `high_upside` as in the selector contract.
  - **Forbidden under v3** (must be absent, not merely null): `auto_target`, `next_reasoning_move`, `next_reasoning_rationale`, `information_request`, `rival_shadow`, `competition_status`, `recommended_competition`, `single_target`.
  - `development_mode: "DUAL_BUNDLES"` or `"SINGLE_TARGET"`.
- **DUAL_BUNDLES** — exactly two development targets:
  ```json
  "development_targets": [
    {"target_type": "B", "target_id": "B1", "why_develop": "…"},
    {"target_type": "B", "target_id": "B2", "why_develop": "…"}
  ],
  "material_difference": "…"
  ```
  - Both targets must be existing B-IDs from the frozen `bundles` list, must be distinct, and must independently meet the quality bar.
  - `material_difference` MUST explain a structural distinction (different causal mechanism, system boundary, unit of analysis, control structure, temporal mechanism, intervention logic, or mutually tensioned assumptions) — not a wording or topic difference, not a superset/subset pair with no emergent difference.
  - Do not force a second bundle merely for diversity; do not reward a weak idea for being different.
- **SINGLE_TARGET** — used when no second defensible materially distinct bundle exists:
  ```json
  "development_targets": [
    {"target_type": "B", "target_id": "B1", "why_develop": "… why no second target was defensible …"}
  ],
  "material_difference": null
  ```
  - Exactly one target, `target_type` `B` (must exist in `bundles`) or `P` (must exist in the `perspectives` mapping).
  - `why_develop` must state explicitly why a second materially distinct target was not defensible.
  - `material_difference` MUST be null or empty.
- Freeze: `"$PIZM_CHECKPOINT" freeze --stage portfolio --run-id <slug> --input <path>`.
- The portfolio freeze reveals **no** next semantic contract. Proceed to Deep A.

### Stage 5: Deep A and Deep B (sequential)
- Reveal `references/deep.md`. Each selected target gets one ordinary Deep development under the `pizm-development-v2` contract. Deep remains hypothesis elaboration, not validation.
- Order follows the frozen `development_targets` array: the first entry is Deep A, the second (when present) is Deep B. This order is deterministic and is preserved by the rendered handoff.
- **Sequential execution:** develop A → freeze → develop B → freeze.
- Freeze with `"$PIZM_CHECKPOINT" freeze --stage development-v2 --run-id <slug> --target <target_id> --input <path>`. Target identity locks freeze bundle membership (`member_refs`), thesis, mechanism, and boundaries.
- Soft guidance: ~1400–2400 words per target when material supports it.

#### Best-effort separation (same-host limits)
- Deep B develops B from B's frozen bundle identity and the source/context only.
- Deep B must not compare against, synthesize with, imitate, or reference Deep A.
- Same-host context separation is best-effort within a shared conversation. Do not claim independent-model or fresh-context execution, and do not report separation as guaranteed.
- If the two developments visibly converge before finalization, record that as a separate later experiment (stage-local or fresh-worker execution). Do not attempt to solve it inside this run.

#### Hard prohibitions
- Do NOT Deep bundle members individually (one bundle = one Deep).
- Do NOT combine A and B into a single joint development.
- Do NOT critique A before developing B.
- Do NOT produce `deep-review-v2-A`, `deep-review-v2-B`, or any Critic artifact.
- Do NOT produce `comparison-review-v1.json`.
- Do NOT run LEVER.

### Stage 6: Deterministic Handoff Assembly
- Once the last required development artifact is frozen, semantic reasoning is finished. The checkpoint reveals no further contract: proceed immediately to finalization.
- 1. Archive the run with the canonical `create` command (see §5).
- 2. Render the deterministic development pack:
  ```bash
  "$PIZM_SESSION_BUNDLE" render \
    --run-dir ".ai/pizm/run-$RUN_ID" \
    --task "<original task>" \
    --subject-slug "$SUBJECT_SLUG"
  ```
  This writes `run-<subject-slug>.md` (report that path). The pack contains: original task, exploration coverage (three passes), the curated Perspective/Bundle map, Development Target A and B (frozen identity, full Deep synthesis, mechanism, predictions/observables, boundaries, provisional epistemic census, evidence debt), the frozen material difference, explicit non-claims, and a suggested downstream task.
- 3. **HTML status:** interactive HTML is NOT supported for BONK v3. Do not invoke `"$PIZM_SESSION_BUNDLE" render-html` on a v3 run (the CLI refuses with a stable non-zero error). The Markdown development pack is the primary deliverable.
- 4. Report the pack location, the target IDs developed, and the frozen material difference. Do not add a winner, a preference, or a verdict.
- Output is a pure, byte-identical function of frozen inputs. Deterministic finalization MUST NOT generate a hidden comparison or a third model.

---

## 5. Archive Shape and Accounting

### Dual path
```text
pass-01-normal
pass-02-residual
pass-03-rift
search-field
portfolio
deep-<A_target_id>
deep-<B_target_id>
```

### Degraded (SINGLE_TARGET) path
```text
pass-01-normal
pass-02-residual
pass-03-rift
search-field
portfolio
deep-<target_id>
```

No BONK v3 run contains `comparison-review` or `lever-*` stages. A v3 archive carrying any deep-review, comparison-review, or LEVER artifact (JSON, `.sha256`, or `.meta.json`) fails closed.

The archive's Deep stages MUST be exactly the frozen `development_targets` — same targets, same count. A missing, extra, duplicate, or wrong-target Deep stage fails closed, and each bundled development artifact must declare the target id its stage names.

### Canonical archive command (dual)
```bash
"$PIZM_SESSION_BUNDLE" create \
  --output-root .ai/pizm/bundles \
  --slug "$RUN_ID" \
  --skill-root "$PIZM_SKILL_ROOT" \
  --stage pass-01-normal=".ai/pizm/run-$RUN_ID" \
  --stage pass-02-residual=".ai/pizm/run-$RUN_ID" \
  --stage pass-03-rift=".ai/pizm/run-$RUN_ID" \
  --stage search-field=".ai/pizm/run-$RUN_ID" \
  --stage portfolio=".ai/pizm/run-$RUN_ID" \
  --stage deep-"$TARGET_A_ID"=".ai/pizm/run-$RUN_ID" \
  --stage deep-"$TARGET_B_ID"=".ai/pizm/run-$RUN_ID" \
  --accounting "$ACCOUNTING_JSON" \
  --subject-slug "$SUBJECT_SLUG" \
  --provider "$PROVIDER" \
  --model "$MODEL" \
  --model-source "$MODEL_SOURCE" \
  --pizm-version "$PIZM_VERSION" \
  --evidence-kind live
```
For a degraded single-target run, pass the single `--stage deep-"$TARGET_ID"` and omit the second development stage.

`--accounting` is mandatory for BONK. Expected derived counts:
```text
dual   = 6   (Search ×3 + Portfolio + Deep A + Deep B)
single = 5   (Search ×3 + Portfolio + Deep)
```
The archive manifest records all six normalized counters: `semantic_stage_count` (derived), `host_inference_count`, `model_repair_count`, `checkpoint_retry_count`, `candidate_bytes` (derived), `development_bytes` (derived).

---

## 6. Degraded Path (SINGLE_TARGET)

If the portfolio records `development_mode: "SINGLE_TARGET"`:
1. Search Passes 1, 2, and 3 all execute and appear in the record.
2. Portfolio names the single target and states in `why_develop` why a second defensible materially distinct target does not exist.
3. Exactly one Deep pass develops that target.
4. No Critic, no Compare, no LEVER, no winner.
5. The handoff renders one development target plus the recorded reason no second target was developed.

---

## 7. Semantic Stage Budgets and Repairs

### Stage Budgets
- **Dual BONK:** Search ×3 + Portfolio + Deep A + Deep B = **6 semantic stages**.
- **Degraded single BONK:** Search ×3 + Portfolio + Deep = **5 semantic stages**.
- Final assembly, `run.md` rendering, and archive creation add **zero** semantic stages.

### Bounded Repair Limits
- Max 1 model repair per stage.
- Max 2 model repairs across the entire BONK run.
- If budget or repairs are exhausted, fail closed with `BUDGET_EXHAUSTED`.

---

## 8. Legacy Compatibility and Manual Primitives

- `pizm-portfolio-selection-v2`, `comparison-review-v1`, `deep-compare.md`, and `deep-reviewer.md` are **not deleted**. Existing archived BONK v2 runs remain readable and renderable; v2 is read compatibility only and is never written by new BONK runs.
- Manual `/pizm critic` remains available as an advanced/experimental primitive and still uses `references/deep-reviewer.md`.
- Manual `/pizm lever` remains available under its current gate.
- AUTO is unchanged: `/pizm auto` still runs its own pipeline, including its Critic stage.
- `/pizm synthesize` does not exist. Do not invent a synthesis stage, a comparison stage, or a third model inside BONK.
