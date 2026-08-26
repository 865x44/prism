STATUS: APPROVED_OFFLINE_DETERMINISTIC

# FORGE_ADAPTER_V0

Deterministic adapter transforming Prism Humor candidate and develop artifacts into a single Forge seed artifact.

- Version ID: `forge-adapter-v0`
- Model Execution: None (offline deterministic mapping, no live LLM calls)

## Purpose
Merges a reviewed Prism Humor candidate artifact (`candidates/<id>.yaml`) with its developed expansion artifact (`develop-<id>.yaml`) into a single YAML seed file matching Forge's 18 humor seed fields (`HUMOR_FIELDS`).

## Inputs
1. Candidate YAML (`--candidate PATH`):
   - Required fields: `id`, `collision`, `shared_object`, `comic_mechanism`, `reality_anchor`, `gameability`
   - Optional fields: `title`, `subtitle`
2. Develop YAML (`--develop PATH`):
   - Required fields: `bundle_id` (must match candidate `id`), `core_premise`, `causal_chain`, `straight_faced_logic`, `escalation_ladder`, `reversal`, `compression`, `character_affordances`, `institutional_consequences`, `callback_potential`, `failure_boundary`
   - Optional fields: `title`, `subtitle`

## Outputs
Forge seed YAML containing exactly 18 string fields (`HUMOR_FIELDS`):
1. `id` (from candidate `id` / develop `bundle_id`)
2. `collision` (from candidate)
3. `shared_object` (from candidate)
4. `comic_mechanism` (from candidate)
5. `reality_anchor` (from candidate)
6. `gameability` (from candidate)
7. `core_premise` (from develop)
8. `causal_chain` (from develop)
9. `straight_faced_logic` (from develop)
10. `escalation_ladder` (from develop)
11. `reversal` (from develop)
12. `compression` (from develop)
13. `character_affordances` (from develop)
14. `institutional_consequences` (from develop)
15. `callback_potential` (from develop)
16. `failure_boundary` (from develop)
17. `title` (mechanically derived)
18. `subtitle` (mechanically derived)

## Mechanical Derivation Rules (No Plot Generation)
- `title`:
  1. Non-empty override if provided
  2. `develop.title` if non-empty
  3. `candidate.title` if non-empty
  4. If `candidate.shared_object` is non-empty: `Case {id}: {shared_object}`
  5. If `candidate.collision` is non-empty: `Case {id}: {collision}`
  6. Fallback: `Case {id}`
- `subtitle`:
  1. Non-empty override if provided
  2. `develop.subtitle` if non-empty
  3. `candidate.subtitle` if non-empty
  4. `develop.core_premise` if non-empty
  5. If `collision` and `shared_object` are both non-empty: `Collision of {collision} around {shared_object}.`
  6. Fallback: `Seed adaptation for {id}.`

## CLI
```bash
python -m humor forge-seed --candidate PATH --develop PATH [--out PATH]
```
- Missing `--out`: prints YAML output to stdout.
- Exit code 0 on success, exit code 1 on `AdapterError`, I/O, or YAML parse errors to stderr.
