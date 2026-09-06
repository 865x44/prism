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
CHECKPOINT_SYMLINK = Path.home() / ".local" / "bin" / "pizm-checkpoint"
SYMLINK_PRESENT = CHECKPOINT_SYMLINK.is_symlink()


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
    (refs / "deep-compare.md").write_text("# DEEP COMPARE RUBRIC\nhidden rubric")
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
    # Explore stage does not auto-reveal selector; manual search halts cleanly
    assert "NEXT CONTRACT" not in result.stdout

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
    inp = write_json(project / "dev.json", valid_deep())

    result = run_ck("freeze", "--stage", "deep", "--run-id", "order-test",
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
    # Delete the deep reviewer contract
    contract_path = skill / "references" / "deep-reviewer.md"
    contract_path.unlink()

    inp = write_json(project / "dev.json", valid_deep())
    result = run_ck("freeze", "--stage", "deep", "--run-id", "no-contract",
                    "--input", inp, "--project-root", str(project),
                    "--skill-root", str(skill))

    assert result.returncode != 0
    assert "contract" in result.stderr.lower()
    assert "references/" not in result.stderr
    assert "deep-reviewer" not in result.stderr
    run_dir = project / ".ai" / "pizm" / "run-no-contract"
    assert not (run_dir / "development.json").exists()
    assert not (run_dir / "development.sha256").exists()
    assert not (run_dir / "development.meta.json").exists()

    # Restore contract and retry with SAME run-id
    contract_path.write_text("# DEEP REVIEWER RUBRIC\nhidden rubric")
    retry = run_ck("freeze", "--stage", "deep", "--run-id", "no-contract",
                   "--input", inp, "--project-root", str(project),
                   "--skill-root", str(skill))
    assert retry.returncode == 0
    assert "FREEZE_OK" in retry.stdout
    assert (run_dir / "development.json").exists()
    assert (run_dir / "development.sha256").exists()
    assert (run_dir / "development.meta.json").exists()

def test_no_hidden_path_in_errors(workspace):
    """Error messages must not reveal hidden contract file paths."""
    project, skill = workspace
    (skill / "references" / "deep-reviewer.md").unlink()

    inp = write_json(project / "dev.json", valid_deep())
    result = run_ck("freeze", "--stage", "deep", "--run-id", "no-path-leak",
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


@pytest.mark.skipif(not SYMLINK_PRESENT, reason="developer-machine symlink ~/.local/bin/pizm-checkpoint not installed")
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


@pytest.mark.skipif(not SYMLINK_PRESENT, reason="developer-machine symlink ~/.local/bin/pizm-checkpoint not installed")
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

    # Verify explore does not auto-reveal selector
    assert "NEXT CONTRACT" not in result.stdout
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
    assert "NEXT CONTRACT" not in result.stdout

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
        "frozen_hash": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
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
                "candidates_ref": "candidates.json",
                "frozen_hash": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
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
        "perspectives": {"P1": "pass01:c01"},
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
        "next_reasoning_move": None,
        "next_reasoning_rationale": None,
        "auto_target": None,
        "information_request": None,
        "rival_shadow": None,
    }

def valid_portfolio_v2(left_id="B1", right_id="B2"):
    return {
        "schema_version": "pizm-portfolio-selection-v2",
        "stage": "portfolio",
        "route": "BONK",
        "field_hash": "b" * 64,
        "perspectives": {"P1": "pass01:c01", "P2": "pass01:c02"},
        "competition_status": "TWO_DEFENSIBLE_BUNDLES",
        "recommended_competition": {
            "left_bundle_id": left_id,
            "right_bundle_id": right_id,
            "competition_axis": f"Axis {left_id} vs {right_id}",
            "discriminating_observation": "Observation",
        },
        "candidate_assessments": [
            {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "r1", "nearest_overlap": None, "reason": "good"},
            {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "r2", "nearest_overlap": None, "reason": "good"},
        ],
        "bundles": [
            {"bundle_id": left_id, "member_refs": ["pass01:c01", "pass01:c02"], "bundle_thesis": "t1", "composition_gain": "g1", "member_roles": {}, "member_ablation": {"pass01:c01": "a", "pass01:c02": "b"}, "internal_tension": "ten", "weakest_link": "w", "new_consequence_or_prediction": "p"},
            {"bundle_id": right_id, "member_refs": ["pass01:c01", "pass01:c02"], "bundle_thesis": "t2", "composition_gain": "g2", "member_roles": {}, "member_ablation": {"pass01:c01": "a", "pass01:c02": "b"}, "internal_tension": "ten", "weakest_link": "w", "new_consequence_or_prediction": "p"},
        ],
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


def test_real_two_pass_cli_chain(workspace):
    """Real two-pass CLI chain creating pass01, pass02, and both search field snapshots solely via CLI freeze."""
    project, skill = workspace
    run_id = "real-two-pass"

    # 1. Pass 01 explore freeze (unfrozen payload input only)
    p1 = valid_explore()
    inp_p1 = write_json(project / "input_p1.json", p1)
    res_p1 = run_ck(
        "freeze", "--stage", "explore", "--run-id", run_id,
        "--artifact-suffix", "pass01",
        "--input", inp_p1, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert res_p1.returncode == 0, res_p1.stderr
    assert "FREEZE_OK" in res_p1.stdout
    sha_p1 = res_p1.stdout.split()[1]

    # 2. Pass 01 search-field freeze
    sf1 = {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "passes": [
            {
                "pass_id": "pass01",
                "candidates_ref": "candidates-pass01.json",
                "frozen_hash": sha_p1,
            }
        ],
        "entries": ["pass01:c01", "pass01:c02"],
    }
    inp_sf1 = write_json(project / "input_sf1.json", sf1)
    res_sf1 = run_ck(
        "freeze", "--stage", "search-field", "--run-id", run_id,
        "--artifact-suffix", "pass01",
        "--input", inp_sf1, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert res_sf1.returncode == 0, res_sf1.stderr
    assert "FREEZE_OK" in res_sf1.stdout
    sha_sf1 = res_sf1.stdout.split()[1]

    # 3. Pass 02 explore freeze
    p2 = valid_explore()
    inp_p2 = write_json(project / "input_p2.json", p2)
    res_p2 = run_ck(
        "freeze", "--stage", "explore", "--run-id", run_id,
        "--artifact-suffix", "pass02",
        "--input", inp_p2, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert res_p2.returncode == 0, res_p2.stderr
    assert "FREEZE_OK" in res_p2.stdout
    sha_p2 = res_p2.stdout.split()[1]

    # 4. Pass 02 search-field freeze (retains pass01 prefix, names search-field-pass01.json as predecessor)
    sf2 = {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "prior_ref": "search-field-pass01.json",
        "prior_hash": sha_sf1,
        "passes": [
            {
                "pass_id": "pass01",
                "candidates_ref": "candidates-pass01.json",
                "frozen_hash": sha_p1,
            },
            {
                "pass_id": "pass02",
                "candidates_ref": "candidates-pass02.json",
                "frozen_hash": sha_p2,
            },
        ],
        "entries": ["pass01:c01", "pass01:c02", "pass02:c01", "pass02:c02"],
    }
    inp_sf2 = write_json(project / "input_sf2.json", sf2)
    res_sf2 = run_ck(
        "freeze", "--stage", "search-field", "--run-id", run_id,
        "--artifact-suffix", "pass02",
        "--input", inp_sf2, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert res_sf2.returncode == 0, res_sf2.stderr
    assert "FREEZE_OK" in res_sf2.stdout
    sha_sf2 = res_sf2.stdout.split()[1]

    # 5. Portfolio v2 freeze referencing search-field-pass02.json and its hash
    pv2 = {
        "schema_version": "pizm-portfolio-selection-v2",
        "stage": "portfolio",
        "route": "BONK",
        "field_ref": "search-field-pass02.json",
        "field_hash": sha_sf2,
        "competition_status": "NO_SECOND_DEFENSIBLE_BUNDLE",
        "recommended_competition": None,
        "perspectives": {"P1": "pass01:c01", "P2": "pass02:c01"},
        "candidate_assessments": [
            {
                "candidate_ref": "pass01:c01",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "res1",
                "nearest_overlap": None,
                "reason": "good",
            },
            {
                "candidate_ref": "pass02:c01",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "res2",
                "nearest_overlap": None,
                "reason": "good",
            },
        ],
        "bundles": [
            {
                "bundle_id": "B1",
                "member_refs": ["pass01:c01", "pass02:c01"],
                "bundle_thesis": "thesis",
                "composition_gain": "gain",
                "member_roles": {},
                "member_ablation": {"pass01:c01": "a", "pass02:c01": "b"},
                "internal_tension": "tension",
                "weakest_link": "link",
                "new_consequence_or_prediction": "pred",
            }
        ],
        "single_target": {"target_type": "B", "target_id": "B1"},
    }
    inp_pv2 = write_json(project / "input_pv2.json", pv2)
    res_pv2 = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", run_id,
        "--input", inp_pv2, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert res_pv2.returncode == 0, res_pv2.stderr
    assert "FREEZE_OK" in res_pv2.stdout

    # Assert exactly the 4 suffixed stages (6 suffixed artifact pairs / 12 files) exist on disk
    run_dir = project / ".ai" / "pizm" / f"run-{run_id}"
    expected_suffixed_files = [
        "candidates-pass01.json", "candidates-pass01.sha256", "candidates-pass01.meta.json",
        "search-field-pass01.json", "search-field-pass01.sha256", "search-field-pass01.meta.json",
        "candidates-pass02.json", "candidates-pass02.sha256", "candidates-pass02.meta.json",
        "search-field-pass02.json", "search-field-pass02.sha256", "search-field-pass02.meta.json",
    ]
    for fn in expected_suffixed_files:
        assert (run_dir / fn).is_file(), f"missing expected file {fn}"
    assert (run_dir / "portfolio.json").is_file()
    assert (run_dir / "portfolio.sha256").is_file()
    assert (run_dir / "portfolio.meta.json").is_file()


def test_search_field_freeze_success(workspace):
    project, skill = workspace
    inp_cand = write_json(project / "cand.json", valid_explore())
    res_cand = run_ck(
        "freeze", "--stage", "explore", "--run-id", "field-run-1",
        "--input", inp_cand, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert res_cand.returncode == 0, res_cand.stderr
    cand_hash = res_cand.stdout.split()[1]

    data = {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "passes": [
            {
                "pass_id": "pass01",
                "candidates_ref": "candidates.json",
                "frozen_hash": cand_hash,
            }
        ],
        "entries": ["pass01:c01", "pass01:c02"],
    }
    inp = write_json(project / "field.json", data)
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
    assert "NEXT CONTRACT" not in result.stdout

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
    inp_cand1 = write_json(project / "cand1.json", valid_explore())
    res1 = run_ck("freeze", "--stage", "explore", "--run-id", "field-bad-order",
                  "--artifact-suffix", "pass01",
                  "--input", inp_cand1, "--project-root", str(project), "--skill-root", str(skill))
    assert res1.returncode == 0
    sha1 = res1.stdout.split()[1]

    inp_cand2 = write_json(project / "cand2.json", valid_explore())
    res2 = run_ck("freeze", "--stage", "explore", "--run-id", "field-bad-order",
                  "--artifact-suffix", "pass02",
                  "--input", inp_cand2, "--project-root", str(project), "--skill-root", str(skill))
    assert res2.returncode == 0
    sha2 = res2.stdout.split()[1]

    data = {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "passes": [
            {"pass_id": "pass01", "candidates_ref": "candidates-pass01.json", "frozen_hash": sha1},
            {"pass_id": "pass02", "candidates_ref": "candidates-pass02.json", "frozen_hash": sha2},
        ],
        "entries": ["pass02:c01", "pass01:c02"],
    }
    inp = write_json(project / "field_bad_order.json", data)
    result = run_ck(
        "freeze", "--stage", "search-field", "--run-id", "field-bad-order",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "append-only" in result.stderr


def test_search_field_unregistered_pass_rejected(workspace):
    project, skill = workspace
    inp_cand1 = write_json(project / "cand1.json", valid_explore())
    res1 = run_ck("freeze", "--stage", "explore", "--run-id", "field-unknown-pass",
                  "--artifact-suffix", "pass01",
                  "--input", inp_cand1, "--project-root", str(project), "--skill-root", str(skill))
    assert res1.returncode == 0
    sha1 = res1.stdout.split()[1]

    data = {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "passes": [
            {"pass_id": "pass01", "candidates_ref": "candidates-pass01.json", "frozen_hash": sha1},
        ],
        "entries": ["pass01:c01", "pass07:c01"],
    }
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
    inp_cand1 = write_json(project / "cand1.json", valid_explore())
    res1 = run_ck("freeze", "--stage", "explore", "--run-id", "field-reuse",
                  "--artifact-suffix", "pass01",
                  "--input", inp_cand1, "--project-root", str(project), "--skill-root", str(skill))
    assert res1.returncode == 0
    sha1 = res1.stdout.split()[1]

    inp_cand2 = write_json(project / "cand2.json", valid_explore())
    res2 = run_ck("freeze", "--stage", "explore", "--run-id", "field-reuse",
                  "--artifact-suffix", "pass02",
                  "--input", inp_cand2, "--project-root", str(project), "--skill-root", str(skill))
    assert res2.returncode == 0
    sha2 = res2.stdout.split()[1]

    data = {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "passes": [
            {"pass_id": "pass01", "candidates_ref": "candidates-pass01.json", "frozen_hash": sha1},
            {"pass_id": "pass02", "candidates_ref": "candidates-pass02.json", "frozen_hash": sha2},
        ],
        "entries": ["pass01:c01", "pass02:c01"],
    }
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
    # Contract map: manual portfolio does not reveal selector
    assert "NEXT CONTRACT" not in result.stdout

@pytest.mark.parametrize(
    "target,valid",
    [
        ({"target_type": "P", "target_id": "P1"}, True),
        ({"target_type": "P", "target_id": "P3"}, False),  # V4 Slice 2: not promoted (only P1)
        ({"target_type": "B", "target_id": "B1"}, True),
        ({"target_type": "B", "target_id": "B9"}, False),  # not a proposed bundle
        ({"target_type": "X", "target_id": "P1"}, False),
    ],
)
def test_portfolio_auto_targets(workspace, target, valid):
    project, skill = workspace
    data = valid_portfolio()
    data["route"] = "AUTO"
    data["next_reasoning_move"] = "DEEP"
    data["next_reasoning_rationale"] = "Developing nominated target."
    data["bundles"] = [bundle()]
    data["auto_target"] = target
    inp = write_json(project / "portfolio_auto.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", f"auto-{abs(hash(json.dumps(target)))}",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert (result.returncode == 0) == valid


def _auto_deep_portfolio(rival=None):
    """V4 Slice 2 helper: v1 AUTO/DEEP portfolio with a single promoted P (P1)."""
    data = valid_portfolio()
    data["route"] = "AUTO"
    data["next_reasoning_move"] = "DEEP"
    data["next_reasoning_rationale"] = "Developing nominated target."
    data["bundles"] = [bundle()]
    data["auto_target"] = {"target_type": "B", "target_id": "B1"}
    data["rival_shadow"] = rival
    return data


def _rival(pid):
    return {
        "target_type": "P",
        "target_id": pid,
        "core_claim": "Rival mechanism",
        "why_remains_live": "Unexplained residual",
        "differentiator_or_source_anchor": "Different anchor",
    }


def test_portfolio_auto_target_p999_rejected(workspace):
    """V4 Slice 2: auto_target P999 is rejected when only P1 is promoted."""
    project, skill = workspace
    data = _auto_deep_portfolio()
    data["auto_target"] = {"target_type": "P", "target_id": "P999"}
    inp = write_json(project / "portfolio_p999.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "auto-p999",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "does not resolve to a promoted Perspective" in result.stderr


def test_portfolio_rival_shadow_unpromoted_p_rejected(workspace):
    """V4 Slice 2: rival_shadow P2 is rejected when only P1 is promoted."""
    project, skill = workspace
    data = _auto_deep_portfolio(rival=_rival("P2"))
    inp = write_json(project / "portfolio_rival_p2.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "auto-rival-p2",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "does not resolve to a promoted Perspective" in result.stderr


def test_portfolio_rival_shadow_promoted_p_accepted(workspace):
    """V4 Slice 2: rival_shadow P1 is accepted when P1 is promoted."""
    project, skill = workspace
    data = _auto_deep_portfolio(rival=_rival("P1"))
    inp = write_json(project / "portfolio_rival_p1.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "auto-rival-p1",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode == 0, result.stderr


def _continued_conversation_portfolio():
    """Review fix: previous visible max P6, one new KEEP materializes as P7."""
    data = valid_portfolio()
    data["route"] = "AUTO"
    data["next_reasoning_move"] = "DEEP"
    data["next_reasoning_rationale"] = "Developing nominated target."
    data["perspectives"] = {"P7": "pass01:c01"}
    data["auto_target"] = {"target_type": "P", "target_id": "P7"}
    data["high_upside"] = [{"ref": "pass01:c01", "why": "Frontier payoff.", "risk": "Thin support."}]
    return data


def _freeze_portfolio(project, skill, data, name, run_id):
    inp = write_json(project / name, data)
    return run_ck(
        "freeze", "--stage", "portfolio", "--run-id", run_id,
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )


def test_portfolio_v1_mapping_p7_accepted(workspace):
    """Reviewer scenario: one new KEEP after P1..P6 freezes as P7 with target P7."""
    project, skill = workspace
    result = _freeze_portfolio(project, skill, _continued_conversation_portfolio(),
                               "portfolio_p7.json", "map-p7-ok")
    assert result.returncode == 0, result.stderr
    assert "FREEZE_OK" in result.stdout


def test_portfolio_v1_mapping_smuggled_p999_rejected(workspace):
    """A v1 perspectives map pointing at a DROP ref is rejected (no P999 bypass)."""
    project, skill = workspace
    data = _continued_conversation_portfolio()
    data["perspectives"] = {"P999": "pass01:c02"}
    data["auto_target"] = {"target_type": "P", "target_id": "P999"}
    data["high_upside"] = [{"ref": "pass01:c02", "why": "Bogus.", "risk": "Bogus."}]
    result = _freeze_portfolio(project, skill, data, "portfolio_p999.json", "map-p999")
    assert result.returncode != 0
    assert "must cover exactly the KEEP candidate refs" in result.stderr


def test_portfolio_v1_mapping_extra_ref_rejected(workspace):
    project, skill = workspace
    data = _continued_conversation_portfolio()
    data["perspectives"] = {"P7": "pass01:c01", "P8": "pass01:c09"}
    result = _freeze_portfolio(project, skill, data, "portfolio_extra.json", "map-extra")
    assert result.returncode != 0
    assert "must cover exactly the KEEP candidate refs" in result.stderr


def test_portfolio_v1_mapping_nondict_rejected(workspace):
    project, skill = workspace
    data = _continued_conversation_portfolio()
    data["perspectives"] = ["P7"]
    result = _freeze_portfolio(project, skill, data, "portfolio_nondict.json", "map-nondict")
    assert result.returncode != 0
    assert "must be an object when present" in result.stderr


def test_portfolio_v1_mapping_auto_outside_mapping_rejected(workspace):
    """auto_target P1 is rejected when the frozen mapping assigns P7."""
    project, skill = workspace
    data = _continued_conversation_portfolio()
    data["auto_target"] = {"target_type": "P", "target_id": "P1"}
    result = _freeze_portfolio(project, skill, data, "portfolio_outside.json", "map-outside")
    assert result.returncode != 0
    assert "does not resolve to a promoted Perspective" in result.stderr


def test_portfolio_v1_mapping_duplicate_ref_rejected(workspace):
    project, skill = workspace
    data = _continued_conversation_portfolio()
    data["candidate_assessments"].append({
        "candidate_ref": "pass01:c03",
        "disposition": "KEEP",
        "standalone_quality": "strong",
        "unique_residue": "Third mechanism",
        "nearest_overlap": None,
        "reason": "Distinct",
    })
    data["perspectives"] = {"P7": "pass01:c01", "P8": "pass01:c01"}
    result = _freeze_portfolio(project, skill, data, "portfolio_dup.json", "map-dup")
    assert result.returncode != 0
    assert "duplicate candidate ref mapped" in result.stderr


def test_portfolio_v1_mapping_nonincreasing_rejected(workspace):
    project, skill = workspace
    data = _continued_conversation_portfolio()
    data["candidate_assessments"].append({
        "candidate_ref": "pass01:c03",
        "disposition": "KEEP",
        "standalone_quality": "strong",
        "unique_residue": "Third mechanism",
        "nearest_overlap": None,
        "reason": "Distinct",
    })
    data["perspectives"] = {"P8": "pass01:c01", "P7": "pass01:c03"}
    result = _freeze_portfolio(project, skill, data, "portfolio_nonincr.json", "map-nonincr")
    assert result.returncode != 0
    assert "strictly increasing" in result.stderr


def test_portfolio_v1_mapping_rival_p7_accepted(workspace):
    """rival_shadow resolves through the v1 mapping as well."""
    project, skill = workspace
    data = _continued_conversation_portfolio()
    data["bundles"] = [bundle()]
    data["auto_target"] = {"target_type": "B", "target_id": "B1"}
    data["rival_shadow"] = {
        "target_type": "P",
        "target_id": "P7",
        "core_claim": "Rival mechanism",
        "why_remains_live": "Unexplained residual",
        "differentiator_or_source_anchor": "Different anchor",
    }
    result = _freeze_portfolio(project, skill, data, "portfolio_rival_p7.json", "map-rival-p7")
    assert result.returncode == 0, result.stderr


def test_portfolio_v1_freeze_without_perspectives_rejected(workspace):
    """New-writer contract: a v1 freeze without the perspectives map fails closed,
    even when every other field is valid."""
    project, skill = workspace
    data = valid_portfolio()
    del data["perspectives"]
    result = _freeze_portfolio(project, skill, data, "portfolio_nomap.json", "map-absent")
    assert result.returncode != 0
    assert "requires perspectives mapping" in result.stderr


def _manual_portfolio_with_aids():
    """V4 Slice 3 helper: v1 MANUAL portfolio, single KEEP pass01:c01."""
    return valid_portfolio()


def _hu_entry(ref="pass01:c01", why="Huge payoff if true.", risk="May be overstated."):
    return {"ref": ref, "why": why, "risk": risk}


def test_portfolio_plain_explanation_accepted(workspace):
    """V4 Slice 3: valid plain_explanation on a KEEP assessment freezes."""
    project, skill = workspace
    data = _manual_portfolio_with_aids()
    data["candidate_assessments"][0]["plain_explanation"] = (
        "This perspective claims latency drives batching. "
        "The non-obvious shift is treating review wait as a batching incentive. "
        "If true, cutting queue time shrinks batches without new process."
    )
    inp = write_json(project / "portfolio_plain_ok.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "plain-ok",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode == 0, result.stderr


def test_portfolio_plain_explanation_empty_rejected(workspace):
    project, skill = workspace
    data = _manual_portfolio_with_aids()
    data["candidate_assessments"][0]["plain_explanation"] = "   "
    inp = write_json(project / "portfolio_plain_empty.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "plain-empty",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "plain_explanation must be non-empty string" in result.stderr


def test_portfolio_plain_explanation_oversized_rejected(workspace):
    project, skill = workspace
    data = _manual_portfolio_with_aids()
    data["candidate_assessments"][0]["plain_explanation"] = "x" * 2001
    inp = write_json(project / "portfolio_plain_big.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "plain-big",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "exceeds 2000 chars" in result.stderr


def test_portfolio_high_upside_accepted(workspace):
    """V4 Slice 3: valid high_upside spotlight on a KEEP ref freezes."""
    project, skill = workspace
    data = _manual_portfolio_with_aids()
    data["high_upside"] = [_hu_entry()]
    inp = write_json(project / "portfolio_hu_ok.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "hu-ok",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode == 0, result.stderr


def test_portfolio_high_upside_empty_list_accepted(workspace):
    project, skill = workspace
    data = _manual_portfolio_with_aids()
    data["high_upside"] = []
    inp = write_json(project / "portfolio_hu_empty.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "hu-empty",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode == 0, result.stderr


def test_portfolio_high_upside_drop_ref_rejected(workspace):
    """V4 Slice 3: high_upside on a DROP ref is rejected (KEEP-only eligibility)."""
    project, skill = workspace
    data = _manual_portfolio_with_aids()
    data["high_upside"] = [_hu_entry(ref="pass01:c02")]
    inp = write_json(project / "portfolio_hu_drop.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "hu-drop",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "does not resolve to an eligible visible Perspective ref" in result.stderr


def test_portfolio_high_upside_quota_rejected(workspace):
    project, skill = workspace
    data = _manual_portfolio_with_aids()
    data["high_upside"] = [_hu_entry() for _ in range(4)]
    inp = write_json(project / "portfolio_hu_quota.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "hu-quota",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "at most 3 entries" in result.stderr


def test_portfolio_high_upside_score_rejected(workspace):
    """V4 Slice 3: numeric score keys are forbidden in the attention cue."""
    project, skill = workspace
    data = _manual_portfolio_with_aids()
    entry = _hu_entry()
    entry["score"] = 0.97
    data["high_upside"] = [entry]
    inp = write_json(project / "portfolio_hu_score.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "hu-score",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "attention cue, not a score" in result.stderr


def test_portfolio_high_upside_missing_risk_rejected(workspace):
    project, skill = workspace
    data = _manual_portfolio_with_aids()
    entry = _hu_entry()
    del entry["risk"]
    data["high_upside"] = [entry]
    inp = write_json(project / "portfolio_hu_norisk.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "hu-norisk",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode != 0
    assert "high_upside[0].risk must be non-empty string" in result.stderr


def test_portfolio_auto_without_target_rejected(workspace):
    project, skill = workspace
    data = valid_portfolio()
    data["route"] = "AUTO"
    data["next_reasoning_move"] = "DEEP"
    data["next_reasoning_rationale"] = "Developing nominated target."
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



def test_portfolio_auto_gather_information_success(workspace):
    project, skill = workspace
    data = valid_portfolio()
    data["route"] = "AUTO"
    data["next_reasoning_move"] = "GATHER_INFORMATION"
    data["next_reasoning_rationale"] = "Clarification needed from user."
    data["auto_target"] = None
    data["information_request"] = {
        "mode": "USER_QUESTION",
        "missing_information": "latency constraints",
        "why_it_changes_route": "changes target choice",
        "questions": ["What is the target latency budget?"],
        "suggested_observation": None,
    }
    inp = write_json(project / "portfolio_gather.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "auto-gather-info",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode == 0, result.stderr


def test_portfolio_auto_preserve_only_success(workspace):
    project, skill = workspace
    data = valid_portfolio()
    data["route"] = "AUTO"
    data["next_reasoning_move"] = "PRESERVE_ONLY"
    data["next_reasoning_rationale"] = "Preserving search field without deep development."
    data["auto_target"] = None
    data["information_request"] = None
    data["rival_shadow"] = None
    inp = write_json(project / "portfolio_preserve.json", data)
    result = run_ck(
        "freeze", "--stage", "portfolio", "--run-id", "auto-preserve",
        "--input", inp, "--project-root", str(project), "--skill-root", str(skill),
    )
    assert result.returncode == 0, result.stderr

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
        "comparative_standing": None,
        "development_delta": {
            "summary": "initial development",
            "new_load_bearing_claims": [],
            "strengthened_claims": [],
            "new_causal_arrows_or_mechanisms": [],
            "material_imports": [],
            "scope_expansions": [],
        },
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
    # Reveal semantics: manual development-v2 freeze does NOT reveal critic (STOP)
    assert "NEXT CONTRACT" not in result.stdout
    assert "DEEP REVIEWER RUBRIC" not in result.stdout
    run_dir = project / ".ai" / "pizm" / "run-dev2-p"
    assert (run_dir / "development-v2.json").exists()
    assert (run_dir / "development-v2.sha256").exists()
    assert (run_dir / "development-v2.meta.json").exists()


def test_development_v2_freeze_auto_reveals_critic(workspace):
    """AUTO route development-v2 freeze reveals deep-reviewer.md."""
    project, skill = workspace
    run_id = "dev2-auto"
    run_dir = project / ".ai" / "pizm" / f"run-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    auto_port = valid_portfolio()
    auto_port["route"] = "AUTO"
    auto_port["next_reasoning_move"] = "DEEP"
    auto_port["next_reasoning_rationale"] = "Developing P7."
    auto_port["auto_target"] = {"target_type": "P", "target_id": "P7"}
    write_json(run_dir / "portfolio.json", auto_port)
    port_raw = (run_dir / "portfolio.json").read_bytes()
    (run_dir / "portfolio.sha256").write_text(hashlib.sha256(port_raw).hexdigest())

    result = freeze_dev_v2(workspace, valid_dev_v2("P", "P7"), run_id)
    assert result.returncode == 0, result.stderr
    assert "FREEZE_OK" in result.stdout
    assert "--- NEXT CONTRACT ---" in result.stdout
    assert "DEEP REVIEWER RUBRIC" in result.stdout
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


# ── Canonical Resolver Containment Tests ─────────────────────────────────


def test_resolver_rejects_absolute_path(workspace):
    project, skill = workspace
    data = {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "passes": [
            {"pass_id": "pass01", "candidates_ref": "/etc/passwd", "frozen_hash": "a" * 64}
        ],
        "entries": ["pass01:c01"],
    }
    inp = write_json(project / "abs_ref.json", data)
    result = run_ck("freeze", "--stage", "search-field", "--run-id", "abs-ref",
                    "--input", inp, "--project-root", str(project), "--skill-root", str(skill))
    assert result.returncode != 0
    assert "absolute" in result.stderr.lower()


def test_resolver_rejects_path_traversal(workspace):
    project, skill = workspace
    data = {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "passes": [
            {"pass_id": "pass01", "candidates_ref": "../secret.json", "frozen_hash": "a" * 64}
        ],
        "entries": ["pass01:c01"],
    }
    inp = write_json(project / "trav_ref.json", data)
    result = run_ck("freeze", "--stage", "search-field", "--run-id", "trav-ref",
                    "--input", inp, "--project-root", str(project), "--skill-root", str(skill))
    assert result.returncode != 0
    assert "traversal" in result.stderr.lower()


def test_resolver_rejects_missing_sidecar(workspace):
    project, skill = workspace
    run_id = "missing-sidecar"
    run_dir = project / ".ai" / "pizm" / f"run-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "candidates.json").write_text('{"schema_version": "pizm-candidate-pool-v1"}', encoding="utf-8")
    # Do NOT write candidates.sha256

    data = {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "passes": [
            {"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": "a" * 64}
        ],
        "entries": ["pass01:c01"],
    }
    inp = write_json(project / "missing_sidecar.json", data)
    result = run_ck("freeze", "--stage", "search-field", "--run-id", run_id,
                    "--input", inp, "--project-root", str(project), "--skill-root", str(skill))
    assert result.returncode != 0
    assert "missing sidecar" in result.stderr.lower()


def test_resolver_rejects_tampered_sidecar(workspace):
    project, skill = workspace
    run_id = "tampered-sidecar"
    run_dir = project / ".ai" / "pizm" / f"run-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    cand_bytes = b'{"schema_version": "pizm-candidate-pool-v1"}'
    (run_dir / "candidates.json").write_bytes(cand_bytes)
    (run_dir / "candidates.sha256").write_text("badhash" * 8, encoding="utf-8")

    data = {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "passes": [
            {"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": "a" * 64}
        ],
        "entries": ["pass01:c01"],
    }
    inp = write_json(project / "tampered_sidecar.json", data)
    result = run_ck("freeze", "--stage", "search-field", "--run-id", run_id,
                    "--input", inp, "--project-root", str(project), "--skill-root", str(skill))
    assert result.returncode != 0
    assert "sidecar hash mismatch" in result.stderr.lower()


# ── Comparison Seam Tests (§1.5) ─────────────────────────────────────────


def test_comparison_seam_success(workspace):
    project, skill = workspace
    run_id = "comp-seam-ok"
    run_dir = project / ".ai" / "pizm" / f"run-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_p = json.dumps(valid_portfolio_v2("B1", "B2"), indent=2).encode("utf-8")
    (run_dir / "portfolio.json").write_bytes(raw_p)
    (run_dir / "portfolio.sha256").write_text(hashlib.sha256(raw_p).hexdigest(), encoding="utf-8")
    (run_dir / "portfolio.meta.json").write_text('{"stage":"portfolio"}', encoding="utf-8")
    # 1. Freeze B1
    dev1 = valid_dev_v2("B", "B1")
    inp1 = write_json(project / "dev1.json", dev1)
    res1 = run_ck("freeze", "--stage", "development-v2", "--run-id", run_id, "--target", "B1",
                  "--input", inp1, "--project-root", str(project), "--skill-root", str(skill))
    assert res1.returncode == 0
    sha_b1 = res1.stdout.split()[1]

    # 2. Freeze B2
    dev2 = valid_dev_v2("B", "B2")
    dev2["identity_lock"]["bundle_id"] = "B2"
    inp2 = write_json(project / "dev2.json", dev2)
    res2 = run_ck("freeze", "--stage", "development-v2", "--run-id", run_id, "--target", "B2",
                  "--input", inp2, "--project-root", str(project), "--skill-root", str(skill))
    assert res2.returncode == 0
    sha_b2 = res2.stdout.split()[1]

    # 3. Freeze comparison review declaring development_ref and frozen_hash
    comp_data = {
        "schema_version": "pizm-comparison-review-v1",
        "stage": "comparison-review-v1",
        "left_target_id": "B1",
        "right_target_id": "B2",
        "left_review": {
            "target_id": "B1",
            "development_ref": "development-v2-B1.json",
            "frozen_hash": sha_b1,
            "terminal_state": "MODEL_READY",
            "independent_countermodel": "cm1",
            "load_bearing_reassessment": [
                {"claim": "c1", "critic_epistemic_status": "SUPPORTED"}
            ],
            "findings": {"unresolved_load_bearing_contradiction": False},
        },
        "right_review": {
            "target_id": "B2",
            "development_ref": "development-v2-B2.json",
            "frozen_hash": sha_b2,
            "terminal_state": "MODEL_READY",
            "independent_countermodel": "cm2",
            "load_bearing_reassessment": [
                {"claim": "c2", "critic_epistemic_status": "SUPPORTED"}
            ],
            "findings": {"unresolved_load_bearing_contradiction": False},
        },
        "comparison": {
            "current_preference": "LEFT",
            "competition_axis": "axis",
            "strongest_reason_for_left": "r1",
            "strongest_reason_for_right": "r2",
            "discriminating_observation": "obs",
            "what_would_change_the_decision": "change",
            "shared_evidence_debt": [],
        },
    }
    inp_c = write_json(project / "comp.json", comp_data)
    res_c = run_ck("freeze", "--stage", "comparison-review-v1", "--run-id", run_id,
                   "--input", inp_c, "--project-root", str(project), "--skill-root", str(skill))
    assert res_c.returncode == 0, res_c.stderr
    assert "FREEZE_OK" in res_c.stdout


def test_comparison_seam_tampered_hash_rejected(workspace):
    project, skill = workspace
    run_id = "comp-tampered-hash"
    run_dir = project / ".ai" / "pizm" / f"run-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_p = json.dumps(valid_portfolio_v2("B1", "B2"), indent=2).encode("utf-8")
    (run_dir / "portfolio.json").write_bytes(raw_p)
    (run_dir / "portfolio.sha256").write_text(hashlib.sha256(raw_p).hexdigest(), encoding="utf-8")
    (run_dir / "portfolio.meta.json").write_text('{"stage":"portfolio"}', encoding="utf-8")
    dev1 = valid_dev_v2("B", "B1")
    inp1 = write_json(project / "dev1.json", dev1)
    run_ck("freeze", "--stage", "development-v2", "--run-id", run_id, "--target", "B1",
           "--input", inp1, "--project-root", str(project), "--skill-root", str(skill))

    dev2 = valid_dev_v2("B", "B2")
    dev2["identity_lock"]["bundle_id"] = "B2"
    inp2 = write_json(project / "dev2.json", dev2)
    run_ck("freeze", "--stage", "development-v2", "--run-id", run_id, "--target", "B2",
           "--input", inp2, "--project-root", str(project), "--skill-root", str(skill))

    comp_data = {
        "schema_version": "pizm-comparison-review-v1",
        "stage": "comparison-review-v1",
        "left_target_id": "B1",
        "right_target_id": "B2",
        "left_review": {
            "target_id": "B1",
            "development_ref": "development-v2-B1.json",
            "frozen_hash": "deadbeef" * 8,  # tampered hash
            "terminal_state": "MODEL_READY",
            "independent_countermodel": "cm1",
            "load_bearing_reassessment": [
                {"claim": "c1", "critic_epistemic_status": "SUPPORTED"}
            ],
            "findings": {"unresolved_load_bearing_contradiction": False},
        },
        "right_review": {
            "target_id": "B2",
            "development_ref": "development-v2-B2.json",
            "frozen_hash": "a" * 64,
            "terminal_state": "MODEL_READY",
            "independent_countermodel": "cm2",
            "load_bearing_reassessment": [
                {"claim": "c2", "critic_epistemic_status": "SUPPORTED"}
            ],
            "findings": {"unresolved_load_bearing_contradiction": False},
        },
        "comparison": {
            "current_preference": "LEFT",
            "competition_axis": "axis",
            "strongest_reason_for_left": "r1",
            "strongest_reason_for_right": "r2",
            "discriminating_observation": "obs",
            "what_would_change_the_decision": "change",
            "shared_evidence_debt": [],
        },
    }
    inp_c = write_json(project / "comp_tamper.json", comp_data)
    res_c = run_ck("freeze", "--stage", "comparison-review-v1", "--run-id", run_id,
                   "--input", inp_c, "--project-root", str(project), "--skill-root", str(skill))
    assert res_c.returncode != 0
    assert "hash mismatch" in res_c.stderr.lower()


def test_comparison_seam_wrong_target_rejected(workspace):
    project, skill = workspace
    run_id = "comp-wrong-target"
    run_dir = project / ".ai" / "pizm" / f"run-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_p = json.dumps(valid_portfolio_v2("B1", "B2"), indent=2).encode("utf-8")
    (run_dir / "portfolio.json").write_bytes(raw_p)
    (run_dir / "portfolio.sha256").write_text(hashlib.sha256(raw_p).hexdigest(), encoding="utf-8")
    (run_dir / "portfolio.meta.json").write_text('{"stage":"portfolio"}', encoding="utf-8")
    dev1 = valid_dev_v2("B", "B1")
    inp1 = write_json(project / "dev1.json", dev1)
    res1 = run_ck("freeze", "--stage", "development-v2", "--run-id", run_id, "--target", "B1",
                  "--input", inp1, "--project-root", str(project), "--skill-root", str(skill))
    sha_b1 = res1.stdout.split()[1]

    # review_B2 wrongly references B1 artifact
    comp_data = {
        "schema_version": "pizm-comparison-review-v1",
        "stage": "comparison-review-v1",
        "left_target_id": "B1",
        "right_target_id": "B2",
        "left_review": {
            "target_id": "B1",
            "development_ref": "development-v2-B1.json",
            "frozen_hash": sha_b1,
            "terminal_state": "MODEL_READY",
            "independent_countermodel": "cm1",
            "load_bearing_reassessment": [
                {"claim": "c1", "critic_epistemic_status": "SUPPORTED"}
            ],
            "findings": {"unresolved_load_bearing_contradiction": False},
        },
        "right_review": {
            "target_id": "B2",
            "development_ref": "development-v2-B1.json",  # wrong target! points to B1
            "frozen_hash": sha_b1,
            "terminal_state": "MODEL_READY",
            "independent_countermodel": "cm2",
            "load_bearing_reassessment": [
                {"claim": "c2", "critic_epistemic_status": "SUPPORTED"}
            ],
            "findings": {"unresolved_load_bearing_contradiction": False},
        },
        "comparison": {
            "current_preference": "LEFT",
            "competition_axis": "axis",
            "strongest_reason_for_left": "r1",
            "strongest_reason_for_right": "r2",
            "discriminating_observation": "obs",
            "what_would_change_the_decision": "change",
            "shared_evidence_debt": [],
        },
    }
    inp_c = write_json(project / "comp_wrong.json", comp_data)
    res_c = run_ck("freeze", "--stage", "comparison-review-v1", "--run-id", run_id,
                   "--input", inp_c, "--project-root", str(project), "--skill-root", str(skill))
    assert res_c.returncode != 0
    assert "target mismatch" in res_c.stderr.lower()


# ── Parameterized Post-Write Cleanup & Retry Tests (§1.5) ────────────────


@pytest.mark.parametrize("stage_kind", ["unsuffixed", "suffixed", "target_scoped"])
@pytest.mark.parametrize("failure_type", ["sha_fail", "meta_fail", "readback_corrupt", "contract_fail"])
def test_post_write_cleanup_and_retry_parameterized(workspace, stage_kind, failure_type):
    """Injected post-write failure cleans up only the failing stage's 3 files; siblings intact; retry succeeds."""
    project, skill = workspace
    run_id = f"pw-{stage_kind}-{failure_type}".replace("_", "-")
    run_dir = project / ".ai" / "pizm" / f"run-{run_id}"

    # Step 1: Pre-populate sibling stage in same run_dir
    if stage_kind == "unsuffixed":
        # Pre-populate 'deep' artifact
        inp_deep = write_json(project / "init_deep.json", valid_deep())
        res_init = run_ck("freeze", "--stage", "deep", "--run-id", run_id,
                          "--input", inp_deep, "--project-root", str(project), "--skill-root", str(skill))
        assert res_init.returncode == 0
        sibling_files = ["development.json", "development.sha256", "development.meta.json"]
        failing_stage = "explore"
        failing_prefix = "candidates"
        failing_input = write_json(project / "fail_input.json", valid_explore())
        freeze_extra_args = []
    elif stage_kind == "suffixed":
        # Pre-populate pass01 explore
        inp_p1 = write_json(project / "init_p1.json", valid_explore())
        res_init = run_ck("freeze", "--stage", "explore", "--run-id", run_id, "--artifact-suffix", "pass01",
                          "--input", inp_p1, "--project-root", str(project), "--skill-root", str(skill))
        assert res_init.returncode == 0
        sibling_files = ["candidates-pass01.json", "candidates-pass01.sha256", "candidates-pass01.meta.json"]
        failing_stage = "explore"
        failing_prefix = "candidates-pass02"
        failing_input = write_json(project / "fail_input.json", valid_explore())
        freeze_extra_args = ["--artifact-suffix", "pass02"]
    else:  # target_scoped
        # Pre-populate development-v2-B1
        inp_b1 = write_json(project / "init_b1.json", valid_dev_v2("B", "B1"))
        res_init = run_ck("freeze", "--stage", "development-v2", "--run-id", run_id, "--target", "B1",
                          "--input", inp_b1, "--project-root", str(project), "--skill-root", str(skill))
        assert res_init.returncode == 0
        sibling_files = ["development-v2-B1.json", "development-v2-B1.sha256", "development-v2-B1.meta.json"]
        failing_stage = "development-v2"
        failing_prefix = "development-v2-B2"
        b2_payload = valid_dev_v2("B", "B2")
        b2_payload["identity_lock"]["bundle_id"] = "B2"
        failing_input = write_json(project / "fail_input.json", b2_payload)
        freeze_extra_args = ["--target", "B2"]

    # Verify sibling files exist
    for fn in sibling_files:
        assert (run_dir / fn).is_file(), f"sibling file {fn} should exist before failure"

    # Step 2: Inject failure
    script_to_run = CHECKPOINT
    contract_to_restore = None

    corrupt_script = project / f"corrupt_{failure_type}.py"
    orig_code = Path(CHECKPOINT).read_text(encoding="utf-8")
    if failure_type == "contract_fail":
        # Inject failure at post-write contract reveal point
        patched = orig_code.replace(
            "# Read contract AFTER hash-confirmed freeze.",
            '_cleanup_stage(run_dir, prefix)\n    return _die("cannot read next-stage contract")',
        )
    elif failure_type == "sha_fail":
        # Break sha256 writing
        patched = orig_code.replace(
            '_durable_exclusive_write(sha_path, computed_hash.encode("utf-8"))',
            'raise OSError("injected sha write failure")',
        )
    elif failure_type == "meta_fail":
        # Break metadata writing
        patched = orig_code.replace(
            'meta_path, json.dumps(meta, indent=2).encode("utf-8")',
            'raise OSError("injected meta write failure")',
        )
    elif failure_type == "readback_corrupt":
        # Force readback hash mismatch
        patched = orig_code.replace(
            'if _sha256_hex(readback) != computed_hash:',
            'if True:  # forced hash mismatch',
        )
    corrupt_script.write_text(patched, encoding="utf-8")
    corrupt_script.chmod(0o755)
    script_to_run = str(corrupt_script)

    # Run failing freeze
    cmd = [
        sys.executable, script_to_run,
        "freeze", "--stage", failing_stage, "--run-id", run_id,
        "--input", str(failing_input),
        "--project-root", str(project),
        "--skill-root", str(skill),
    ] + freeze_extra_args
    res_fail = subprocess.run(cmd, capture_output=True, text=True)
    assert res_fail.returncode != 0, f"expected failure for {failure_type}, stdout: {res_fail.stdout}"

    # Step 3: Assert only owned triple (.json, .sha256, .meta.json) for failing_prefix is absent
    for ext in (".json", ".sha256", ".meta.json"):
        assert not (run_dir / (failing_prefix + ext)).exists(), f"owned file {failing_prefix + ext} must be deleted by cleanup"

    # Assert sibling files are untouched
    for fn in sibling_files:
        assert (run_dir / fn).is_file(), f"sibling file {fn} was wrongly removed"

    # Step 4: Restore environment and retry with uncorrupted CLI
    if contract_to_restore is not None:
        c_path, c_text = contract_to_restore
        c_path.write_text(c_text, encoding="utf-8")

    retry_cmd = [
        sys.executable, CHECKPOINT,
        "freeze", "--stage", failing_stage, "--run-id", run_id,
        "--input", str(failing_input),
        "--project-root", str(project),
        "--skill-root", str(skill),
    ] + freeze_extra_args
    res_retry = subprocess.run(retry_cmd, capture_output=True, text=True)
    assert res_retry.returncode == 0, f"retry failed: {res_retry.stderr}"
    assert "FREEZE_OK" in res_retry.stdout

    # Assert all owned files now exist
    for ext in (".json", ".sha256", ".meta.json"):
        assert (run_dir / (failing_prefix + ext)).is_file(), f"retried file {failing_prefix + ext} must exist after retry"


class TestForgeRoute:
    """FORGE-ROUTE-1..6: Route constraints, degraded single_target ownership, and arbitrary IDs."""

    def _make_search_field(self, workspace, run_id):
        project, skill = workspace
        cand = valid_explore()
        inp_cand = write_json(project / f"cand_{run_id}.json", cand)
        res_cand = run_ck("freeze", "--stage", "explore", "--run-id", run_id, "--input", inp_cand,
                          "--project-root", str(project), "--skill-root", str(skill))
        assert res_cand.returncode == 0
        sha_cand = res_cand.stdout.split()[1]

        sf = {"schema_version": "pizm-search-field-v1", "stage": "search-field",
              "passes": [{"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": sha_cand}],
              "entries": ["pass01:c01", "pass01:c02"]}
        inp_sf = write_json(project / f"sf_{run_id}.json", sf)
        res_sf = run_ck("freeze", "--stage", "search-field", "--run-id", run_id, "--input", inp_sf,
                        "--project-root", str(project), "--skill-root", str(skill))
        assert res_sf.returncode == 0
        return res_sf.stdout.split()[1]

    def test_forge_route_1_v2_forge_only_acceptance(self, workspace):
        """FORGE-ROUTE-1: v2 portfolio with route='BONK' is accepted."""
        project, skill = workspace
        run_id = "fr-route-1"
        sf_hash = self._make_search_field(workspace, run_id)

        pv2 = {
            "schema_version": "pizm-portfolio-selection-v2",
            "stage": "portfolio",
            "route": "BONK",
            "field_ref": "search-field.json",
            "field_hash": sf_hash,
            "perspectives": {"P1": "pass01:c01", "P2": "pass01:c02"},
            "competition_status": "TWO_DEFENSIBLE_BUNDLES",
            "recommended_competition": {
                "left_bundle_id": "B1",
                "right_bundle_id": "B2",
                "competition_axis": "Axis",
                "discriminating_observation": "Observation",
            },
            "candidate_assessments": [
                {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "r1", "nearest_overlap": None, "reason": "good"},
                {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "r2", "nearest_overlap": None, "reason": "good"},
            ],
            "bundles": [
                {"bundle_id": "B1", "member_refs": ["pass01:c01", "pass01:c02"], "bundle_thesis": "t1", "composition_gain": "g1", "member_roles": {}, "member_ablation": {"pass01:c01": "a", "pass01:c02": "b"}, "internal_tension": "ten", "weakest_link": "w", "new_consequence_or_prediction": "p"},
                {"bundle_id": "B2", "member_refs": ["pass01:c01", "pass01:c02"], "bundle_thesis": "t2", "composition_gain": "g2", "member_roles": {}, "member_ablation": {"pass01:c01": "a", "pass01:c02": "b"}, "internal_tension": "ten", "weakest_link": "w", "new_consequence_or_prediction": "p"},
            ],
        }
        inp = write_json(project / "pv2_1.json", pv2)
        res = run_ck("freeze", "--stage", "portfolio", "--run-id", run_id, "--input", inp,
                     "--project-root", str(project), "--skill-root", str(skill))
        assert res.returncode == 0, res.stderr
        assert "FREEZE_OK" in res.stdout

    def test_forge_route_2_manual_auto_masquerade_rejected(self, workspace):
        """FORGE-ROUTE-2: v2 portfolio with route='MANUAL' or route='AUTO' is rejected fail-closed."""
        project, skill = workspace
        run_id = "fr-route-2"
        sf_hash = self._make_search_field(workspace, run_id)

        pv2_manual = {
            "schema_version": "pizm-portfolio-selection-v2",
            "stage": "portfolio",
            "route": "MANUAL",
            "field_ref": "search-field.json",
            "field_hash": sf_hash,
            "perspectives": {"P1": "pass01:c01", "P2": "pass01:c02"},
            "competition_status": "NO_SECOND_DEFENSIBLE_BUNDLE",
            "single_target": {"target_type": "B", "target_id": "B1"},
            "candidate_assessments": [
                {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "r1", "nearest_overlap": None, "reason": "good"},
                {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "r2", "nearest_overlap": None, "reason": "good"},
            ],
            "bundles": [
                {"bundle_id": "B1", "member_refs": ["pass01:c01", "pass01:c02"], "bundle_thesis": "t1", "composition_gain": "g1", "member_roles": {}, "member_ablation": {"pass01:c01": "a", "pass01:c02": "b"}, "internal_tension": "ten", "weakest_link": "w", "new_consequence_or_prediction": "p"},
            ],
        }
        inp_m = write_json(project / "pv2_m.json", pv2_manual)
        res_m = run_ck("freeze", "--stage", "portfolio", "--run-id", run_id, "--input", inp_m,
                       "--project-root", str(project), "--skill-root", str(skill))
        assert res_m.returncode != 0
        assert "pizm-portfolio-selection-v2 requires route 'BONK'" in res_m.stderr

        pv2_auto = dict(pv2_manual)
        pv2_auto["route"] = "AUTO"
        pv2_auto["auto_target"] = {"target_type": "B", "target_id": "B1"}
        inp_a = write_json(project / "pv2_a.json", pv2_auto)
        res_a = run_ck("freeze", "--stage", "portfolio", "--run-id", run_id, "--input", inp_a,
                       "--project-root", str(project), "--skill-root", str(skill))
        assert res_a.returncode != 0
        assert "pizm-portfolio-selection-v2 requires route 'BONK'" in res_a.stderr

    def test_forge_route_3_degraded_single_target_deep_reviewer_reveal(self, workspace):
        """FORGE-ROUTE-3: Degraded FORGE portfolio with single_target reveals deep-reviewer.md after development freeze."""
        project, skill = workspace
        run_id = "fr-route-3"
        sf_hash = self._make_search_field(workspace, run_id)

        pv2 = {
            "schema_version": "pizm-portfolio-selection-v2",
            "stage": "portfolio",
            "route": "BONK",
            "field_ref": "search-field.json",
            "field_hash": sf_hash,
            "perspectives": {"P1": "pass01:c01", "P2": "pass01:c02"},
            "competition_status": "NO_SECOND_DEFENSIBLE_BUNDLE",
            "single_target": {"target_type": "B", "target_id": "B1"},
            "candidate_assessments": [
                {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "r1", "nearest_overlap": None, "reason": "good"},
                {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "r2", "nearest_overlap": None, "reason": "good"},
            ],
            "bundles": [
                {"bundle_id": "B1", "member_refs": ["pass01:c01", "pass01:c02"], "bundle_thesis": "t1", "composition_gain": "g1", "member_roles": {}, "member_ablation": {"pass01:c01": "a", "pass01:c02": "b"}, "internal_tension": "ten", "weakest_link": "w", "new_consequence_or_prediction": "p"},
            ],
        }
        inp = write_json(project / "pv2_deg.json", pv2)
        res_p = run_ck("freeze", "--stage", "portfolio", "--run-id", run_id, "--input", inp,
                       "--project-root", str(project), "--skill-root", str(skill))
        assert res_p.returncode == 0

        # Freeze development B1 -> reveals deep-reviewer.md
        dev_b1 = valid_dev_v2("B", "B1")
        inp_dev = write_json(project / "dev_b1.json", dev_b1)
        res_dev = run_ck("freeze", "--stage", "development-v2", "--run-id", run_id, "--target", "B1",
                         "--input", inp_dev, "--project-root", str(project), "--skill-root", str(skill))
        assert res_dev.returncode == 0, res_dev.stderr
        assert "FREEZE_OK" in res_dev.stdout
        assert "--- NEXT CONTRACT ---" in res_dev.stdout
        assert "DEEP REVIEWER RUBRIC" in res_dev.stdout

    def test_forge_route_4_two_defensible_forbids_single_target(self, workspace):
        """FORGE-ROUTE-4: TWO_DEFENSIBLE_BUNDLES portfolio that provides single_target is rejected."""
        project, skill = workspace
        run_id = "fr-route-4"
        sf_hash = self._make_search_field(workspace, run_id)

        pv2 = {
            "schema_version": "pizm-portfolio-selection-v2",
            "stage": "portfolio",
            "route": "BONK",
            "field_ref": "search-field.json",
            "field_hash": sf_hash,
            "perspectives": {"P1": "pass01:c01", "P2": "pass01:c02"},
            "competition_status": "TWO_DEFENSIBLE_BUNDLES",
            "single_target": {"target_type": "B", "target_id": "B1"},
            "recommended_competition": {
                "left_bundle_id": "B1",
                "right_bundle_id": "B2",
                "competition_axis": "Axis",
                "discriminating_observation": "Observation",
            },
            "candidate_assessments": [
                {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "r1", "nearest_overlap": None, "reason": "good"},
                {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "r2", "nearest_overlap": None, "reason": "good"},
            ],
            "bundles": [
                {"bundle_id": "B1", "member_refs": ["pass01:c01", "pass01:c02"], "bundle_thesis": "t1", "composition_gain": "g1", "member_roles": {}, "member_ablation": {"pass01:c01": "a", "pass01:c02": "b"}, "internal_tension": "ten", "weakest_link": "w", "new_consequence_or_prediction": "p"},
                {"bundle_id": "B2", "member_refs": ["pass01:c01", "pass01:c02"], "bundle_thesis": "t2", "composition_gain": "g2", "member_roles": {}, "member_ablation": {"pass01:c01": "a", "pass01:c02": "b"}, "internal_tension": "ten", "weakest_link": "w", "new_consequence_or_prediction": "p"},
            ],
        }
        inp = write_json(project / "pv2_bad_dual.json", pv2)
        res = run_ck("freeze", "--stage", "portfolio", "--run-id", run_id, "--input", inp,
                     "--project-root", str(project), "--skill-root", str(skill))
        assert res.returncode != 0
        assert "single_target is forbidden when competition_status is TWO_DEFENSIBLE_BUNDLES" in res.stderr

    def test_forge_route_5_invalid_single_target_rejected(self, workspace):
        """FORGE-ROUTE-5: NO_SECOND_DEFENSIBLE_BUNDLE with missing, invalid, or non-existent single_target is rejected."""
        project, skill = workspace
        run_id = "fr-route-5"
        sf_hash = self._make_search_field(workspace, run_id)

        # Missing single_target
        pv2_missing = {
            "schema_version": "pizm-portfolio-selection-v2",
            "stage": "portfolio",
            "route": "BONK",
            "field_ref": "search-field.json",
            "field_hash": sf_hash,
            "perspectives": {"P1": "pass01:c01", "P2": "pass01:c02"},
            "competition_status": "NO_SECOND_DEFENSIBLE_BUNDLE",
            "candidate_assessments": [
                {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "r1", "nearest_overlap": None, "reason": "good"},
                {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "r2", "nearest_overlap": None, "reason": "good"},
            ],
            "bundles": [
                {"bundle_id": "B1", "member_refs": ["pass01:c01", "pass01:c02"], "bundle_thesis": "t1", "composition_gain": "g1", "member_roles": {}, "member_ablation": {"pass01:c01": "a", "pass01:c02": "b"}, "internal_tension": "ten", "weakest_link": "w", "new_consequence_or_prediction": "p"},
            ],
        }
        inp1 = write_json(project / "pv2_miss.json", pv2_missing)
        res1 = run_ck("freeze", "--stage", "portfolio", "--run-id", run_id, "--input", inp1,
                      "--project-root", str(project), "--skill-root", str(skill))
        assert res1.returncode != 0
        assert "single_target is required" in res1.stderr

        # Non-existent B-ID
        pv2_bad_bid = dict(pv2_missing)
        pv2_bad_bid["single_target"] = {"target_type": "B", "target_id": "B99"}
        inp2 = write_json(project / "pv2_bad_b.json", pv2_bad_bid)
        res2 = run_ck("freeze", "--stage", "portfolio", "--run-id", run_id, "--input", inp2,
                      "--project-root", str(project), "--skill-root", str(skill))
        assert res2.returncode != 0
        assert "must reference a bundle_id proposed in this portfolio" in res2.stderr

        # Non-existent P-ID
        pv2_bad_pid = dict(pv2_missing)
        pv2_bad_pid["single_target"] = {"target_type": "P", "target_id": "P99"}
        inp3 = write_json(project / "pv2_bad_p.json", pv2_bad_pid)
        res3 = run_ck("freeze", "--stage", "portfolio", "--run-id", run_id, "--input", inp3,
                      "--project-root", str(project), "--skill-root", str(skill))
        assert res3.returncode != 0
        assert "must reference a perspective id in perspectives mapping" in res3.stderr

    def test_forge_route_6_arbitrary_ids_in_v2_portfolio(self, workspace):
        """FORGE-ROUTE-6: Arbitrary bundle IDs (e.g. B3/B7) succeed in v2 portfolio and freeze."""
        project, skill = workspace
        run_id = "fr-route-6"
        sf_hash = self._make_search_field(workspace, run_id)

        pv2 = {
            "schema_version": "pizm-portfolio-selection-v2",
            "stage": "portfolio",
            "route": "BONK",
            "field_ref": "search-field.json",
            "field_hash": sf_hash,
            "perspectives": {"P1": "pass01:c01", "P2": "pass01:c02"},
            "competition_status": "TWO_DEFENSIBLE_BUNDLES",
            "recommended_competition": {
                "left_bundle_id": "B3",
                "right_bundle_id": "B7",
                "competition_axis": "Arbitrary axis",
                "discriminating_observation": "Arbitrary test observation",
            },
            "candidate_assessments": [
                {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "r1", "nearest_overlap": None, "reason": "good"},
                {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "r2", "nearest_overlap": None, "reason": "good"},
            ],
            "bundles": [
                {"bundle_id": "B3", "member_refs": ["pass01:c01", "pass01:c02"], "bundle_thesis": "t3", "composition_gain": "g3", "member_roles": {}, "member_ablation": {"pass01:c01": "a", "pass01:c02": "b"}, "internal_tension": "ten", "weakest_link": "w", "new_consequence_or_prediction": "p"},
                {"bundle_id": "B7", "member_refs": ["pass01:c01", "pass01:c02"], "bundle_thesis": "t7", "composition_gain": "g7", "member_roles": {}, "member_ablation": {"pass01:c01": "a", "pass01:c02": "b"}, "internal_tension": "ten", "weakest_link": "w", "new_consequence_or_prediction": "p"},
            ],
        }
        inp = write_json(project / "pv2_b3_b7.json", pv2)
        res = run_ck("freeze", "--stage", "portfolio", "--run-id", run_id, "--input", inp,
                     "--project-root", str(project), "--skill-root", str(skill))
        assert res.returncode == 0, res.stderr
        assert "FREEZE_OK" in res.stdout


class TestPolishingWaveInvariants:
    """Invariants for AUTO two-pass, field provenance, and manual deep stop."""

    def test_multi_pass_portfolio_without_field_ref_fails_closed(self, workspace):
        project, skill = workspace
        run_id = "pw-multi-no-ref"
        run_dir = project / ".ai" / "pizm" / f"run-{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Pre-populate multi-pass search fields
        sf1 = write_json(run_dir / "search-field-pass01.json", {"dummy": 1})
        (run_dir / "search-field-pass01.sha256").write_text("1" * 64)
        sf2 = write_json(run_dir / "search-field-pass02.json", {"dummy": 2})
        (run_dir / "search-field-pass02.sha256").write_text("2" * 64)

        port = valid_portfolio()
        port["field_ref"] = None  # omitted
        inp = write_json(project / "port_no_ref.json", port)
        res = run_ck("freeze", "--stage", "portfolio", "--run-id", run_id, "--input", inp,
                     "--project-root", str(project), "--skill-root", str(skill))
        assert res.returncode != 0
        assert "multi-pass portfolio requires explicit field_ref pointing to final search field" in res.stderr

    def test_multi_pass_portfolio_stale_pass01_ref_rejected(self, workspace):
        project, skill = workspace
        run_id = "pw-multi-stale-ref"
        run_dir = project / ".ai" / "pizm" / f"run-{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Pre-populate multi-pass search fields pass01 and pass02
        sf1_data = {
            "schema_version": "pizm-search-field-v1",
            "stage": "search-field",
            "passes": [{"pass_id": "pass01", "candidates_ref": "candidates-pass01.json", "frozen_hash": "a" * 64}],
            "entries": ["pass01:c01"],
        }
        sf1_raw = json.dumps(sf1_data, indent=2).encode("utf-8")
        (run_dir / "search-field-pass01.json").write_bytes(sf1_raw)
        sf1_hash = hashlib.sha256(sf1_raw).hexdigest()
        (run_dir / "search-field-pass01.sha256").write_text(sf1_hash)

        sf2_data = {
            "schema_version": "pizm-search-field-v1",
            "stage": "search-field",
            "passes": [
                {"pass_id": "pass01", "candidates_ref": "candidates-pass01.json", "frozen_hash": "a" * 64},
                {"pass_id": "pass02", "candidates_ref": "candidates-pass02.json", "frozen_hash": "b" * 64},
            ],
            "entries": ["pass01:c01", "pass02:c01"],
        }
        sf2_raw = json.dumps(sf2_data, indent=2).encode("utf-8")
        (run_dir / "search-field-pass02.json").write_bytes(sf2_raw)
        sf2_hash = hashlib.sha256(sf2_raw).hexdigest()
        (run_dir / "search-field-pass02.sha256").write_text(sf2_hash)

        # Portfolio referencing pass01 with valid pass01 hash -> MUST REJECT
        port_stale = valid_portfolio()
        port_stale["field_ref"] = "search-field-pass01.json"
        port_stale["field_hash"] = sf1_hash
        inp_stale = write_json(project / "port_stale.json", port_stale)
        res_stale = run_ck("freeze", "--stage", "portfolio", "--run-id", run_id, "--input", inp_stale,
                          "--project-root", str(project), "--skill-root", str(skill))
        assert res_stale.returncode != 0
        assert "field_ref must reference the final search field 'search-field-pass02.json', got 'search-field-pass01.json'" in res_stale.stderr

        # Portfolio referencing pass02 with valid pass02 hash -> MUST ACCEPT
        port_final = valid_portfolio()
        port_final["field_ref"] = "search-field-pass02.json"
        port_final["field_hash"] = sf2_hash
        inp_final = write_json(project / "port_final.json", port_final)
        res_final = run_ck("freeze", "--stage", "portfolio", "--run-id", run_id, "--input", inp_final,
                          "--project-root", str(project), "--skill-root", str(skill))
        assert res_final.returncode == 0, res_final.stderr
        assert "FREEZE_OK" in res_final.stdout

    def test_multi_pass_portfolio_with_field_ref_verifies_ok(self, workspace):
        project, skill = workspace
        run_id = "pw-multi-with-ref"
        run_dir = project / ".ai" / "pizm" / f"run-{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)

        cand1_raw = json.dumps(valid_explore()).encode("utf-8")
        (run_dir / "candidates-pass01.json").write_bytes(cand1_raw)
        cand1_hash = hashlib.sha256(cand1_raw).hexdigest()
        (run_dir / "candidates-pass01.sha256").write_text(cand1_hash)

        sf_data = {
            "schema_version": "pizm-search-field-v1",
            "stage": "search-field",
            "passes": [{"pass_id": "pass01", "candidates_ref": "candidates-pass01.json", "frozen_hash": cand1_hash}],
            "entries": ["pass01:c01", "pass01:c02"],
        }
        sf_raw = json.dumps(sf_data, indent=2).encode("utf-8")
        (run_dir / "search-field-pass02.json").write_bytes(sf_raw)
        sf_hash = hashlib.sha256(sf_raw).hexdigest()
        (run_dir / "search-field-pass02.sha256").write_text(sf_hash)

        port = valid_portfolio()
        port["field_ref"] = "search-field-pass02.json"
        port["field_hash"] = sf_hash
        inp = write_json(project / "port_with_ref.json", port)
        res = run_ck("freeze", "--stage", "portfolio", "--run-id", run_id, "--input", inp,
                     "--project-root", str(project), "--skill-root", str(skill))
        assert res.returncode == 0, res.stderr
        assert "FREEZE_OK" in res.stdout

    def test_manual_portfolio_development_stops_without_critic(self, workspace):
        project, skill = workspace
        run_id = "pw-man-stop"
        run_dir = project / ".ai" / "pizm" / f"run-{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)

        port_raw = json.dumps(valid_portfolio()).encode("utf-8")
        (run_dir / "portfolio.json").write_bytes(port_raw)
        (run_dir / "portfolio.sha256").write_text(hashlib.sha256(port_raw).hexdigest())

        dev_payload = valid_dev_v2("P", "P7")
        inp_dev = write_json(project / "dev_man.json", dev_payload)
        res = run_ck("freeze", "--stage", "development-v2", "--run-id", run_id,
                     "--input", inp_dev, "--project-root", str(project), "--skill-root", str(skill))
        assert res.returncode == 0, res.stderr
        assert "FREEZE_OK" in res.stdout
        assert "NEXT CONTRACT" not in res.stdout

    def test_p_target_suffixed_development_resolved_symmetrically(self, workspace):
        project, skill = workspace
        run_id = "pw-p-suffix"
        run_dir = project / ".ai" / "pizm" / f"run-{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Freeze development with --target P3 (generates development-v2-P3.json)
        dev_p3 = valid_dev_v2("P", "P3")
        inp_dev = write_json(project / "dev_p3.json", dev_p3)
        res_dev = run_ck("freeze", "--stage", "development-v2", "--run-id", run_id, "--target", "P3",
                         "--input", inp_dev, "--project-root", str(project), "--skill-root", str(skill))
        assert res_dev.returncode == 0, res_dev.stderr
        dev_hash = res_dev.stdout.split()[1]
        assert (run_dir / "development-v2-P3.json").is_file()

        # Review target P3 without explicit target_ref -> must resolve development-v2-P3.json symmetrically
        rev_data = {
            "schema_version": "pizm-deep-review-v2",
            "stage": "deep-review-v2",
            "frozen_hash": dev_hash,
            "target_type": "P",
            "target_id": "P3",
            "terminal_state": "MODEL_READY",
            "identity_verified": True,
            "independent_countermodel": "Countermodel.",
            "load_bearing_reassessment": [
                {"claim": "Claim 1", "critic_epistemic_status": "SUPPORTED"}
            ],
            "findings": {
                "identity_drift": None,
                "cross_field_contradictions": [],
                "readiness_blockers": [],
                "readiness_blocker_details": {},
                "unsupported_specificity": [],
                "epistemic_laundering": [],
                "cost_relocation": None,
                "round_trip_skeleton": "claim -> mechanism",
            },
            "evidence_debt": [],
            "cheapest_discriminating_test": "Test 1.",
            "verdict_rationale": "Grounded.",
            "inquiry_program": None,
        }
        inp_rev = write_json(project / "rev_p3.json", rev_data)
        res_rev = run_ck("freeze", "--stage", "deep-review-v2", "--run-id", run_id, "--target", "P3",
                         "--input", inp_rev, "--project-root", str(project), "--skill-root", str(skill))
        assert res_rev.returncode == 0, res_rev.stderr
        assert "FREEZE_OK" in res_rev.stdout
        assert (run_dir / "deep-review-v2-P3.json").is_file()
