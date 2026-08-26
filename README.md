# Prism

Prism is a semantic exploration and model-development tool designed to discover materially distinct perspectives, evaluate structural overlap and composition, deepen selected angles into explicit causal models, subject them to adversarial critique, and derive bounded practical leverage.

---

## What Prism Is

Prism helps users move beyond surface-level brainstorming. Instead of generating lists of fluent stylistic variations, Prism searches for structurally independent causal models of a problem, identifies non-obvious composition gains between perspectives, subjects developed models to independent adversarial evaluation, and determines testable leverage points.

---

## Product Surface

### Manual Primitives
- **Search (Explore)**: Generates a structured field of distinct candidate perspectives ($P\langle n\rangle$). Supports three internal search policies:
  - `initial` (NORMAL): Broad structural divergence across the problem space.
  - `residual`: Divergence directed away from accumulated prior perspectives (*`360` is a deprecated compatibility alias for residual Search*).
  - `rift` (RIFT): Non-obvious, distant structural reframings that preserve the underlying mechanism of the source while rejecting decorative analogy.
- **Portfolio Judge**: Evaluates frozen candidate pools categorically, promoting valid perspectives ($P\langle n\rangle$) and assembling composed Bundles ($B\langle n\rangle$) with explicit composition gains.
- **Deep**: Develops a selected perspective ($P\langle n\rangle$), composed bundle ($B\langle n\rangle$), or direct seed into a comprehensive causal model (`pizm-development-v2`).
- **Critic**: Performs independent adversarial reassessment of a developed model (`pizm-deep-review-v2`), determining its readiness (`MODEL_READY`, `NEED_EVIDENCE`, `RETURN_TO_EXPLORE`).
- **LEVER**: Formulates bounded interventions and testable moves from a validated `MODEL_READY` model.

*Note: "Breadth" is superseded terminology and is not a public user mode. "MAX" is superseded and eliminated as a product route.*

### Automated Pipelines
- **AUTO (`/pizm auto <task>`)**: Bounded single-target pipeline: Search $\to$ Portfolio $\to$ Deep(best $P$ or $B$) $\to$ Critic $\to$ optional LEVER $\to$ deterministic final synthesis.
- **FORGE (`/pizm forge <task>`)**: Heavy dual-competition pipeline: Search(initial) $\to$ Search(residual) $\to$ Portfolio $\to$ Deep(LEFT) $\to$ Deep(RIGHT) $\to$ Compare $\to$ optional LEVER $\to$ deterministic final synthesis.

---

## Mental Model & Topologies

### Core Mental Model
```text
Search
  └─► Portfolio Judge
        ├─► Perspectives P<n> / Bundles B<n>
        └─► Deep (Development v2)
              └─► Critic (Review v2)
                    └─► [Optional] LEVER
```

### AUTO Topology
```text
/pizm auto <task>
  │
  ├─► Search(initial) ────────► Freeze candidates + search-field manifest
  ├─► Portfolio Judge ────────► Freeze portfolio (route: AUTO, one auto_target: P or B)
  ├─► Deep(target) ───────────► Freeze development-v2
  ├─► Critic Review ──────────► Freeze deep-review-v2 (MODEL_READY | NEED_EVIDENCE | RETURN_TO_EXPLORE)
  ├─► [Conditional LEVER] ───► Freeze design + review (if MODEL_READY and ACTION_OR_DECISION)
  └─► Deterministic FINAL ────► Session bundle archive & deterministic run.md (0 model calls)
```

### FORGE Topology
```text
/pizm forge <task>
  │
  ├─► Search(initial) ───────────────► Freeze pass01 + search-field
  ├─► Search(residual) ──────────────► Freeze pass02 + search-field
  ├─► Portfolio Judge ───────────────► Freeze portfolio-v2 (TWO_DEFENSIBLE_BUNDLES or NO_SECOND_DEFENSIBLE_BUNDLE)
  ├─► Deep(LEFT) ────────────────────► Freeze development-v2-<left_id>
  ├─► Deep(RIGHT) ───────────────────► Freeze development-v2-<right_id>
  ├─► Reveal deep-compare.md ────────► Freeze comparison-review-v1 (Critic LEFT + Critic RIGHT + Compare)
  ├─► [Conditional LEVER] ───────────► Freeze design + review on preferred MODEL_READY bundle
  └─► Deterministic FINAL ───────────► Session bundle archive & deterministic run.md (0 model calls)
```

---

## Installation & Skill Setup

The canonical Pizm skill resides in `skills/pizm/`. It is designed to run directly within host coding agents and harnesses (such as OpenCode or OMP) without requiring external provider wrappers.

### Installing the Skill

To install or update the skill in your local OpenCode environment:

```bash
mkdir -p ~/.config/opencode/skills/pizm
cp -r skills/pizm/* ~/.config/opencode/skills/pizm/
```

Verify mirror integrity:

```bash
for f in SKILL.md agents/openai.yaml references/auto.md references/deep.md references/deep-compare.md references/deep-reviewer.md references/explore.md references/explore-selector.md references/forge.md references/lever.md references/lever-reviewer.md references/reasoning-arsenal.md; do
  cmp -s "skills/pizm/$f" "$HOME/.config/opencode/skills/pizm/$f" || { echo "Mirror mismatch in $f"; exit 1; }
done
echo "Skill mirror verified."
```

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
