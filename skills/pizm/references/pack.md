# Pizm PACK v1 Pipeline Contract

PACK is the recommended automated exploration route of Pizm. It executes exactly one bounded path — Search(initial), Search(residual), Search(rift), and Portfolio Curation — and then renders a deterministic research packet (`research-pack-<slug>.md`).

PACK uses a cheap host model to expand and structure the hypothesis space before a stronger model or human performs final synthesis, epistemic judgment, or decision-making.

## Explicit Delegation Requirement

PACK executes ONLY via explicit `/pizm pack <task>` user delegation. Manual Pizm modes (`/pizm`, `normal`, `explore`, `rift`, `360`, `deep`, `/pizm lever`) NEVER trigger or emulate PACK behavior. Discussing PACK with the user remains possible without executing it.

## Execution Scope & Root Contract

PACK's helper executables and skill root are location-dependent. Resolve them once, before the first freeze, and use the resolved values everywhere:

```text
$PIZM_CHECKPOINT       repo checkout: bin/pizm-checkpoint
                       installed host: $HOME/.local/bin/pizm-checkpoint
$PIZM_SESSION_BUNDLE   repo checkout: bin/pizm-session-bundle
                       installed host: $HOME/.local/bin/pizm-session-bundle
$PIZM_SKILL_ROOT       the directory containing the currently loaded Pizm SKILL.md
                       repo checkout: skills/pizm
                       installed host: $HOME/.claude/skills/pizm or $HOME/.config/opencode/skills/pizm
```

An installed host must use the helper and skill root deployed together by the supported installer, must not mix repo and installed locations, and must be synchronized to the label-aware version before executing this flow. Every command recipe below is written with these variables: a displayed `bin/...` or `skills/pizm` path is the repo-checkout value of the same variable, never a separate command.

## Core Operational Promise & Non-Claims

PACK is an expansion, structuring, and handoff route, NOT an adjudication or validation route.

Prism PACK explicitly does not establish or claim that:
- any Perspective is true;
- any Bundle is validated;
- any candidate is a final recommendation;
- any causal mechanism has been independently verified;
- Prism's curation represents a truth ranking.

PACK produces ZERO Deep stages, ZERO Critic stages, ZERO Comparison stages, and ZERO LEVER stages. It never emits `MODEL_READY` or selects a winning hypothesis.

---

## Operational Happy Path

For normal successful PACK execution, follow the commands and artifact schemas in this contract and the currently loaded stage contract directly. Do not invoke Pizm CLI `--help`, inspect Pizm Python source, or read Pizm tests before attempting prescribed operations. If the prescribed command succeeds, continue immediately to the next pipeline step.

### Stage-Contract Loading Order
1. Load `references/explore.md` when Search begins (covers `initial`, `residual`, and `rift` search policies).
2. The contract strictly forbids loading or reading `references/explore-selector.md` before the final Search Field (`pass03`) has been frozen and hash-verified. (Same-host contract separation is best-effort within a shared conversation; do not claim absolute same-host blindness).
3. Do not load `references/deep.md`, `references/deep-reviewer.md`, `references/deep-compare.md`, or `references/lever*.md`. PACK terminates after Portfolio curation and research pack assembly.

### Freeze Success and Repair Rules
- `FREEZE_OK` from the prescribed checkpoint command is authoritative for that freeze. After `FREEZE_OK`, do not reopen validator source/tests or re-read the just-frozen artifact solely to verify the successful freeze.
- Validator rejection is not permission for unrestricted repository archaeology. First repair directly from: (1) the surfaced validation error, (2) the current stage contract, and (3) the existing bounded repair budget. Inspect implementation files only if these are genuinely insufficient to continue.

---

## 1. Pipeline Execution Sequence

A single `$RUN_ID` is used across all three passes and final artifacts.

```text
PACK TASK
→ optional pre-search high-information questions (default 0; normal max 1)
→ Search(initial) pass01 GENERATE → freeze explore pass01 + search-field manifest pass01
→ Search(residual) pass02 GENERATE → freeze explore pass02 + search-field manifest pass02
→ Search(rift) pass03 GENERATE → freeze explore pass03 + search-field manifest pass03
→ (only after pass03 freeze: reveal references/explore-selector.md)
→ PORTFOLIO CURATION over accumulated field → freeze portfolio record (route PACK)
→ create session archive (mandatory --accounting, semantic_stage_count == 4)
→ deterministic research-pack-<subject-slug>.md
→ STOP
```

### Stage Details

1. **PACK TASK**: Receive the user's task prompt via `/pizm pack <task>`.
   - Resolve single run ID: `$RUN_ID`.
   - Apply optional one-question scope-fork trigger if a genuine material fork exists; otherwise proceed directly.

2. **Search Pass 1 (initial)**: Broad structural search under `initial` policy.
   - Freeze candidates:
     ```bash
     "$PIZM_CHECKPOINT" freeze --stage explore --run-id "$RUN_ID" --artifact-suffix pass01 --input "$CANDIDATES_PASS01_JSON"
     ```
   - Freeze search-field manifest:
     ```bash
     "$PIZM_CHECKPOINT" freeze --stage search-field --run-id "$RUN_ID" --artifact-suffix pass01 --input "$SEARCH_FIELD_PASS01_JSON"
     ```

