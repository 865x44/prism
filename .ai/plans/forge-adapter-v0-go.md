# Forge Adapter v0 Implementation Spec (Prism Humor → Forge Case 47 Seed)

GO

## 1. Exact New Module Path
- Path: `/home/alx/projects/prism/src/humor/forge_adapter.py`
- Sits beside existing humor modules in `/home/alx/projects/prism/src/humor/`:
  - `__init__.py`
  - `__main__.py`
  - `ioyaml.py`
  - `isolation.py`
  - `manifest.py`
  - `prompts.py`
  - `review.py`
  - `versions.py`

## 2. Public Function Signatures
```python
from __future__ import annotations

from pathlib import Path
from typing import Mapping

from humor.ioyaml import dump, load

class AdapterError(ValueError):
    """Raised when candidate or develop inputs fail schema or ID alignment checks."""
    pass

def derive_title(candidate: Mapping[str, str], develop: Mapping[str, str], override: str | None = None) -> str:
    """Mechanically derive a seed title without inventing narrative plot."""
    ...

def derive_subtitle(candidate: Mapping[str, str], develop: Mapping[str, str], override: str | None = None) -> str:
    """Mechanically derive a seed subtitle without inventing narrative plot."""
    ...

def adapt_candidate_and_develop(
    candidate: Mapping[str, str],
    develop: Mapping[str, str],
    *,
    title: str | None = None,
    subtitle: str | None = None,
) -> dict[str, str]:
    """Merge Candidate and Develop mappings into a 18-key Forge Case 47 seed dict."""
    ...

def adapt_files(
    candidate_path: Path,
    develop_path: Path,
    out_path: Path | None = None,
    *,
    title: str | None = None,
    subtitle: str | None = None,
) -> str:
    """Load candidate and develop YAML files, adapt to Forge seed, optionally write to out_path, and return YAML text."""
    ...
```

## 3. Field Mapping Table
Target fields match `HUMOR_FIELDS` from `/home/alx/projects/forge-case47/projects/case47/generate.py` (18 keys total):

| # | HUMOR_FIELDS Key | Source Mapping | Source Key / Rule | Required / Fallback |
|---|---|---|---|---|
| 1 | `id` | Candidate / Develop | `candidate["id"]` == `develop["bundle_id"]` | Required; mismatch raises `AdapterError` |
| 2 | `collision` | Candidate | `candidate["collision"]` | Required |
| 3 | `shared_object` | Candidate | `candidate["shared_object"]` | Required |
| 4 | `comic_mechanism` | Candidate | `candidate["comic_mechanism"]` | Required |
| 5 | `reality_anchor` | Candidate | `candidate["reality_anchor"]` | Required |
| 6 | `gameability` | Candidate | `candidate["gameability"]` | Required |
| 7 | `core_premise` | Develop | `develop["core_premise"]` | Required |
| 8 | `causal_chain` | Develop | `develop["causal_chain"]` | Required |
| 9 | `straight_faced_logic` | Develop | `develop["straight_faced_logic"]` | Required |
| 10 | `escalation_ladder` | Develop | `develop["escalation_ladder"]` | Required |
| 11 | `reversal` | Develop | `develop["reversal"]` | Required |
| 12 | `compression` | Develop | `develop["compression"]` | Required |
| 13 | `character_affordances` | Develop | `develop["character_affordances"]` | Required |
| 14 | `institutional_consequences` | Develop | `develop["institutional_consequences"]` | Required |
| 15 | `callback_potential` | Develop | `develop["callback_potential"]` | Required |
| 16 | `failure_boundary` | Develop | `develop["failure_boundary"]` | Required |
| 17 | `title` | Derived / Override | `derive_title(candidate, develop, override)` | Mechanical fallback (never empty) |
| 18 | `subtitle` | Derived / Override | `derive_subtitle(candidate, develop, override)` | Mechanical fallback (never empty) |

## 4. Mechanical Title and Subtitle Derivation Algorithm
Zero narrative plot invention. Purely deterministic selection and string templating:

