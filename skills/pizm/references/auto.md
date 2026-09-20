# Pizm AUTO v1 Pipeline Contract

AUTO is an automated execution mode of Pizm that executes exactly one bounded path — Search(initial), Search(rift), Portfolio Judge, Deep on one nominated target, Critic review, optional LEVER — and then renders a deterministic final report plus deterministic `run.md` and `run.html`.

## Explicit Delegation Requirement

AUTO executes ONLY via explicit `/pizm auto <task>` user delegation. Manual Pizm modes (`/pizm`, `normal`, `explore`, `rift`, `360`, `deep`, `/pizm lever`) NEVER trigger or emulate AUTO behavior. Discussing AUTO with the user remains possible without executing it.

AUTO enforces a strict single-target rule: exactly one nominated target (P or B) is deepened. AUTO executes two bounded Search passes before Portfolio: Pass 1 (initial) and Pass 2 (rift). There is no third Search pass, no second Deep, no alternative branch, no decide stage or inference, no secondary candidate concept, and no auto-360 or reroll loops.

---
## Operational happy path

For normal successful AUTO execution, follow the commands and artifact schemas in this contract and the currently loaded stage contract directly. Do not invoke Pizm CLI `--help`, inspect Pizm Python source, or read Pizm tests before attempting prescribed operations. If the prescribed command succeeds, continue immediately to the next pipeline step.

### Stage-contract loading order
- Load `references/explore.md` when Search begins (initial pass).
- Reveal `references/explore-selector.md` only after final Search Field freeze (`pass02`). Do not inspect validator/test implementations to learn future-stage schemas before reaching that stage.
- Reveal `references/deep.md` only after Portfolio nominates a `DEEP` target (`auto_target`).
- Reveal `references/deep-reviewer.md` only through the normal post-Deep freeze reveal.
- Reveal `references/lever.md` and `references/lever-reviewer.md` only when the conditional LEVER gate fires (`task_orientation == "ACTION_OR_DECISION"` and `terminal_state == "MODEL_READY"`).

### Freeze success and repair rules
- `FREEZE_OK` from the prescribed checkpoint command is authoritative for that freeze. After `FREEZE_OK`, do not reopen validator source/tests or re-read the just-frozen artifact solely to verify the successful freeze.
- Validator rejection is not permission for unrestricted repository archaeology. First repair directly from: (1) the surfaced validation error, (2) the current stage contract, and (3) the existing bounded repair budget. Inspect implementation files only if these are genuinely insufficient to continue.

---


## 1. Pipeline Execution Sequence

The AUTO pipeline executes dynamic reasoning-budget routing based on the Portfolio Judge decision:

```text
AUTO TASK
→ optional pre-search high-information questions (default 0; normal max 1)
→ Search(initial) pass01 GENERATE → freeze explore pass01 + search-field manifest pass01
→ Search(rift) pass02 GENERATE → freeze explore pass02 + search-field manifest pass02
→ PORTFOLIO JUDGE over accumulated field → freeze portfolio record (route AUTO)
   ├─ [next_reasoning_move: DEEP]
   │  → DEEP(target) DEVELOP (development-v2) → freeze
   │  → CRITIC REVIEW (deep-review-v2) → freeze
   │  → [conditional] same manual LEVER primitive (design + review)
   │  → deterministic FINAL assembly + run.md + run.html
   ├─ [next_reasoning_move: GATHER_INFORMATION]
   │  → intentional terminal outcome: freeze information request (no Deep/Critic)
   │  → deterministic FINAL assembly + run.md + run.html (renders questions / observation)
   └─ [next_reasoning_move: PRESERVE_ONLY]
      → intentional terminal outcome: freeze preserved field (no Deep/Critic)
      → deterministic FINAL assembly + run.md + run.html (renders preserved field)
```

### Stage Execution Details:

