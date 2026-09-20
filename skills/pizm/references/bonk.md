# Pizm BONK Pipeline Contract

BONK is the heavy automated path of Pizm that performs two-pass Search, judges the accumulated field for competing composite models, develops both models independently (Deep left and Deep right), executes adversarial Critic and comparative reasoning, runs optional LEVER on a ready target, and renders a deterministic final report plus deterministic `run.md` and `run.html`.

**Date:** 2026-08-25
**Prerequisite:** Plan 1 semantic primitives (Search Field v1, deterministic B-IDs, Deep v2, Critic v2, LEVER, atomic freeze checkpoints, deterministic session renderer).

---

## 1. Explicit Delegation Requirement

BONK executes ONLY via explicit user delegation:

```text
/pizm bonk <task>
```

Manual Pizm modes (`/pizm`, `normal`, `explore`, `rift`, `360`, `deep`, `/pizm lever`, `/pizm auto`) NEVER trigger or emulate BONK behavior. Discussing BONK with the user remains possible without executing it.

---
## Operational happy path

For normal successful BONK execution, follow the commands and artifact schemas in this contract and the currently loaded stage contracts directly. Do not invoke Pizm CLI `--help`, inspect Pizm Python source, or read Pizm tests before attempting prescribed operations. If the prescribed command succeeds, continue immediately to the next pipeline step.

### Stage-contract loading order
- Stage 1–2: Load `references/explore.md` for Search Pass 1 (initial) and Search Pass 2 (residual).
- Stage 3: Reveal `references/explore-selector.md` only after final Search Field freeze (`pass02`).
- Stage 4: Reveal `references/deep.md` for sequential Deep(LEFT) and Deep(RIGHT) development.
- Stage 5: Reveal `references/deep-reviewer.md` and `references/deep-compare.md` only after BOTH Deep LEFT and Deep RIGHT are frozen and hash-verified.
- Stage 6: Reveal `references/lever.md` and `references/lever-reviewer.md` only when the conditional LEVER gate fires (`task_orientation == "ACTION_OR_DECISION"` and preferred target is `MODEL_READY`).

### Freeze success and repair rules
- `FREEZE_OK` from the prescribed checkpoint command is authoritative for that freeze. After `FREEZE_OK`, do not reopen validator source/tests or re-read the just-frozen artifact solely to verify the successful freeze.
- Validator rejection is not permission for unrestricted repository archaeology. First repair directly from: (1) the surfaced validation error, (2) the current stage contract, and (3) the existing bounded repair budget. Inspect implementation files only if these are genuinely insufficient to continue.

---


## 2. Target Topology & Execution Sequence

```text
Search(initial)
→ freeze explore pass 01 + search-field manifest

Search(residual)
→ freeze explore pass 02 + search-field manifest

Portfolio Judge over accumulated field
→ identify two defensible competing Bundles when possible (pizm-portfolio-selection-v2, route BONK)

Deep(LEFT)
→ freeze development-v2-<left_target_id>

Deep(RIGHT)
→ freeze development-v2-<right_target_id>

Critic + Compare(LEFT, RIGHT)
→ reveal references/deep-compare.md
→ freeze comparison-review-v1

[conditional] LEVER on preferred MODEL_READY model (design + review)

deterministic FINAL assembly (zero model calls)
deterministic run.md and run.html rendering (zero model calls)
```

---

## 3. Detailed Stage Contracts

### Stage 0: Run Identity (before any freeze)
- Derive `subject_slug` from the task subject with the deterministic ASCII rule (`bin/pizm_run_state.py slugify_subject`: lowercase, Cyrillic transliterated, non-alphanumeric → hyphens). Mint one run-id `<subject_slug>-YYYYMMDDtHHMMSSz-<rand4>` (UTC timestamp + 4 lowercase-alphanumeric chars, same shape as `generate_run_id`). Use this run-id for every `--run-id` freeze below (run dir becomes `.ai/pizm/run-<run-id>/`) and for `--slug` at archive time, so run dir, bundle, and reader slug stay aligned. Never use a bare timestamp or short random id.

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
- **No automatic third Search.** BONK v1 executes exactly two automatic Search passes.

