"""Wave 2A.1 tests for the ``pizm-checkpoint freeze-search-field`` builder.

The builder reads ONLY a verified frozen ``candidates-passNN.json`` and emits
the canonical accumulated ``search-field-passNN.json`` (refs, hashes, prior
linkage, append-only ordering). Hand-authored field JSON is no longer needed.

Case coverage: happy pass01/02/03 chain, honest exhaustion, missing/invalid
sidecars, pass gap, prior mismatch, idempotent re-run (byte-identical AND
legacy byte-differing), conflict fail-closed, invalid candidate id, ordering,
unsuffixed rejection, and concurrent double-invoke.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT = os.environ.get(
    "PIZM_CHECKPOINT_UNDER_TEST",
    str(REPO_ROOT / "bin" / "pizm-checkpoint"),
)


@pytest.fixture
def workspace(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    skill = tmp_path / "skill"
    (skill / "references").mkdir(parents=True)
    return project, skill


# ── helpers ───────────────────────────────────────────────────────────


def _run_ck(*args):
    return subprocess.run(
        [sys.executable, CHECKPOINT, *args], capture_output=True, text=True
    )


def _run_dir(project, run_id):
    return project / ".ai" / "pizm" / f"run-{run_id}"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path, data, **dump_kwargs):
    kwargs = {"indent": 2}
    kwargs.update(dump_kwargs)
    Path(path).write_text(json.dumps(data, **kwargs), encoding="utf-8")
    return Path(path)


def _write_frozen(path, data, **dump_kwargs):
    """Write artifact + a matching .sha256 sidecar, bypassing freeze validation."""
    path = _write_json(path, data, **dump_kwargs)
    path.with_suffix(".sha256").write_text(_sha256(path), encoding="utf-8")
    return path


def _candidates(ids, mode="NORMAL", extra=None):
    data = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": mode,
        "candidates": [
            {"candidate_id": cid, "content": f"idea {cid}"} for cid in ids
        ],
    }
    if extra:
        data.update(extra)
    return data


def _freeze_explore(project, skill, run_id, ids, suffix, mode="NORMAL",
                    extra=None, name=None):
    inp = project / (name or f"_in_explore_{suffix or 'main'}.json")
    _write_json(inp, _candidates(ids, mode, extra))
    cmd = [
        "freeze", "--stage", "explore", "--run-id", run_id, "--input", str(inp),
        "--project-root", str(project), "--skill-root", str(skill),
    ]
    if suffix:
        cmd += ["--artifact-suffix", suffix]
    res = _run_ck(*cmd)
    assert res.returncode == 0, res.stderr
    return res.stdout.split()[1]


def _freeze_field(project, skill, run_id, payload, suffix, dump_kwargs=None):
    inp = project / f"_in_field_{suffix}.json"
    _write_json(inp, payload, **(dump_kwargs or {}))
    return _run_ck(
        "freeze", "--stage", "search-field", "--run-id", run_id, "--input", str(inp),
        "--project-root", str(project), "--skill-root", str(skill),
        "--artifact-suffix", suffix,
    )


def _build(project, skill, run_id, suffix, candidates_ref=None):
    cmd = [
        "freeze-search-field", "--run-id", run_id, "--artifact-suffix", suffix,
        "--project-root", str(project),
    ]
    if skill:
        cmd += ["--skill-root", str(skill)]
    if candidates_ref:
        cmd += ["--candidates-ref", candidates_ref]
    return _run_ck(*cmd)


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


def _load(project, run_id, name):
    return json.loads((_run_dir(project, run_id) / name).read_text(encoding="utf-8"))


def _snapshot(run_dir, prefix):
    return {
        p.name: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in sorted(run_dir.glob(prefix + ".*"))
    }


# ── happy paths ───────────────────────────────────────────────────────


def test_happy_pass01_builds_canonical_field(workspace):
    project, skill = workspace
    run_id = "sf-happy01"
    h1 = _freeze_explore(project, skill, run_id, ("c01", "c02"), "pass01")
    res = _build(project, skill, run_id, "pass01")
    assert res.returncode == 0, res.stderr
    parts = res.stdout.split()
    assert parts[0] == "SEARCH_FIELD_OK"
    field = _load(project, run_id, "search-field-pass01.json")
    assert field["passes"] == [
        {"pass_id": "pass01", "candidates_ref": "candidates-pass01.json", "frozen_hash": h1}
    ]
    assert field["entries"] == ["pass01:c01", "pass01:c02"]
    assert "prior_ref" not in field and "prior_hash" not in field
    assert parts[1] == _sha256(_run_dir(project, run_id) / "search-field-pass01.json")


def test_happy_pass01_02_03_chain_accumulates(workspace):
    project, skill = workspace
    run_id = "sf-chain"
    h1 = _freeze_explore(project, skill, run_id, ("c01", "c02"), "pass01")
    assert _build(project, skill, run_id, "pass01").returncode == 0
    h2 = _freeze_explore(project, skill, run_id, ("c01", "c03"), "pass02", mode="360")
    assert _build(project, skill, run_id, "pass02").returncode == 0
    h3 = _freeze_explore(project, skill, run_id, ("c02",), "pass03", mode="RIFT")
    assert _build(project, skill, run_id, "pass03").returncode == 0

    field = _load(project, run_id, "search-field-pass03.json")
    assert [p["pass_id"] for p in field["passes"]] == ["pass01", "pass02", "pass03"]
    assert [p["frozen_hash"] for p in field["passes"]] == [h1, h2, h3]
    assert field["entries"] == [
        "pass01:c01", "pass01:c02", "pass02:c01", "pass02:c03", "pass03:c02",
    ]
    assert field["prior_ref"] == "search-field-pass02.json"
    assert field["prior_hash"] == _sha256(
        _run_dir(project, run_id) / "search-field-pass02.json"
    )


def test_honest_exhaustion_pass_adds_no_new_refs(workspace):
    project, skill = workspace
    run_id = "sf-exhaust"
    _freeze_explore(project, skill, run_id, ("c01", "c02"), "pass01")
    assert _build(project, skill, run_id, "pass01").returncode == 0
    _freeze_explore(
        project, skill, run_id, (), "pass02", mode="360",
        extra={"exhaustion_reason": "no new territory found"},
    )
    res = _build(project, skill, run_id, "pass02")
    assert res.returncode == 0, res.stderr
    field = _load(project, run_id, "search-field-pass02.json")
    assert [p["pass_id"] for p in field["passes"]] == ["pass01", "pass02"]
    assert field["entries"] == ["pass01:c01", "pass01:c02"]


def test_entry_ordering_preserved_and_appended(workspace):
    project, skill = workspace
    run_id = "sf-order"
    _freeze_explore(project, skill, run_id, ("c03", "c01", "c02"), "pass01")
    assert _build(project, skill, run_id, "pass01").returncode == 0
    assert _load(project, run_id, "search-field-pass01.json")["entries"] == [
        "pass01:c03", "pass01:c01", "pass01:c02",
    ]
    _freeze_explore(project, skill, run_id, ("c02", "c03"), "pass02", mode="360")
    assert _build(project, skill, run_id, "pass02").returncode == 0
    assert _load(project, run_id, "search-field-pass02.json")["entries"] == [
        "pass01:c03", "pass01:c01", "pass01:c02", "pass02:c02", "pass02:c03",
    ]


# ── input verification failures ───────────────────────────────────────


def test_missing_candidates_sidecar_fails(workspace):
    project, skill = workspace
    run_id = "sf-nosha"
    _freeze_explore(project, skill, run_id, ("c01",), "pass01")
    (_run_dir(project, run_id) / "candidates-pass01.sha256").unlink()
    res = _build(project, skill, run_id, "pass01")
    assert res.returncode != 0
    assert "missing sidecar" in res.stderr
    assert not (_run_dir(project, run_id) / "search-field-pass01.json").exists()


def test_candidates_hash_mismatch_fails(workspace):
    project, skill = workspace
    run_id = "sf-badhash"
    _freeze_explore(project, skill, run_id, ("c01",), "pass01")
    (_run_dir(project, run_id) / "candidates-pass01.sha256").write_text(
        "0" * 64, encoding="utf-8"
    )
    res = _build(project, skill, run_id, "pass01")
    assert res.returncode != 0
    assert "mismatch" in res.stderr
    assert not (_run_dir(project, run_id) / "search-field-pass01.json").exists()


def test_pass_gap_without_prior_fails(workspace):
    project, skill = workspace
    run_id = "sf-gap"
    _freeze_explore(project, skill, run_id, ("c01",), "pass01")
    assert _build(project, skill, run_id, "pass01").returncode == 0
    _freeze_explore(project, skill, run_id, ("c01",), "pass03")
    res = _build(project, skill, run_id, "pass03")
    assert res.returncode != 0
    assert "pass02" in res.stderr
    assert not (_run_dir(project, run_id) / "search-field-pass03.json").exists()


def test_prior_sidecar_mismatch_fails(workspace):
    project, skill = workspace
    run_id = "sf-prior"
    _freeze_explore(project, skill, run_id, ("c01",), "pass01")
    assert _build(project, skill, run_id, "pass01").returncode == 0
    _freeze_explore(project, skill, run_id, ("c01",), "pass02")
    (_run_dir(project, run_id) / "search-field-pass01.sha256").write_text(
        "1" * 64, encoding="utf-8"
    )
    res = _build(project, skill, run_id, "pass02")
    assert res.returncode != 0
    assert "sidecar hash mismatch" in res.stderr
    assert not (_run_dir(project, run_id) / "search-field-pass02.json").exists()


def test_invalid_candidate_id_rejected(workspace):
    project, skill = workspace
    run_id = "sf-badid"
    run_dir = _run_dir(project, run_id)
    run_dir.mkdir(parents=True)
    _write_frozen(run_dir / "candidates-pass01.json", _candidates(("bad id",)))
    res = _build(project, skill, run_id, "pass01")
    assert res.returncode != 0
    assert "invalid candidate_id" in res.stderr
    assert not (run_dir / "search-field-pass01.json").exists()


def test_unsuffixed_suffix_rejected(workspace):
    project, skill = workspace
    res = _run_ck(
        "freeze-search-field", "--run-id", "sf-unsuffixed",
        "--artifact-suffix", "main", "--project-root", str(project),
    )
    assert res.returncode != 0
    assert "invalid artifact-suffix" in res.stderr
    # Omitting the required suffix is an argparse usage error.
    res2 = _run_ck(
        "freeze-search-field", "--run-id", "sf-unsuffixed",
        "--project-root", str(project),
    )
    assert res2.returncode == 2


# ── retry / confirm policy ────────────────────────────────────────────


def test_idempotent_rerun_byte_identical_zero_writes(workspace):
    project, skill = workspace
    run_id = "sf-idem"
    _freeze_explore(project, skill, run_id, ("c01", "c02"), "pass01")
    assert _build(project, skill, run_id, "pass01").returncode == 0
    run_dir = _run_dir(project, run_id)
    before = _snapshot(run_dir, "search-field-pass01")
    res = _build(project, skill, run_id, "pass01")
    assert res.returncode == 0, res.stderr
    assert "SEARCH_FIELD_OK" in res.stdout
    assert _snapshot(run_dir, "search-field-pass01") == before


def test_legacy_equivalent_bytes_differ_confirms_zero_writes(workspace):
    """A hand-built legacy field with identical semantics but different bytes
    must confirm (not conflict) and must not be rewritten."""
    project, skill = workspace
    run_id = "sf-legacy"
    h1 = _freeze_explore(project, skill, run_id, ("c01", "c02"), "pass01")
    legacy = _field(
        [_pass("pass01", "candidates-pass01.json", h1)],
        ["pass01:c01", "pass01:c02"],
    )
    res = _freeze_field(project, skill, run_id, legacy, "pass01",
                        dump_kwargs={"indent": 4, "sort_keys": True})
    assert res.returncode == 0, res.stderr
    run_dir = _run_dir(project, run_id)
    artifact = run_dir / "search-field-pass01.json"
    legacy_bytes = artifact.read_bytes()
    before = _snapshot(run_dir, "search-field-pass01")

    res2 = _build(project, skill, run_id, "pass01")
    assert res2.returncode == 0, res2.stderr
    assert "SEARCH_FIELD_OK" in res2.stdout
    assert artifact.read_bytes() == legacy_bytes
    assert _snapshot(run_dir, "search-field-pass01") == before


def test_missing_target_sidecar_completed_for_confirmed_content(workspace):
    project, skill = workspace
    run_id = "sf-complete"
    h1 = _freeze_explore(project, skill, run_id, ("c01", "c02"), "pass01")
    legacy = _field(
        [_pass("pass01", "candidates-pass01.json", h1)],
        ["pass01:c01", "pass01:c02"],
    )
    assert _freeze_field(project, skill, run_id, legacy, "pass01").returncode == 0
    run_dir = _run_dir(project, run_id)
    artifact = run_dir / "search-field-pass01.json"
    json_bytes = artifact.read_bytes()
    sidecar = run_dir / "search-field-pass01.sha256"
    sidecar.unlink()

    res = _build(project, skill, run_id, "pass01")
    assert res.returncode == 0, res.stderr
    assert artifact.read_bytes() == json_bytes  # confirmed JSON untouched
    assert sidecar.read_text(encoding="utf-8").strip() == _sha256(artifact)


def test_conflicting_existing_field_fails_closed(workspace):
    project, skill = workspace
    run_id = "sf-conflict"
    h1 = _freeze_explore(project, skill, run_id, ("c01", "c02"), "pass01")
    run_dir = _run_dir(project, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    conflicting = _field(
        [_pass("pass01", "candidates-pass01.json", h1)], ["pass01:c01"]
    )
    artifact = _write_frozen(run_dir / "search-field-pass01.json", conflicting)
    before = artifact.read_bytes()

    res = _build(project, skill, run_id, "pass01")
    assert res.returncode != 0
    assert "conflict" in res.stderr.lower()
    assert artifact.read_bytes() == before  # never clobbered


def test_conflicting_field_with_invalid_sidecar_not_completed(workspace):
    project, skill = workspace
    run_id = "sf-conflict-badsidecar"
    h1 = _freeze_explore(project, skill, run_id, ("c01", "c02"), "pass01")
    run_dir = _run_dir(project, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    conflicting = _field(
        [_pass("pass01", "candidates-pass01.json", h1)], ["pass01:c01"]
    )
    artifact = _write_json(run_dir / "search-field-pass01.json", conflicting)
    sidecar = run_dir / "search-field-pass01.sha256"
    sidecar.write_text("2" * 64, encoding="utf-8")

    res = _build(project, skill, run_id, "pass01")
    assert res.returncode != 0
    assert "conflict" in res.stderr.lower()
    assert sidecar.read_text(encoding="utf-8") == "2" * 64  # not repaired
    assert artifact.exists()  # not deleted


def test_orphan_sidecar_without_json_fails_closed_preserving_foreign(workspace):
    project, skill = workspace
    run_id = "sf-orphan"
    _freeze_explore(project, skill, run_id, ("c01",), "pass01")
    run_dir = _run_dir(project, run_id)
    orphan = run_dir / "search-field-pass01.sha256"
    orphan.write_text("3" * 64, encoding="utf-8")

    res = _build(project, skill, run_id, "pass01")
    assert res.returncode != 0
    assert orphan.read_text(encoding="utf-8") == "3" * 64  # foreign file preserved
    assert not (run_dir / "search-field-pass01.json").exists()


# ── Wave 2A.3: lying sidecar / bad meta must fail closed ──────────────


def test_equivalent_field_with_wrong_sidecar_hash_fails_closed(workspace):
    """A present-but-wrong .sha256 is a lying record: never repaired."""
    project, skill = workspace
    run_id = "sf3-sidecar-lie"
    h1 = _freeze_explore(project, skill, run_id, ("c01", "c02"), "pass01")
    legacy = _field(
        [_pass("pass01", "candidates-pass01.json", h1)],
        ["pass01:c01", "pass01:c02"],
    )
    res = _freeze_field(project, skill, run_id, legacy, "pass01",
                        dump_kwargs={"indent": 4, "sort_keys": True})
    assert res.returncode == 0, res.stderr
    run_dir = _run_dir(project, run_id)
    artifact = run_dir / "search-field-pass01.json"
    sidecar = run_dir / "search-field-pass01.sha256"
    json_bytes = artifact.read_bytes()
    sidecar.write_text("f" * 64, encoding="utf-8")
    before = _snapshot(run_dir, "search-field-pass01")

    res2 = _build(project, skill, run_id, "pass01")
    assert res2.returncode != 0
    assert "mismatch" in res2.stderr
    assert artifact.read_bytes() == json_bytes  # JSON never rewritten
    assert sidecar.read_text(encoding="utf-8") == "f" * 64  # not repaired
    assert _snapshot(run_dir, "search-field-pass01") == before


def test_equivalent_field_with_corrupt_meta_fails_closed(workspace):
    """A present-but-bad .meta.json must fail closed, not confirm."""
    project, skill = workspace
    run_id = "sf3-meta-bad"
    h1 = _freeze_explore(project, skill, run_id, ("c01", "c02"), "pass01")
    legacy = _field(
        [_pass("pass01", "candidates-pass01.json", h1)],
        ["pass01:c01", "pass01:c02"],
    )
    res = _freeze_field(project, skill, run_id, legacy, "pass01",
                        dump_kwargs={"indent": 4, "sort_keys": True})
    assert res.returncode == 0, res.stderr
    run_dir = _run_dir(project, run_id)
    meta = run_dir / "search-field-pass01.meta.json"

    meta.write_text("{ not valid json", encoding="utf-8")
    before = _snapshot(run_dir, "search-field-pass01")
    res2 = _build(project, skill, run_id, "pass01")
    assert res2.returncode != 0
    assert "mismatch" in res2.stderr
    assert _snapshot(run_dir, "search-field-pass01") == before

    # Valid JSON but inconsistent sha256 is equally fail-closed.
    meta.write_text(json.dumps({"sha256": "0" * 64}), encoding="utf-8")
    before2 = _snapshot(run_dir, "search-field-pass01")
    res3 = _build(project, skill, run_id, "pass01")
    assert res3.returncode != 0
    assert "mismatch" in res3.stderr
    assert _snapshot(run_dir, "search-field-pass01") == before2


# ── concurrency ───────────────────────────────────────────────────────


def test_concurrent_double_invoke_one_wins_other_confirms(workspace):
    project, skill = workspace
    run_id = "sf-concurrent"
    _freeze_explore(project, skill, run_id, ("c01", "c02"), "pass01")
    cmd = [
        sys.executable, CHECKPOINT, "freeze-search-field", "--run-id", run_id,
        "--artifact-suffix", "pass01", "--project-root", str(project),
        "--skill-root", str(skill),
    ]

    def _invoke():
        return subprocess.run(cmd, capture_output=True, text=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _invoke(), range(2)))

    assert all(r.returncode == 0 for r in results), [r.stderr for r in results]
    hashes = {
        r.stdout.split()[1] for r in results if "SEARCH_FIELD_OK" in r.stdout
    }
    assert len(hashes) == 1
    run_dir = _run_dir(project, run_id)
    artifact = run_dir / "search-field-pass01.json"
    assert _load(project, run_id, "search-field-pass01.json")["entries"] == [
        "pass01:c01", "pass01:c02",
    ]
    assert (run_dir / "search-field-pass01.sha256").read_text(
        encoding="utf-8"
    ).strip() == _sha256(artifact)


# ── Wave 2A.3b partial-state hardening ─────────────────────────────────


def test_preexisting_wrong_meta_blocks_json_creation(workspace):
    """P1-1: JSON absent + pre-planted wrong-hash meta fails BEFORE any write.

    The builder must be at least as strict as legacy ``freeze()``: a lying
    provenance record beside an absent JSON can never be endorsed by
    ``SEARCH_FIELD_OK``, and the foreign meta must be left byte-untouched.
    """
    project, skill = workspace
    run_id = "sf3b-meta-orphan"
    _freeze_explore(project, skill, run_id, ("c01", "c02"), "pass01")
    run_dir = _run_dir(project, run_id)
    meta = run_dir / "search-field-pass01.meta.json"
    meta.write_text(
        json.dumps(
            {
                "sha256": "0" * 64,
                "timestamp": "2026-01-01T00:00:00+00:00",
                "run_id": run_id,
                "stage": "search-field",
                "schema_version": "pizm-search-field-v1",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    meta_before = meta.read_bytes()

    res = _build(project, skill, run_id, "pass01")
    assert res.returncode != 0
    assert "mismatch" in res.stderr
    assert not (run_dir / "search-field-pass01.json").exists()
    assert not (run_dir / "search-field-pass01.sha256").exists()
    assert meta.read_bytes() == meta_before


def test_wrong_meta_with_absent_sha_writes_nothing(workspace):
    """P1-2: correct JSON + ABSENT sha + wrong meta -> zero writes (no sha)."""
    project, skill = workspace
    run_id = "sf3b-confirm-nosha"
    h1 = _freeze_explore(project, skill, run_id, ("c01", "c02"), "pass01")
    legacy = _field(
        [_pass("pass01", "candidates-pass01.json", h1)],
        ["pass01:c01", "pass01:c02"],
    )
    assert _freeze_field(project, skill, run_id, legacy, "pass01").returncode == 0
    run_dir = _run_dir(project, run_id)
    (run_dir / "search-field-pass01.sha256").unlink()
    meta = run_dir / "search-field-pass01.meta.json"
    meta.write_text(
        json.dumps(
            {
                "sha256": "0" * 64,
                "timestamp": "2026-01-01T00:00:00+00:00",
                "run_id": run_id,
                "stage": "search-field",
                "schema_version": "pizm-search-field-v1",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    before = _snapshot(run_dir, "search-field-pass01")

    res = _build(project, skill, run_id, "pass01")
    assert res.returncode != 0
    assert "mismatch" in res.stderr
    assert not (run_dir / "search-field-pass01.sha256").exists()
    assert _snapshot(run_dir, "search-field-pass01") == before


def test_concurrent_sidecar_completion_one_winner_no_clobber(workspace):
    """P2-3: two racers completing a MISSING sha sidecar never clobber it.

    Exclusive create makes exactly one process the creator; the loser re-reads
    and confirms. JSON and meta must stay byte-stable.
    """
    project, skill = workspace
    run_id = "sf3b-sidecar-race"
    _freeze_explore(project, skill, run_id, ("c01", "c02"), "pass01")
    assert _build(project, skill, run_id, "pass01").returncode == 0
    run_dir = _run_dir(project, run_id)
    artifact = run_dir / "search-field-pass01.json"
    sidecar = run_dir / "search-field-pass01.sha256"
    meta = run_dir / "search-field-pass01.meta.json"
    sidecar.unlink()
    assert not sidecar.exists()
    json_before = artifact.read_bytes()
    meta_before = meta.read_bytes()

    cmd = [
        sys.executable, CHECKPOINT, "freeze-search-field", "--run-id", run_id,
        "--artifact-suffix", "pass01", "--project-root", str(project),
        "--skill-root", str(skill),
    ]

    def _invoke():
        return subprocess.run(cmd, capture_output=True, text=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _invoke(), range(2)))

    assert all(r.returncode == 0 for r in results), [r.stderr for r in results]
    assert sidecar.read_text(encoding="utf-8").strip() == _sha256(artifact)
    assert artifact.read_bytes() == json_before
    assert meta.read_bytes() == meta_before


def test_legacy_shaped_meta_with_correct_values_accepted(workspace):
    """Compat: the 5-key meta legacy ``freeze()`` writes is accepted unchanged."""
    project, skill = workspace
    run_id = "sf3b-legacy-meta"
    h1 = _freeze_explore(project, skill, run_id, ("c01", "c02"), "pass01")
    legacy = _field(
        [_pass("pass01", "candidates-pass01.json", h1)],
        ["pass01:c01", "pass01:c02"],
    )
    assert _freeze_field(project, skill, run_id, legacy, "pass01").returncode == 0
    run_dir = _run_dir(project, run_id)
    artifact = run_dir / "search-field-pass01.json"
    meta = run_dir / "search-field-pass01.meta.json"
    meta.write_text(
        json.dumps(
            {
                "sha256": _sha256(artifact),
                "timestamp": "2026-01-01T00:00:00+00:00",
                "run_id": run_id,
                "stage": "search-field",
                "schema_version": "pizm-search-field-v1",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    before = _snapshot(run_dir, "search-field-pass01")

    res = _build(project, skill, run_id, "pass01")
    assert res.returncode == 0, res.stderr
    assert "SEARCH_FIELD_OK" in res.stdout
    assert _snapshot(run_dir, "search-field-pass01") == before