1. **AUTO TASK**: Receive the user's task prompt via `/pizm auto <task>`.
   - **Optional Pre-search Information Gathering**: Pre-search budget is default 0 questions; normal pre-search maximum is 1 high-information question. Ask one high-information clarifying question before committing to Search only when an unresolved scope fork has two or more plausible answers whose answers materially redirect the solution family, search territory, load-bearing constraints, evidence interpretation, or reasoning route. (The broader 0–3 clarifying question allowance is retained only for compatibility with post-Search GATHER_INFORMATION when a newly discovered material route fork surfaces after Search/Portfolio). Consuming existing context first is mandatory; do not ask generic preference questionnaires or if materially relevant branches can be honestly and cheaply covered within Search. In a noninteractive context, do not block: span plausible branches across Pass 1 candidates when feasible, or state the assumed branch and preserve the alternative as a declared material assumption (host guidance only, not a runtime detector). Pre-search questions are the primary clarification path.
   - **Run Identity (before any freeze)**: Derive `subject_slug` from the task subject with the deterministic ASCII rule (`bin/pizm_run_state.py slugify_subject`: lowercase, Cyrillic transliterated, non-alphanumeric → hyphens). Mint one run-id `<subject_slug>-YYYYMMDDtHHMMSSz-<rand4>` (UTC timestamp + 4 lowercase-alphanumeric chars, same shape as `generate_run_id`). Use this run-id for every `--run-id` freeze below (run dir becomes `.ai/pizm/run-<run-id>/`) and for `--slug` at archive time, so run dir, bundle, and reader slug stay aligned. Never use a bare timestamp or short random id.
2. **Search Pass 1 (initial)**: Run initial Search adhering to `references/explore.md` (soft target 12–16 candidates when supported; hard bounds 1..20 candidates, ≤ 192 KiB total payload, ≤ 12 KiB per candidate). Freeze raw pass via `bin/pizm-checkpoint freeze --stage explore --run-id <slug> --artifact-suffix pass01 --input <path>` -> creates `candidates-pass01.json`. Register `pass01` in the append-only search-field manifest conforming to `pizm-search-field-v1` and freeze via `bin/pizm-checkpoint freeze --stage search-field --run-id <slug> --artifact-suffix pass01 --input <path>` -> creates `search-field-pass01.json`. No judging or selector reveal occurs after Pass 1.
3. **Search Pass 2 (rift)**: Consume the frozen accumulated field from Pass 1. Using the already loaded `references/explore.md`, run second Search pass adhering to the RIFT search policy (searching for distant structural shifts, reframing unit of analysis/causality/scale, avoiding occupied territory). Freeze raw pass via `bin/pizm-checkpoint freeze --stage explore --run-id <slug> --artifact-suffix pass02 --input <path>` -> creates `candidates-pass02.json`. Update the search-field manifest naming `search-field-pass01.json` as `prior_ref` with verified `prior_hash` and freeze via `bin/pizm-checkpoint freeze --stage search-field --run-id <slug> --artifact-suffix pass02 --input <path>` -> creates `search-field-pass02.json`. No automatic third Search exists.
4. **PORTFOLIO JUDGE**: Only after verified final search-field freeze, reveal `references/explore-selector.md`. The judge evaluates the exact accumulated field from both passes categorically and freezes one portfolio record conforming to `pizm-portfolio-selection-v1` with `route: "AUTO"`, explicit `field_ref: "search-field-pass02.json"` matching `field_hash`, and chooses `next_reasoning_move`:
   - `DEEP`: nominates exactly one `auto_target` (`{"target_type": "P"|"B", "target_id": ...}`) and an optional live `rival_shadow`. Proceeds to Deep development.
   - `GATHER_INFORMATION`: intentional completed terminal outcome. Reserved strictly for a newly discovered material route fork surfaced by Search/RIFT/Portfolio that could not reasonably have been asked before search. If pre-search questions were already asked, prefer 1 additional question, not a routine questionnaire. Emits an `information_request` (mode `USER_QUESTION` or `EXTERNAL_OBSERVATION`) and terminates without developing Deep or invoking Critic/LEVER.
   - `PRESERVE_ONLY`: intentional completed terminal outcome. Preserves the field without further reasoning spend and terminates without developing Deep or invoking Critic/LEVER.
   - **Task orientation**: while judging, classify the task as `ANALYTICAL` or `ACTION_OR_DECISION`, reusing the existing bounded judgment already exercised in the conversation (no classifier call, no extra model turn, no new semantic abstraction). If genuinely ambiguous, default to `ANALYTICAL`. Orientation is conversational routing metadata; it adds no semantic stage.
