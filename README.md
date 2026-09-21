# Prism

Prism is a semantic exploration and structuring tool: it expands a problem into materially distinct perspectives, evaluates structural overlap and composition, curates them into explicit Perspectives and Bundles, and hands the structured field downstream — to a stronger model or a human — for synthesis, judgment, and decision.

---

## What Prism Is

Prism helps users move beyond surface-level brainstorming. Its core promise is **expand → structure → hand off**: Prism's analytical core searches for structurally independent causal models of a problem, curates them into explicit Perspectives ($P\langle n\rangle$) and composed Bundles ($B\langle n\rangle$), and hands a structured field downstream for synthesis, judgment, and decision. The recommended automatic route is **PACK** (cheap-model exploration → curated research packet → stronger model or human); **BONK** is the heavy dual-development route. Deep, Critic, LEVER, and AUTO remain available as optional advanced operations: Deep elaborates a hypothesis rather than validating it, and Critic/LEVER are advanced/manual/experimental primitives. For dedicated language work, Prism provides WORDCRAFT as a separate, optional creative operation.

---

## Quick Start

```bash
git clone https://github.com/865x44/prism.git
cd prism
./bin/install-pizm --host both
```

Canonical interaction form in Claude Code or OpenCode:

```text
/pizm <task>
```

Mode cheat sheet:

```text
/pizm <task>           normal exploration (initial search -> portfolio)
/pizm rift <task>      adversarial reframing (rift search -> portfolio)
/pizm deep P3          develop one perspective or bundle (elaboration, not validation)
/pizm critic P3        advanced/manual adversarial critique of a developed model
/pizm lever P3         advanced/manual bounded leverage from a MODEL_READY model
/pizm pack <task>      RECOMMENDED automatic route: three passes -> curated research packet
/pizm bonk <task>      heavy dual-development pipeline (three passes -> two bundles, no winner)
/pizm auto <task>      EXPERIMENTAL autonomous single-target pipeline (ends in an automated verdict)
/pizm wordcraft <text>   craft memorable words, phrases, and linguistic hooks
```
---

## Product Surface

### Manual Primitives (Cumulative Reference Experience)
- **Search (Explore)**: Generates a structured field of distinct candidate perspectives ($P\langle n\rangle$). Supports three internal search policies (`initial` / NORMAL, `residual` / 360, `rift` / RIFT) and an explicit Information Gathering budget (0–3 clarifying questions allowed only when answers materially fork search territory or downstream reasoning spend; no standalone probe subsystem).
- **Portfolio Judge**: Evaluates frozen candidate pools categorically, promoting valid perspectives ($P\langle n\rangle$) and assembling composed Bundles ($B\langle n\rangle$) with explicit composition gains. Separates field survival (`KEEP`/`BORDERLINE`/`MERGE`/`DROP`) from downstream reasoning spend.
- **Deep**: Develops a selected perspective ($P\langle n\rangle$), composed bundle ($B\langle n\rangle$), or direct seed into a comprehensive causal model (`pizm-development-v2`), recording a compact development delta and comparative standing against a live rival shadow when present. Deep elaborates its target into its strongest honest form; it neither validates the hypothesis nor settles its provisional epistemic census.
- **Critic**: Performs independent adversarial reassessment of a developed model (`pizm-deep-review-v2`), distinguishing readiness blockers (B1–B4) from logical contradictions, determining terminal readiness (`MODEL_READY`, `NEED_EVIDENCE` with structured inquiry program, `RETURN_TO_EXPLORE`).
- **LEVER**: Formulates bounded interventions and testable moves from a validated `MODEL_READY` model.

*Note: "Breadth" is superseded terminology and is not a public user mode. "MAX" is superseded and eliminated as a product route.*

*Note: **Critic** and **LEVER** are advanced/manual/experimental primitives. They remain fully available and unchanged, but they are explicit user-request steps outside the recommended journey (PACK for exploration handoff, BONK for dual development); the recommended journeys do not invoke them.*

