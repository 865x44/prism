# Prism vNext Plan 1 → Plan 2 Handoff

Date: 2026-08-25. Branch `prism/semantic-core-auto-v1`. Base: `7fff59d`.
Operational note only: commits, schemas, primitives, invariants, open items.

## Commits

```text
7fff59d  base (prism/core-productization): pre-vNext checkpoint/bundle tooling
a81eac7  feat(C1): search field v1 + portfolio judge v1 + reasoning arsenal
5537f30  feat(C2): deep v2 + critic v2 + manual P/B flows
fda5822  feat(C3): AUTO v1 + deterministic run.md renderer
HEAD      chore(C4): plan1 tooling closeout (= this commit: handoff note only; verification slice, no feature delta)
```

## Authoritative schemas (payload ceilings)

| Stage (`--stage`) | Schema | Ceiling |
|---|---|---|
| `explore` | `pizm-candidates-v1` (unchanged) | ≤20 candidates, ≤192 KiB total, ≤12 KiB per candidate |
| `search-field` | `pizm-search-field-v1` | 32 KiB |
| `portfolio` | `pizm-portfolio-selection-v1` | 160 KiB |
| `development-v2` | `pizm-development-v2` | 192 KiB |
| `deep-review-v2` | `pizm-deep-review-v2` | 128 KiB |
| `deep` (legacy) | `pizm-development-v1` — still valid for old artifacts | unchanged |
| `lever-design` / `lever-review` | `pizm-lever-design-v1` / `pizm-lever-review-v1` — unchanged | 64 KiB each |

Not in Plan 1: `comparison-review-v1` (Plan 2 only; the string appears nowhere in Plan 1 code or tests).
Legacy selector records `pizm-selection-v1` / `pizm-auto-selection-v1` remain readable history.

## Callable primitives

Freeze (installed as `~/.local/bin/pizm-checkpoint`, symlink to repo `bin/pizm-checkpoint`):

```bash
pizm-checkpoint freeze --stage {explore|search-field|portfolio|development-v2|deep-review-v2|lever-design|lever-review|deep} \
  --run-id <lowercase-slug> --input <artifact.json> [--project-root .] [--skill-root ~/.config/opencode/skills/pizm]
```

Writes `<project-root>/.ai/pizm/run-<run-id>/{<prefix>.json,<prefix>.sha256,<prefix>.meta.json}` via exclusive durable create; refuses overwrite; verifies hash on read-back; fails closed with `PAYLOAD_TOO_LARGE`; prints `FREEZE_OK <sha256>` and reveals the next-stage contract only after verified freeze (terminal stages reveal nothing).

Render (deterministic reader; zero model calls):

```bash
bin/pizm-session-bundle render --run-dir <run-dir> --task "<original task>" [--output path]
```

Requires the frozen quartet `candidates.json` + `portfolio.json` + `development-v2.json` + `deep-review-v2.json` (sidecars verified when present); optional `design.json`+`review.json` lever pair and `search-field.json`. Portfolio must be `route:"AUTO"` with exactly one `auto_target` (P or B). Byte-identical output for identical inputs. `bin/pizm-session-bundle create` (session archive) is unchanged.

## Stable invariants

- Terminal states everywhere: exactly `MODEL_READY | NEED_EVIDENCE | RETURN_TO_EXPLORE` (no fourth status, no rebuild loop).
- Old strings parse forever: `pizm-candidates-v1`, `pizm-development-v1`, `pizm-lever-*-v1`, modes `NORMAL|360|RIFT` readable; `360` = deprecated alias executing Search(residual), explicit-only.
- Composite refs `passNN:cMM`: local `cNN` may repeat across passes without collision; search-field manifest is append-only (later entry never belongs to an earlier pass).
- P-IDs: monotonic, never recycled or rebound; `DIRECT_SEED` allowed for Deep target type P only.
- B-IDs: host-assigned via `_assign_bundle_ids` (canonicalize → assign → freeze); reuse preserves the prior id; never renumbered after user-visible assignment; ambiguous prior state fails closed.
- Frozen artifacts are immutable (exclusive link-based publish, overwrite refused); freeze-before-reveal seam preserved for every hidden contract.
- AUTO v1: one Search → one Portfolio → one P/B target → one Deep → one Critic → optional LEVER (only `ACTION_OR_DECISION` AND `MODEL_READY`) → deterministic FINAL + run.md. Budget: 4 semantic stages (+2 LEVER); repairs max 1 per stage, 2 per run; `BUDGET_EXHAUSTED` fail-closed.
- Critic decision couplings enforced fail-closed: unresolved load-bearing contradiction blocks `MODEL_READY`; `identity_verified:false` forces `RETURN_TO_EXPLORE`; unsupported-specificity findings require recorded evidence debt; B targets require member-ablation finding.
- Skill mirror: 9-file `cmp -s` loop `docs/pizm-skill-staged-2026-08-24/` ↔ `~/.config/opencode/skills/pizm/` is the entire sync gate (see reconciliation note §3).

## Unresolved issues

None blocking Plan 2. Two cosmetic closeout notes, deliberately not fixed in C4 (reference-content changes were out of scope absent a DoD forcing):

1. `references/reasoning-arsenal.md` still says its Critic moves are "not yet wired into any stage contract" (plus migration note "reserved for later slices"). Stale since C2: `deep-reviewer.md` now consumes all seven moves. Fold a two-line wording update into the first Plan 2 slice that touches references anyway.
2. Plan 1 §4 accumulated-field hard safety ceiling "~28" is not stated in `references/explore.md` (initial 12–16 and residual 6–10 soft targets are present; enforced hard bounds remain the per-pass checkpoint ceilings plus the 32 KiB manifest). Add one sentence there if Plan 2 wants it normative.

## Known limitations for Plan 2

- Portfolio v1 has no competition fields: bundles never compete or merge with each other; exactly one `auto_target` per portfolio record.
- Renderer expects the AUTO v1 artifact layout/names above; old v0 run dirs (`development.json` + `selection.json`, e.g. `.ai/pizm/run-auto20260825x1`) do not render.
- Comparison stage absent by design (`comparison-review-v1` is Plan 2 surface; FORGE not built).
- `--task` text exists only at render time; it is not stored in any frozen artifact, so reproducing a run.md verbatim requires the original task string.
- Same-host `OBSERVE_IN_DOGFOOD` stands (auto.md §5): Judge/Deep see earlier-stage conversation context; the judged field is always the hash-frozen artifact set, and Deep remains blind to the critic contract until development-v2 freezes.