5. **DEEP(target) DEVELOP**: If `next_reasoning_move == "DEEP"`, deepen exactly the nominated target following `references/deep.md` under the development-v2 contract. The developed artifact's target must equal the portfolio's `auto_target` verbatim: a promoted perspective (`P<n>`, identity lock preserving its `p_id`) or a proposed bundle (`B<n>`, identity lock freezing `member_refs`; one Bundle = one Deep, never per-member mini-Deeps). Single Deep only. If `rival_shadow` was frozen in Portfolio, Deep receives it and records `comparative_standing`.
6. **Freeze Deep**: Freeze the development-v2 artifact before any review begins. In AUTO mode, the checkpoint will reveal `references/deep-reviewer.md`.
7. **CRITIC REVIEW**: Execute independent critic review following `references/deep-reviewer.md` under the `pizm-deep-review-v2` contract and freeze the review artifact.
8. **Conditional LEVER Primitive**:
   - If `terminal_state == "MODEL_READY"` AND `task_orientation == "ACTION_OR_DECISION"`:
     Execute the same manual LEVER primitive (`references/lever.md` and `references/lever-reviewer.md`) using identical prompts and review logic as `/pizm lever`, with zero duplication.
   - Otherwise (if `task_orientation == "ANALYTICAL"` or `terminal_state != "MODEL_READY"`):
     Do not invoke LEVER.
9. **FINAL Assembly + run.md**: Assemble the final output deterministically from frozen artifacts (Section 3).
   - **Deterministic Finalization Fast Path**: Once the last semantic artifact required by the selected branch is successfully frozen, semantic reasoning is finished. Proceed immediately through finalization:
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

   - **Execution Scope & Root Contract**:
     The displayed `bin/pizm-session-bundle` and `skills/pizm` commands are verified for execution from the Prism repository checkout. An installed host must use the helper and skill root deployed together by the supported installer, must not mix repo and installed locations, and must be synchronized to the label-aware version before executing this flow.

   - **Canonical Session Archive Command Template (`create`)**:
     Execute archive creation using this exact recipe (zero `--help` calls needed):
     ```bash
     bin/pizm-session-bundle create \
       --output-root .ai/pizm/bundles \
       --slug "$RUN_ID" \
       --skill-root skills/pizm \
       --stage pass-01-normal=".ai/pizm/run-$RUN_ID" \
       --stage pass-02-rift=".ai/pizm/run-$RUN_ID" \
       --stage search-field=".ai/pizm/run-$RUN_ID" \
       --stage portfolio=".ai/pizm/run-$RUN_ID" \
       --stage deep-"$TARGET_ID"=".ai/pizm/run-$RUN_ID" \
       --accounting "$ACCOUNTING_JSON" \
       --subject-slug "$SUBJECT_SLUG" \
       --provider "$PROVIDER" \
       --model "$MODEL" \
       --model-source "$MODEL_SOURCE" \
       --pizm-version "$PIZM_VERSION" \
       --evidence-kind live
     ```
     *(Notes: if LEVER was executed, append `--stage lever-"$TARGET_ID"=".ai/pizm/run-$RUN_ID"`; for honest-stop terminal portfolios without Deep, omit the `deep-...` stage).*

   - **Deterministic Markdown and HTML Rendering**:
     Render the readable `run.md` deterministically with the session-bundle tool (`bin/pizm-session-bundle render --run-dir ".ai/pizm/run-$RUN_ID" --task "<original task>" --subject-slug "$SUBJECT_SLUG"`). The renderer reads ONLY frozen checkpoint artifacts, emits byte-identical output for identical inputs, and performs zero model calls. Next, render the interactive `run.html` and resolve the reader link deterministically:
     ```bash
     bin/pizm-session-bundle render-html --run-dir ".ai/pizm/run-$RUN_ID" --task "<original task>" --subject-slug "$SUBJECT_SLUG" --provider "$PROVIDER" --model "$MODEL" --model-source "$MODEL_SOURCE" --pizm-version "$PIZM_VERSION" --ensure-reader
     ```
   - **Reader Link Contract**:
     - If the local reader server is active, `bin/pizm-session-bundle render-html --ensure-reader` outputs `READER_URL http://127.0.0.1:41144/run/<run-id>/`. Present this URL in the final report.
     - If the reader server is inactive or fails to start, the tool outputs `READER_OFFLINE file://<path>/run-<subject_slug>.html (local reader server inactive)`. Present this deterministic direct file URL.
     - Reader availability must NEVER block or fail the run: the semantic results and frozen artifacts are already authoritative.
   - **Artifact & Suffix Chain**: Checkpoint artifacts follow the standard freeze chain: `candidates-pass01.json`, `search-field-pass01.json`, `candidates-pass02.json`, `search-field-pass02.json`, `portfolio.json`, `development-v2-$TARGET_ID.json`, `deep-review-v2-$TARGET_ID.json` (and optional `design.json` / `review.json`).
   - **Ephemeral Accounting Contract**: `--accounting <path>` supplies caller-provided bounded non-derived counts (`host_inference_count`, `model_repair_count`, `checkpoint_retry_count`). The bundle computes and validates derived counts (`semantic_stage_count`, `candidate_bytes`, `development_bytes`). The archive manifest records the normalized six-counter object; the ephemeral accounting file is never archived into inputs.
   - **Run Fingerprint Contract**: Capturing model, provider, model source (`HOST_RUNTIME | EXPLICIT_OVERRIDE | UNKNOWN`), Pizm version (`skills/pizm/VERSION`), and subject slug into the archive manifest AND the rendered `run.html` header is pure execution bookkeeping: pass the same flag values to `create` and to `render-html` (explicit `UNKNOWN` when the host cannot report a value exactly). Without these flags the header falls back to `not recorded (legacy)`. Zero additional inference calls are performed. Metadata never enters reasoning prompts or influences candidate generation. If the host reports a `provider/model` composite in `--model` with no separate provider, capture and render normalize it deterministically (first-`/` split); prefer passing `--provider` and `--model` separately when both are known.