### Automated Pipelines (recommended hierarchy)

Exactly one automatic route is recommended. The heavier routes exist for specific needs, and all automatic routes remain deterministic at final assembly (zero model calls).

1. **PACK (`/pizm pack <task>`) — RECOMMENDED automatic route (exploration and handoff).** Cheap model → structured exploration → research packet → stronger model/human judgment: `Search(initial) → Search(residual) → Search(rift) → Portfolio curation (route: "PACK") → deterministic research packet (research-pack-<slug>.md)`. PACK executes **zero** Deep, Critic, Comparison, and LEVER stages, never emits `MODEL_READY` or a winner, and makes no readiness claim; synthesis, epistemic judgment, and decision stay with the downstream model or human.
2. **BONK (`/pizm bonk <task>`) — heavy dual-development route.** Three-pass exploration → two materially distinct strong Bundles → develop both → handoff without automatic winner or synthesis: `Search(initial) → Search(residual) → Search(rift) → Portfolio dual-development selection (pizm-portfolio-selection-v3) → Deep A → Deep B → deterministic development pack (run-<subject-slug>.md)`. BONK executes **no** Critic, Compare, or LEVER stage; the two targets are not contestants, are never ranked, and are handed downstream unranked and unsynthesized. When no second defensible materially distinct Bundle exists, BONK takes the honest single-target path rather than fabricating one.
3. **AUTO (`/pizm auto <task>`) — EXPERIMENTAL end-to-end synthesis/adjudication route.** Dynamic single-target pipeline: `Search(initial) → Search(rift) → Portfolio → dynamic reasoning-budget branch (Deep on nominated target → Critic → optional LEVER; intentional Information Gathering stop; or field Preservation stop) → deterministic final synthesis (run.md and run.html)`. Because AUTO ends in an automated readiness verdict, it is **not** the recommended default: prefer PACK for exploration handoff or BONK for dual development unless you explicitly want an automated Critic verdict.

Manual **Critic** and **LEVER** remain available as advanced/manual/experimental primitives (explicit user request only). Neither PACK nor BONK invokes them, and neither is part of the recommended user journey; only AUTO retains an automatic Critic stage.

#### Post-change product P1 (recorded, not implemented)

> A manually orchestrated Search → Deep → Critic → LEVER trajectory should eventually be exportable as one coherent artifact without the user locating multiple `.ai/pizm/run-*` directories.

This is out of scope for the current change: manual runs have no persistent session identity yet and rely on host conversation/session export.

> The frozen search field hash-pins every `candidates` artifact but does not prove that the field's `entries` list is the exact union of the candidates those artifacts actually declare: a manifest can name a `passNN:cNN` that exists in no pass, or omit one that does, and `_validate_search_field` will not notice. Portfolio refs are likewise only validated syntactically at freeze (shape, not membership in a candidate index), so the deterministic renderer is currently the first place a dangling ref fails closed. Closing this properly means deciding the candidate-ID grammar (generated `cNN` versus arbitrary strings), whether `entries` must be the exact union of every pass's candidates, and how already-frozen legacy manifests are read forward — a schema-completeness redesign rather than a bounded repair. Recorded as post-merge debt; the current renderers fail closed on unresolvable refs instead.

### Optional Creative Operation
- **WORDCRAFT (`/pizm wordcraft <text>`)**: Generates memorable, quotable, and coined language (words, derived forms, compounds, metaphors, aphorisms, punchlines) from direct text or accessible Pizm perspectives/bundles. Executes on the current host model in a single prompt-only pass with qualitative context-first selection and an explicit `NO WINNER` path when the source text is already stronger. WORDCRAFT is strictly optional and is not part of analytical readiness or the PACK/BONK/AUTO pipelines.
---

## Mental Model & Topologies