### Stage 3: Portfolio Judge over Accumulated Field
- Reveal `references/explore-selector.md`.
- Evaluate all accumulated candidates from both passes categorically and structurally.
- Freeze one portfolio record conforming to `pizm-portfolio-selection-v2`:
  - Enforce `route: "BONK"`.
  - Enforce `field_ref` (pointing to the exact frozen search field JSON) and `field_hash` (matching its frozen SHA-256 sidecar).
  - Provide canonical `perspectives` mapping (`{"P1": "pass01:c01", "P2": "pass01:c02", "P3": "pass02:c01", ...}`) which strictly controls rendered perspective labels and continued P-IDs across passes.
  - Enforce `competition_status`: `"TWO_DEFENSIBLE_BUNDLES"` or `"NO_SECOND_DEFENSIBLE_BUNDLE"`.
  - When two defensible bundles exist (`TWO_DEFENSIBLE_BUNDLES`):
    - `recommended_competition` specifies `left_bundle_id`, `right_bundle_id`, `competition_axis`, `discriminating_observation`, and optional `discriminating_question`.
    - Both left and right bundles require genuine composition gain, bundle thesis, member ablation (no passengers), internal tension, and distinct explanatory programs.
    - Competing pair must differ on a load-bearing axis (e.g. primary mechanism, binding constraint, system boundary, agency location, time dynamics, causal direction, prediction, intervention implication).
    - `single_target` is forbidden in dual competition.
  - When no second defensible bundle exists (`NO_SECOND_DEFENSIBLE_BUNDLE`):
    - `competition_status = "NO_SECOND_DEFENSIBLE_BUNDLE"`.
    - `recommended_competition = null`.
    - Required `single_target = {"target_type": "B", "target_id": "B<n>"}` (or `"target_type": "P"`).
    - Do not invent or force an artificial second bundle.
  - `auto_target` is forbidden in all v2 portfolios.

### Stage 4: Deep(LEFT) & Deep(RIGHT)
- When two defensible bundles exist:
  - **Sequential execution:** Develop LEFT → freeze → Develop RIGHT → freeze. First Deep freeze emits no comparison contract.
  - Each bundle receives a separate full development inference under the `pizm-development-v2` contract (`references/deep.md`).
  - Target identity locks freeze bundle membership (`member_refs`), thesis, mechanism, and boundaries.
  - Soft guidance: ~1400–2400 words per bundle when material supports it.
  - **Hard prohibitions:**
    - Do NOT Deep bundle members individually (one bundle = one Deep).
    - Do NOT combine LEFT and RIGHT into a single joint development.
    - Do NOT critique LEFT before developing RIGHT.
  - Freeze `development-v2-<left_target_id>` and `development-v2-<right_target_id>` using `bin/pizm-checkpoint freeze --stage development-v2 --target <left_target_id> ...` and `--target <right_target_id> ...`.

### Stage 5: Critic and Comparative Review
- Revealed (`references/deep-reviewer.md` + `references/deep-compare.md`) only after BOTH Deep LEFT and Deep RIGHT are frozen and hash-verified.
- Execute adversarial critique and comparative reasoning under `pizm-comparison-review-v1` (`references/deep-compare.md`):
  - Each side review is a full Deep Reviewer pass under the CURRENT `references/deep-reviewer.md` (all checks, §3b use-site warrant with 1–3 tables per side, B1–B4 readiness semantics). The freeze enforces the tables; a side frozen without them is rejected.
  - Declare explicit LEFT and RIGHT development artifact references and verified frozen hashes (`left_review.development_ref`, `left_review.frozen_hash`, `right_review.development_ref`, `right_review.frozen_hash`), verifying targets matching LEFT and RIGHT bundle IDs.
  - Act as critic of LEFT, critic of RIGHT, and comparative reasoner using the 8-move Critic arsenal.
  - Formulate independent countermodels, audit load-bearing claims, flag unsupported specificity and epistemic laundering, and identify shared evidence debt.
  - Determine `current_preference`: `LEFT | RIGHT | CONDITIONAL | UNRESOLVED`.
  - **No forced winner:** `CONDITIONAL` and `UNRESOLVED` are first-class terminal states.
  - Specify `competition_axis`, `strongest_reason_for_left`, `strongest_reason_for_right`, `discriminating_observation`, and `what_would_change_the_decision`.
  - **Decision rule:** An unresolved load-bearing contradiction or `RETURN_TO_EXPLORE` state in a bundle's review blocks preference for that bundle.