---

## 2. Honest-Stop Rules

- **Portfolio Terminal Outcomes**: If the Portfolio Judge produces `next_reasoning_move == "GATHER_INFORMATION"` or `next_reasoning_move == "PRESERVE_ONLY"`, execution stops honestly as a completed run at Portfolio. No Deep/Critic/LEVER artifacts are created, and execution does not auto-resume. Continuation requires explicit fresh user instruction or a fresh run.
- **Critic Non-Ready Outcomes**: If the Critic produces `terminal_state == "NEED_EVIDENCE"` or `terminal_state == "RETURN_TO_EXPLORE"`, execution MUST stop honestly at that point with the stated reason from the review verdict.
- No other search or refinement primitive starts afterward (no second Deep, no alternative branch, no reroll, no auto-recovery).
- The pipeline proceeds directly to FINAL assembly to render the honest-stop report and its `run.md`.
---

## 3. Deterministic FINAL Assembly

`FINAL` is a DETERMINISTIC ASSEMBLY rendered directly from frozen structured artifacts (`candidates-pass01.json`, `candidates-pass02.json`, the search-field manifest, `portfolio.json`, `development-v2-$TARGET_ID.json`, `deep-review-v2-$TARGET_ID.json`, and `design.json` / `review.json` if LEVER was executed).

- **Zero Model Invocations**: FINAL increments neither `semantic_stage_count` nor `host_inference_count` and performs ZERO tool-call model turns. The subsequent `run.md` rendering is equally deterministic: byte-identical output for identical frozen inputs, zero model calls.
- **Contract Prohibition**: If an implementation ever requires an additional model turn or tool call for FINAL or for `run.md` rendering, STOP and replan the budget/contract instead of hiding it.
- **Fixed Assembly Template**: The final response is formatted strictly using the fixed deterministic template below:

### Fixed FINAL Assembly Template

