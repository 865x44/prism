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
    (refs / "explore.md").write_text("# EXPLORE GENERATOR CONTRACT\n")
    (refs / "lever-reviewer.md").write_text("# LEVER REVIEWER RUBRIC\nhidden rubric")
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


# ── Search-field & portfolio stages (C1) ──────────────────────────────


def valid_search_field():
    return {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "passes": [
            {
                "pass_id": "pass01",
                "candidates_ref": "run-alpha/candidates.json",
                "frozen_hash": "a" * 64,
            }
        ],
        "entries": ["pass01:c01", "pass01:c02"],
    }


def valid_portfolio():
    return {
        "schema_version": "pizm-portfolio-selection-v1",
        "stage": "portfolio",
        "route": "MANUAL",
        "field_hash": "b" * 64,
        "candidate_assessments": [
            {
                "candidate_ref": "pass01:c01",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "only candidate carrying the delay mechanism",
                "nearest_overlap": None,
                "reason": "distinct mechanism, well grounded",
            },
            {
                "candidate_ref": "pass01:c02",
                "disposition": "DROP",
                "standalone_quality": "weak",
                "unique_residue": "",
                "nearest_overlap": "pass01:c01",
                "reason": "paraphrase of pass01:c01",
            },
        ],
        "bundles": [],
        "auto_target": None,
    }


def bundle(**overrides):
    b = {
        "bundle_id": "B1",
        "member_refs": ["pass01:c02", "pass01:c08"],
        "bundle_thesis": "delay and threshold jointly explain collapse timing",
        "composition_gain": "predicts collapse onset that neither member predicts alone",
        "member_roles": {},
        "member_ablation": {
            "pass01:c02": "without the delay mechanism the timing prediction vanishes",
            "pass01:c08": "without the threshold the collapse direction is unexplained",
        },
        "internal_tension": "delay pushes later, threshold pulls earlier",
        "weakest_link": "threshold calibration",
        "new_consequence_or_prediction": "collapse occurs within one delay cycle of threshold crossing",
    }
    b.update(overrides)
    return b