### `derive_title` Priority Chain:
1. `override` (if provided as non-empty string)
2. `develop.get("title")` (if present and non-empty)
3. `candidate.get("title")` (if present and non-empty)
4. If `candidate.get("shared_object")` is non-empty: `f"Case {cid}: {candidate['shared_object']}"`
5. If `candidate.get("collision")` is non-empty: `f"Case {cid}: {candidate['collision']}"`
6. Fallback: `f"Case {cid}"`

### `derive_subtitle` Priority Chain:
1. `override` (if provided as non-empty string)
2. `develop.get("subtitle")` (if present and non-empty)
3. `candidate.get("subtitle")` (if present and non-empty)
4. `develop.get("core_premise")` (if present and non-empty)
5. If `candidate.get("collision")` and `candidate.get("shared_object")` are non-empty:
   `f"Collision of {candidate['collision']} around {candidate['shared_object']}."`
6. Fallback: `f"Seed adaptation for {cid}."`

## 5. CLI Specification
- File to edit: `/home/alx/projects/prism/src/humor/__main__.py`
- Subparser name: `forge-seed`
- Arguments shape:
  ```
  python -m humor forge-seed --candidate <PATH> --develop <PATH> [--out <PATH>]
  ```
- Optional convenience runner for run directories:
  ```
  python -m humor forge-seed --run-dir <DIR> --id <ID> [--out <PATH>]
  ```
- Subparser definition pattern (copying `manifest` and `replay`):
  ```python
  seed = sub.add_parser("forge-seed")
  seed.add_argument("--candidate", help="Path to candidate YAML file")
  seed.add_argument("--develop", help="Path to develop YAML file")
  seed.add_argument("--run-dir", help="Path to pipeline run directory containing candidates/ and develop-*.yaml")
  seed.add_argument("--id", help="Humor ID (e.g. H1, H2) when using --run-dir")
  seed.add_argument("--out", "-o", help="Output path for Forge seed YAML (defaults to stdout if omitted)")
  ```
- No new console script in `pyproject.toml` (`humor` is already executed via `python -m humor`).

## 6. Test File and Assertions
- Test file path: `/home/alx/projects/prism/tests/test_humor_forge_adapter.py`
- Test framework: `pytest` (standard Prism test runner configured in `pyproject.toml`)
- Key test scenarios:
  1. `test_adapt_synthetic_v0_h1`:
     - Load `/home/alx/projects/prism/prism-runs/pipeline/fixtures/synthetic-v0/candidates/H1.yaml`
     - Load `/home/alx/projects/prism/prism-runs/pipeline/fixtures/synthetic-v0/develop-H1.yaml`
     - Execute `adapt_candidate_and_develop(cand, dev)`
     - Assert all 18 `HUMOR_FIELDS` keys exist and are non-empty strings.
     - Assert `seed["id"] == "H1"`.
     - Assert `seed["collision"] == "money-animal"`.
     - Assert `seed["shared_object"] == "vault-born rats"`.
     - Assert `seed["core_premise"] == "vault births create new money and new property"`.
     - Assert `seed["title"] == "Case H1: vault-born rats"`.
     - Assert `seed["subtitle"] == "vault births create new money and new property"`.
     - Serialize with `humor.ioyaml.dump` and reload with `humor.ioyaml.load` and `yaml.safe_load`, asserting exact equality.
  2. `test_adapt_synthetic_v0_h2`:
     - Convert H2 candidate + develop-H2.
     - Assert all 18 `HUMOR_FIELDS` keys present and `id == "H2"`.
  3. `test_id_mismatch_raises_adapter_error`:
     - Provide H1 candidate with develop-H2 (`bundle_id: "H2"`).
     - Assert `pytest.raises(AdapterError)`.
  4. `test_cli_forge_seed`:
     - Invoke `main(["forge-seed", "--candidate", str(cand_path), "--develop", str(dev_path), "--out", str(out_path)])`.
     - Assert return code `0` and output file matches expected schema.