```markdown
# Pizm AUTO Analysis: <Task Title / Summary>

## 1. Nominated Perspective
- **Target**: <P<n> | B<n>> — <Title>
- **Source**: <auto_target nominated by the frozen portfolio record>
- **Task Orientation**: <ANALYTICAL | ACTION_OR_DECISION>
- **Core Claim / Shift**: <identity_lock claim / structural_shift>
- **Grounding Anchor**: <identity_lock grounding basis>
- **Boundary**: <identity_lock boundary>

## 2. Developed Model Summary
- **Thesis**: <developed_model.thesis>
- **Primary Mechanism**: <mechanism_chain or identity_lock mechanism>
- **Load-Bearing Claims**: <census claims with epistemic statuses>
- **Key Predictions**: <predictions_or_observables>
- **Evidence Debt**: <evidence_debt>

## 3. Deep Review Verdict
- **Terminal State**: <MODEL_READY | NEED_EVIDENCE | RETURN_TO_EXPLORE>
- **Review Rationale**: <verdict_rationale from the deep-review-v2 record>
<!-- IF terminal_state != "MODEL_READY": -->
- **Stop Reason**: Honest stop triggered due to non-ready status (<terminal_state>). No further primitives executed.
<!-- END IF -->

<!-- IF LEVER executed (task_orientation == "ACTION_OR_DECISION" AND terminal_state == "MODEL_READY"): -->
## 4. Reality-Facing Levers
<!-- For each accepted lever from the lever review: -->
### Lever <lever_id>: <intervention_or_test_point>
- **Model Link**: <model_link>
- **Minimum Bounded Move**: <minimum_bounded_move>
- **Expected Observation**: <expected_observation_or_response>
- **Disconfirming Signal**: <disconfirming_signal>
- **Stop Condition**: <stop_condition>
- **Remaining Assumptions**: <remaining_assumptions>
<!-- If adaptation_or_countermove present: -->
- **Adaptation / Countermove**: <adaptation_or_countermove>
<!-- End For -->
- **Lever Review Outcome**: <LEVER | NO_DEFENSIBLE_LEVER> (<verdict_rationale>)
<!-- END IF -->

## Reading & Reader Record
- **Readable Record**: `<run-dir>/run.md`
- **Interactive Trace**: `<run-dir>/run.html`
- **Reader URL**: `http://127.0.0.1:41144/run/<slug>/` (or `file://<absolute-path>/run.html` if local reader server inactive)
```

After presenting FINAL, render `run.md` and `run.html` for the reading record: all candidate ideas appear compactly, the developed model and critic verdict are rendered fully enough for normal reading, and machine bookkeeping (hashes, schema strings, byte counts, repair/host counters) stays out of the readable document. Resolve the local reader link via `bin/pizm-session-bundle render-html --ensure-reader`, falling back deterministically to the local `file://` URL if the reader server is inactive.

## 4. Operational Cost Accounting and Ceilings

### Semantic Stage Budget

- Base AUTO path: Search(initial) + Search(rift) + Portfolio + Deep + Critic = 5 semantic stages.
- Optional LEVER: Design + Review add 2 semantic stages = 7 semantic stages total.
- FINAL assembly, `run.md`, and `run.html` rendering are deterministic: they add zero semantic stages.

### Accounting and Counters

The bundle archive manifest records all six normalized counters:
1. `semantic_stage_count` (derived from stage collection)
2. `host_inference_count` (caller-supplied non-derived counter)
3. `model_repair_count` (caller-supplied non-derived counter)
4. `checkpoint_retry_count` (caller-supplied non-derived counter)
5. `candidate_bytes` (derived from frozen candidate JSON byte sizes)
6. `development_bytes` (derived from frozen development JSON byte sizes)

### Repair Accounting

- Repairs and tool-loop continuations are accounted separately from the semantic stage budget.
- max 1 model repair per stage.
- max 2 model repairs across the entire AUTO run.
- No unbounded retries.
### Fail-Closed Budget Enforcement

If semantic stage or model repair ceilings are exhausted at any point:
- The run immediately terminates with `BUDGET_EXHAUSTED`.
- Fail-closed rule: Do not reveal unreached future-stage contracts or rubrics.
- Archive failure evidence and report `BUDGET_EXHAUSTED` with the exact stage reached.

---

## 5. Known Limitation Note (OBSERVE_IN_DOGFOOD)

In same-host execution, the Portfolio Judge and Deep DEVELOP see earlier stage context (generator prose, selector rubric) in conversation history. This is accepted as `OBSERVE_IN_DOGFOOD` per W0 reconciliation Risk 1:
- The judged field is always the hash-frozen artifact set, never loose conversation content.
- Deep DEVELOP remains structurally blind to its own Critic rubric until after the development-v2 artifact is frozen.