- Freeze artifact via `bin/pizm-checkpoint freeze --stage comparison-review-v1 --run-id <slug> --input <path>`.

### Stage 6: Optional LEVER
- Automatically runs ONLY when:
  - Task orientation is `ACTION_OR_DECISION` (classified during judging).
  - AND the comparison identifies a suitable `MODEL_READY` target (or single-bundle degraded route is `MODEL_READY`).
- If `current_preference` is `CONDITIONAL` or `UNRESOLVED`: do NOT force LEVER; surface the discriminating observation as the recommended next step.
- If task orientation is `ANALYTICAL`: do not run LEVER.
- When executed, runs standard manual LEVER design and review (`references/lever.md` and `references/lever-reviewer.md`).
### Stage 7: Deterministic FINAL Assembly, run.md, and run.html
- **Deterministic Finalization Fast Path**: Once the last semantic artifact required by the BONK run (Comparison Review or degraded single Critic) is successfully frozen, semantic reasoning is finished. Proceed immediately through finalization:
  1. execute the canonical `create` command to archive the run;
  2. render the readable Markdown record;
  3. render interactive HTML with `--ensure-reader`;
  4. report the final user-facing summary with Reader URL or direct file URL.
- **Prohibitions during finalization**:
  - Do not inspect Pizm tests, CLI `--help`, or `bin/pizm-session-bundle` source.
  - Do not read back generated `run-<subject-slug>.md` or `run-<subject-slug>.html` into context.
  - Do not re-render outputs or copy named files to legacy `run.md`/`run.html` (named records are authoritative; do not manufacture duplicate files).
  - Do not perform an unrequested extra semantic review turn.
  - If any deterministic command succeeds, trust its output and proceed to the next step.

- **Canonical Session Archive Command Template (`create`)**:
  Execute archive creation using this exact recipe for two-bundle competition (zero `--help` calls needed):
  ```bash
  bin/pizm-session-bundle create \
    --output-root .ai/pizm/bundles \
    --slug "$RUN_ID" \
    --skill-root skills/pizm \
    --stage pass-01-normal=".ai/pizm/run-$RUN_ID" \
    --stage pass-02-residual=".ai/pizm/run-$RUN_ID" \
    --stage search-field=".ai/pizm/run-$RUN_ID" \
    --stage portfolio=".ai/pizm/run-$RUN_ID" \
    --stage deep-"$LEFT_ID"=".ai/pizm/run-$RUN_ID" \
    --stage deep-"$RIGHT_ID"=".ai/pizm/run-$RUN_ID" \
    --stage comparison-review=".ai/pizm/run-$RUN_ID" \
    --accounting "$ACCOUNTING_JSON" \
    --subject-slug "$SUBJECT_SLUG" \
    --provider "$PROVIDER" \
    --model "$MODEL" \
    --model-source "$MODEL_SOURCE" \
    --pizm-version "$PIZM_VERSION" \
    --evidence-kind live
  ```
  *(Notes: for degraded single-bundle runs with `NO_SECOND_DEFENSIBLE_BUNDLE`, pass single `--stage deep-"$TARGET_ID"=".ai/pizm/run-$RUN_ID"` and omit `comparison-review`; if LEVER was executed, append `--stage lever-"$TARGET_ID"=".ai/pizm/run-$RUN_ID"`).*