## 7. Contract Update Outline for `contracts/humor/forge-adapter-v0.md`
- Target file: `/home/alx/projects/prism/contracts/humor/forge-adapter-v0.md`
- New status: `STATUS: APPROVED_OFFLINE_DETERMINISTIC` (replacing `STATUS: DEFERRED_PENDING_RESEARCH`)
- Contract specification sections:
  1. **Purpose**: Deterministic structural adapter bridging Prism Humor candidate/develop outputs to Forge Case 47 seed format.
  2. **Invariants**:
     - Zero live LLM calls (`no-live-call`). Purely offline deterministic merge.
     - Mechanical title and subtitle fallback derivation without plot invention.
     - Exact schema adherence to Forge Case 47 `HUMOR_FIELDS`.
     - Byte-reproducible YAML formatting via `humor.ioyaml`.
  3. **Input Schema**:
     - Candidate YAML: `id`, `collision`, `shared_object`, `comic_mechanism`, `reality_anchor`, `gameability` (plus standard candidate metadata).
     - Develop YAML: `bundle_id`, `core_premise`, `causal_chain`, `straight_faced_logic`, `escalation_ladder`, `reversal`, `compression`, `character_affordances`, `institutional_consequences`, `callback_potential`, `failure_boundary`.
  4. **Output Schema**:
     - Forge Case 47 Seed YAML: exactly the 18 keys named in `HUMOR_FIELDS`.
  5. **CLI Interface**:
     - `python -m humor forge-seed --candidate <path> --develop <path> [--out <path>]`

## 8. Confirmation: Synthetic-v0 H1 Coverage
- **Can synthetic-v0 H1 candidate+develop fill every HUMOR_FIELDS key without an LLM?**
  **YES**.
- **Gap List**:
  **None (0 gaps)**.
  - Direct Candidate mappings (6/18): `id`, `collision`, `shared_object`, `comic_mechanism`, `reality_anchor`, `gameability`.
  - Direct Develop mappings (10/18): `core_premise`, `causal_chain`, `straight_faced_logic`, `escalation_ladder`, `reversal`, `compression`, `character_affordances`, `institutional_consequences`, `callback_potential`, `failure_boundary`.
  - Mechanical Derivations (2/18): `title` (from `id` + `shared_object`), `subtitle` (from `core_premise`).
  - Total: 18 / 18 keys covered.

## 9. Confirmation: STATE Active Invariant Analysis
- **Does STATE `STOP_BEFORE_FURTHER_SEMANTIC_LIVE_CALLS` forbid a deterministic offline adapter?**
  **NO (Verdict: GO)**.
- **Quote from `/home/alx/projects/prism/.ai/STATE.md` (Active Invariant 5)**:
  > `"5. STOP_BEFORE_FURTHER_SEMANTIC_LIVE_CALLS: no 360 or Deep execution until a revised cross-pass separation topology and newly hashed packet receive explicit human approval. No automatic fallback to external Core, a fresh selector, Qwen CLI, or OpenCode CLI."`
- **Analysis**:
  The invariant explicitly restricts live semantic model inferences (360/Deep execution, external Core, fresh selector, Qwen CLI, OpenCode CLI without approved hashed packet). It does not restrict offline, deterministic Python transformations or test suites. Therefore, implementation of `forge-adapter-v0` as a deterministic offline tool is **GO**.

## 10. Forbidden Scope (Untouched Files)
The following paths are strictly forbidden and must remain untouched:
- `/home/alx/projects/forge/` (entire repository)
- In `/home/alx/projects/prism/`:
  - `campaign_v0.py`
  - `runtime.py`
  - `check.sh`
  - `md_to_html.py`
  - `src/prism/engine/` (and all engine modules)
  - `src/prism/perspective_core/` (and all perspective core modules)
  - During this synthesis task: do not create `src/humor/forge_adapter.py`, do not edit `src/humor/__main__.py`, do not edit `contracts/humor/forge-adapter-v0.md`, and do not create `tests/test_humor_forge_adapter.py`.
