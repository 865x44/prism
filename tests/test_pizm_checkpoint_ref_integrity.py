"""Wave 1 referential-integrity gate for ``bin/pizm-checkpoint`` freeze.

These are the freeze-time checks added on top of the existing checkpoint
suite:

* search-field ``entries`` must equal (as a set) the candidates actually
  frozen in the hash-verified per-pass ``candidates-passNN.json`` artifacts;
* a ``candidate_id`` must be referenceable under the composite-ref grammar
  ``passNN:<id>`` (character class alignment, no hard ``cNN`` shape);
* a portfolio's candidate-linking fields must all resolve to the frozen
  input field, and ``candidate_assessments`` must cover it exactly once;
* a failed freeze leaves no partial "successful" artifact state.

The reject cases are red-first: run this module with
``PIZM_CHECKPOINT_UNDER_TEST=<base-checkpoint>`` to observe the pre-fix
validator accepting the payloads (documented in the wave report).
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT = os.environ.get(
    "PIZM_CHECKPOINT_UNDER_TEST",
    str(REPO_ROOT / "bin" / "pizm-checkpoint"),
)


@pytest.fixture
def workspace(tmp_path):
    """Workspace with project root, skill root, and contract stubs."""
    project = tmp_path / "project"
    project.mkdir()
    skill = tmp_path / "skill"
    (skill / "references").mkdir(parents=True)
    (skill / "references" / "explore-selector.md").write_text(
        "# EXPLORE SELECTOR RUBRIC\nhidden rubric"
    )
    (skill / "references" / "deep-reviewer.md").write_text(
        "# DEEP REVIEWER RUBRIC\nhidden rubric"
    )
    (skill / "references" / "explore.md").write_text(
        "# EXPLORE GENERATOR CONTRACT\n"
    )
    (skill / "references" / "lever-reviewer.md").write_text(
        "# LEVER REVIEWER RUBRIC\nhidden rubric"
    )
    (skill / "references" / "deep-compare.md").write_text(
        "# DEEP COMPARE RUBRIC\nhidden rubric"
    )
    return project, skill


# ── payload / CLI helpers ─────────────────────────────────────────────


def _write_json(path, data):
    p = Path(path)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return str(p)


def _run_ck(*args):
    return subprocess.run(
        [sys.executable, CHECKPOINT, *args], capture_output=True, text=True
    )


def _freeze(project, skill, stage, run_id, payload, suffix=None, name=None):
    inp = _write_json(project / (name or f"_in_{stage}_{suffix or 'main'}.json"), payload)
    cmd = [
        "freeze", "--stage", stage, "--run-id", run_id, "--input", inp,
        "--project-root", str(project), "--skill-root", str(skill),
    ]
    if suffix:
        cmd += ["--artifact-suffix", suffix]
    return _run_ck(*cmd)


def _run_dir(project, run_id):
    return project / ".ai" / "pizm" / f"run-{run_id}"


def _candidates(ids, mode="NORMAL", extra=None):
    data = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": mode,
        "candidates": [{"candidate_id": cid, "content": f"idea {cid}"} for cid in ids],
    }
    if extra:
        data.update(extra)
    return data


def _explore(project, skill, run_id, ids, mode="NORMAL", suffix=None, extra=None):
    res = _freeze(project, skill, "explore", run_id, _candidates(ids, mode, extra), suffix)
    assert res.returncode == 0, res.stderr
    return res.stdout.split()[1]


def _pass(pass_id, ref, frozen_hash):
    return {"pass_id": pass_id, "candidates_ref": ref, "frozen_hash": frozen_hash}


def _field(passes, entries, extra=None):
    data = {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "passes": passes,
        "entries": entries,
    }
    if extra:
        data.update(extra)
    return data


def _assessment(ref, disposition="KEEP", quality="strong", residue="unique residue",
                overlap=None, reason="distinct mechanism"):
    return {
        "candidate_ref": ref,
        "disposition": disposition,
        "standalone_quality": quality,
        "unique_residue": residue,
        "nearest_overlap": overlap,
        "reason": reason,
    }


def _portfolio_v1(field_ref, field_hash, assessments, route="MANUAL",
                  perspectives=None, bundles=None, high_upside=None):
    data = {
        "schema_version": "pizm-portfolio-selection-v1",
        "stage": "portfolio",
        "route": route,
        "field_ref": field_ref,
        "field_hash": field_hash,
        "perspectives": perspectives if perspectives is not None
        else {"P1": "pass01:c01"},
        "candidate_assessments": assessments,
        "bundles": bundles or [],
        "next_reasoning_move": None,
        "next_reasoning_rationale": None,
        "information_request": None,
        "rival_shadow": None,
        "auto_target": None,
    }
    if high_upside is not None:
        data["high_upside"] = high_upside
    return data


def _basic_run(project, skill, run_id):
    """One explore pass + one accumulated search field (c01, c02)."""
    cand_sha = _explore(project, skill, run_id, ids=("c01", "c02"))
    field = _field(
        [_pass("pass01", "candidates.json", cand_sha)],
        ["pass01:c01", "pass01:c02"],
    )
    res = _freeze(project, skill, "search-field", run_id, field)
    assert res.returncode == 0, res.stderr
    return "search-field.json", res.stdout.split()[1]


def _three_pass_field(project, skill, run_id):
    """Accumulated pass01..pass03 field; returns (ref, hash)."""
    sha1 = _explore(project, skill, run_id, ids=("c01", "c02"), suffix="pass01")
    sha2 = _explore(project, skill, run_id, ids=("c01",), suffix="pass02")
    sha3 = _explore(project, skill, run_id, ids=("c01",), suffix="pass03")
    field = _field(
        [
            _pass("pass01", "candidates-pass01.json", sha1),
            _pass("pass02", "candidates-pass02.json", sha2),
            _pass("pass03", "candidates-pass03.json", sha3),
        ],
        ["pass01:c01", "pass01:c02", "pass02:c01", "pass03:c01"],
    )
    res = _freeze(project, skill, "search-field", run_id, field, suffix="pass03")
    assert res.returncode == 0, res.stderr
    return "search-field-pass03.json", res.stdout.split()[1]


# ── search-field referential integrity ────────────────────────────────


def test_invented_candidate_ref_rejected(workspace):
    """`pass02:c99`-style invented refs must fail closed."""
    project, skill = workspace
    run_id = "ri-invented"
    sha1 = _explore(project, skill, run_id, ids=("c01", "c02"), suffix="pass01")
    sha2 = _explore(project, skill, run_id, ids=("c01",), suffix="pass02")
    field = _field(
        [
            _pass("pass01", "candidates-pass01.json", sha1),
            _pass("pass02", "candidates-pass02.json", sha2),
        ],
        ["pass01:c01", "pass01:c02", "pass02:c01", "pass02:c99"],
    )
    res = _freeze(project, skill, "search-field", run_id, field, suffix="pass02")
    assert res.returncode != 0
    assert "unknown candidate" in res.stderr
    assert "pass02:c99" in res.stderr


def test_missing_real_candidate_rejected(workspace):
    """A frozen candidate absent from `entries` must fail closed."""
    project, skill = workspace
    run_id = "ri-missing"
    sha1 = _explore(project, skill, run_id, ids=("c01", "c02"))
    field = _field([_pass("pass01", "candidates.json", sha1)], ["pass01:c01"])
    res = _freeze(project, skill, "search-field", run_id, field)
    assert res.returncode != 0
    assert "omit" in res.stderr
    assert "pass01:c02" in res.stderr


def test_duplicate_entry_ref_rejected(workspace):
    project, skill = workspace
    run_id = "ri-dup-ref"
    sha1 = _explore(project, skill, run_id, ids=("c01", "c02"))
    field = _field(
        [_pass("pass01", "candidates.json", sha1)],
        ["pass01:c01", "pass01:c01", "pass01:c02"],
    )
    res = _freeze(project, skill, "search-field", run_id, field)
    assert res.returncode != 0
    assert "duplicate composite ref" in res.stderr


def test_duplicate_candidate_id_rejected(workspace):
    project, skill = workspace
    run_id = "ri-dup-id"
    res = _freeze(
        project, skill, "explore", run_id,
        _candidates(("c01", "c01")),
    )
    assert res.returncode != 0
    assert "duplicate candidate_id" in res.stderr


@pytest.mark.parametrize("bad_id", ["c.1", "c:1", "c 1", "c/1", ""])
def test_unreferenceable_candidate_id_rejected(workspace, bad_id):
    """IDs outside the composite-ref character class are not freezable."""
    project, skill = workspace
    run_id = f"ri-grammar-{hashlib.sha256(bad_id.encode()).hexdigest()[:8]}"
    res = _freeze(project, skill, "explore", run_id, _candidates((bad_id,)))
    assert res.returncode != 0
    assert "candidate_id" in res.stderr


def test_non_numeric_candidate_id_is_referenceable(workspace):
    """No hard cNN shape: any composite-compatible id freezes and references."""
    project, skill = workspace
    run_id = "ri-grammar-ok"
    sha = _explore(project, skill, run_id, ids=("c-1_x",))
    field = _field([_pass("pass01", "candidates.json", sha)], ["pass01:c-1_x"])
    res = _freeze(project, skill, "search-field", run_id, field)
    assert res.returncode == 0, res.stderr


def test_empty_residual_pass_keeps_accumulated_field(workspace):
    """Honest 360 exhaustion contributes no refs and leaves prior entries intact."""
    project, skill = workspace
    run_id = "ri-exhaust"
    sha1 = _explore(project, skill, run_id, ids=("c01", "c02"), suffix="pass01")
    sf1 = _field(
        [_pass("pass01", "candidates-pass01.json", sha1)],
        ["pass01:c01", "pass01:c02"],
    )
    res1 = _freeze(project, skill, "search-field", run_id, sf1, suffix="pass01")
    assert res1.returncode == 0, res1.stderr
    sf1_hash = res1.stdout.split()[1]

    sha2 = _explore(
        project, skill, run_id, ids=(), mode="360", suffix="pass02",
        extra={"exhaustion_reason": "No genuinely uncovered structural territory."},
    )
    sf2 = _field(
        [
            _pass("pass01", "candidates-pass01.json", sha1),
            _pass("pass02", "candidates-pass02.json", sha2),
        ],
        ["pass01:c01", "pass01:c02"],
        extra={"prior_ref": "search-field-pass01.json", "prior_hash": sf1_hash},
    )
    res2 = _freeze(project, skill, "search-field", run_id, sf2, suffix="pass02")
    assert res2.returncode == 0, res2.stderr
    final = json.loads((_run_dir(project, run_id) / "search-field-pass02.json").read_text())
    assert final["entries"] == ["pass01:c01", "pass01:c02"]


# ── portfolio referential integrity ───────────────────────────────────


def test_portfolio_missing_assessments_rejected(workspace):
    project, skill = workspace
    run_id = "ri-pf-miss"
    field_ref, field_hash = _basic_run(project, skill, run_id)
    port = _portfolio_v1(field_ref, field_hash, [_assessment("pass01:c01")])
    res = _freeze(project, skill, "portfolio", run_id, port)
    assert res.returncode != 0
    assert "miss 1 field candidate" in res.stderr
    assert "pass01:c02" in res.stderr


def test_portfolio_unknown_assessment_ref_rejected(workspace):
    project, skill = workspace
    run_id = "ri-pf-unknown"
    field_ref, field_hash = _basic_run(project, skill, run_id)
    port = _portfolio_v1(field_ref, field_hash, [
        _assessment("pass01:c01"),
        _assessment("pass01:c02", disposition="DROP", quality="weak", residue=""),
        _assessment("pass01:c99", disposition="DROP", quality="weak", residue=""),
    ])
    res = _freeze(project, skill, "portfolio", run_id, port)
    assert res.returncode != 0
    assert "unknown candidate" in res.stderr
    assert "pass01:c99" in res.stderr


def test_portfolio_duplicate_assessment_ref_rejected(workspace):
    project, skill = workspace
    run_id = "ri-pf-dup"
    field_ref, field_hash = _basic_run(project, skill, run_id)
    port = _portfolio_v1(field_ref, field_hash, [
        _assessment("pass01:c01"),
        _assessment("pass01:c01"),
        _assessment("pass01:c02"),
    ])
    res = _freeze(project, skill, "portfolio", run_id, port)
    assert res.returncode != 0
    assert "duplicate candidate_ref" in res.stderr


def test_portfolio_unknown_nearest_overlap_rejected(workspace):
    project, skill = workspace
    run_id = "ri-pf-overlap"
    field_ref, field_hash = _basic_run(project, skill, run_id)
    port = _portfolio_v1(field_ref, field_hash, [
        _assessment("pass01:c01", overlap="pass01:c99"),
        _assessment("pass01:c02"),
    ], perspectives={"P1": "pass01:c01", "P2": "pass01:c02"})
    res = _freeze(project, skill, "portfolio", run_id, port)
    assert res.returncode != 0
    assert "nearest_overlap" in res.stderr
    assert "pass01:c99" in res.stderr


def test_portfolio_unknown_bundle_member_rejected(workspace):
    project, skill = workspace
    run_id = "ri-pf-bundle"
    field_ref, field_hash = _basic_run(project, skill, run_id)
    bundle = {
        "bundle_id": "B1",
        "member_refs": ["pass01:c01", "pass01:c99"],
        "bundle_thesis": "thesis",
        "composition_gain": "gain",
        "member_roles": {},
        "member_ablation": {"pass01:c01": "a", "pass01:c99": "b"},
        "internal_tension": "tension",
        "weakest_link": "link",
        "new_consequence_or_prediction": "prediction",
    }
    port = _portfolio_v1(
        field_ref, field_hash,
        [_assessment("pass01:c01"), _assessment("pass01:c02")],
        perspectives={"P1": "pass01:c01", "P2": "pass01:c02"},
        bundles=[bundle],
    )
    res = _freeze(project, skill, "portfolio", run_id, port)
    assert res.returncode != 0
    assert "member_refs" in res.stderr
    assert "pass01:c99" in res.stderr


def test_portfolio_unknown_high_upside_ref_rejected(workspace):
    project, skill = workspace
    run_id = "ri-pf-hu"
    field_ref, field_hash = _basic_run(project, skill, run_id)
    port = _portfolio_v1(
        field_ref, field_hash,
        [_assessment("pass01:c01"), _assessment("pass01:c02")],
        perspectives={"P1": "pass01:c01", "P2": "pass01:c02"},
        high_upside=[{"ref": "pass01:c99", "why": "w", "risk": "r"}],
    )
    res = _freeze(project, skill, "portfolio", run_id, port)
    assert res.returncode != 0
    assert "pass01:c99" in res.stderr


def test_failed_freeze_leaves_no_partial_state(workspace):
    project, skill = workspace
    run_id = "ri-partial"
    sha1 = _explore(project, skill, run_id, ids=("c01", "c02"))
    bad_field = _field(
        [_pass("pass01", "candidates.json", sha1)],
        ["pass01:c01", "pass01:c99"],
    )
    res = _freeze(project, skill, "search-field", run_id, bad_field)
    assert res.returncode != 0
    rd = _run_dir(project, run_id)
    for name in ("search-field.json", "search-field.sha256", "search-field.meta.json"):
        assert not (rd / name).exists(), f"partial artifact leaked: {name}"


# ── green accepts: correct PACK and BONK v3 fixtures ──────────────────


def test_correct_pack_fixture_accepts_and_is_deterministic(workspace):
    project, skill = workspace
    field_ref, field_hash = _three_pass_field(project, skill, "ri-pack")
    assessments = [
        _assessment("pass01:c01"),
        _assessment("pass01:c02"),
        _assessment("pass02:c01", disposition="DROP", quality="weak", residue=""),
        _assessment("pass03:c01", disposition="DROP", quality="weak", residue=""),
    ]
    port = _portfolio_v1(
        field_ref, field_hash, assessments, route="PACK",
        perspectives={"P1": "pass01:c01", "P2": "pass01:c02"},
        high_upside=[{"ref": "pass01:c02", "why": "broad reach", "risk": "single context"}],
    )
    res = _freeze(project, skill, "portfolio", "ri-pack", port)
    assert res.returncode == 0, res.stderr
    bytes_a = (_run_dir(project, "ri-pack") / "portfolio.json").read_bytes()

    # Identical payload frozen in an independent run reproduces the artifact bytes.
    field_ref_b, field_hash_b = _three_pass_field(project, skill, "ri-pack-b")
    port_b = _portfolio_v1(
        field_ref_b, field_hash_b, assessments, route="PACK",
        perspectives={"P1": "pass01:c01", "P2": "pass01:c02"},
        high_upside=[{"ref": "pass01:c02", "why": "broad reach", "risk": "single context"}],
    )
    res_b = _freeze(project, skill, "portfolio", "ri-pack-b", port_b)
    assert res_b.returncode == 0, res_b.stderr
    bytes_b = (_run_dir(project, "ri-pack-b") / "portfolio.json").read_bytes()
    assert bytes_a == bytes_b


def test_correct_bonk_v3_fixture_accepts(workspace):
    project, skill = workspace
    field_ref, field_hash = _three_pass_field(project, skill, "ri-v3")
    bundle_a = {
        "bundle_id": "B1",
        "member_refs": ["pass01:c01", "pass01:c02"],
        "bundle_thesis": "thesis B1",
        "composition_gain": "gain B1",
        "member_roles": {},
        "member_ablation": {"pass01:c01": "a", "pass01:c02": "b"},
        "internal_tension": "tension B1",
        "weakest_link": "weak B1",
        "new_consequence_or_prediction": "prediction B1",
    }
    bundle_b = {
        "bundle_id": "B2",
        "member_refs": ["pass02:c01", "pass03:c01"],
        "bundle_thesis": "thesis B2",
        "composition_gain": "gain B2",
        "member_roles": {},
        "member_ablation": {"pass02:c01": "a", "pass03:c01": "b"},
        "internal_tension": "tension B2",
        "weakest_link": "weak B2",
        "new_consequence_or_prediction": "prediction B2",
    }
    port = {
        "schema_version": "pizm-portfolio-selection-v3",
        "stage": "portfolio",
        "route": "BONK",
        "field_ref": field_ref,
        "field_hash": field_hash,
        "perspectives": {"P1": "pass01:c01", "P2": "pass01:c02"},
        "candidate_assessments": [
            _assessment("pass01:c01"),
            _assessment("pass01:c02"),
            _assessment("pass02:c01", disposition="DROP", quality="weak", residue=""),
            _assessment("pass03:c01", disposition="DROP", quality="weak", residue=""),
        ],
        "bundles": [bundle_a, bundle_b],
        "high_upside": [],
        "development_mode": "DUAL_BUNDLES",
        "development_targets": [
            {"target_type": "B", "target_id": "B1", "why_develop": "develop B1"},
            {"target_type": "B", "target_id": "B2", "why_develop": "develop B2"},
        ],
        "material_difference": "B1 changes the mechanism; B2 shifts the boundary.",
    }
    res = _freeze(project, skill, "portfolio", "ri-v3", port)
    assert res.returncode == 0, res.stderr
    assert "FREEZE_OK" in res.stdout
    assert "NEXT CONTRACT" not in res.stdout