- **Deterministic Markdown and HTML Rendering**:
  Render the readable `run.md` deterministically using `bin/pizm-session-bundle render --run-dir ".ai/pizm/run-$RUN_ID" --task "<task>" --subject-slug "$SUBJECT_SLUG"` (writes the named record `run-<subject-slug>.md`; report that path).
  Render the interactive full-trace `run.html` and resolve the reader link deterministically:
  ```bash
  $HOME/.local/bin/pizm-session-bundle render-html --run-dir ".ai/pizm/run-$RUN_ID" --task "<task>" --subject-slug "$SUBJECT_SLUG" --provider "$PROVIDER" --model "$MODEL" --model-source "$MODEL_SOURCE" --pizm-version "$PIZM_VERSION" --ensure-reader
  ```
  - If the local reader server is active, the tool outputs `READER_URL http://127.0.0.1:41144/run/<slug>/`. Present this URL in the final report.
  - If inactive or on port collision, the tool outputs `READER_OFFLINE file://<path>/run.html (local reader server inactive)`. Present this deterministic `file://` fallback.
- In the final user-facing report, include the reading records:
  ```markdown
  ## Reading & Reader Record
  - **Readable Record**: `<run-dir>/run-<subject_slug>.md`
  - **Interactive Trace**: `<run-dir>/run-<subject_slug>.html`
  - **Reader URL**: `http://127.0.0.1:41144/run/<run-id>/` (or `file://<absolute-path>/run-<subject_slug>.html` if local reader server inactive)
  ```
- Output is a pure, byte-identical function of frozen inputs.
- **Run Fingerprint Contract**: Capturing model, provider, model source (`HOST_RUNTIME | EXPLICIT_OVERRIDE | UNKNOWN`), Pizm version (`skills/pizm/VERSION`), and subject slug into the archive manifest AND the rendered `run.html` header is pure execution bookkeeping: pass the same flag values to `create` and to `render-html` (explicit `UNKNOWN` when the host cannot report a value exactly). Without these flags the header falls back to `not recorded (legacy)`. Zero additional inference calls are performed. Metadata never enters reasoning prompts or influences candidate generation. If the host reports a `provider/model` composite in `--model` with no separate provider, capture and render normalize it deterministically (first-`/` split); prefer passing `--provider` and `--model` separately when both are known.
---

## 4. Degraded Path (Single Defensible Bundle)

If Portfolio records `competition_status: NO_SECOND_DEFENSIBLE_BUNDLE`:
1. Search Pass 1 (initial) and Pass 2 (residual) both execute and appear in the record.
2. Portfolio identifies `single_target` (e.g. B1 or standalone P) and explicitly notes `NO_SECOND_DEFENSIBLE_BUNDLE`.
3. Compare stage is skipped without failing the run.
4. Deep develops `single_target.target_id`.
5. Single-model Critic evaluates the developed target (`pizm-deep-review-v2`).
6. Optional LEVER runs if task is `ACTION_OR_DECISION` and status is `MODEL_READY`.
7. Final report, `run.md`, and `run.html` state `NO_SECOND_DEFENSIBLE_BUNDLE` and render single-model review.

---

## 5. Semantic Stage Budgets and Repairs

### Stage Budgets
- **Analytical BONK (2 Bundles):** Pass 1 + Pass 2 + Portfolio + Deep LEFT + Deep RIGHT + Critic/Compare = **6 semantic stages**.
- **Action BONK with LEVER (2 Bundles):** 6 + Lever Design + Lever Review = **8 semantic stages**.
- **Degraded Single-Bundle Path:** 5 stages (analytical) or 7 stages (with LEVER).
- Final assembly, `run.md`, and `run.html` rendering add **zero** semantic stages.

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
- Max 2 model repairs across the entire BONK run.
- If budget or repairs are exhausted, fail closed with `BUDGET_EXHAUSTED`.