### Core Mental Model (Cumulative Manual Reference)
```text
Search (Information Gathering: 0–3 questions if route-forking)
  └─► Portfolio Judge
        ├─► Perspectives P<n> / Bundles B<n> (Field Survival)
        └─► Deep (Development v2 + Delta + Comparative Standing)
              └─► Critic (Review v2: Blockers vs Contradiction)
                    ├─► MODEL_READY ──► [Optional] LEVER
                    ├─► NEED_EVIDENCE ──► Inquiry Program
                    └─► RETURN_TO_EXPLORE
```

### PACK Topology (recommended automatic route)
```text
/pizm pack <task>
  │
  ├─► Search(initial)  ──────────────► Freeze pass01 + search-field-pass01
  ├─► Search(residual) ──────────────► Freeze pass02 + search-field-pass02
  ├─► Search(rift)     ──────────────► Freeze pass03 + search-field-pass03 (FINAL)
  ├─► Portfolio Curation ────────────► Freeze portfolio (route: PACK, all routing keys null)
  └─► Deterministic FINAL ───────────► Session bundle archive, research-pack-<slug>.md (0 model calls)
```

*PACK Handoff*: the research packet is the deliverable. PACK performs zero Deep, Critic, Comparison, and LEVER stages, emits no `MODEL_READY` and no winner, and hands the curated field to a stronger model or human for synthesis and decision. Interactive HTML is not supported for PACK; the Markdown packet is primary.

### BONK Topology (heavy dual-development route)
```text
/pizm bonk <task>
  │
  ├─► Search(initial)  ──────────────► Freeze pass01 + search-field-pass01
  ├─► Search(residual) ──────────────► Freeze pass02 + search-field-pass02
  ├─► Search(rift)     ──────────────► Freeze pass03 + search-field-pass03 (FINAL)
  ├─► Portfolio dual-development ────► Freeze portfolio-v3 (DUAL_BUNDLES or SINGLE_TARGET)
  ├─► Deep A ────────────────────────► Freeze development-v2-<A_target_id>
  ├─► Deep B ────────────────────────► Freeze development-v2-<B_target_id> (omitted on SINGLE_TARGET)
  └─► Deterministic FINAL ───────────► Session bundle archive, run-<subject-slug>.md (0 model calls)
```

*BONK Dual-Development Handoff*: no Critic, no Compare, no LEVER, no winner, and no synthesized third model. Both developments and the frozen `material_difference` are handed downstream unranked. Legacy BONK v2 archives (including `comparison-review-v1`) remain readable, but new BONK runs never write them. Interactive HTML is not supported for BONK v3; the Markdown pack is primary.

### AUTO Topology (experimental route)
```text
/pizm auto <task>
  │
  ├─► Search(initial) ────────► Freeze pass01 + search-field-pass01
  ├─► Search(rift) ───────────► Freeze pass02 + search-field-pass02 (FINAL)
  ├─► Portfolio Judge ────────► Freeze portfolio (route: AUTO)
  │     │
  │     ├─► [next_reasoning_move: DEEP]
  │     │     ├─► Deep(target) ───────► Freeze development-v2 (with delta & rival standing)
  │     │     ├─► Critic Review ──────► Freeze deep-review-v2 (MODEL_READY | NEED_EVIDENCE | RETURN_TO_EXPLORE)
  │     │     └─► [Conditional LEVER] ► Freeze design + review (if MODEL_READY and ACTION_OR_DECISION)
  │     │
  │     ├─► [next_reasoning_move: GATHER_INFORMATION]
  │     │     └─► Intentional terminal stop (freeze information request; 0 Deep/Critic/LEVER files)
  │     │
  │     └─► [next_reasoning_move: PRESERVE_ONLY]
  │           └─► Intentional terminal stop (freeze preserved field; 0 Deep/Critic/LEVER files)
  │
  └─► Deterministic FINAL ────► Session bundle archive, run.md + run.html, optional Reader URL (0 model calls)
```

*AUTO Honest Stops*: When the Portfolio Judge produces `GATHER_INFORMATION` or `PRESERVE_ONLY`, AUTO stops immediately as a completed run without creating Deep/Critic/LEVER files. When the Critic produces `NEED_EVIDENCE` (with structured inquiry program) or `RETURN_TO_EXPLORE`, execution stops honestly at Critic.