def _load_checkpoint_module():
    import importlib.util
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader("pizm_checkpoint_under_test", CHECKPOINT)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_search_field_freeze_success(workspace):
    project, skill = workspace
    inp = write_json(project / "field.json", valid_search_field())
    result = run_ck(
        "freeze", "--stage", "search-field", "--run-id", "field-run-1",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode == 0, result.stderr
    assert "FREEZE_OK" in result.stdout
    run_dir = project / ".ai" / "pizm" / "run-field-run-1"
    assert (run_dir / "search-field.json").exists()
    assert (run_dir / "search-field.sha256").exists()
    assert (run_dir / "search-field.meta.json").exists()
    meta = json.loads((run_dir / "search-field.meta.json").read_text())
    assert meta["schema_version"] == "pizm-search-field-v1"
    assert meta["stage"] == "search-field"
    # Contract map: search-field reveals the explore reference after freeze.
    assert "# EXPLORE GENERATOR CONTRACT" in result.stdout


def test_search_field_payload_too_large(workspace):
    project, skill = workspace
    data = valid_search_field()
    data["passes"][0]["candidates_ref"] = "x" * 40000
    inp = write_json(project / "big_field.json", data)
    result = run_ck(
        "freeze", "--stage", "search-field", "--run-id", "field-too-big",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "PAYLOAD_TOO_LARGE" in result.stderr
    assert "32768" in result.stderr
    assert not (project / ".ai" / "pizm" / "run-field-too-big" / "search-field.json").exists()


def test_search_field_append_only_ordering_enforced(workspace):
    project, skill = workspace
    data = valid_search_field()
    data["passes"].append({
        "pass_id": "pass02", "candidates_ref": "run-beta/candidates.json", "frozen_hash": "c" * 64,
    })
    data["entries"] = ["pass02:c01", "pass01:c03"]
    inp = write_json(project / "field_bad_order.json", data)
    result = run_ck(
        "freeze", "--stage", "search-field", "--run-id", "field-bad-order",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "append-only" in result.stderr


def test_search_field_unregistered_pass_rejected(workspace):
    project, skill = workspace
    data = valid_search_field()
    data["entries"].append("pass07:c01")
    inp = write_json(project / "field_unknown_pass.json", data)
    result = run_ck(
        "freeze", "--stage", "search-field", "--run-id", "field-unknown-pass",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "unregistered pass" in result.stderr


def test_two_passes_reuse_local_c_ids_without_collision(workspace):
    """Same local id c01 under two passes yields distinct composite refs."""
    project, skill = workspace
    data = valid_search_field()
    data["passes"].append({
        "pass_id": "pass02", "candidates_ref": "run-beta/candidates.json", "frozen_hash": "d" * 64,
    })
    data["entries"] = ["pass01:c01", "pass02:c01"]
    inp = write_json(project / "field_reuse.json", data)
    result = run_ck(
        "freeze", "--stage", "search-field", "--run-id", "field-reuse",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode == 0, result.stderr


def test_portfolio_manual_freeze_success(workspace):
    project, skill = workspace
    inp = write_json(project / "portfolio.json", valid_portfolio())
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "pfolio-run-1",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode == 0, result.stderr
    assert "FREEZE_OK" in result.stdout
    run_dir = project / ".ai" / "pizm" / "run-pfolio-run-1"
    assert (run_dir / "portfolio.json").exists()
    assert (run_dir / "portfolio.sha256").exists()
    assert (run_dir / "portfolio.meta.json").exists()
    meta = json.loads((run_dir / "portfolio.meta.json").read_text())
    assert meta["schema_version"] == "pizm-portfolio-selection-v1"
    # Contract map: portfolio reveals the selector reference after freeze.
    assert "EXPLORE SELECTOR RUBRIC" in result.stdout


@pytest.mark.parametrize(
    "target,valid",
    [
        ({"target_type": "P", "target_id": "P3"}, True),
        ({"target_type": "B", "target_id": "B1"}, True),
        ({"target_type": "B", "target_id": "B9"}, False),  # not a proposed bundle
        ({"target_type": "X", "target_id": "P1"}, False),
    ],
)
def test_portfolio_auto_targets(workspace, target, valid):
    project, skill = workspace
    data = valid_portfolio()
    data["route"] = "AUTO"
    data["bundles"] = [bundle()]
    data["auto_target"] = target
    inp = write_json(project / "portfolio_auto.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", f"auto-{abs(hash(json.dumps(target)))}",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert (result.returncode == 0) == valid


def test_portfolio_auto_without_target_rejected(workspace):
    project, skill = workspace
    data = valid_portfolio()
    data["route"] = "AUTO"
    del data["auto_target"]
    inp = write_json(project / "portfolio_auto_missing.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "auto-missing-target",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "exactly one auto_target" in result.stderr


def test_portfolio_manual_with_target_rejected(workspace):
    project, skill = workspace
    data = valid_portfolio()
    data["auto_target"] = {"target_type": "P", "target_id": "P1"}
    inp = write_json(project / "portfolio_manual_target.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "manual-with-target",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "null" in result.stderr


def test_portfolio_payload_too_large(workspace):
    project, skill = workspace
    data = valid_portfolio()
    data["field_hash"] = "e" * 170000
    inp = write_json(project / "portfolio_big.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "pfolio-too-big",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "PAYLOAD_TOO_LARGE" in result.stderr
    assert "163840" in result.stderr
    assert not (project / ".ai" / "pizm" / "run-pfolio-too-big" / "portfolio.json").exists()


def test_bundle_passenger_fails_ablation(workspace):
    """member_ablation missing an entry for one member must be rejected."""
    project, skill = workspace
    data = valid_portfolio()
    incomplete = bundle()
    del incomplete["member_ablation"]["pass01:c08"]
    data["bundles"] = [incomplete]
    inp = write_json(project / "portfolio_passenger.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "passenger-bundle",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "member_ablation" in result.stderr


def test_bundle_single_member_rejected(workspace):
    project, skill = workspace
    data = valid_portfolio()
    data["bundles"] = [bundle(member_refs=["pass01:c02"])]
    inp = write_json(project / "portfolio_solo_bundle.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "solo-bundle",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "at least 2" in result.stderr


def test_duplicate_bundle_id_rejected(workspace):
    project, skill = workspace
    data = valid_portfolio()
    data["bundles"] = [bundle(), bundle(bundle_id="B1", member_refs=["pass02:c01", "pass02:c02"])]
    inp = write_json(project / "portfolio_dup_bid.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "dup-bid",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "duplicate bundle_id" in result.stderr


def test_prior_bundles_renumbering_rejected(workspace):
    """Proposed ids diverging from the deterministic assignment fail closed."""
    project, skill = workspace
    data = valid_portfolio()
    renamed = bundle(bundle_id="B7")
    data["bundles"] = [renamed]
    data["prior_bundles"] = [{"bundle_id": "B1", "member_refs": ["pass01:c02", "pass01:c08"]}]
    inp = write_json(project / "portfolio_renum.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "renumber-attempt",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "deterministic B-ID assignment violated" in result.stderr


def test_prior_bundles_reuse_preserves_id(workspace):
    project, skill = workspace
    data = valid_portfolio()
    fresh = bundle(
        bundle_id="B2",
        member_refs=["pass02:c01", "pass02:c02"],
        member_ablation={
            "pass02:c01": "without this member the cost-shift view vanishes",
            "pass02:c02": "without this member the incentive view vanishes",
        },
    )
    reused = bundle()  # same membership as prior B1 -> keeps B1
    data["bundles"] = [reused, fresh]
    data["prior_bundles"] = [{"bundle_id": "B1", "member_refs": ["pass01:c08", "pass01:c02"]}]
    inp = write_json(project / "portfolio_reuse.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "reuse-prior",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode == 0, result.stderr


# ── Deterministic B-ID helper (pure function) ───────────────────────────


def test_assign_bundle_ids_fresh_monotonic():
    module = _load_checkpoint_module()
    props = [
        {"member_refs": ["pass01:c02", "pass01:c08"]},
        {"member_refs": ["pass02:c01", "pass02:c02"]},
    ]
    assert module._assign_bundle_ids([], props) == ["B1", "B2"]


def test_assign_bundle_ids_reuse_preserves_and_continues_monotonic():
    module = _load_checkpoint_module()
    prior = [
        {"bundle_id": "B1", "member_refs": ["pass01:c08", "pass01:c02"]},
        {"bundle_id": "B4", "member_refs": ["pass00:c01", "pass00:c02"]},
    ]
    props = [
        {"member_refs": ["pass01:c02", "pass01:c08"]},   # reuse B1
        {"member_refs": ["pass09:c01", "pass09:c02"]},   # fresh above max(1,4)
    ]
    assert module._assign_bundle_ids(prior, props) == ["B1", "B5"]


def test_assign_bundle_ids_deterministic_across_reruns():
    module = _load_checkpoint_module()
    prior = [{"bundle_id": "B2", "member_refs": ["pass01:c01", "pass01:c03"]}]
    props = [
        {"member_refs": ["pass01:c05", "pass01:c06"]},
        {"member_refs": ["pass01:c01", "pass01:c03"]},
        {"member_refs": ["pass03:c02", "pass04:c09"]},
    ]
    first = module._assign_bundle_ids(prior, props)
    second = module._assign_bundle_ids(prior, props)
    assert first == second
    # Fresh ids are monotonic above every known id (prior max B2); the
    # reused membership keeps B2; reruns are byte-identical (no renumbering).
    assert first == ["B3", "B2", "B4"]


def test_assign_bundle_ids_ambiguous_prior_state_fails_closed():
    module = _load_checkpoint_module()
    prior = [
        {"bundle_id": "B1", "member_refs": ["pass01:c01", "pass01:c02"]},
        {"bundle_id": "B2", "member_refs": ["pass01:c02", "pass01:c01"]},
    ]
    with pytest.raises(ValueError, match="ambiguous prior state"):
        module._assign_bundle_ids(prior, [{"member_refs": ["pass05:c01", "pass05:c02"]}])


def test_old_stage_validations_still_pass(workspace):
    """Existing schemas stay valid after C1 additions."""
    project, skill = workspace
    for stage, payload, run in (
        ("explore", valid_explore(), "old-explore"),
        ("deep", valid_deep(), "old-deep"),
        ("lever-design", valid_lever_design_data(), "old-lever"),
    ):
        inp = write_json(project / f"{run}.json", payload)
        result = run_ck(
            "freeze", "--stage", stage, "--run-id", run,
            "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
        )
        assert result.returncode == 0, f"{stage} regressed: {result.stderr}"


# ── Development-v2 & deep-review-v2 stages (C2) ──────────────────────────


def valid_dev_v2(target_type="P", target_id="P7"):
    lock = {
        "title": "T", "core_claim": "C", "structural_shift": "S",
        "mechanism": "M", "boundary": "B",
    }
    if target_type == "P":
        lock["p_id"] = target_id
    else:
        lock["bundle_id"] = target_id
        lock["member_refs"] = ["pass01:c01", "pass01:c02"]
    model = {
        "thesis": "developed thesis",
        "synthesis": "analytical prose synthesis of the developed model",
        "dynamics": "model behavior under pressure",
        "mechanism_chain": ["step 1", "step 2", "step 3"],
        "implications": ["i1"],
        "predictions_or_observables": ["o1"],
        "break_conditions": ["b1"],
        "unresolved_tensions": [],
        "evidence_debt": [],
        "load_bearing_claims": [
            {
                "claim": "claim one",
                "role_in_model": "core",
                "epistemic_status": "SUPPORTED",
                "what_would_weaken_or_refute": "observation x",
            },
            {
                "claim": "claim two",
                "role_in_model": "durability",
                "epistemic_status": "SPECULATIVE",
                "what_would_weaken_or_refute": "observation y",
            },
        ],
    }
    if target_type == "B":
        model["member_contributions"] = {
            "pass01:c01": "contributes A",
            "pass01:c02": "contributes B",
        }
        model["member_ablation"] = {
            "pass01:c01": "A disappears",
            "pass01:c02": "B disappears",
        }
        model["unresolved_tensions"] = ["composition tension"]
    return {
        "schema_version": "pizm-development-v2",
        "stage": "development-v2",
        "target": {"target_type": target_type, "target_id": target_id},
        "identity_lock": lock,
        "developed_model": model,
    }


def freeze_dev_v2(workspace, payload, run_id):
    project, skill = workspace
    inp = write_json(project / f"{run_id}.json", payload)
    return run_ck(
        "freeze", "--stage", "development-v2", "--run-id", run_id,
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )


def test_development_v2_freeze_success_p(workspace):
    project, skill = workspace
    result = freeze_dev_v2(workspace, valid_dev_v2("P", "P7"), "dev2-p")
    assert result.returncode == 0, result.stderr
    assert "FREEZE_OK" in result.stdout
    # Reveal semantics: development-v2 freeze reveals the hidden critic contract
    assert "DEEP REVIEWER RUBRIC" in result.stdout
    run_dir = project / ".ai" / "pizm" / "run-dev2-p"
    assert (run_dir / "development-v2.json").exists()
    assert (run_dir / "development-v2.sha256").exists()
    assert (run_dir / "development-v2.meta.json").exists()


def test_development_v2_freeze_success_b(workspace):
    result = freeze_dev_v2(workspace, valid_dev_v2("B", "B1"), "dev2-b")
    assert result.returncode == 0, result.stderr


def test_development_v2_bundle_identity_lock_preserves_member_ids(workspace):
    """bundle_id and member_refs are frozen into the identity lock; drift fails closed."""
    mismatched = valid_dev_v2("B", "B1")
    mismatched["identity_lock"]["bundle_id"] = "B2"
    result = freeze_dev_v2(workspace, mismatched, "dev2-b-id-drift")
    assert result.returncode != 0
    assert "identity drift fails closed" in result.stderr

    bad_refs = valid_dev_v2("B", "B1")
    bad_refs["identity_lock"]["member_refs"] = ["pass01:c01"]
    result = freeze_dev_v2(workspace, bad_refs, "dev2-b-single-member")
    assert result.returncode != 0
    assert "member_refs" in result.stderr

    bad_format = valid_dev_v2("B", "B1")
    bad_format["identity_lock"]["member_refs"] = ["P1", "P2"]
    result = freeze_dev_v2(workspace, bad_format, "dev2-b-bad-ref-format")
    assert result.returncode != 0
    assert "composite ref" in result.stderr

    missing_contribution = valid_dev_v2("B", "B1")
    del missing_contribution["developed_model"]["member_contributions"]["pass01:c02"]
    result = freeze_dev_v2(workspace, missing_contribution, "dev2-b-missing-contrib")
    assert result.returncode != 0
    assert "member_contributions" in result.stderr

    missing_ablation = valid_dev_v2("B", "B1")
    missing_ablation["developed_model"]["member_ablation"]["pass01:c01"] = ""
    result = freeze_dev_v2(workspace, missing_ablation, "dev2-b-empty-ablation")
    assert result.returncode != 0
    assert "member_ablation" in result.stderr


def test_development_v2_p_rejects_member_only_fields(workspace):
    payload = valid_dev_v2("P", "P7")
    payload["developed_model"]["member_contributions"] = {"pass01:c01": "x"}
    result = freeze_dev_v2(workspace, payload, "dev2-p-member-fields")
    assert result.returncode != 0
    assert "Bundle targets" in result.stderr


@pytest.mark.parametrize(
    "status", ["SUPPORTED", "INFERRED", "SPECULATIVE", "UNKNOWN"]
)
def test_development_v2_census_enum_accepted(workspace, status):
    payload = valid_dev_v2()
    payload["developed_model"]["load_bearing_claims"][0]["epistemic_status"] = status
    result = freeze_dev_v2(workspace, payload, f"census-{status.lower()}")
    assert result.returncode == 0, result.stderr


def test_development_v2_census_enum_invalid_rejected(workspace):
    payload = valid_dev_v2()
    payload["developed_model"]["load_bearing_claims"][0]["epistemic_status"] = "PROBABLY_TRUE"
    result = freeze_dev_v2(workspace, payload, "census-bad-enum")
    assert result.returncode != 0
    assert "epistemic_status" in result.stderr


def test_development_v2_synthesis_must_be_prose_string(workspace):
    """Synthesis is first-class prose; a card list fails closed."""
    payload = valid_dev_v2()
    payload["developed_model"]["synthesis"] = ["card one", "card two"]
    result = freeze_dev_v2(workspace, payload, "synthesis-list")
    assert result.returncode != 0
    assert "synthesis" in result.stderr


@pytest.mark.parametrize("chain", [["a"], ["a", "b"], [f"step {i}" for i in range(7)]])
def test_development_v2_mechanism_chain_bounds(workspace, chain):
    payload = valid_dev_v2()
    payload["developed_model"]["mechanism_chain"] = chain
    result = freeze_dev_v2(workspace, payload, "chain-bounds")
    assert result.returncode != 0
    assert "3..6" in result.stderr


def test_development_v2_census_size_bounds(workspace):
    too_few = valid_dev_v2()
    too_few["developed_model"]["load_bearing_claims"] = too_few[
        "developed_model"
    ]["load_bearing_claims"][:1]
    result = freeze_dev_v2(workspace, too_few, "census-too-few")
    assert result.returncode != 0
    assert "load_bearing_claims" in result.stderr