3. **Search Pass 2 (residual)**: Consume accumulated field from Pass 1; search for missing mechanisms, variables, boundaries, and countermodels under `residual` policy.
   - Freeze candidates:
     ```bash
     "$PIZM_CHECKPOINT" freeze --stage explore --run-id "$RUN_ID" --artifact-suffix pass02 --input "$CANDIDATES_PASS02_JSON"
     ```
   - Freeze search-field manifest:
     ```bash
     "$PIZM_CHECKPOINT" freeze --stage search-field --run-id "$RUN_ID" --artifact-suffix pass02 --input "$SEARCH_FIELD_PASS02_JSON"
     ```

4. **Search Pass 3 (rift)**: Consume accumulated field from Passes 1 and 2; search for distant structural shifts, reframing unit of analysis, causality, boundary, agency, or time scales under `rift` policy.
   - Freeze candidates:
     ```bash
     "$PIZM_CHECKPOINT" freeze --stage explore --run-id "$RUN_ID" --artifact-suffix pass03 --input "$CANDIDATES_PASS03_JSON"
     ```
   - Freeze search-field manifest:
     ```bash
     "$PIZM_CHECKPOINT" freeze --stage search-field --run-id "$RUN_ID" --artifact-suffix pass03 --input "$SEARCH_FIELD_PASS03_JSON"
     ```

5. **PORTFOLIO CURATION**: Only after `search-field-pass03.json` is frozen, reveal `references/explore-selector.md`.
   - Evaluate all accumulated candidates categorically (`KEEP | BORDERLINE | MERGE | DROP`).
   - Compose Bundles (`B1, B2, ...`) from kept candidates.
   - Enforce schema `pizm-portfolio-selection-v1` with `route: "PACK"`.
   - For `route: "PACK"`, all five downstream routing fields MUST be present and null:
     - `next_reasoning_move = null`
     - `next_reasoning_rationale = null`
     - `information_request = null`
     - `rival_shadow = null`
     - `auto_target = null`
   - Enforce `field_ref: "search-field-pass03.json"`. The basename MUST be exactly `search-field-pass03.json`: the checkpoint fails closed on any other name, so a PACK portfolio cannot be frozen before the third pass exists.
   - Freeze portfolio:
     ```bash
     "$PIZM_CHECKPOINT" freeze --stage portfolio --run-id "$RUN_ID" --input "$PORTFOLIO_JSON"
     ```
   - Checkpoint freeze reveals no next semantic contract. Proceed immediately to deterministic finalization.

6. **Archive Creation (`create`)**:
   - Canonical stage specifications:
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
       --accounting "$ACCOUNTING_JSON" \
       --subject-slug "$SUBJECT_SLUG" \
       --provider "$PROVIDER" \
       --model "$MODEL" \
       --model-source "$MODEL_SOURCE" \
       --pizm-version "$PIZM_VERSION" \
       --evidence-kind live
     ```
   - `--accounting` is mandatory for PACK. The manifest records derived `semantic_stage_count: 4` (Search pass 1 + Search pass 2 + Search pass 3 + Portfolio curation).
   - A PACK archive carries exactly these five stages: `pass-01-normal`, `pass-02-residual`, `pass-03-rift`, `search-field`, `portfolio`. A `deep-*`, `comparison*`, or `lever-*` stage fails closed, and so does any development, deep-review, comparison-review, or LEVER artifact (JSON, `.sha256`, or `.meta.json`) riding along in the PACK run directory.

7. **Deterministic Research Packet Rendering**:
   - Render the portable Markdown research pack:
     ```bash
     "$PIZM_SESSION_BUNDLE" render \
       --run-dir ".ai/pizm/run-$RUN_ID" \
       --task "<original task>" \
       --output ".ai/pizm/run-$RUN_ID/research-pack-$SUBJECT_SLUG.md"
     ```
   - **HTML Status**: HTML rendering is NOT supported for PACK in Wave A. Do not invoke `"$PIZM_SESSION_BUNDLE" render-html` on a PACK run (the CLI will refuse with a stable non-zero error). The primary deliverable is the Markdown research pack and frozen archive bundle.
   - The packet is rendered only from a complete three-pass run: `candidates-pass01.json`, `candidates-pass02.json`, `candidates-pass03.json`, and `search-field-pass03.json` are all required, and a partial run fails closed instead of producing a one-pass packet.
   - Packet shape: promoted `KEEP` Perspectives render as full cards; BORDERLINE candidates and MERGE residues render as compact cards under `## Preserved open / merged territory` (so the cheap Portfolio is never the last censor of the field); `DROP` stays count-only in the curation summary.

8. **STOP**: Present the research packet location and summary. Do not prompt for automatic Deep development. The handoff belongs to the user or downstream model.