*AUTO Positioning*: AUTO is the only route that ends in an automated readiness verdict, which is why it is documented as experimental rather than as the recommended default. Its runtime is unchanged; PACK remains the recommended automatic route and BONK the heavy dual-development route.

## Installation & Skill Setup

### Native Pizm Skill (Claude Code & OpenCode)

Native Pizm runs directly on the host model in Claude Code, OpenCode, and compatible Agent Skills harnesses with **zero API keys** and **zero external provider configuration**.

To install the skill and helper binaries:

```bash
# Install to both Claude Code and OpenCode
./bin/install-pizm --host both

# Or target a single harness:
./bin/install-pizm --host claude-code   # installs to ~/.claude/skills/pizm/
./bin/install-pizm --host opencode      # installs to ~/.config/opencode/skills/pizm/
```

This copies the canonical skill directory and copies the deterministic helpers (`pizm-checkpoint`, `pizm-session-bundle`, `pizm-reader-server`, `pizm_render_html.py`) to `~/.local/bin/`.

Verify mirror integrity:

```bash
for f in SKILL.md agents/openai.yaml references/auto.md references/deep.md references/deep-compare.md references/deep-reviewer.md references/explore.md references/explore-selector.md references/bonk.md references/pack.md references/lever.md references/lever-reviewer.md references/reasoning-arsenal.md references/wordcraft.md; do
  cmp -s "skills/pizm/$f" "$HOME/.config/opencode/skills/pizm/$f" || { echo "Mirror mismatch in $f"; exit 1; }
done
echo "Skill mirror verified."
```

### Native Skill vs Legacy Runtime

- **Native Pizm Skill (`skills/pizm/`)**: The canonical interactive product. Executes directly on the current host model using staged reasoning contracts. Requires no API keys, provider setup, or runtime services.
- **Legacy CLI (`prism`)**: Python runtime CLI (`prism = prism.runtime.cli:main`) for offline regression testing and development. Not required for ordinary interactive Pizm usage in Claude Code or OpenCode.
### Development Environment

For testing and running the verification suite:

```bash
git clone https://github.com/865x44/prism.git
cd prism
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run test suite:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

---

## Outputs & Artifact Authority

Prism strictly separates provenance/machine authority from human presentation:

1. **Authoritative Machine Artifacts**: Structured JSON files with `.sha256` sidecars (e.g. `candidates-*.json`, `search-field-*.json`, `portfolio.json`, `development-v2-*.json`, `deep-review-v2-*.json`, `comparison-review-v1.json`, `manifest.json`) are the sole authority for verification, provenance, and debugging.
2. **Deterministic `run.md`**: Human-readable markdown synthesized directly from frozen JSON artifacts via `bin/pizm-session-bundle render` (zero model calls).
3. **Deterministic `run.html`**: Self-contained interactive full-trace report synthesized directly from frozen JSON artifacts via `bin/pizm-session-bundle render-html` (zero model calls).
4. **Local Reader Server (`pizm-reader-server`)**: Optional local transport/convenience for browser navigation (`http://127.0.0.1:41144/`). Reader server availability never affects the semantic validity of a run; `file://` URL fallback is always provided.
---

## Repository Map

```text
skills/pizm/          Canonical native Pizm skill (prompts, reference rubrics, schemas)
bin/                  Deterministic checkpoint (pizm-checkpoint) and bundle/rendering tools (pizm-session-bundle)
src/prism/            Python reference substrate, legacy CLI, and cold-path tooling
src/prism/perspective_core/  Frozen Python reference core (byte-for-byte immutable)
tests/                Contract, checkpoint, bundle, and regression test suites
contracts/            System and pipeline contract specifications
docs/architecture.md  Detailed technical architecture and stage contracts
```

---

## License

MIT. See [LICENSE](LICENSE).
