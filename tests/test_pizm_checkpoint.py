"""
Focused behavioral tests for bin/pizm-checkpoint.

Covers: both stages, byte identity, sidecar/meta values, hash verification,
invalid schema, duplicate candidate id, duplicate P-ID, invalid P-ID,
refuse overwrite, hidden contract absent on failure and present after success,
simulated corrupted read-back failure, source-level provider-free guarantee,
stage-scoped metadata, explore+deep coexistence, concurrent exclusive publish,
missing contract nonzero+cleanup, retry after corruption, fullmatch on IDs,
root non-object, no hidden path in errors.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

CHECKPOINT = str(Path(__file__).resolve().parent.parent / "bin" / "pizm-checkpoint")
REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def workspace(tmp_path):
    """Workspace with project root, skill root, and contract stubs."""
    project = tmp_path / "project"
    project.mkdir()
    skill = tmp_path / "skill"
    skill.mkdir()
    refs = skill / "references"
    refs.mkdir()
    (refs / "explore-selector.md").write_text("# EXPLORE SELECTOR RUBRIC\nhidden rubric")
    (refs / "deep-reviewer.md").write_text("# DEEP REVIEWER RUBRIC\nhidden rubric")
    return project, skill


def run_ck(*args, cwd=None):
    return subprocess.run(
        [sys.executable, CHECKPOINT, *args],
        capture_output=True, text=True, cwd=cwd,
    )


def write_json(path, data):
    p = Path(path)
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


def valid_explore():
    return {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {"candidate_id": "c1", "content": "idea one"},
            {"candidate_id": "c2", "content": "idea two"},
        ],
    }


def valid_deep():
    return {
        "schema_version": "pizm-development-v1",
        "stage": "deep",
        "selected_p_ids": ["P1", "P3"],
        "development": {"P1": {"body": "developed text"}, "P3": {"body": "more"}},
    }


# ── Explore stage ─────────────────────────────────────────────────────


def test_explore_freeze_success(workspace):
    project, skill = workspace
    inp = write_json(project / "cand.json", valid_explore())

    result = run_ck(
        "freeze", "--stage", "explore", "--run-id", "test-run-1",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )

    assert result.returncode == 0
    assert "FREEZE_OK" in result.stdout

    run_dir = project / ".ai" / "pizm" / "run-test-run-1"
    assert (run_dir / "candidates.json").exists()
    assert (run_dir / "candidates.sha256").exists()
    assert (run_dir / "candidates.meta.json").exists()


def test_explore_byte_identity(workspace):
    project, skill = workspace
    raw = json.dumps(valid_explore()).encode("utf-8")
    inp = project / "cand.json"
    inp.write_bytes(raw)

    run_ck("freeze", "--stage", "explore", "--run-id", "byte-test",
           "--input", str(inp), "--project-root", str(project),
           "--skill-root", str(skill))

    artifact = project / ".ai" / "pizm" / "run-byte-test" / "candidates.json"
    assert artifact.read_bytes() == raw


def test_explore_sha256_sidecar(workspace):
    project, skill = workspace
    raw = json.dumps(valid_explore()).encode("utf-8")
    inp = project / "cand.json"
    inp.write_bytes(raw)

    run_ck("freeze", "--stage", "explore", "--run-id", "sha-test",
           "--input", str(inp), "--project-root", str(project),
           "--skill-root", str(skill))

    expected = hashlib.sha256(raw).hexdigest()
    sha_file = project / ".ai" / "pizm" / "run-sha-test" / "candidates.sha256"
    assert sha_file.read_text() == expected


def test_explore_metadata(workspace):
    project, skill = workspace
    inp = write_json(project / "cand.json", valid_explore())

    run_ck("freeze", "--stage", "explore", "--run-id", "meta-test",
           "--input", inp, "--project-root", str(project),
           "--skill-root", str(skill))

    meta = json.loads(
        (project / ".ai" / "pizm" / "run-meta-test" / "candidates.meta.json").read_text()
    )
    assert meta["run_id"] == "meta-test"
    assert meta["stage"] == "explore"
    assert meta["schema_version"] == "pizm-candidates-v1"
    raw = json.dumps(valid_explore()).encode("utf-8")
    assert meta["sha256"] == hashlib.sha256(raw).hexdigest()
    assert "timestamp" in meta


# ── Deep stage ────────────────────────────────────────────────────────


def test_deep_freeze_success(workspace):
    project, skill = workspace
    inp = write_json(project / "dev.json", valid_deep())

    result = run_ck(
        "freeze", "--stage", "deep", "--run-id", "deep-run-1",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )

    assert result.returncode == 0
    assert "FREEZE_OK" in result.stdout
    assert (project / ".ai" / "pizm" / "run-deep-run-1" / "development.json").exists()
    assert (project / ".ai" / "pizm" / "run-deep-run-1" / "development.sha256").exists()
    assert (project / ".ai" / "pizm" / "run-deep-run-1" / "development.meta.json").exists()


def test_deep_byte_identity(workspace):
    project, skill = workspace
    raw = json.dumps(valid_deep()).encode("utf-8")
    inp = project / "dev.json"
    inp.write_bytes(raw)

    run_ck("freeze", "--stage", "deep", "--run-id", "deep-byte",
           "--input", str(inp), "--project-root", str(project),
           "--skill-root", str(skill))

    artifact = project / ".ai" / "pizm" / "run-deep-byte" / "development.json"
    assert artifact.read_bytes() == raw


# ── Validation failures ───────────────────────────────────────────────


def test_invalid_schema_version_explore(workspace):
    project, skill = workspace
    data = valid_explore()
    data["schema_version"] = "wrong"
    inp = write_json(project / "bad.json", data)

    result = run_ck("freeze", "--stage", "explore", "--run-id", "bad-schema",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0
    assert not (project / ".ai" / "pizm" / "run-bad-schema" / "candidates.json").exists()


def test_duplicate_candidate_id(workspace):
    project, skill = workspace
    data = valid_explore()
    data["candidates"] = [
        {"candidate_id": "c1", "content": "a"},
        {"candidate_id": "c1", "content": "b"},
    ]
    inp = write_json(project / "dup.json", data)

    result = run_ck("freeze", "--stage", "explore", "--run-id", "dup-test",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0
    assert "duplicate" in result.stderr.lower()


def test_duplicate_selected_p_ids(workspace):
    project, skill = workspace
    data = valid_deep()
    data["selected_p_ids"] = ["P1", "P1"]
    inp = write_json(project / "dup-pid.json", data)

    result = run_ck("freeze", "--stage", "deep", "--run-id", "dup-pid",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0
    assert "duplicate" in result.stderr.lower()


def test_invalid_p_id(workspace):
    project, skill = workspace
    data = valid_deep()
    data["selected_p_ids"] = ["P0", "P1"]
    inp = write_json(project / "bad-pid.json", data)

    result = run_ck("freeze", "--stage", "deep", "--run-id", "bad-pid",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0


def test_empty_candidates_list(workspace):
    project, skill = workspace
    data = valid_explore()
    data["candidates"] = []
    inp = write_json(project / "empty.json", data)

    result = run_ck("freeze", "--stage", "explore", "--run-id", "empty-cand",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0


def test_invalid_mode(workspace):
    project, skill = workspace
    data = valid_explore()
    data["mode"] = "DEEP"
    inp = write_json(project / "bad-mode.json", data)

    result = run_ck("freeze", "--stage", "explore", "--run-id", "bad-mode",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0


def test_empty_development_object(workspace):
    project, skill = workspace
    data = valid_deep()
    data["development"] = {}
    inp = write_json(project / "empty-dev.json", data)

    result = run_ck("freeze", "--stage", "deep", "--run-id", "empty-dev",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0


def test_invalid_json_input(workspace):
    project, skill = workspace
    inp = project / "notjson.txt"
    inp.write_text("not valid json{{{")

    result = run_ck("freeze", "--stage", "explore", "--run-id", "bad-json",
                    "--input", str(inp), "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0


def test_root_non_object(workspace):
    """Root JSON value that is not an object must be rejected cleanly."""
    project, skill = workspace
    inp = project / "array.json"
    inp.write_text("[1, 2, 3]")

    result = run_ck("freeze", "--stage", "explore", "--run-id", "root-array",
                    "--input", str(inp), "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0
    assert "object" in result.stderr.lower() or "schema" in result.stderr.lower()


def test_root_string(workspace):
    project, skill = workspace
    inp = project / "string.json"
    inp.write_text('"just a string"')

    result = run_ck("freeze", "--stage", "deep", "--run-id", "root-string",
                    "--input", str(inp), "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0


# ── Run-ID validation (fullmatch) ────────────────────────────────────


def test_invalid_run_id_uppercase(workspace):
    project, skill = workspace
    inp = write_json(project / "cand.json", valid_explore())

    result = run_ck("freeze", "--stage", "explore", "--run-id", "Bad-Run",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0


def test_invalid_run_id_special_chars(workspace):
    project, skill = workspace
    inp = write_json(project / "cand.json", valid_explore())

    result = run_ck("freeze", "--stage", "explore", "--run-id", "bad_run!",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0


def test_run_id_trailing_newline_rejected(workspace):
    """Trailing newline in run-id must be rejected by fullmatch."""
    project, skill = workspace
    inp = write_json(project / "cand.json", valid_explore())

    result = run_ck("freeze", "--stage", "explore", "--run-id", "bad-id\n",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0


# ── P-ID fullmatch ────────────────────────────────────────────────────


@pytest.mark.parametrize("p_id,valid", [
    ("P1", True),
    ("P9", True),
    ("P10", True),
    ("P999", True),
    ("P0", False),
    ("P01", False),
    ("p1", False),
    ("P", False),
    ("P1a", False),
    ("PP1", False),
])
def test_p_id_patterns(workspace, p_id, valid):
    project, skill = workspace
    data = valid_deep()
    data["selected_p_ids"] = [p_id]
    inp = write_json(project / f"pid-{p_id}.json", data)

    result = run_ck("freeze", "--stage", "deep", "--run-id", f"pid-{p_id.lower()}",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    if valid:
        assert result.returncode == 0
    else:
        assert result.returncode != 0


def test_p_id_trailing_newline_rejected(workspace):
    """Trailing newline in P-ID must be rejected by fullmatch."""
    project, skill = workspace
    data = valid_deep()
    data["selected_p_ids"] = ["P1\n"]
    inp = write_json(project / "pid-nl.json", data)

    result = run_ck("freeze", "--stage", "deep", "--run-id", "pid-newline",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0

def test_direct_seed_accepted(workspace):
    """DIRECT_SEED must be accepted as valid selected_p_ids entry."""
    project, skill = workspace
    data = valid_deep()
    data["selected_p_ids"] = ["DIRECT_SEED"]
    inp = write_json(project / "direct-seed.json", data)

    result = run_ck("freeze", "--stage", "deep", "--run-id", "direct-seed",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode == 0

def test_direct_seed_duplicate_rejected(workspace):
    """Duplicate DIRECT_SEED must be rejected."""
    project, skill = workspace
    data = valid_deep()
    data["selected_p_ids"] = ["DIRECT_SEED", "DIRECT_SEED"]
    inp = write_json(project / "dup-seed.json", data)

    result = run_ck("freeze", "--stage", "deep", "--run-id", "dup-seed",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0
    assert "duplicate" in result.stderr.lower()

# ── Refuse overwrite ─────────────────────────────────────────────────


def test_refuse_overwrite(workspace):
    project, skill = workspace
    inp = write_json(project / "cand.json", valid_explore())

    r1 = run_ck("freeze", "--stage", "explore", "--run-id", "no-overwrite",
                "--input", inp, "--project-root", str(project),
                "--skill-root", str(skill))
    assert r1.returncode == 0

    r2 = run_ck("freeze", "--stage", "explore", "--run-id", "no-overwrite",
                "--input", inp, "--project-root", str(project),
                "--skill-root", str(skill))
    assert r2.returncode != 0
    assert "exist" in r2.stderr.lower() or "overwrite" in r2.stderr.lower()
    # Original frozen files must survive the refusal
    run_dir = project / ".ai" / "pizm" / "run-no-overwrite"
    with open(inp, "rb") as f:
        original_bytes = f.read()
    original_sha = hashlib.sha256(original_bytes).hexdigest()
    assert (run_dir / "candidates.json").read_bytes() == original_bytes
    assert (run_dir / "candidates.sha256").read_text() == original_sha
    assert (run_dir / "candidates.meta.json").exists()


# ── Hidden contract ───────────────────────────────────────────────────


def test_contract_absent_on_failure(workspace):
    project, skill = workspace
    data = valid_explore()
    data["schema_version"] = "wrong"
    inp = write_json(project / "bad.json", data)

    result = run_ck("freeze", "--stage", "explore", "--run-id", "contract-fail",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0
    assert "NEXT CONTRACT" not in result.stdout
    assert "RUBRIC" not in result.stdout


def test_contract_present_after_success(workspace):
    project, skill = workspace
    inp = write_json(project / "cand.json", valid_explore())

    result = run_ck("freeze", "--stage", "explore", "--run-id", "contract-ok",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode == 0
    assert "FREEZE_OK" in result.stdout
    assert "NEXT CONTRACT" in result.stdout
    assert "EXPLORE SELECTOR RUBRIC" in result.stdout


def test_deep_contract_present(workspace):
    project, skill = workspace
    inp = write_json(project / "dev.json", valid_deep())

    result = run_ck("freeze", "--stage", "deep", "--run-id", "deep-contract",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode == 0
    assert "NEXT CONTRACT" in result.stdout
    assert "DEEP REVIEWER RUBRIC" in result.stdout


def test_contract_before_freeze_ok_ordering(workspace):
    project, skill = workspace
    inp = write_json(project / "cand.json", valid_explore())

    result = run_ck("freeze", "--stage", "explore", "--run-id", "order-test",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode == 0
    lines = result.stdout.split("\n")
    freeze_idx = next(i for i, l in enumerate(lines) if l.startswith("FREEZE_OK"))
    contract_idx = next(i for i, l in enumerate(lines) if "NEXT CONTRACT" in l)
    assert freeze_idx < contract_idx


def test_missing_contract_nonzero_and_cleanup(workspace):
    """Missing contract file → nonzero exit, no artifacts left behind, retry succeeds."""
    project, skill = workspace
    # Delete the explore contract
    contract_path = skill / "references" / "explore-selector.md"
    contract_path.unlink()

    inp = write_json(project / "cand.json", valid_explore())
    result = run_ck("freeze", "--stage", "explore", "--run-id", "no-contract",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0
    assert "contract" in result.stderr.lower()
    assert "references/" not in result.stderr
    assert "explore-selector" not in result.stderr
    run_dir = project / ".ai" / "pizm" / "run-no-contract"
    assert not (run_dir / "candidates.json").exists()
    assert not (run_dir / "candidates.sha256").exists()
    assert not (run_dir / "candidates.meta.json").exists()

    # Restore contract and retry with SAME run-id
    contract_path.write_text("# EXPLORE SELECTOR RUBRIC\nhidden rubric")
    retry = run_ck("freeze", "--stage", "explore", "--run-id", "no-contract",
                   "--input", inp, "--project-root", str(project),
                   "--skill-root", str(skill))
    assert retry.returncode == 0
    assert "FREEZE_OK" in retry.stdout
    assert (run_dir / "candidates.json").exists()
    assert (run_dir / "candidates.sha256").exists()
    assert (run_dir / "candidates.meta.json").exists()



def test_no_hidden_path_in_errors(workspace):
    """Error messages must not reveal hidden contract file paths."""
    project, skill = workspace
    (skill / "references" / "explore-selector.md").unlink()

    inp = write_json(project / "cand.json", valid_explore())
    result = run_ck("freeze", "--stage", "explore", "--run-id", "no-path-leak",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0
    assert "explore-selector" not in result.stderr
    assert "deep-reviewer" not in result.stderr
    assert "references/" not in result.stderr


# ── Corrupted read-back ───────────────────────────────────────────────


def test_corrupted_readback_simulated(workspace):
    """Simulate hash mismatch by patching the script."""
    project, skill = workspace
    raw = json.dumps(valid_explore()).encode("utf-8")
    inp = project / "cand.json"
    inp.write_bytes(raw)

    corrupt_script = project / "corrupt-checkpoint.py"
    original = Path(CHECKPOINT).read_text()
    corrupted = original.replace(
        "if _sha256_hex(readback) != computed_hash:",
        "if True:  # forced mismatch",
    )
    corrupt_script.write_text(corrupted)
    corrupt_script.chmod(0o755)

    result = subprocess.run(
        [sys.executable, str(corrupt_script),
         "freeze", "--stage", "explore", "--run-id", "corrupt-test",
         "--input", str(inp), "--project-root", str(project),
         "--skill-root", str(skill)],
        capture_output=True, text=True,
    )

    assert result.returncode != 0
    assert "hash mismatch" in result.stderr.lower()
    assert "NEXT CONTRACT" not in result.stdout
    # Cleanup: no artifacts remain
    run_dir = project / ".ai" / "pizm" / "run-corrupt-test"
    assert not (run_dir / "candidates.json").exists()
    assert not (run_dir / "candidates.sha256").exists()


def test_retry_after_simulated_corruption(workspace):
    """After a corrupted read-back failure, retrying with uncorrupted CLI succeeds."""
    project, skill = workspace
    raw = json.dumps(valid_explore()).encode("utf-8")
    inp = project / "cand.json"
    inp.write_bytes(raw)

    # First: corrupt attempt
    corrupt_script = project / "corrupt-checkpoint.py"
    original = Path(CHECKPOINT).read_text()
    corrupted = original.replace(
        "if _sha256_hex(readback) != computed_hash:",
        "if True:  # forced mismatch",
    )
    corrupt_script.write_text(corrupted)
    corrupt_script.chmod(0o755)

    r1 = subprocess.run(
        [sys.executable, str(corrupt_script),
         "freeze", "--stage", "explore", "--run-id", "retry-test",
         "--input", str(inp), "--project-root", str(project),
         "--skill-root", str(skill)],
        capture_output=True, text=True,
    )
    assert r1.returncode != 0

    # Second: normal retry with same run-id should succeed (cleanup was complete)
    r2 = run_ck("freeze", "--stage", "explore", "--run-id", "retry-test",
                "--input", str(inp), "--project-root", str(project),
                "--skill-root", str(skill))
    assert r2.returncode == 0
    assert "FREEZE_OK" in r2.stdout


# ── Stage-scoped coexistence ──────────────────────────────────────────


def test_explore_deep_same_run_dir(workspace):
    """Explore and deep can coexist in the same run-<id> directory."""
    project, skill = workspace

    # Freeze explore
    inp_e = write_json(project / "cand.json", valid_explore())
    r1 = run_ck("freeze", "--stage", "explore", "--run-id", "both-stages",
                "--input", inp_e, "--project-root", str(project),
                "--skill-root", str(skill))
    assert r1.returncode == 0

    # Freeze deep in same run dir
    inp_d = write_json(project / "dev.json", valid_deep())
    r2 = run_ck("freeze", "--stage", "deep", "--run-id", "both-stages",
                "--input", inp_d, "--project-root", str(project),
                "--skill-root", str(skill))
    assert r2.returncode == 0

    run_dir = project / ".ai" / "pizm" / "run-both-stages"
    assert (run_dir / "candidates.json").exists()
    assert (run_dir / "candidates.sha256").exists()
    assert (run_dir / "candidates.meta.json").exists()
    assert (run_dir / "development.json").exists()
    assert (run_dir / "development.sha256").exists()
    assert (run_dir / "development.meta.json").exists()


def test_explore_overwrite_refused_deep_ok_same_dir(workspace):
    """Refuse explore overwrite but deep in same dir still works."""
    project, skill = workspace

    inp = write_json(project / "cand.json", valid_explore())
    run_ck("freeze", "--stage", "explore", "--run-id", "mixed",
           "--input", inp, "--project-root", str(project),
           "--skill-root", str(skill))

    # Second explore in same dir → refused
    r2 = run_ck("freeze", "--stage", "explore", "--run-id", "mixed",
                "--input", inp, "--project-root", str(project),
                "--skill-root", str(skill))
    assert r2.returncode != 0
    # Original frozen files must survive the refusal
    run_dir = project / ".ai" / "pizm" / "run-mixed"
    with open(inp, "rb") as f:
        original_bytes = f.read()
    original_sha = hashlib.sha256(original_bytes).hexdigest()
    assert (run_dir / "candidates.json").read_bytes() == original_bytes
    assert (run_dir / "candidates.sha256").read_text() == original_sha
    assert (run_dir / "candidates.meta.json").exists()

    # Deep in same dir → succeeds
    inp_d = write_json(project / "dev.json", valid_deep())
    r3 = run_ck("freeze", "--stage", "deep", "--run-id", "mixed",
                "--input", inp_d, "--project-root", str(project),
                "--skill-root", str(skill))
    assert r3.returncode == 0


# ── Concurrent exclusive publish ─────────────────────────────────────


def test_concurrent_freeze_exclusive(workspace):
    """Two concurrent freezes of same stage+run-id: exactly one succeeds."""
    import concurrent.futures

    project, skill = workspace
    inp = write_json(project / "cand.json", valid_explore())

    def attempt():
        return run_ck("freeze", "--stage", "explore", "--run-id", "concurrent",
                      "--input", inp, "--project-root", str(project),
                      "--skill-root", str(skill))

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt) for _ in range(2)]
        results = [f.result() for f in futures]

    ok_count = sum(1 for r in results if r.returncode == 0)
    fail_count = sum(1 for r in results if r.returncode != 0)
    assert ok_count == 1, f"Expected exactly 1 success, got {ok_count}"
    assert fail_count == 1
    # The winning frozen triple must be intact and internally consistent
    run_dir = project / ".ai" / "pizm" / "run-concurrent"
    artifact = run_dir / "candidates.json"
    sha_file = run_dir / "candidates.sha256"
    meta_file = run_dir / "candidates.meta.json"
    assert artifact.exists()
    assert sha_file.exists()
    assert meta_file.exists()
    assert sha_file.read_text() == hashlib.sha256(artifact.read_bytes()).hexdigest()


# ── Hash verification round-trip ──────────────────────────────────────


def test_hash_verification_roundtrip(workspace):
    project, skill = workspace
    raw = json.dumps(valid_explore()).encode("utf-8")
    inp = project / "cand.json"
    inp.write_bytes(raw)

    run_ck("freeze", "--stage", "explore", "--run-id", "hash-rt",
           "--input", str(inp), "--project-root", str(project),
           "--skill-root", str(skill))

    run_dir = project / ".ai" / "pizm" / "run-hash-rt"
    artifact = (run_dir / "candidates.json").read_bytes()
    stored_hash = (run_dir / "candidates.sha256").read_text()
    assert stored_hash == hashlib.sha256(artifact).hexdigest()


# ── Missing input file ────────────────────────────────────────────────


def test_missing_input_file(workspace):
    project, skill = workspace

    result = run_ck("freeze", "--stage", "explore", "--run-id", "missing-input",
                    "--input", str(project / "nonexistent.json"),
                    "--project-root", str(project), "--skill-root", str(skill))

    assert result.returncode != 0


# ── Explore modes ────────────────────────────────────────────────────


@pytest.mark.parametrize("mode", ["NORMAL", "360", "RIFT"])
def test_explore_modes(workspace, mode):
    project, skill = workspace
    data = valid_explore()
    data["mode"] = mode
    inp = write_json(project / f"cand-{mode}.json", data)

    result = run_ck("freeze", "--stage", "explore", "--run-id", f"mode-{mode.lower()}",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode == 0


# ── Source-level guarantees ────────────────────────────────────────────


def test_no_provider_imports():
    source = Path(CHECKPOINT).read_text()
    forbidden = [
        "openai", "anthropic", "requests", "httpx", "aiohttp",
        "urllib.request", "urllib3", "http.client",
        "torch", "transformers", "huggingface",
    ]
    for term in forbidden:
        assert f"import {term}" not in source
        assert f"from {term}" not in source


def test_stdlib_only():
    source = Path(CHECKPOINT).read_text()
    import re as re_mod
    imports = re_mod.findall(r"^(?:import|from)\s+(\S+)", source, re_mod.MULTILINE)
    stdlib = {
        "argparse", "hashlib", "json", "os", "re", "sys", "tempfile",
        "datetime", "pathlib",
    }
    for imp in imports:
        top = imp.split(".")[0]
        assert top in stdlib, f"Non-stdlib import: {imp}"


def test_no_selection_logic():
    source = Path(CHECKPOINT).read_text()
    for term in ["select_best", "score", "rank", "choose_winner"]:
        assert f"def {term}" not in source.lower()


# ── Symlink and unrelated-cwd behavioral tests ───────────────────────


def test_symlink_resolves_to_canonical_script():
    """Stable entrypoint ~/.local/bin/pizm-checkpoint resolves to repo script."""
    import os
    symlink = Path.home() / ".local" / "bin" / "pizm-checkpoint"
    assert symlink.is_symlink(), "~/.local/bin/pizm-checkpoint must be a symlink"
    target = symlink.resolve()
    canonical = REPO_ROOT / "bin" / "pizm-checkpoint"
    assert target == canonical, (
        f"Symlink target {target} != canonical {canonical}"
    )
    # Symlink must point to an executable Python script
    assert target.exists(), "Symlink target does not exist"


def test_checkpoint_from_unrelated_cwd(tmp_path):
    """Invoke checkpoint from an unrelated temporary cwd, no repo assumptions.

    Proves artifact/hash/contract success from an arbitrary working directory.
    Does NOT mutate the real symlink.
    """
    # Set up an isolated project and skill tree under tmp_path
    unrelated_cwd = tmp_path / "unrelated-workspace"
    unrelated_cwd.mkdir()
    project = tmp_path / "some-project"
    project.mkdir()
    skill = tmp_path / "skill-copy"
    skill.mkdir()
    skill_refs = skill / "references"
    skill_refs.mkdir()
    # Write a minimal contract stub (hidden selector)
    (skill_refs / "explore-selector.md").write_text(
        "# Explore Selector Stub\nEVALUATE.\n", encoding="utf-8"
    )

    # Write a valid explore artifact
    artifact = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {"candidate_id": "c1", "title": "Seed", "content": "Test."}
        ],
    }
    input_path = unrelated_cwd / "pending.json"
    input_path.write_text(json.dumps(artifact), encoding="utf-8")

    # Resolve the stable symlink entrypoint
    import os
    symlink = Path.home() / ".local" / "bin" / "pizm-checkpoint"
    assert symlink.is_symlink()
    entrypoint = str(symlink)

    # Invoke from the unrelated cwd
    result = subprocess.run(
        [
            sys.executable, entrypoint, "freeze",
            "--stage", "explore",
            "--run-id", "unrelated-cwd-test",
            "--input", str(input_path),
            "--project-root", str(project),
            "--skill-root", str(skill),
        ],
        cwd=str(unrelated_cwd),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
    assert "FREEZE_OK" in result.stdout

    # Verify artifacts landed under the specified project root (not cwd)
    run_dir = project / ".ai" / "pizm" / "run-unrelated-cwd-test"
    assert run_dir.exists()
    candidates = run_dir / "candidates.json"
    sidecar = run_dir / "candidates.sha256"
    meta = run_dir / "candidates.meta.json"
    assert candidates.exists()
    assert sidecar.exists()
    assert meta.exists()

    # Verify hash integrity
    expected_hash = hashlib.sha256(candidates.read_bytes()).hexdigest()
    assert sidecar.read_text() == expected_hash

    # Verify contract was revealed
    assert "NEXT CONTRACT" in result.stdout
    assert "Explore Selector Stub" in result.stdout

    # Verify nothing landed in the unrelated cwd
    assert not (unrelated_cwd / ".ai").exists()

# ── Payload Safety Bounds (R1) ──────────────────────────────────────────


def test_candidate_count_up_to_20_accepted(workspace):
    """Candidate pool of up to 20 candidates must be accepted."""
    project, skill = workspace
    data = valid_explore()
    data["candidates"] = [
        {"candidate_id": f"c{i}", "title": f"Idea {i}", "content": f"description {i}"}
        for i in range(1, 21)
    ]
    inp = write_json(project / "cand20.json", data)

    result = run_ck(
        "freeze", "--stage", "explore", "--run-id", "pool-20-test",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )

    assert result.returncode == 0, result.stderr
    assert "FREEZE_OK" in result.stdout
    assert "NEXT CONTRACT" in result.stdout


def test_candidate_count_21_rejected_payload_too_large(workspace):
    """Candidate pool of 21 must be rejected with PAYLOAD_TOO_LARGE and fail closed."""
    project, skill = workspace
    data = valid_explore()
    data["candidates"] = [
        {"candidate_id": f"c{i}", "title": f"Idea {i}", "content": f"description {i}"}
        for i in range(1, 22)
    ]
    inp = write_json(project / "cand21.json", data)

    result = run_ck(
        "freeze", "--stage", "explore", "--run-id", "pool-21-test",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )

    assert result.returncode != 0
    assert "PAYLOAD_TOO_LARGE" in result.stderr
    assert "candidate count" in result.stderr
    # Fail-closed: contract NOT printed, stage artifacts NOT written
    assert "NEXT CONTRACT" not in result.stdout
    assert "EXPLORE SELECTOR RUBRIC" not in result.stdout
    assert not (project / ".ai" / "pizm" / "run-pool-21-test" / "candidates.json").exists()


def test_single_candidate_oversized_rejected(workspace):
    """Single candidate exceeding 12 KiB (12288 bytes) must be rejected with PAYLOAD_TOO_LARGE."""
    project, skill = workspace
    data = valid_explore()
    # Create candidate with > 12 KiB serialized size
    big_content = "x" * 13000
    data["candidates"] = [
        {"candidate_id": "c1", "title": "Normal"},
        {"candidate_id": "c2", "title": "Huge", "content": big_content},
    ]
    inp = write_json(project / "cand-oversized-item.json", data)

    result = run_ck(
        "freeze", "--stage", "explore", "--run-id", "single-oversized-test",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )

    assert result.returncode != 0
    assert "PAYLOAD_TOO_LARGE" in result.stderr
    assert "12288" in result.stderr or "12 KiB" in result.stderr or "serialized size" in result.stderr
    # Fail-closed: contract NOT printed, stage artifacts NOT written
    assert "NEXT CONTRACT" not in result.stdout
    assert "EXPLORE SELECTOR RUBRIC" not in result.stdout
    assert not (project / ".ai" / "pizm" / "run-single-oversized-test" / "candidates.json").exists()


def test_total_artifact_oversized_rejected(workspace):
    """Total candidates artifact exceeding 192 KiB (196608 bytes) must be rejected with PAYLOAD_TOO_LARGE."""
    project, skill = workspace
    data = valid_explore()
    # 20 candidates, each ~10 KiB (under 12 KiB individually, but 20 * 10 = ~200 KiB > 192 KiB)
    data["candidates"] = [
        {"candidate_id": f"c{i}", "title": f"Idea {i}", "content": "y" * 10000}
        for i in range(1, 21)
    ]
    inp = write_json(project / "cand-oversized-total.json", data)

    result = run_ck(
        "freeze", "--stage", "explore", "--run-id", "total-oversized-test",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )

    assert result.returncode != 0
    assert "PAYLOAD_TOO_LARGE" in result.stderr
    assert "196608" in result.stderr or "192 KiB" in result.stderr
    # Fail-closed: contract NOT printed, stage artifacts NOT written
    assert "NEXT CONTRACT" not in result.stdout
    assert "EXPLORE SELECTOR RUBRIC" not in result.stdout
    assert not (project / ".ai" / "pizm" / "run-total-oversized-test" / "candidates.json").exists()


# ── Lever Stages & Terminal State (R2) ──────────────────────────────────


def valid_lever_design_data():
    return {
        "schema_version": "pizm-lever-design-v1",
        "stage": "lever",
        "levers": [
            {
                "lever_id": "L1",
                "intervention_or_test_point": "Rate-limit threshold",
                "model_link": "Backpressure mechanism",
                "minimum_bounded_move": "Adjust limit to 100 req/s",
                "expected_observation_or_response": "Latency drop",
                "disconfirming_signal": "Error rate spike",
                "stop_condition": "5xx > 1%",
                "remaining_assumptions": "Workers healthy",
            }
        ],
    }


def test_lever_design_freeze_success(workspace):
    project, skill = workspace
    (skill / "references" / "lever-reviewer.md").write_text("# LEVER REVIEWER RUBRIC")
    inp = write_json(project / "lever_design.json", valid_lever_design_data())

    result = run_ck(
        "freeze", "--stage", "lever-design", "--run-id", "lever-design-1",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )

    assert result.returncode == 0, result.stderr
    assert "FREEZE_OK" in result.stdout
    assert "references/lever-reviewer.md" in result.stdout
    run_dir = project / ".ai" / "pizm" / "run-lever-design-1"
    assert (run_dir / "design.json").exists()
    assert (run_dir / "design.sha256").exists()
    assert (run_dir / "design.meta.json").exists()


def test_lever_review_freeze_success(workspace):
    project, skill = workspace
    review_data = {
        "schema_version": "pizm-lever-review-v1",
        "stage": "lever",
        "frozen_hash": "a" * 64,
        "outcome": "LEVER",
        "verdicts": [{"lever_id": "L1", "verdict": "ACCEPT", "reason": "Good fit"}],
    }
    inp = write_json(project / "lever_review.json", review_data)

    result = run_ck(
        "freeze", "--stage", "lever-review", "--run-id", "lever-review-1",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )

    assert result.returncode == 0, result.stderr
    assert "FREEZE_OK" in result.stdout
    # lever-review has no next contract
    assert "NEXT CONTRACT" not in result.stdout
    run_dir = project / ".ai" / "pizm" / "run-lever-review-1"
    assert (run_dir / "review.json").exists()
    assert (run_dir / "review.sha256").exists()
    assert (run_dir / "review.meta.json").exists()


def test_lever_design_invalid_count(workspace):
    project, skill = workspace
    data = valid_lever_design_data()
    data["levers"] = []
    inp = write_json(project / "empty_levers.json", data)

    result = run_ck(
        "freeze", "--stage", "lever-design", "--run-id", "bad-count-0",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "levers" in result.stderr


def test_lever_design_duplicate_id(workspace):
    project, skill = workspace
    data = valid_lever_design_data()
    lever_copy = dict(data["levers"][0])
    data["levers"].append(lever_copy)
    inp = write_json(project / "dup_levers.json", data)

    result = run_ck(
        "freeze", "--stage", "lever-design", "--run-id", "dup-lever-id",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "duplicate" in result.stderr
