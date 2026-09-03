# Prism

Prism is a semantic exploration and model-development tool designed to discover materially distinct perspectives, evaluate structural overlap and composition, deepen selected angles into explicit causal models, subject them to adversarial critique, and derive bounded practical leverage.

---

## What Prism Is

Prism helps users move beyond surface-level brainstorming. Instead of generating lists of fluent stylistic variations, Prism searches for structurally independent causal models of a problem, identifies non-obvious composition gains between perspectives, subjects developed models to independent adversarial evaluation, and determines testable leverage points.

---

## Product Surface

### Manual Primitives (Cumulative Reference Experience)
- **Search (Explore)**: Generates a structured field of distinct candidate perspectives ($P\langle n\rangle$). Supports three internal search policies (`initial` / NORMAL, `residual` / 360, `rift` / RIFT) and an explicit Information Gathering budget (0–3 clarifying questions allowed only when answers materially fork search territory or downstream reasoning spend; no standalone probe subsystem).
- **Portfolio Judge**: Evaluates frozen candidate pools categorically, promoting valid perspectives ($P\langle n\rangle$) and assembling composed Bundles ($B\langle n\rangle$) with explicit composition gains. Separates field survival (`KEEP`/`BORDERLINE`/`MERGE`/`DROP`) from downstream reasoning spend.
- **Deep**: Develops a selected perspective ($P\langle n\rangle$), composed bundle ($B\langle n\rangle$), or direct seed into a comprehensive causal model (`pizm-development-v2`), recording a compact development delta and comparative standing against a live rival shadow when present.
- **Critic**: Performs independent adversarial reassessment of a developed model (`pizm-deep-review-v2`), distinguishing readiness blockers (B1–B4) from logical contradictions, determining terminal readiness (`MODEL_READY`, `NEED_EVIDENCE` with structured inquiry program, `RETURN_TO_EXPLORE`).
- **LEVER**: Formulates bounded interventions and testable moves from a validated `MODEL_READY` model.

*Note: "Breadth" is superseded terminology and is not a public user mode. "MAX" is superseded and eliminated as a product route.*

### Automated Pipelines
- **AUTO (`/pizm auto <task>`)**: Dynamic single-target pipeline: Search(initial) $\to$ Search(rift) $\to$ Portfolio $\to$ dynamic reasoning-budget branch (Deep on nominated target $\to$ Critic $\to$ optional LEVER; intentional Information Gathering stop; or field Preservation stop) $\to$ deterministic final synthesis (`run.md` and `run.html`).
- **BONK (`/pizm bonk <task>`)**: Heavy dual-competition pipeline: Search(initial) $\to$ Search(residual) $\to$ Portfolio $\to$ Deep(LEFT) $\to$ Deep(RIGHT) $\to$ Compare $\to$ optional LEVER $\to$ deterministic final synthesis (`run.md` and `run.html`).
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

### AUTO Topology
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
for f in SKILL.md agents/openai.yaml references/auto.md references/deep.md references/deep-compare.md references/deep-reviewer.md references/explore.md references/explore-selector.md references/bonk.md references/lever.md references/lever-reviewer.md references/reasoning-arsenal.md; do
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

- **JSON Artifacts**: Structured JSON files with `.sha256` sidecars (e.g. `candidates-*.json`, `portfolio.json`, `development-v2-*.json`, `deep-review-v2-*.json`, `comparison-review-v1.json`, `manifest.json`) are the sole authority for verification, provenance, and debugging.
- **Deterministic `run.md`**: Human-readable markdown synthesized directly from frozen JSON artifacts via `bin/pizm-session-bundle render`. Generated with zero model calls.

---

## Repository Map

```text
skills/pizm/          Canonical native Pizm skill (prompts, reference rubrics, schemas)
bin/                  Deterministic checkpoint (pizm-checkpoint) and bundle/rendering tools (pizm-session-bundle)
src/prism/            Python reference substrate, legacy CLI, and cold-path tooling
src/prism/perspective_core/  Frozen Python reference core (byte-for-byte immutable)
tests/                Contract, checkpoint, bundle, and regression test suites
contracts/            Failure-capture specification
docs/architecture.md  Detailed technical architecture and stage contracts
.ai/                  Operational project memory, session logs, and state cursors
```

---

## License

MIT. See [LICENSE](LICENSE).
