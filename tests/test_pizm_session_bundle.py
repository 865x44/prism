"""
Focused behavioral tests for bin/pizm-session-bundle.

Covers:
- Default slug (timestamp + random)
- Explicit slug (deterministic)
- Exact byte-identical copies of stage artifacts
- Hash verification and corruption detection
- Overwrite refusal
- Input basename collision refusal
- Directory input refusal
- Transcript copy and FOLLOW_UP_CANDIDATE fallback
- Stage requirements (missing files fail)
- Stage label format validation
- Stage ordering preserved in manifest
- Sample manifest round-trip
- Skill hash computation
- No session/provider discovery strings in source
- Cold-path sufficiency (bundle has everything for re-judge/replay)
- SHA sidecar verification before copy
- Evidence kind recorded correctly
"""
import hashlib
import json
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from importlib.machinery import SourceFileLoader

import pytest

BUNDLE_CLI = str(Path(__file__).resolve().parent.parent / "bin" / "pizm-session-bundle")
REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = REPO_ROOT / "prism-runs" / "session-sample-offline-20260824"


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
_bundle_loader = SourceFileLoader("pizm_session_bundle", BUNDLE_CLI)
_bundle_spec = importlib.util.spec_from_loader("pizm_session_bundle", _bundle_loader)
_bundle_mod = importlib.util.module_from_spec(_bundle_spec)
_bundle_loader.exec_module(_bundle_mod)
_compute_semantic_stage_count = _bundle_mod._compute_semantic_stage_count


def run_bundle(*args, cwd=None):
    return subprocess.run(
        [sys.executable, BUNDLE_CLI, *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace(tmp_path):
    """Workspace with skill root, stage sources, and input files."""
    # Skill root
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("# Pizm Skill\nTest skill content")
    refs = skill / "references"
    refs.mkdir()
    (refs / "explore.md").write_text("# Explore generator contract")
    (refs / "explore-selector.md").write_text("# Selector rubric (hidden)")
    (refs / "deep.md").write_text("# Deep developer contract")
    (refs / "deep-reviewer.md").write_text("# Reviewer rubric (hidden)")
    agents = skill / "agents"
    agents.mkdir()
    (agents / "openai.yaml").write_text("model: gpt-4\n")

    # Stage sources — Explore (NORMAL)
    explore_dir = tmp_path / "run-explore-01"
    explore_dir.mkdir()
    candidates = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {"candidate_id": "c1", "content": "alpha perspective"},
            {"candidate_id": "c2", "content": "beta perspective"},
        ],
    }
    cand_json = json.dumps(candidates, indent=2).encode("utf-8")
    (explore_dir / "candidates.json").write_bytes(cand_json)
    (explore_dir / "candidates.sha256").write_text(_sha256_hex(cand_json))
    selection = {"selected": "c1", "reason": "strongest material novelty"}
    (explore_dir / "selection.json").write_text(json.dumps(selection))

    # Stage sources — Deep
    deep_dir = tmp_path / "run-deep-P1"
    deep_dir.mkdir()
    development = {
        "schema_version": "pizm-development-v1",
        "stage": "deep",
        "selected_p_ids": ["P1"],
        "development": {"P1": {"title": "Deep analysis", "body": "developed content"}},
    }
    dev_json = json.dumps(development, indent=2).encode("utf-8")
    (deep_dir / "development.json").write_bytes(dev_json)
    (deep_dir / "development.sha256").write_text(_sha256_hex(dev_json))
    review = {"status": "MODEL_READY", "assessment": "sufficient evidence"}
    (deep_dir / "review.json").write_text(json.dumps(review))

    # Input files
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    (inputs_dir / "source.txt").write_text("This is source material for the session.")
    (inputs_dir / "notes.md").write_text("# Notes\nSome observations.")

    # Transcript
    transcript = tmp_path / "session.jsonl"
    transcript.write_text('{"role":"user","content":"analyze this"}\n')

    # Output root
    output = tmp_path / "output"
    output.mkdir()

    return {
        "skill": skill,
        "explore": explore_dir,
        "deep": deep_dir,
        "inputs": inputs_dir,
        "transcript": transcript,
        "output": output,
        "tmp": tmp_path,
    }


# ---------------------------------------------------------------------------
# 1. Default slug generation
# ---------------------------------------------------------------------------


class TestDefaultSlug:
    def test_default_slug_generates_output(self, workspace):
        """Without --slug, output uses timestamp+random format."""
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode == 0, r.stderr
        # Find the created directory
        dirs = list(workspace["output"].iterdir())
        assert len(dirs) == 1
        name = dirs[0].name
        assert name.startswith("session-")
        slug = name[len("session-"):]
        # Timestamp format: YYYYMMDDtHHMMSSz-xxxx
        assert re.match(r"\d{8}t\d{6}z-[a-z0-9]{4}", slug)

    def test_default_slugs_are_unique(self, workspace):
        """Two invocations produce different slugs."""
        r1 = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        # Need fresh explore dir for second run (sha sidecar still valid)
        r2 = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r1.returncode == 0
        assert r2.returncode == 0
        dirs = sorted(d.name for d in workspace["output"].iterdir())
        assert len(dirs) == 2
        assert dirs[0] != dirs[1]


# ---------------------------------------------------------------------------
# 2. Explicit slug
# ---------------------------------------------------------------------------


class TestExplicitSlug:
    def test_explicit_slug_deterministic(self, workspace):
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "test-run-01",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode == 0, r.stderr
        bundle_dir = workspace["output"] / "session-test-run-01"
        assert bundle_dir.is_dir()
        manifest = json.loads((bundle_dir / "manifest.json").read_text())
        assert manifest["slug"] == "test-run-01"

    def test_invalid_slug_rejected(self, workspace):
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "INVALID_SLUG!",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode != 0
        assert "slug" in r.stderr.lower() or "must be" in r.stderr.lower()


# ---------------------------------------------------------------------------
# 3. Exact byte-identical copies
# ---------------------------------------------------------------------------


class TestExactCopies:
    def test_stage_artifacts_byte_identical(self, workspace):
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "copy-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
            "--stage", f"deep-P1={workspace['deep']}",
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-copy-test"

        # Explore files
        for fname in ("candidates.json", "candidates.sha256", "selection.json"):
            src = workspace["explore"] / fname
            dst = bundle / "pass-01-normal" / fname
            assert dst.read_bytes() == src.read_bytes(), f"{fname} not byte-identical"

        # Deep files
        for fname in ("development.json", "development.sha256", "review.json"):
            src = workspace["deep"] / fname
            dst = bundle / "deep-P1" / fname
            assert dst.read_bytes() == src.read_bytes(), f"{fname} not byte-identical"

    def test_inputs_byte_identical(self, workspace):
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "input-copy",
            "--skill-root", str(workspace["skill"]),
            "--input", str(workspace["inputs"] / "source.txt"),
            "--input", str(workspace["inputs"] / "notes.md"),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-input-copy"
        for fname in ("source.txt", "notes.md"):
            src = workspace["inputs"] / fname
            dst = bundle / "inputs" / fname
            assert dst.read_bytes() == src.read_bytes()


# ---------------------------------------------------------------------------
# 4. Hash verification and corruption
# ---------------------------------------------------------------------------


class TestHashVerification:
    def test_manifest_hashes_match_copied_files(self, workspace):
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "hash-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
            "--input", str(workspace["inputs"] / "source.txt"),
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-hash-test"
        manifest = json.loads((bundle / "manifest.json").read_text())

        # Verify every artifact hash in manifest matches the actual file
        for rel_path, expected_hash in manifest["artifacts"].items():
            actual = _sha256_hex((bundle / rel_path).read_bytes())
            assert actual == expected_hash, f"hash mismatch for {rel_path}"

    def test_corrupted_source_sha_fails(self, workspace):
        """Corrupt the sha256 sidecar in the source → bundle creation fails."""
        (workspace["explore"] / "candidates.sha256").write_text("0" * 64)
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "corrupt-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode != 0
        assert "hash mismatch" in r.stderr.lower() or "mismatch" in r.stderr.lower()
        # Bundle dir should NOT have been created
        assert not (workspace["output"] / "session-corrupt-test").exists()


# ---------------------------------------------------------------------------
# 5. Overwrite refusal
# ---------------------------------------------------------------------------


class TestOverwriteRefusal:
    def test_refuse_overwrite_existing_bundle(self, workspace):
        # First creation succeeds
        r1 = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "dup-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r1.returncode == 0

        # Second with same slug fails
        r2 = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "dup-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r2.returncode != 0
        assert "already exists" in r2.stderr


# ---------------------------------------------------------------------------
# 6. Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_input_basename_collision(self, workspace):
        """Two inputs with same basename are refused."""
        dup_dir = workspace["tmp"] / "dup"
        dup_dir.mkdir()
        (dup_dir / "source.txt").write_text("different content same name")
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "collision-test",
            "--skill-root", str(workspace["skill"]),
            "--input", str(workspace["inputs"] / "source.txt"),
            "--input", str(dup_dir / "source.txt"),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode != 0
        assert "collision" in r.stderr.lower()

    def test_directory_input_refused(self, workspace):
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "dir-input-test",
            "--skill-root", str(workspace["skill"]),
            "--input", str(workspace["inputs"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode != 0
        assert "directory" in r.stderr.lower()

    def test_missing_input_refused(self, workspace):
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "missing-input",
            "--skill-root", str(workspace["skill"]),
            "--input", str(workspace["tmp"] / "nonexistent.txt"),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode != 0


# ---------------------------------------------------------------------------
# 7. Transcript copy and fallback
# ---------------------------------------------------------------------------


class TestTranscript:
    def test_transcript_copied_when_supplied(self, workspace):
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "tx-test",
            "--skill-root", str(workspace["skill"]),
            "--transcript", str(workspace["transcript"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-tx-test"
        tx_file = bundle / "transcript" / "session.jsonl"
        assert tx_file.exists()
        assert tx_file.read_bytes() == workspace["transcript"].read_bytes()
        manifest = json.loads((bundle / "manifest.json").read_text())
        assert manifest["transcript"]["status"] == "present"
        assert "transcript/" in manifest["transcript"]["path"]

    def test_transcript_fallback_follow_up(self, workspace):
        """Without --transcript, manifest records FOLLOW_UP_CANDIDATE."""
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "no-tx-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-no-tx-test"
        manifest = json.loads((bundle / "manifest.json").read_text())
        tx = manifest["transcript"]
        assert tx["status"] == "FOLLOW_UP_CANDIDATE"
        assert tx["problem"] == "transcript not supplied"
        assert "no session discovery attempted" in tx["evidence"]
        assert "does not inspect host sessions" in tx["why"]
        assert "minimal_next_experiment" in tx
        # No transcript directory
        assert not (bundle / "transcript").exists()


# ---------------------------------------------------------------------------
# 8. Stage requirements and validation
# ---------------------------------------------------------------------------


class TestStageRequirements:
    def test_missing_selection_json_fails(self, workspace):
        """Explore stage requires selection.json."""
        (workspace["explore"] / "selection.json").unlink()
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "missing-sel",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode != 0
        assert "selection.json" in r.stderr

    def test_missing_review_json_fails(self, workspace):
        """Deep stage requires review.json."""
        (workspace["deep"] / "review.json").unlink()
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "missing-rev",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"deep-P1={workspace['deep']}",
        )
        assert r.returncode != 0
        assert "review.json" in r.stderr

    def test_invalid_stage_label_rejected(self, workspace):
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "bad-label",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"invalid-label={workspace['explore']}",
        )
        assert r.returncode != 0
        assert "invalid stage label" in r.stderr.lower()
    def test_duplicate_stage_label_rejected(self, workspace):
        """Duplicate stage labels are rejected."""
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "dup-stage",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode != 0
    def test_atomic_cleanup_on_failure(self, workspace):
        """A copy failure after temp creation leaves no partial or temp bundle."""
        # Optional metadata is discovered only during copy, after all source
        # validation and temp-directory creation. A directory at that path
        # forces read_bytes() to fail inside the transactional publish block.
        (workspace["explore"] / "candidates.meta.json").mkdir()

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "cleanup-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )

        assert r.returncode != 0
        assert not (workspace["output"] / "session-cleanup-test").exists()
        temp_dirs = [
            path for path in workspace["output"].iterdir()
            if path.name.startswith(".pizm-bundle-")
        ]
        assert temp_dirs == []

    def test_missing_output_root_is_created(self, workspace):
        output = workspace["tmp"] / "new" / "nested" / "output"
        r = run_bundle(
            "create",
            "--output-root", str(output),
            "--slug", "new-output-root",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode == 0, r.stderr
        assert (output / "session-new-output-root" / "manifest.json").exists()
    def test_stage_order_preserved(self, workspace):
        """Stages appear in manifest in the order given on CLI."""
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "order-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"deep-P1={workspace['deep']}",
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-order-test"
        manifest = json.loads((bundle / "manifest.json").read_text())
        assert manifest["stages"] == ["deep-P1", "pass-01-normal"]

    def test_deep_direct_seed_label_accepted(self, workspace):
        """deep-DIRECT_SEED is a valid stage label."""
        # Create a deep source dir with DIRECT_SEED-compatible content
        ds_dir = workspace["tmp"] / "run-deep-ds"
        ds_dir.mkdir()
        development = {
            "schema_version": "pizm-development-v1",
            "stage": "deep",
            "selected_p_ids": ["DIRECT_SEED"],
            "development": {"DIRECT_SEED": {"title": "Direct seed", "body": "content"}},
        }
        dev_json = json.dumps(development, indent=2).encode("utf-8")
        (ds_dir / "development.json").write_bytes(dev_json)
        (ds_dir / "development.sha256").write_text(_sha256_hex(dev_json))
        (ds_dir / "review.json").write_text(json.dumps({"status": "MODEL_READY"}))

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "ds-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"deep-DIRECT_SEED={ds_dir}",
        )
        assert r.returncode == 0, r.stderr

    def test_pass_label_modes(self, workspace):
        """pass-NN-rift and pass-NN-360 are valid labels."""
        for label in ("pass-02-rift", "pass-03-360"):
            slug = label.replace("-", "")
            r = run_bundle(
                "create",
                "--output-root", str(workspace["output"]),
                "--slug", slug,
                "--skill-root", str(workspace["skill"]),
                "--stage", f"{label}={workspace['explore']}",
            )
            assert r.returncode == 0, f"Failed for {label}: {r.stderr}"


# ---------------------------------------------------------------------------
# 9. Manifest round-trip
# ---------------------------------------------------------------------------


class TestManifestRoundTrip:
    def test_manifest_structure(self, workspace):
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "manifest-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
            "--stage", f"deep-P1={workspace['deep']}",
            "--input", str(workspace["inputs"] / "source.txt"),
            "--transcript", str(workspace["transcript"]),
            "--harness", "omp-test",
            "--model", "qwen-test",
            "--repo-commit", "abc123",
            "--evidence-kind", "offline_fixture",
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-manifest-test"
        manifest = json.loads((bundle / "manifest.json").read_text())

        # Required fields
        assert manifest["schema_version"] == "pizm-session-bundle-v1"
        assert manifest["identity_scope"] == "archive_only"
        assert "created_utc" in manifest
        assert manifest["evidence_kind"] == "offline_fixture"
        assert manifest["slug"] == "manifest-test"
        assert "skill_hash" in manifest
        assert len(manifest["skill_hash"]) == 64  # hex sha256
        assert manifest["harness"] == "omp-test"
        assert manifest["model"] == "qwen-test"
        assert manifest["repo_commit"] == "abc123"
        assert manifest["stages"] == ["pass-01-normal", "deep-P1"]
        assert len(manifest["inputs"]) == 1
        assert manifest["inputs"][0]["filename"] == "source.txt"
        assert len(manifest["inputs"][0]["sha256"]) == 64
        assert manifest["transcript"]["status"] == "present"

        # All artifacts present and hashed
        for rel_path, sha in manifest["artifacts"].items():
            assert (bundle / rel_path).exists(), f"missing: {rel_path}"
            assert _sha256_hex((bundle / rel_path).read_bytes()) == sha

    def test_optional_fields_omitted_when_empty(self, workspace):
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "minimal-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-minimal-test"
        manifest = json.loads((bundle / "manifest.json").read_text())
        assert "harness" not in manifest
        assert "model" not in manifest
        assert "repo_commit" not in manifest


# ---------------------------------------------------------------------------
# 10. Skill hash
# ---------------------------------------------------------------------------


class TestSkillHash:
    def test_skill_hash_deterministic(self, workspace):
        """Same skill root produces same hash."""
        r1 = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "sh1",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        r2 = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "sh2",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r1.returncode == 0
        assert r2.returncode == 0
        m1 = json.loads(
            (workspace["output"] / "session-sh1" / "manifest.json").read_text()
        )
        m2 = json.loads(
            (workspace["output"] / "session-sh2" / "manifest.json").read_text()
        )
        assert m1["skill_hash"] == m2["skill_hash"]

    def test_skill_hash_changes_with_content(self, workspace):
        """Modifying a skill file changes the hash."""
        r1 = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "before",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        (workspace["skill"] / "SKILL.md").write_text("# MODIFIED")
        r2 = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "after",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        m1 = json.loads(
            (workspace["output"] / "session-before" / "manifest.json").read_text()
        )
        m2 = json.loads(
            (workspace["output"] / "session-after" / "manifest.json").read_text()
        )
        assert m1["skill_hash"] != m2["skill_hash"]


# ---------------------------------------------------------------------------
# 11. No session/provider discovery
# ---------------------------------------------------------------------------


class TestNoDiscovery:
    def test_source_has_no_session_discovery(self):
        """CLI source must not contain session/latest/global discovery strings."""
        source = Path(BUNDLE_CLI).read_text(encoding="utf-8")
        forbidden = [
            "latest_session",
            "latest-session",
            "session_registry",
            "session-registry",
            "global_pointer",
            "global-pointer",
            "find_latest",
            "find-latest",
            "auto_discover",
            "auto-discover",
        ]
        for term in forbidden:
            assert term not in source.lower(), f"source contains forbidden term: {term}"

    def test_source_has_no_provider_calls(self):
        """CLI source must not invoke providers or models."""
        source = Path(BUNDLE_CLI).read_text(encoding="utf-8")
        forbidden = [
            "openai",
            "anthropic",
            "provider_call",
            "model_invoke",
            "llm_call",
            "api_key",
        ]
        for term in forbidden:
            assert term not in source.lower(), f"source contains forbidden term: {term}"


# ---------------------------------------------------------------------------
# 12. Cold-path sufficiency
# ---------------------------------------------------------------------------


class TestColdPathSufficiency:
    def test_bundle_has_rejudge_materials(self, workspace):
        """Bundle contains everything needed for fresh re-judge."""
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "rejudge-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
            "--stage", f"deep-P1={workspace['deep']}",
            "--input", str(workspace["inputs"] / "source.txt"),
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-rejudge-test"

        # Frozen pool bytes
        assert (bundle / "pass-01-normal" / "candidates.json").exists()
        assert (bundle / "pass-01-normal" / "candidates.sha256").exists()
        # Selection for comparison
        assert (bundle / "pass-01-normal" / "selection.json").exists()

        # Frozen development bytes
        assert (bundle / "deep-P1" / "development.json").exists()
        assert (bundle / "deep-P1" / "development.sha256").exists()
        # Review for comparison
        assert (bundle / "deep-P1" / "review.json").exists()

        # Source materials
        assert (bundle / "inputs" / "source.txt").exists()

        # Manifest with all hashes
        manifest = json.loads((bundle / "manifest.json").read_text())
        assert "artifacts" in manifest
        assert len(manifest["artifacts"]) > 0
        assert "skill_hash" in manifest


# ---------------------------------------------------------------------------
# 13. Permanent sample bundle round-trip
# ---------------------------------------------------------------------------


class TestPermanentSample:
    def test_sample_exists_and_valid(self):
        """The permanent sample bundle at prism-runs/ exists and is well-formed."""
        if not SAMPLE_DIR.exists():
            pytest.skip("permanent sample not yet generated")
        manifest_path = SAMPLE_DIR / "manifest.json"
        assert manifest_path.exists(), "sample manifest missing"
        manifest = json.loads(manifest_path.read_text())
        assert manifest["schema_version"] == "pizm-session-bundle-v1"
        assert manifest["evidence_kind"] == "offline_fixture"
        assert manifest["transcript"]["status"] == "FOLLOW_UP_CANDIDATE"

    def test_sample_hashes_verify(self):
        """All artifact hashes in sample manifest match actual files."""
        if not SAMPLE_DIR.exists():
            pytest.skip("permanent sample not yet generated")
        manifest = json.loads((SAMPLE_DIR / "manifest.json").read_text())
        for rel_path, expected_hash in manifest["artifacts"].items():
            actual = _sha256_hex((SAMPLE_DIR / rel_path).read_bytes())
            assert actual == expected_hash, (
                f"sample hash mismatch: {rel_path}"
            )

    def test_sample_has_required_structure(self):
        """Sample has at least one explore and one deep stage."""
        if not SAMPLE_DIR.exists():
            pytest.skip("permanent sample not yet generated")
        manifest = json.loads((SAMPLE_DIR / "manifest.json").read_text())
        stages = manifest["stages"]
        has_explore = any(s.startswith("pass-") for s in stages)
        has_deep = any(s.startswith("deep-") for s in stages)
        assert has_explore, "sample missing explore stage"
        assert has_deep, "sample missing deep stage"

    def test_sample_has_input(self):
        """Sample includes at least one input file."""
        if not SAMPLE_DIR.exists():
            pytest.skip("permanent sample not yet generated")
        manifest = json.loads((SAMPLE_DIR / "manifest.json").read_text())
        assert len(manifest["inputs"]) >= 1
        # Check pasted-text.txt exists
        has_pasted = any(
            inp["filename"] == "pasted-text.txt" for inp in manifest["inputs"]
        )
        assert has_pasted, "sample missing inputs/pasted-text.txt"

    def test_sample_selection_schema(self):
        """Sample selection.json has full pizm-selection-v1 field set."""
        if not SAMPLE_DIR.exists():
            pytest.skip("permanent sample not yet generated")
        manifest = json.loads((SAMPLE_DIR / "manifest.json").read_text())
        # Find explore stage
        explore_stage = next(s for s in manifest["stages"] if s.startswith("pass-"))
        sel_path = SAMPLE_DIR / explore_stage / "selection.json"
        sel = json.loads(sel_path.read_text())
        # Required pizm-selection-v1 fields
        assert sel["schema_version"] == "pizm-selection-v1"
        assert sel["stage"] == "explore"
        assert sel["mode"] in ("NORMAL", "360", "RIFT")
        assert "frozen_hash" in sel and len(sel["frozen_hash"]) == 64
        assert isinstance(sel["dispositions"], list) and len(sel["dispositions"]) > 0
        for d in sel["dispositions"]:
            assert "candidate_id" in d
            assert d["disposition"] in ("KEEP", "BORDERLINE", "MERGE", "DROP")
            assert d["standalone_quality"] in ("strong", "borderline", "weak")
            assert d["marginal_contribution"] in ("high", "medium", "low", "none")
            assert "reason" in d
        assert isinstance(sel["kept"], list)
        assert isinstance(sel["merged"], list)
        assert "next_free_p" in sel and sel["next_free_p"].startswith("P")

    def test_sample_candidates_schema(self):
        """Sample candidates.json has documented pizm-candidates-v1 field set."""
        if not SAMPLE_DIR.exists():
            pytest.skip("permanent sample not yet generated")
        manifest = json.loads((SAMPLE_DIR / "manifest.json").read_text())
        explore_stage = next(s for s in manifest["stages"] if s.startswith("pass-"))
        cand_path = SAMPLE_DIR / explore_stage / "candidates.json"
        cand = json.loads(cand_path.read_text())
        assert cand["schema_version"] == "pizm-candidates-v1"
        assert cand["stage"] == "explore"
        assert cand["mode"] in ("NORMAL", "360", "RIFT")
        assert isinstance(cand["candidates"], list) and len(cand["candidates"]) > 0
        for c in cand["candidates"]:
            assert "candidate_id" in c and isinstance(c["candidate_id"], str)
            assert "title" in c and isinstance(c["title"], str)
            # Semantic core fields
            assert "semantic_core" in c
            sc = c["semantic_core"]
            for field in ("claim", "structural_shift", "mechanism",
                          "grounding_anchor", "what_becomes_visible", "boundary"):
                assert field in sc, f"semantic_core missing {field}"
            # Epistemics arrays
            assert "epistemics" in c
            ep = c["epistemics"]
            for arr in ("supported", "inferred", "speculative", "unknown"):
                assert arr in ep and isinstance(ep[arr], list)

    def test_sample_development_schema(self):
        """Sample development.json has full pizm-development-v1 field set."""
        if not SAMPLE_DIR.exists():
            pytest.skip("permanent sample not yet generated")
        manifest = json.loads((SAMPLE_DIR / "manifest.json").read_text())
        deep_stage = next(s for s in manifest["stages"] if s.startswith("deep-"))
        dev_path = SAMPLE_DIR / deep_stage / "development.json"
        dev = json.loads(dev_path.read_text())
        assert dev["schema_version"] == "pizm-development-v1"
        assert dev["stage"] == "deep"
        assert isinstance(dev["selected_p_ids"], list)
        assert isinstance(dev["development"], dict)
        for p_id, dev_data in dev["development"].items():
            # Identity lock
            assert "identity_lock" in dev_data
            il = dev_data["identity_lock"]
            for field in ("p_id", "title", "core_claim", "structural_shift",
                          "mechanism", "boundary"):
                assert field in il, f"identity_lock missing {field}"
            # Developed model
            assert "developed_model" in dev_data
            dm = dev_data["developed_model"]
            for field in ("strengthened_claim", "load_bearing_mechanism",
                          "implications", "strongest_objection", "break_conditions"):
                assert field in dm, f"developed_model missing {field}"
            # Epistemics
            assert "epistemics" in dev_data
            ep = dev_data["epistemics"]
            for arr in ("supported", "inferred", "speculative", "unknown",
                        "assumptions", "evidence_needed"):
                assert arr in ep, f"epistemics missing {arr}"

    def test_sample_review_schema(self):
        """Sample review.json has full pizm-review-v1 field set."""
        if not SAMPLE_DIR.exists():
            pytest.skip("permanent sample not yet generated")
        manifest = json.loads((SAMPLE_DIR / "manifest.json").read_text())
        deep_stage = next(s for s in manifest["stages"] if s.startswith("deep-"))
        rev_path = SAMPLE_DIR / deep_stage / "review.json"
        rev = json.loads(rev_path.read_text())
        assert rev["schema_version"] == "pizm-review-v1"
        assert rev["stage"] == "deep"
        assert "frozen_hash" in rev and len(rev["frozen_hash"]) == 64
        assert rev["terminal_state"] in ("MODEL_READY", "NEED_EVIDENCE", "RETURN_TO_EXPLORE")
        assert isinstance(rev["identity_verified"], bool)
        assert "findings" in rev
        f = rev["findings"]
        for field in ("identity_drift", "model_assessment", "objection_assessment",
                      "epistemic_assessment", "evidence_gaps"):
            assert field in f, f"findings missing {field}"
        assert "verdict_rationale" in rev and isinstance(rev["verdict_rationale"], str)

    def test_sample_sidecars_match_artifacts(self):
        """Sample .sha256 sidecars contain correct hashes for their artifacts."""
        if not SAMPLE_DIR.exists():
            pytest.skip("permanent sample not yet generated")
        manifest = json.loads((SAMPLE_DIR / "manifest.json").read_text())
        for stage in manifest["stages"]:
            stage_dir = SAMPLE_DIR / stage
            if stage.startswith("pass-"):
                artifact = stage_dir / "candidates.json"
                sidecar = stage_dir / "candidates.sha256"
            else:
                artifact = stage_dir / "development.json"
                sidecar = stage_dir / "development.sha256"
            expected = hashlib.sha256(artifact.read_bytes()).hexdigest()
            actual = sidecar.read_text(encoding="utf-8").strip()
            assert actual == expected, (
                f"Sidecar hash mismatch for {stage}: expected {expected}, got {actual}"
            )

# ---------------------------------------------------------------------------
# Selector Diagnostics Tests (R1.6)
# ---------------------------------------------------------------------------


class TestSelectorDiagnostics:
    """Tests for post-hoc deterministic selector diagnostics."""

    def test_bundle_computes_selector_diagnostics(self, workspace):
        """Bundle computes diagnostics for explore stage and embeds in manifest."""
        structured_selection = {
            "schema_version": "pizm-selection-v1",
            "stage": "explore",
            "mode": "NORMAL",
            "frozen_hash": "a" * 64,
            "dispositions": [
                {
                    "candidate_id": "c1",
                    "disposition": "KEEP",
                    "standalone_quality": "strong",
                    "marginal_contribution": "high",
                    "reason": "Novel mechanism",
                },
                {
                    "candidate_id": "c2",
                    "disposition": "BORDERLINE",
                    "standalone_quality": "borderline",
                    "marginal_contribution": "medium",
                    "reason": "Conventional angle",
                },
                {
                    "candidate_id": "c3",
                    "disposition": "MERGE",
                    "standalone_quality": "strong",
                    "marginal_contribution": "medium",
                    "reason": "Merge into c1",
                },
                {
                    "candidate_id": "c4",
                    "disposition": "DROP",
                    "standalone_quality": "weak",
                    "marginal_contribution": "none",
                    "reason": "Generic platitude",
                },
            ],
            "kept": ["c1"],
            "merged": [{"target": "c1", "sources": ["c3"]}],
            "next_free_p": "P2",
        }
        (workspace["explore"] / "selection.json").write_text(
            json.dumps(structured_selection, indent=2), encoding="utf-8"
        )
        candidates = {
            "schema_version": "pizm-candidates-v1",
            "stage": "explore",
            "mode": "NORMAL",
            "candidates": [
                {"candidate_id": f"c{i}", "title": f"Idea {i}"}
                for i in range(1, 5)
            ],
        }
        cand_bytes = json.dumps(candidates, indent=2).encode("utf-8")
        (workspace["explore"] / "candidates.json").write_bytes(cand_bytes)
        (workspace["explore"] / "candidates.sha256").write_text(_sha256_hex(cand_bytes))

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "diag-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )

        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-diag-test"
        manifest = json.loads((bundle / "manifest.json").read_text())

        assert "diagnostics" in manifest
        assert "pass-01-normal" in manifest["diagnostics"]
        diag = manifest["diagnostics"]["pass-01-normal"]

        assert diag["candidate_count"] == 4
        assert diag["keep_count"] == 1
        assert diag["borderline_count"] == 1
        assert diag["merge_count"] == 1
        assert diag["drop_count"] == 1
        assert diag["disposition_distribution"] == {
            "KEEP": 1,
            "BORDERLINE": 1,
            "MERGE": 1,
            "DROP": 1,
        }
        assert diag["duplicate_or_merge_count"] == 1
        assert diag["serialized_candidates_bytes"] == len(cand_bytes)
        assert diag["serialized_selection_bytes"] == len(
            json.dumps(structured_selection, indent=2).encode("utf-8")
        )

        diag_file = bundle / "pass-01-normal" / "diagnostics.json"
        assert diag_file.exists()
        assert json.loads(diag_file.read_text()) == diag
        assert "pass-01-normal/diagnostics.json" in manifest["artifacts"]
        assert manifest["artifacts"]["pass-01-normal/diagnostics.json"] == _sha256_hex(diag_file.read_bytes())


# ---------------------------------------------------------------------------
# Lever stages and terminal-state validation (R2)
# ---------------------------------------------------------------------------


class TestLeverBundlingAndTerminalState:
    def test_bundle_lever_stage_success(self, workspace):
        """Bundle handles lever-P<id> stage with design and review artifacts."""
        lever_dir = workspace["tmp"] / "run-lever-P1"
        lever_dir.mkdir()
        design_data = {
            "schema_version": "pizm-lever-design-v1",
            "stage": "lever",
            "levers": [{"lever_id": "L1", "intervention_or_test_point": "Test point"}],
        }
        design_bytes = json.dumps(design_data).encode("utf-8")
        (lever_dir / "design.json").write_bytes(design_bytes)
        (lever_dir / "design.sha256").write_text(_sha256_hex(design_bytes))

        review_data = {
            "schema_version": "pizm-lever-review-v1",
            "stage": "lever",
            "frozen_hash": _sha256_hex(design_bytes),
            "outcome": "LEVER",
        }
        review_bytes = json.dumps(review_data).encode("utf-8")
        (lever_dir / "review.json").write_bytes(review_bytes)
        (lever_dir / "review.sha256").write_text(_sha256_hex(review_bytes))

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "lever-bundle-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"lever-P1={lever_dir}",
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-lever-bundle-test"
        assert (bundle / "lever-P1" / "design.json").exists()
        assert (bundle / "lever-P1" / "review.json").exists()
        manifest = json.loads((bundle / "manifest.json").read_text())
        assert "lever-P1" in manifest["stages"]

    def test_bundle_validates_terminal_state_valid(self, workspace):
        """Review artifacts with valid terminal_state (MODEL_READY) bundle without error."""
        review_data = {
            "schema_version": "pizm-review-v1",
            "terminal_state": "MODEL_READY",
            "stage": "deep",
        }
        (workspace["deep"] / "review.json").write_text(json.dumps(review_data))

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "ts-valid-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"deep-P1={workspace['deep']}",
        )
        assert r.returncode == 0, r.stderr

    def test_bundle_validates_terminal_state_invalid_fails(self, workspace):
        """Review artifacts with malformed terminal_state cause bundle error exit 1."""
        review_data = {
            "schema_version": "pizm-review-v1",
            "terminal_state": "INVALID_STATE",
            "stage": "deep",
        }
        (workspace["deep"] / "review.json").write_text(json.dumps(review_data))

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "ts-invalid-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"deep-P1={workspace['deep']}",
        )
        assert r.returncode != 0
        assert "invalid terminal_state 'INVALID_STATE'" in r.stderr


class TestAutoSelectionValidation:
    def test_auto_selection_valid_bundles_ok(self, workspace):
        """Valid pizm-auto-selection-v1 selection artifact bundles without error."""
        sel_data = {
            "schema_version": "pizm-auto-selection-v1",
            "stage": "explore",
            "mode": "NORMAL",
            "frozen_hash": (workspace["explore"] / "candidates.sha256").read_text().strip(),
            "dispositions": [
                {
                    "candidate_id": "c1",
                    "disposition": "KEEP",
                    "standalone_quality": "strong",
                    "marginal_contribution": "high",
                    "reason": "Clear mechanism",
                },
                {
                    "candidate_id": "c2",
                    "disposition": "DROP",
                    "standalone_quality": "weak",
                    "marginal_contribution": "none",
                    "reason": "Weak grounding",
                },
            ],
            "kept": ["c1"],
            "merged": [],
            "next_free_p": "P2",
            "auto_primary_candidate_id": "c1",
            "task_orientation": "ACTION_OR_DECISION",
        }
        (workspace["explore"] / "selection.json").write_text(json.dumps(sel_data))
        acc_file = workspace["tmp"] / "auto_acc.json"
        acc_file.write_text(json.dumps({"host_inference_count": 1, "model_repair_count": 0, "checkpoint_retry_count": 0}))

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "auto-sel-valid-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
            "--accounting", str(acc_file),
        )
        assert r.returncode == 0, r.stderr

    def test_auto_selection_missing_primary_fails(self, workspace):
        """Missing auto_primary_candidate_id triggers BAD_AUTO_SELECTION error."""
        sel_data = {
            "schema_version": "pizm-auto-selection-v1",
            "stage": "explore",
            "mode": "NORMAL",
            "dispositions": [
                {"candidate_id": "c1", "disposition": "KEEP"},
            ],
            "kept": ["c1"],
            "task_orientation": "ANALYTICAL",
        }
        (workspace["explore"] / "selection.json").write_text(json.dumps(sel_data))

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "auto-sel-missing-primary",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode != 0
        assert "BAD_AUTO_SELECTION" in r.stderr

    def test_auto_selection_primary_not_kept_fails(self, workspace):
        """Candidate not in kept list triggers BAD_AUTO_SELECTION error."""
        sel_data = {
            "schema_version": "pizm-auto-selection-v1",
            "stage": "explore",
            "mode": "NORMAL",
            "dispositions": [
                {"candidate_id": "c1", "disposition": "KEEP"},
                {"candidate_id": "c2", "disposition": "DROP"},
            ],
            "kept": ["c1"],
            "auto_primary_candidate_id": "c2",
            "task_orientation": "ANALYTICAL",
        }
        (workspace["explore"] / "selection.json").write_text(json.dumps(sel_data))

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "auto-sel-not-kept",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode != 0
        assert "BAD_AUTO_SELECTION" in r.stderr

    def test_auto_selection_invalid_task_orientation_fails(self, workspace):
        """Invalid task_orientation enum triggers BAD_AUTO_SELECTION error."""
        sel_data = {
            "schema_version": "pizm-auto-selection-v1",
            "stage": "explore",
            "mode": "NORMAL",
            "dispositions": [
                {"candidate_id": "c1", "disposition": "KEEP"},
            ],
            "kept": ["c1"],
            "auto_primary_candidate_id": "c1",
            "task_orientation": "INVALID_CHOICE",
        }
        (workspace["explore"] / "selection.json").write_text(json.dumps(sel_data))

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "auto-sel-bad-orientation",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode != 0
        assert "BAD_AUTO_SELECTION" in r.stderr


# ---------------------------------------------------------------------------
# 6-counter accounting contract and validation tests (§1.6)
# ---------------------------------------------------------------------------


class TestAccountingValidation:
    def test_six_counter_manifest_and_ephemeral_accounting(self, workspace):
        """Accounting produces exact 6-counter manifest and is NOT copied to archive inputs."""
        acc_file = workspace["tmp"] / "accounting.json"
        acc_data = {
            "host_inference_count": 5,
            "model_repair_count": 1,
            "checkpoint_retry_count": 0,
        }
        acc_file.write_text(json.dumps(acc_data), encoding="utf-8")

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "acc-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
            "--accounting", str(acc_file),
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-acc-test"
        manifest = json.loads((bundle / "manifest.json").read_text())

        # Exact 6 keys in accounting manifest
        assert "accounting" in manifest
        acc_manifest = manifest["accounting"]
        expected_keys = {
            "semantic_stage_count",
            "host_inference_count",
            "model_repair_count",
            "checkpoint_retry_count",
            "candidate_bytes",
            "development_bytes",
        }
        assert set(acc_manifest.keys()) == expected_keys
        assert acc_manifest["semantic_stage_count"] == 1
        assert acc_manifest["host_inference_count"] == 5
        assert acc_manifest["model_repair_count"] == 1
        assert acc_manifest["checkpoint_retry_count"] == 0
        cand_bytes = (workspace["explore"] / "candidates.json").stat().st_size
        assert acc_manifest["candidate_bytes"] == cand_bytes
        assert acc_manifest["development_bytes"] == 0

        # Ephemeral accounting file is NOT copied into inputs/
        assert not (bundle / "inputs" / "accounting.json").exists()
        for inp in manifest.get("inputs", []):
            assert "accounting" not in inp["filename"]

    def test_derived_counter_mismatch_fails(self, workspace):
        """Caller supplying mismatched derived counter (e.g. semantic_stage_count) causes failure."""
        acc_file = workspace["tmp"] / "bad_acc.json"
        acc_data = {
            "host_inference_count": 3,
            "model_repair_count": 0,
            "checkpoint_retry_count": 0,
            "semantic_stage_count": 99,  # Mismatch: actual is 1
        }
        acc_file.write_text(json.dumps(acc_data), encoding="utf-8")

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "acc-mismatch",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
            "--accounting", str(acc_file),
        )
        assert r.returncode != 0
        assert "semantic_stage_count mismatch" in r.stderr

    def test_invalid_external_counter_values_fail(self, workspace):
        """Negative integer or boolean in accounting counter triggers failure."""
        acc_file = workspace["tmp"] / "neg_acc.json"
        acc_data = {
            "host_inference_count": -1,
            "model_repair_count": 0,
            "checkpoint_retry_count": 0,
        }
        acc_file.write_text(json.dumps(acc_data), encoding="utf-8")

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "acc-neg",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
            "--accounting", str(acc_file),
        )
        assert r.returncode != 0
        assert "non-negative integer" in r.stderr

    def test_extra_unknown_accounting_keys_fail(self, workspace):
        """Extra unrecognized keys in accounting JSON cause failure."""
        acc_file = workspace["tmp"] / "extra_acc.json"
        acc_data = {
            "host_inference_count": 1,
            "model_repair_count": 0,
            "checkpoint_retry_count": 0,
            "unrecognized_counter": 123,
        }
        acc_file.write_text(json.dumps(acc_data), encoding="utf-8")

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "acc-extra",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
            "--accounting", str(acc_file),
        )
        assert r.returncode != 0
        assert "extra keys" in r.stderr

    def test_auto_requires_accounting(self, workspace):
        """AUTO stage without --accounting fails closed."""
        sel_data = {
            "schema_version": "pizm-auto-selection-v1",
            "stage": "explore",
            "mode": "NORMAL",
            "auto_primary_candidate_id": "c1",
            "kept": ["c1"],
            "dispositions": [{"candidate_id": "c1", "disposition": "KEEP"}],
            "task_orientation": "ANALYTICAL",
        }
        (workspace["explore"] / "selection.json").write_text(json.dumps(sel_data))

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "auto-no-acc",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={workspace['explore']}",
        )
        assert r.returncode != 0
        assert "accounting input is required for AUTO/BONK/FORGE/PACK" in r.stderr


# ---------------------------------------------------------------------------
# Forge v2 archive layout and allowlisted collection tests (§1.6)
# ---------------------------------------------------------------------------


class TestForgeV2ArchiveCollection:
    def test_forge_v2_target_layout_and_sidecar_meta_coverage(self, workspace):
        """Forge v2 target layout collects all allowlisted artifacts and excludes arbitrary lookalikes."""
        # Setup Forge stages
        # 1. Pass 1
        p1_dir = workspace["tmp"] / "pass01"
        p1_dir.mkdir()
        c1 = {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "NORMAL", "candidates": [{"candidate_id": "c01", "content": "P1"}]}
        c1_bytes = json.dumps(c1).encode()
        (p1_dir / "candidates.json").write_bytes(c1_bytes)
        (p1_dir / "candidates.sha256").write_text(_sha256_hex(c1_bytes))
        (p1_dir / "candidates.meta.json").write_text('{"stage":"explore"}')
        (p1_dir / "junk.txt").write_text("should not be copied")
        (p1_dir / "candidates_fake.json").write_text("fake candidate")

        # 2. Pass 2
        p2_dir = workspace["tmp"] / "pass02"
        p2_dir.mkdir()
        c2 = {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "360", "candidates": [{"candidate_id": "c01", "content": "P2"}]}
        c2_bytes = json.dumps(c2).encode()
        (p2_dir / "candidates-pass02.json").write_bytes(c2_bytes)
        (p2_dir / "candidates-pass02.sha256").write_text(_sha256_hex(c2_bytes))
        (p2_dir / "candidates-pass02.meta.json").write_text('{"stage":"explore","suffix":"pass02"}')

        # 3. Search field
        sf_dir = workspace["tmp"] / "sf"
        sf_dir.mkdir()
        sf = {"schema_version": "pizm-search-field-v1", "stage": "search-field", "passes": [], "entries": []}
        sf_bytes = json.dumps(sf).encode()
        (sf_dir / "search-field.json").write_bytes(sf_bytes)
        (sf_dir / "search-field.sha256").write_text(_sha256_hex(sf_bytes))
        (sf_dir / "search-field.meta.json").write_text('{"stage":"search-field"}')

        # 4. Portfolio
        port_dir = workspace["tmp"] / "port"
        port_dir.mkdir()
        port = {"schema_version": "pizm-portfolio-selection-v1", "stage": "portfolio", "route": "AUTO", "auto_target": {"target_type": "B", "target_id": "B1"}}
        port_bytes = json.dumps(port).encode()
        (port_dir / "portfolio.json").write_bytes(port_bytes)
        (port_dir / "portfolio.sha256").write_text(_sha256_hex(port_bytes))
        (port_dir / "portfolio.meta.json").write_text('{"stage":"portfolio"}')

        # 5. Deep B1
        db1_dir = workspace["tmp"] / "db1"
        db1_dir.mkdir()
        db1 = {"schema_version": "pizm-development-v2", "stage": "development-v2", "target": {"target_type": "B", "target_id": "B1"}}
        db1_bytes = json.dumps(db1).encode()
        (db1_dir / "development-v2-B1.json").write_bytes(db1_bytes)
        (db1_dir / "development-v2-B1.sha256").write_text(_sha256_hex(db1_bytes))
        (db1_dir / "development-v2-B1.meta.json").write_text('{"stage":"development-v2","target":"B1"}')
        (db1_dir / "review.json").write_text('{"terminal_state":"MODEL_READY"}')
        (db1_dir / "review.sha256").write_text(_sha256_hex(b'{"terminal_state":"MODEL_READY"}'))

        # 6. Deep B2
        db2_dir = workspace["tmp"] / "db2"
        db2_dir.mkdir()
        db2 = {"schema_version": "pizm-development-v2", "stage": "development-v2", "target": {"target_type": "B", "target_id": "B2"}}
        db2_bytes = json.dumps(db2).encode()
        (db2_dir / "development-v2-B2.json").write_bytes(db2_bytes)
        (db2_dir / "development-v2-B2.sha256").write_text(_sha256_hex(db2_bytes))
        (db2_dir / "development-v2-B2.meta.json").write_text('{"stage":"development-v2","target":"B2"}')
        (db2_dir / "review.json").write_text('{"terminal_state":"MODEL_READY"}')
        (db2_dir / "review.sha256").write_text(_sha256_hex(b'{"terminal_state":"MODEL_READY"}'))

        # 7. Comparison Review
        comp_dir = workspace["tmp"] / "comp"
        comp_dir.mkdir()
        comp = {
            "schema_version": "pizm-comparison-review-v1",
            "stage": "comparison-review-v1",
            "left_target_id": "B1",
            "right_target_id": "B2",
            "left_review": {
                "target_id": "B1",
                "development_ref": "development-v2-B1.json",
                "frozen_hash": _sha256_hex(db1_bytes),
                "terminal_state": "MODEL_READY",
                "independent_countermodel": "cm1",
                "load_bearing_reassessment": [{"claim": "c1", "critic_epistemic_status": "SUPPORTED"}],
                "findings": {"unresolved_load_bearing_contradiction": False},
            },
            "right_review": {
                "target_id": "B2",
                "development_ref": "development-v2-B2.json",
                "frozen_hash": _sha256_hex(db2_bytes),
                "terminal_state": "MODEL_READY",
                "independent_countermodel": "cm2",
                "load_bearing_reassessment": [{"claim": "c2", "critic_epistemic_status": "SUPPORTED"}],
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
        comp_bytes = json.dumps(comp).encode()
        (comp_dir / "comparison-review-v1.json").write_bytes(comp_bytes)
        (comp_dir / "comparison-review-v1.sha256").write_text(_sha256_hex(comp_bytes))
        (comp_dir / "comparison-review-v1.meta.json").write_text('{"stage":"comparison-review-v1"}')

        acc_file = workspace["tmp"] / "forge_acc.json"
        acc_file.write_text(json.dumps({
            "host_inference_count": 7,
            "model_repair_count": 0,
            "checkpoint_retry_count": 0,
        }))

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "forge-v2-bundle",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={p1_dir}",
            "--stage", f"pass-02-residual={p2_dir}",
            "--stage", f"search-field={sf_dir}",
            "--stage", f"portfolio={port_dir}",
            "--stage", f"deep-B1={db1_dir}",
            "--stage", f"deep-B2={db2_dir}",
            "--stage", f"comparison-review={comp_dir}",
            "--accounting", str(acc_file),
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-forge-v2-bundle"
        assert bundle.is_dir()

        # Verify all expected artifacts, sidecars, and metadata exist in bundle
        assert (bundle / "pass-01-normal" / "candidates.json").exists()
        assert (bundle / "pass-01-normal" / "candidates.sha256").exists()
        assert (bundle / "pass-01-normal" / "candidates.meta.json").exists()
        assert (bundle / "pass-02-residual" / "candidates-pass02.json").exists()
        assert (bundle / "pass-02-residual" / "candidates-pass02.sha256").exists()
        assert (bundle / "pass-02-residual" / "candidates-pass02.meta.json").exists()
        assert (bundle / "search-field" / "search-field.json").exists()
        assert (bundle / "portfolio" / "portfolio.json").exists()
        assert (bundle / "deep-B1" / "development-v2-B1.json").exists()
        assert (bundle / "deep-B2" / "development-v2-B2.json").exists()
        assert (bundle / "comparison-review" / "comparison-review-v1.json").exists()

        # Verify arbitrary lookalike / non-allowlisted files are NOT copied
        assert not (bundle / "pass-01-normal" / "junk.txt").exists()
        assert not (bundle / "pass-01-normal" / "candidates_fake.json").exists()

        # Verify 6 accounting counters in manifest
        manifest = json.loads((bundle / "manifest.json").read_text())
        assert manifest["accounting"]["semantic_stage_count"] == 6
        assert manifest["accounting"]["candidate_bytes"] == len(c1_bytes) + len(c2_bytes)
        assert manifest["accounting"]["development_bytes"] == len(db1_bytes) + len(db2_bytes)

    def test_missing_or_tampered_sidecar_fails_before_publish(self, workspace):
        """Tampered sidecar fails bundle creation and leaves no published bundle directory."""
        p1_dir = workspace["tmp"] / "tampered_pass01"
        p1_dir.mkdir()
        c1 = {"schema_version": "pizm-candidates-v1", "stage": "explore"}
        (p1_dir / "candidates.json").write_text(json.dumps(c1))
        (p1_dir / "candidates.sha256").write_text("bad" * 21 + "a")
        (p1_dir / "selection.json").write_text('{"selected":"c1"}')

        acc_file = workspace["tmp"] / "acc.json"
        acc_file.write_text(json.dumps({"host_inference_count": 1, "model_repair_count": 0, "checkpoint_retry_count": 0}))

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "tampered-bundle",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={p1_dir}",
            "--accounting", str(acc_file),
        )
        assert r.returncode != 0
        assert "hash mismatch" in r.stderr.lower()
        assert not (workspace["output"] / "session-tampered-bundle").exists()


def test_render_gather_information_as_intentional_terminal(tmp_path):
    """Rendering an AUTO run that stopped at Portfolio with GATHER_INFORMATION produces clean terminal output."""
    run_dir = tmp_path / "run-gather-terminal"
    run_dir.mkdir()
    cands = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "Model 1",
                "semantic_core": {
                    "claim": "Core claim",
                    "structural_shift": "Shift",
                    "mechanism": "Mechanism",
                    "grounding_anchor": "Anchor",
                    "what_becomes_visible": "Visible",
                    "boundary": "Limit",
                },
                "epistemics": {"supported": ["Fact 1"], "inferred": [], "speculative": [], "unknown": []},
            }
        ],
    }
    c_bytes = json.dumps(cands).encode("utf-8")
    (run_dir / "candidates.json").write_bytes(c_bytes)
    (run_dir / "candidates.sha256").write_text(_sha256_hex(c_bytes))

    port = {
        "schema_version": "pizm-portfolio-selection-v1",
        "stage": "portfolio",
        "route": "AUTO",
        "field_hash": _sha256_hex(c_bytes),
        "candidate_assessments": [
            {
                "candidate_ref": "pass01:c01",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "Residue 1",
                "nearest_overlap": None,
                "reason": "Grounded",
            }
        ],
        "bundles": [],
        "next_reasoning_move": "GATHER_INFORMATION",
        "next_reasoning_rationale": "Missing specific customer latency targets.",
        "auto_target": None,
        "information_request": {
            "mode": "USER_QUESTION",
            "missing_information": "Target latency SLA",
            "why_it_changes_route": "Determines whether caching or sharding is required",
            "questions": ["What is the target latency SLA?"],
            "suggested_observation": None,
        },
        "rival_shadow": None,
    }
    p_bytes = json.dumps(port).encode("utf-8")
    (run_dir / "portfolio.json").write_bytes(p_bytes)
    (run_dir / "portfolio.sha256").write_text(_sha256_hex(p_bytes))

    out_md = tmp_path / "run.md"
    res = run_bundle("render", "--run-dir", str(run_dir), "--task", "Analyze latency architecture", "--output", str(out_md))
    assert res.returncode == 0, res.stderr
    content = out_md.read_text(encoding="utf-8")
    assert "Terminal state: GATHER_INFORMATION" in content
    assert "What is the target latency SLA?" in content
    assert "Honest stop: GATHER_INFORMATION" in content
    assert "## Deep" not in content
    assert "## Critic" not in content


def test_render_auto_exhausted_rift_pass_reports_the_limit(tmp_path):
    """An AUTO RIFT pass that found nothing renders its honest limit instead of
    failing the render (the frozen pass carries the reason)."""
    run_dir = tmp_path / "run-exhausted-rift"
    run_dir.mkdir()
    cands = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "Model 1",
                "semantic_core": {
                    "claim": "Core claim",
                    "structural_shift": "Shift",
                    "mechanism": "Mechanism",
                    "grounding_anchor": "Anchor",
                    "what_becomes_visible": "Visible",
                    "boundary": "Limit",
                },
                "epistemics": {"supported": ["Fact 1"], "inferred": [], "speculative": [], "unknown": []},
            }
        ],
    }
    c1_bytes = json.dumps(cands).encode("utf-8")
    (run_dir / "candidates.json").write_bytes(c1_bytes)
    (run_dir / "candidates.sha256").write_text(_sha256_hex(c1_bytes))

    pass2 = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "RIFT",
        "candidates": [],
        "exhaustion_reason": "The material cannot support a meaningful rift.",
    }
    c2_bytes = json.dumps(pass2).encode("utf-8")
    (run_dir / "candidates-pass02.json").write_bytes(c2_bytes)
    (run_dir / "candidates-pass02.sha256").write_text(_sha256_hex(c2_bytes))

    port = {
        "schema_version": "pizm-portfolio-selection-v1",
        "stage": "portfolio",
        "route": "AUTO",
        "field_hash": _sha256_hex(c1_bytes),
        "candidate_assessments": [
            {
                "candidate_ref": "pass01:c01",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "Residue 1",
                "nearest_overlap": None,
                "reason": "Grounded",
            }
        ],
        "bundles": [],
        "next_reasoning_move": "PRESERVE_ONLY",
        "next_reasoning_rationale": "The second pass found no further grounded territory.",
        "auto_target": None,
        "information_request": None,
        "rival_shadow": None,
    }
    p_bytes = json.dumps(port).encode("utf-8")
    (run_dir / "portfolio.json").write_bytes(p_bytes)
    (run_dir / "portfolio.sha256").write_text(_sha256_hex(p_bytes))

    out_md = tmp_path / "run.md"
    res = run_bundle("render", "--run-dir", str(run_dir), "--task", "Exhausted rift task",
                     "--output", str(out_md))
    assert res.returncode == 0, res.stderr
    content = out_md.read_text(encoding="utf-8")
    assert "## Search Pass 2" in content
    assert "Search policy: rift pass (RIFT)." in content
    assert "No additional grounded territory found." in content
    assert "The material cannot support a meaningful rift." in content


def test_render_html_with_ensure_reader_fallback(tmp_path):
    """When reader server cannot start, render-html --ensure-reader outputs READER_OFFLINE and returns 0."""
    run_dir = tmp_path / "run-fallback-test"
    run_dir.mkdir()
    # Minimal candidates file for valid run
    cand = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "C1",
                "semantic_core": {"claim": "c", "structural_shift": "s", "mechanism": "m", "grounding_anchor": "a", "what_becomes_visible": "v", "boundary": "b"},
                "epistemics": {"supported": ["s"], "inferred": [], "speculative": [], "unknown": []},
            }
        ],
    }
    c_bytes = json.dumps(cand).encode("utf-8")
    (run_dir / "candidates-pass01.json").write_bytes(c_bytes)
    (run_dir / "candidates-pass01.sha256").write_text(_sha256_hex(c_bytes))

    out_html = tmp_path / "run.html"
    # Port 1 is reserved and will fail to bind, exercising deterministic fallback
    res = run_bundle(
        "render-html",
        "--run-dir", str(run_dir),
        "--output", str(out_html),
        "--ensure-reader",
        "--port", "1",
    )
    assert res.returncode == 0, res.stderr
    assert out_html.is_file()
    assert "RENDER_HTML_OK" in res.stdout
    assert "READER_OFFLINE file://" in res.stdout
    assert "(local reader server inactive)" in res.stdout


def test_render_html_with_ensure_reader_canonical_e2e(tmp_path):
    """Canonical E2E: <project>/.ai/pizm/run-foo/ with default root/output -> ensure -> GET returns 200 with HTML."""
    import socket
    import urllib.request
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    free_port = sock.getsockname()[1]
    sock.close()

    # Canonical project layout
    project = tmp_path / "my_project"
    pizm_root = project / ".ai" / "pizm"
    run_dir = pizm_root / "run-canonical77"
    run_dir.mkdir(parents=True)

    cand = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "Canonical Seed Alpha",
                "semantic_core": {"claim": "Unique Mechanism", "structural_shift": "Shift", "mechanism": "Mech", "grounding_anchor": "Anchor", "what_becomes_visible": "Vis", "boundary": "Bound"},
                "epistemics": {"supported": ["Fact"], "inferred": [], "speculative": [], "unknown": []},
            }
        ],
    }
    c_bytes = json.dumps(cand).encode("utf-8")
    (run_dir / "candidates-pass01.json").write_bytes(c_bytes)
    sf_hash = _sha256_hex(c_bytes)
    (run_dir / "candidates-pass01.sha256").write_text(sf_hash)

    port = {
        "schema_version": "pizm-portfolio-selection-v1",
        "stage": "portfolio",
        "route": "AUTO",
        "field_hash": sf_hash,
        "candidate_assessments": [{"candidate_ref": "pass01:c01", "disposition": "KEEP"}],
        "perspectives": {"P1": "pass01:c01"},
        "auto_target": {"target_type": "P", "target_id": "P1"},
    }
    p_bytes = json.dumps(port).encode("utf-8")
    (run_dir / "portfolio.json").write_bytes(p_bytes)
    (run_dir / "portfolio.sha256").write_text(_sha256_hex(p_bytes))
    reader_cli = str(REPO_ROOT / "bin" / "pizm-reader-server")
    try:
        # Run render-html with --ensure-reader WITHOUT --root or --output
        res = run_bundle(
            "render-html",
            "--run-dir", str(run_dir),
            "--ensure-reader",
            "--port", str(free_port),
        )
        assert res.returncode == 0, res.stderr
        expected_html = run_dir / "run.html"
        assert expected_html.is_file()
        assert "RENDER_HTML_OK" in res.stdout
        expected_url = f"http://127.0.0.1:{free_port}/run/canonical77/"
        assert f"READER_URL {expected_url}" in res.stdout

        # Real HTTP GET to the printed URL: must return 200 and exact rendered run content
        with urllib.request.urlopen(expected_url, timeout=3.0) as resp:
            assert resp.status == 200
            body = resp.read().decode("utf-8")
            assert "<!DOCTYPE html>" in body
            assert "Canonical Seed Alpha" in body
            assert resp.headers.get("Cache-Control") == "no-store"
    finally:
        subprocess.run([sys.executable, reader_cli, "stop", "--port", str(free_port), "--root", str(pizm_root)], capture_output=True)


# ---------------------------------------------------------------------------
# GATE1-REPAIR: live-path subject-slug named records
# ---------------------------------------------------------------------------


def _g1_subject_run(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    cand = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "C1",
                "semantic_core": {"claim": "c", "structural_shift": "s", "mechanism": "m", "grounding_anchor": "a", "what_becomes_visible": "v", "boundary": "b"},
                "epistemics": {"supported": ["s"], "inferred": [], "speculative": [], "unknown": []},
            }
        ],
    }
    c_bytes = json.dumps(cand).encode("utf-8")
    (root / "candidates-pass01.json").write_bytes(c_bytes)
    (root / "candidates-pass01.sha256").write_text(_sha256_hex(c_bytes))
    port = {
        "schema_version": "pizm-portfolio-selection-v1",
        "stage": "portfolio",
        "route": "AUTO",
        "field_hash": _sha256_hex(c_bytes),
        "candidate_assessments": [
            {
                "candidate_ref": "pass01:c01",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "Residue 1",
                "nearest_overlap": None,
                "reason": "Grounded",
            }
        ],
        "bundles": [],
        "next_reasoning_move": "GATHER_INFORMATION",
        "next_reasoning_rationale": "Missing specific customer latency targets.",
        "auto_target": None,
        "information_request": {
            "mode": "USER_QUESTION",
            "missing_information": "Target latency SLA",
            "why_it_changes_route": "Determines whether caching or sharding is required",
            "questions": ["What is the target latency SLA?"],
            "suggested_observation": None,
        },
        "rival_shadow": None,
    }
    p_bytes = json.dumps(port).encode("utf-8")
    (root / "portfolio.json").write_bytes(p_bytes)
    (root / "portfolio.sha256").write_text(_sha256_hex(p_bytes))
    return root


def test_g1_render_subject_slug_named_markdown_default(tmp_path):
    run_dir = _g1_subject_run(tmp_path / "run-naming-md")
    res = run_bundle("render", "--run-dir", str(run_dir), "--task", "Naming task", "--subject-slug", "Evo WTF Pikabu")
    assert res.returncode == 0, res.stderr
    assert (run_dir / "run-evo-wtf-pikabu.md").is_file()
    assert not (run_dir / "run.md").exists()
    custom = run_dir / "custom.md"
    res = run_bundle("render", "--run-dir", str(run_dir), "--task", "Naming task", "--subject-slug", "Evo WTF Pikabu", "--output", str(custom))
    assert res.returncode == 0, res.stderr
    assert custom.is_file()


def test_g1_render_html_subject_slug_named_html_default(tmp_path):
    run_dir = _g1_subject_run(tmp_path / "run-naming-html")
    res = run_bundle("render-html", "--run-dir", str(run_dir), "--task", "Naming task", "--subject-slug", "Nerat DTF")
    assert res.returncode == 0, res.stderr
    assert (run_dir / "run-nerat-dtf.html").is_file()
    assert not (run_dir / "run.html").exists()


# ---------------------------------------------------------------------------
# GATE1F-ITER2 D1: host-supplied provider/model composite normalized at capture
# ---------------------------------------------------------------------------


def test_g1f_composite_host_identity_split_in_live_manifest(workspace):
    """Regression: BONK live path delivered `provider/model` in the model field
    with provider lost (header `composite / unknown`). Capture must hold them
    separately. FAILS pre-fix (fields-present-but-conflated must not pass)."""
    r = run_bundle(
        "create",
        "--output-root", str(workspace["output"]),
        "--slug", "composite-identity",
        "--skill-root", str(workspace["skill"]),
        "--stage", f"pass-01-normal={workspace['explore']}",
        "--stage", f"deep-P1={workspace['deep']}",
        "--model", "opencode-zen/muse-spark-1.3-test",
        "--model-source", "HOST_RUNTIME",
        "--evidence-kind", "live",
    )
    assert r.returncode == 0, r.stderr
    manifest = json.loads((workspace["output"] / "session-composite-identity" / "manifest.json").read_text())
    assert manifest["model"] == "muse-spark-1.3-test"
    assert manifest["provider"] == "opencode-zen"
    assert manifest["model_source"] == "HOST_RUNTIME"
    assert "/" not in manifest["model"]


def test_g1f_separate_identity_fields_untouched(workspace):
    """Explicitly separate provider/model pass through unchanged."""
    r = run_bundle(
        "create",
        "--output-root", str(workspace["output"]),
        "--slug", "separate-identity",
        "--skill-root", str(workspace["skill"]),
        "--stage", f"pass-01-normal={workspace['explore']}",
        "--model", "muse-spark-1.3-test",
        "--provider", "opencode-zen",
        "--evidence-kind", "live",
    )
    assert r.returncode == 0, r.stderr
    manifest = json.loads((workspace["output"] / "session-separate-identity" / "manifest.json").read_text())
    assert manifest["model"] == "muse-spark-1.3-test"
    assert manifest["provider"] == "opencode-zen"


# ---------------------------------------------------------------------------
# Label-Aware Artifact Selection in Shared Run Directories
# ---------------------------------------------------------------------------


class TestSharedRunDirLabelAwareBundling:
    """Verifies label-aware artifact selection when multiple stages point to a shared run_dir."""

    def _write_artifact(self, dir_path: Path, filename: str, content: dict) -> Path:
        f = dir_path / filename
        f.write_text(json.dumps(content, indent=2), encoding="utf-8")
        sha_f = dir_path / (filename.rsplit(".", 1)[0] + ".sha256")
        sha_f.write_text(_sha256_hex(f.read_bytes()), encoding="utf-8")
        return f

    def test_shared_run_dir_auto_bundle_label_aware(self, workspace, tmp_path):
        """AUTO shared run-dir: pass-01 and pass-02 select only their respective candidates; no duplicates."""
        run_dir = tmp_path / "shared_auto_run"
        run_dir.mkdir()

        # Write artifacts
        c1 = self._write_artifact(run_dir, "candidates-pass01.json", {
            "schema_version": "pizm-candidates-v1",
            "stage": "explore",
            "mode": "NORMAL",
            "candidates": [{"candidate_id": "c01", "title": "Pass 1 Seed", "core_claim": "C1", "structural_shift": "S1", "mechanism": "M1", "boundary": "B1"}],
        })
        c2 = self._write_artifact(run_dir, "candidates-pass02.json", {
            "schema_version": "pizm-candidates-v1",
            "stage": "explore",
            "mode": "RIFT",
            "candidates": [{"candidate_id": "c02", "title": "Pass 2 Seed", "core_claim": "C2", "structural_shift": "S2", "mechanism": "M2", "boundary": "B2"}],
        })
        c1_size = c1.stat().st_size
        c2_size = c2.stat().st_size

        self._write_artifact(run_dir, "search-field-pass01.json", {
            "schema_version": "pizm-search-field-v1", "stage": "search-field", "field_id": "sf1",
            "passes": [{"pass_id": "pass01", "candidates_ref": "candidates-pass01.json", "frozen_hash": "h1"}],
            "entries": ["pass01:c01"],
        })
        self._write_artifact(run_dir, "search-field-pass02.json", {
            "schema_version": "pizm-search-field-v1", "stage": "search-field", "field_id": "sf2",
            "passes": [
                {"pass_id": "pass01", "candidates_ref": "candidates-pass01.json", "frozen_hash": "h1"},
                {"pass_id": "pass02", "candidates_ref": "candidates-pass02.json", "frozen_hash": "h2"},
            ],
            "entries": ["pass01:c01", "pass02:c02"],
        })
        self._write_artifact(run_dir, "portfolio.json", {
            "schema_version": "pizm-portfolio-selection-v1", "stage": "portfolio", "route": "AUTO",
            "field_hash": "h_sf2",
            "candidate_assessments": [{"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "R1", "nearest_overlap": None, "reason": "Good"}],
            "bundles": [], "auto_target": {"target_type": "P", "target_id": "P1"}, "perspectives": {"P1": "pass01:c01"},
        })
        dev_file = self._write_artifact(run_dir, "development-v2-P1.json", {
            "schema_version": "pizm-development-v2", "stage": "development-v2",
            "target": {"target_type": "P", "target_id": "P1"},
            "identity_lock": {"p_id": "P1", "title": "P1 Title", "core_claim": "C1", "structural_shift": "S1", "mechanism": "M1", "boundary": "B1"},
            "developed_model": {"thesis": "T", "synthesis": "S", "dynamics": "D", "mechanism_chain": ["M"], "implications": ["I"], "predictions_or_observables": ["P"], "break_conditions": ["B"], "unresolved_tensions": ["U"], "evidence_debt": [], "load_bearing_claims": [], "development_delta": {"summary": "Init"}},
        })
        dev_size = dev_file.stat().st_size

        self._write_artifact(run_dir, "deep-review-v2-P1.json", {
            "schema_version": "pizm-deep-review-v2", "stage": "deep-review-v2",
            "terminal_state": "MODEL_READY", "verdict_rationale": "Solid", "evidence_debt": [],
        })
        # Accounting input for AUTO contract
        acc_file = tmp_path / "accounting_auto.json"
        acc_file.write_text(json.dumps({
            "host_inference_count": 5,
            "model_repair_count": 0,
            "checkpoint_retry_count": 0,
        }), encoding="utf-8")

        # Run bundle creation with multiple stages pointing to the shared run_dir
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "auto-shared-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--stage", f"deep-P1={run_dir}",
            "--accounting", str(acc_file),
        )
        bundle = workspace["output"] / "session-auto-shared-test"

        # Verify exact, non-duplicated file contents in stage directories
        pass1_files = {f.name for f in (bundle / "pass-01-normal").iterdir()}
        assert "candidates-pass01.json" in pass1_files
        assert "candidates-pass02.json" not in pass1_files, "pass-02 artifact leaked into pass-01 stage dir"

        pass2_files = {f.name for f in (bundle / "pass-02-rift").iterdir()}
        assert "candidates-pass02.json" in pass2_files
        assert "candidates-pass01.json" not in pass2_files, "pass-01 artifact leaked into pass-02 stage dir"

        deep_files = {f.name for f in (bundle / "deep-P1").iterdir()}
        assert "development-v2-P1.json" in deep_files
        assert "candidates-pass01.json" not in deep_files

        # Verify accounting in manifest: exact sum, no double counting
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["accounting"]["candidate_bytes"] == c1_size + c2_size, (
            f"candidate_bytes double-counted: expected {c1_size + c2_size}, got {manifest['accounting']['candidate_bytes']}"
        )
        assert manifest["accounting"]["development_bytes"] == dev_size
        assert manifest["accounting"]["semantic_stage_count"] == 5

    def test_shared_run_dir_bonk_two_deep_bundle_label_aware(self, workspace, tmp_path):
        """BONK shared run-dir: deep-B1 and deep-B2 select only their respective development artifacts."""
        run_dir = tmp_path / "shared_bonk_run"
        run_dir.mkdir()

        # Explore passes
        c1 = self._write_artifact(run_dir, "candidates-pass01.json", {
            "schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "NORMAL", "candidates": [{"candidate_id": "c01"}],
        })
        c2 = self._write_artifact(run_dir, "candidates-pass02.json", {
            "schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "360", "candidates": [{"candidate_id": "c02"}],
        })
        self._write_artifact(run_dir, "search-field-pass02.json", {
            "schema_version": "pizm-search-field-v1", "stage": "search-field", "field_id": "sf2",
            "passes": [{"pass_id": "pass01", "candidates_ref": "c1", "frozen_hash": "h1"}, {"pass_id": "pass02", "candidates_ref": "c2", "frozen_hash": "h2"}],
            "entries": ["pass01:c01", "pass02:c02"],
        })
        self._write_artifact(run_dir, "portfolio.json", {
            "schema_version": "pizm-portfolio-selection-v2", "stage": "portfolio", "route": "BONK",
            "field_hash": "h_sf2", "competition_status": "TWO_DEFENSIBLE_BUNDLES",
            "recommended_competition": {"left_bundle_id": "B1", "right_bundle_id": "B2", "competition_axis": "Axis", "discriminating_observation": "Obs", "discriminating_question": "Q"},
            "candidate_assessments": [], "bundles": [
                {"bundle_id": "B1", "member_refs": ["pass01:c01"], "bundle_thesis": "TB1", "composition_gain": "G1", "member_roles": {}, "member_ablation": {}, "internal_tension": "T1", "weakest_link": "W1", "new_consequence_or_prediction": "P1"},
                {"bundle_id": "B2", "member_refs": ["pass02:c02"], "bundle_thesis": "TB2", "composition_gain": "G2", "member_roles": {}, "member_ablation": {}, "internal_tension": "T2", "weakest_link": "W2", "new_consequence_or_prediction": "P2"},
            ],
            "perspectives": {"P1": "pass01:c01", "P2": "pass02:c02"},
        })

        # Deep B1 and Deep B2
        dev_b1 = self._write_artifact(run_dir, "development-v2-B1.json", {
            "schema_version": "pizm-development-v2", "stage": "development-v2",
            "target": {"target_type": "B", "target_id": "B1"},
            "identity_lock": {"bundle_id": "B1", "member_refs": ["pass01:c01"], "title": "B1", "core_claim": "CB1", "structural_shift": "SB1", "mechanism": "MB1", "boundary": "BB1"},
            "developed_model": {"thesis": "TB1", "synthesis": "S1", "dynamics": "D1", "mechanism_chain": ["M1"], "implications": [], "predictions_or_observables": [], "break_conditions": [], "unresolved_tensions": [], "evidence_debt": [], "load_bearing_claims": [], "development_delta": {"summary": "Init"}},
        })
        self._write_artifact(run_dir, "deep-review-v2-B1.json", {
            "schema_version": "pizm-deep-review-v2", "stage": "deep-review-v2",
            "terminal_state": "MODEL_READY", "verdict_rationale": "OK", "evidence_debt": [],
        })

        dev_b2 = self._write_artifact(run_dir, "development-v2-B2.json", {
            "schema_version": "pizm-development-v2", "stage": "development-v2",
            "target": {"target_type": "B", "target_id": "B2"},
            "identity_lock": {"bundle_id": "B2", "member_refs": ["pass02:c02"], "title": "B2", "core_claim": "CB2", "structural_shift": "SB2", "mechanism": "MB2", "boundary": "BB2"},
            "developed_model": {"thesis": "TB2", "synthesis": "S2", "dynamics": "D2", "mechanism_chain": ["M2"], "implications": [], "predictions_or_observables": [], "break_conditions": [], "unresolved_tensions": [], "evidence_debt": [], "load_bearing_claims": [], "development_delta": {"summary": "Init"}},
        })
        self._write_artifact(run_dir, "deep-review-v2-B2.json", {
            "schema_version": "pizm-deep-review-v2", "stage": "deep-review-v2",
            "terminal_state": "MODEL_READY", "verdict_rationale": "OK", "evidence_debt": [],
        })

        self._write_artifact(run_dir, "comparison-review-v1.json", {
            "schema_version": "pizm-comparison-review-v1", "stage": "comparison-review-v1",
            "left_target_id": "B1", "right_target_id": "B2",
            "left_review": {"target_id": "B1", "terminal_state": "MODEL_READY"},
            "right_review": {"target_id": "B2", "terminal_state": "MODEL_READY"},
            "comparison": {"current_preference": "LEFT", "competition_axis": "Axis", "strongest_reason_for_left": "R1", "strongest_reason_for_right": "R2", "discriminating_observation": "Obs", "what_would_change_the_decision": "Ev", "shared_evidence_debt": []},
        })

        b1_size = dev_b1.stat().st_size
        b2_size = dev_b2.stat().st_size

        # Accounting input for BONK contract
        acc_file = tmp_path / "accounting_bonk.json"
        acc_file.write_text(json.dumps({
            "host_inference_count": 7,
            "model_repair_count": 0,
            "checkpoint_retry_count": 0,
        }), encoding="utf-8")

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "bonk-shared-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--stage", f"deep-B1={run_dir}",
            "--stage", f"deep-B2={run_dir}",
            "--stage", f"comparison-review={run_dir}",
            "--accounting", str(acc_file),
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-bonk-shared-test"

        # Check stage separation: no cross-contamination between B1 and B2
        b1_files = {f.name for f in (bundle / "deep-B1").iterdir()}
        assert "development-v2-B1.json" in b1_files
        assert "development-v2-B2.json" not in b1_files, "B2 artifact leaked into deep-B1 stage dir"

        b2_files = {f.name for f in (bundle / "deep-B2").iterdir()}
        assert "development-v2-B2.json" in b2_files
        assert "development-v2-B1.json" not in b2_files, "B1 artifact leaked into deep-B2 stage dir"

        # Check accounting: exact sum, no double counting
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["accounting"]["development_bytes"] == b1_size + b2_size, (
            f"development_bytes double-counted: expected {b1_size + b2_size}, got {manifest['accounting']['development_bytes']}"
        )
        assert manifest["accounting"]["candidate_bytes"] == c1.stat().st_size + c2.stat().st_size
        assert manifest["accounting"]["semantic_stage_count"] == 8

    def test_shared_run_dir_bonk_comparison_lever_isolation(self, workspace, tmp_path):
        """BONK + LEVER shared run-dir: comparison-review and lever-B1 isolate each other's artifacts and sidecars."""
        run_dir = tmp_path / "shared_bonk_lever_run"
        run_dir.mkdir()

        # Explore passes
        c1 = self._write_artifact(run_dir, "candidates-pass01.json", {
            "schema_version": "pizm-candidates-v1",
            "stage": "explore",
            "mode": "NORMAL",
            "candidates": [{"candidate_id": "c01", "title": "Pass 1 Seed", "core_claim": "C1", "structural_shift": "S1", "mechanism": "M1", "boundary": "B1"}],
        })
        (run_dir / "candidates-pass01.meta.json").write_text('{"stage":"explore","suffix":"pass01"}', encoding="utf-8")

        c2 = self._write_artifact(run_dir, "candidates-pass02.json", {
            "schema_version": "pizm-candidates-v1",
            "stage": "explore",
            "mode": "360",
            "candidates": [{"candidate_id": "c02", "title": "Pass 2 Seed", "core_claim": "C2", "structural_shift": "S2", "mechanism": "M2", "boundary": "B2"}],
        })
        (run_dir / "candidates-pass02.meta.json").write_text('{"stage":"explore","suffix":"pass02"}', encoding="utf-8")

        # Search fields
        self._write_artifact(run_dir, "search-field-pass01.json", {
            "schema_version": "pizm-search-field-v1", "stage": "search-field", "field_id": "sf1",
            "passes": [{"pass_id": "pass01", "candidates_ref": "candidates-pass01.json", "frozen_hash": "h1"}],
            "entries": ["pass01:c01"],
        })
        (run_dir / "search-field-pass01.meta.json").write_text('{"stage":"search-field","suffix":"pass01"}', encoding="utf-8")

        self._write_artifact(run_dir, "search-field-pass02.json", {
            "schema_version": "pizm-search-field-v1", "stage": "search-field", "field_id": "sf2",
            "passes": [
                {"pass_id": "pass01", "candidates_ref": "candidates-pass01.json", "frozen_hash": "h1"},
                {"pass_id": "pass02", "candidates_ref": "candidates-pass02.json", "frozen_hash": "h2"},
            ],
            "entries": ["pass01:c01", "pass02:c02"],
        })
        (run_dir / "search-field-pass02.meta.json").write_text('{"stage":"search-field","suffix":"pass02"}', encoding="utf-8")

        # Portfolio (BONK route, TWO_DEFENSIBLE_BUNDLES)
        self._write_artifact(run_dir, "portfolio.json", {
            "schema_version": "pizm-portfolio-selection-v2", "stage": "portfolio", "route": "BONK",
            "field_hash": "h_sf2",
            "competition_status": "TWO_DEFENSIBLE_BUNDLES",
            "recommended_competition": {
                "left_bundle_id": "B1",
                "right_bundle_id": "B2",
                "competition_axis": "Axis",
                "why_both_merit_deep": "Reason",
            },
            "candidate_assessments": [
                {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "R1", "nearest_overlap": None, "reason": "Good"},
                {"candidate_ref": "pass02:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "R2", "nearest_overlap": None, "reason": "Good"},
            ],
            "bundles": [
                {"bundle_id": "B1", "title": "Bundle 1", "member_refs": ["pass01:c01"], "core_claim": "C1", "structural_shift": "S1", "compositional_thesis": "T1", "internal_tension": "I1", "synthesis_rationale": "SR1"},
                {"bundle_id": "B2", "title": "Bundle 2", "member_refs": ["pass02:c02"], "core_claim": "C2", "structural_shift": "S2", "compositional_thesis": "T2", "internal_tension": "I2", "synthesis_rationale": "SR2"},
            ],
            "perspectives": {"P1": "pass01:c01", "P2": "pass02:c02"},
        })
        (run_dir / "portfolio.meta.json").write_text('{"stage":"portfolio"}', encoding="utf-8")

        # Deep B1 & B2
        dev_b1 = self._write_artifact(run_dir, "development-v2-B1.json", {
            "schema_version": "pizm-development-v2", "stage": "development-v2",
            "target": {"target_type": "B", "target_id": "B1"},
            "identity_lock": {"bundle_id": "B1", "member_refs": ["pass01:c01"], "title": "B1 Title", "core_claim": "C1", "structural_shift": "S1", "mechanism": "M1", "boundary": "B1"},
            "developed_model": {"thesis": "T1", "synthesis": "S1", "dynamics": "D1", "mechanism_chain": ["M1"], "implications": ["I1"], "predictions_or_observables": ["P1"], "break_conditions": ["B1"], "unresolved_tensions": ["U1"], "evidence_debt": [], "load_bearing_claims": [], "development_delta": {"summary": "Init"}, "member_contributions": {"pass01:c01": "C1"}, "member_ablation": {"pass01:c01": "A1"}},
        })
        (run_dir / "development-v2-B1.meta.json").write_text('{"stage":"development-v2","target":"B1"}', encoding="utf-8")

        dev_b2 = self._write_artifact(run_dir, "development-v2-B2.json", {
            "schema_version": "pizm-development-v2", "stage": "development-v2",
            "target": {"target_type": "B", "target_id": "B2"},
            "identity_lock": {"bundle_id": "B2", "member_refs": ["pass02:c02"], "title": "B2 Title", "core_claim": "C2", "structural_shift": "S2", "mechanism": "M2", "boundary": "B2"},
            "developed_model": {"thesis": "T2", "synthesis": "S2", "dynamics": "D2", "mechanism_chain": ["M2"], "implications": ["I2"], "predictions_or_observables": ["P2"], "break_conditions": ["B2"], "unresolved_tensions": ["U2"], "evidence_debt": [], "load_bearing_claims": [], "development_delta": {"summary": "Init"}, "member_contributions": {"pass02:c02": "C2"}, "member_ablation": {"pass02:c02": "A2"}},
        })
        (run_dir / "development-v2-B2.meta.json").write_text('{"stage":"development-v2","target":"B2"}', encoding="utf-8")

        # Canonical Comparison Review
        self._write_artifact(run_dir, "comparison-review-v1.json", {
            "schema_version": "pizm-comparison-review-v1", "stage": "comparison-review-v1",
            "left_target_id": "B1", "right_target_id": "B2",
            "left_review": {"target_id": "B1", "terminal_state": "MODEL_READY"},
            "right_review": {"target_id": "B2", "terminal_state": "MODEL_READY"},
            "comparison": {"current_preference": "LEFT", "competition_axis": "Axis", "strongest_reason_for_left": "R1", "strongest_reason_for_right": "R2", "discriminating_observation": "Obs", "what_would_change_the_decision": "Ev", "shared_evidence_debt": []},
        })
        (run_dir / "comparison-review-v1.meta.json").write_text('{"stage":"comparison-review-v1"}', encoding="utf-8")

        # LEVER design and review in the same run_dir
        self._write_artifact(run_dir, "design.json", {
            "schema_version": "pizm-lever-design-v1",
            "stage": "lever",
            "levers": [{"lever_id": "L1", "intervention_or_test_point": "Test move"}],
        })
        (run_dir / "design.meta.json").write_text('{"stage":"lever-design"}', encoding="utf-8")

        design_bytes = (run_dir / "design.json").read_bytes()
        self._write_artifact(run_dir, "review.json", {
            "schema_version": "pizm-lever-review-v1",
            "stage": "lever",
            "frozen_hash": _sha256_hex(design_bytes),
            "outcome": "LEVER",
        })
        (run_dir / "review.meta.json").write_text('{"stage":"lever-review"}', encoding="utf-8")

        b1_size = dev_b1.stat().st_size
        b2_size = dev_b2.stat().st_size

        acc_file = tmp_path / "accounting_bonk_lever.json"
        acc_file.write_text(json.dumps({
            "host_inference_count": 9,
            "model_repair_count": 0,
            "checkpoint_retry_count": 0,
        }), encoding="utf-8")

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "bonk-lever-shared-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--stage", f"deep-B1={run_dir}",
            "--stage", f"deep-B2={run_dir}",
            "--stage", f"comparison-review={run_dir}",
            "--stage", f"lever-B1={run_dir}",
            "--accounting", str(acc_file),
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-bonk-lever-shared-test"

        # Bidirectional isolation assertions:
        # 1. Comparison must contain comparison artifacts and sidecars; NO lever artifacts
        comp_files = {f.name for f in (bundle / "comparison-review").iterdir()}
        assert "comparison-review-v1.json" in comp_files
        assert "comparison-review-v1.sha256" in comp_files
        assert "comparison-review-v1.meta.json" in comp_files
        assert "review.json" not in comp_files, "LEVER review.json leaked into comparison-review stage dir"
        assert "review.sha256" not in comp_files, "LEVER review.sha256 leaked into comparison-review stage dir"
        assert "review.meta.json" not in comp_files, "LEVER review.meta.json leaked into comparison-review stage dir"
        assert "design.json" not in comp_files, "LEVER design.json leaked into comparison-review stage dir"
        assert "design.sha256" not in comp_files, "LEVER design.sha256 leaked into comparison-review stage dir"
        assert "design.meta.json" not in comp_files, "LEVER design.meta.json leaked into comparison-review stage dir"

        # 2. LEVER must contain design and review artifacts and sidecars; NO comparison artifacts
        lever_files = {f.name for f in (bundle / "lever-B1").iterdir()}
        assert "design.json" in lever_files
        assert "design.sha256" in lever_files
        assert "design.meta.json" in lever_files
        assert "review.json" in lever_files
        assert "review.sha256" in lever_files
        assert "review.meta.json" in lever_files
        assert "comparison-review-v1.json" not in lever_files, "comparison-review-v1.json leaked into lever-B1 stage dir"
        assert "comparison-review-v1.sha256" not in lever_files, "comparison-review-v1.sha256 leaked into lever-B1 stage dir"
        assert "comparison-review-v1.meta.json" not in lever_files, "comparison-review-v1.meta.json leaked into lever-B1 stage dir"

        # 3. Derived accounting assertions: exact counts, no cross-contamination
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["accounting"]["development_bytes"] == b1_size + b2_size, (
            f"development_bytes mismatch: expected {b1_size + b2_size}, got {manifest['accounting']['development_bytes']}"
        )
        assert manifest["accounting"]["candidate_bytes"] == c1.stat().st_size + c2.stat().st_size
        assert manifest["accounting"]["semantic_stage_count"] == 8


# ---------------------------------------------------------------------------
# Semantic Stage Count Regressions (Wave 0 Artifact-Aware Counting)
# ---------------------------------------------------------------------------


class TestSemanticStageCountRegressions:
    """Verifies all 8 required semantic_stage_count regressions under the artifact-aware derivation."""

    def _write_artifact(self, dir_path: Path, filename: str, content: dict) -> Path:
        f = dir_path / filename
        f.write_text(json.dumps(content, indent=2), encoding="utf-8")
        sha_f = dir_path / (filename.rsplit(".", 1)[0] + ".sha256")
        sha_f.write_text(_sha256_hex(f.read_bytes()), encoding="utf-8")
        return f

    def test_regression_auto_search2_portfolio_deep_critic_is_5(self, workspace, tmp_path):
        """AUTO Search×2 + Portfolio + Deep + Critic = 5."""
        run_dir = tmp_path / "auto_run"
        run_dir.mkdir()
        self._write_artifact(run_dir, "candidates-pass01.json", {
            "schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "NORMAL", "candidates": [{"candidate_id": "c01"}],
        })
        self._write_artifact(run_dir, "candidates-pass02.json", {
            "schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "RIFT", "candidates": [{"candidate_id": "c02"}],
        })
        self._write_artifact(run_dir, "search-field-pass02.json", {
            "schema_version": "pizm-search-field-v1", "stage": "search-field", "field_id": "sf2", "passes": [], "entries": [],
        })
        self._write_artifact(run_dir, "portfolio.json", {
            "schema_version": "pizm-portfolio-selection-v1", "stage": "portfolio", "route": "AUTO",
            "auto_target": {"target_type": "P", "target_id": "P1"}, "next_reasoning_move": "DEEP",
        })
        self._write_artifact(run_dir, "development-v2-P1.json", {
            "schema_version": "pizm-development-v2", "stage": "development-v2", "target": {"target_type": "P", "target_id": "P1"},
        })
        self._write_artifact(run_dir, "deep-review-v2-P1.json", {
            "schema_version": "pizm-deep-review-v2", "stage": "deep-review-v2", "terminal_state": "MODEL_READY",
        })
        acc_file = tmp_path / "acc.json"
        acc_file.write_text(json.dumps({"host_inference_count": 5, "model_repair_count": 0, "checkpoint_retry_count": 0, "semantic_stage_count": 5}), encoding="utf-8")

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "auto-5-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--stage", f"deep-P1={run_dir}",
            "--accounting", str(acc_file),
        )
        assert r.returncode == 0, r.stderr
        manifest = json.loads((workspace["output"] / "session-auto-5-test" / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["accounting"]["semantic_stage_count"] == 5

    def test_regression_auto_plus_lever_is_7(self, workspace, tmp_path):
        """AUTO + LEVER = 7."""
        run_dir = tmp_path / "auto_lever_run"
        run_dir.mkdir()
        self._write_artifact(run_dir, "candidates-pass01.json", {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "NORMAL", "candidates": [{"candidate_id": "c01"}]})
        self._write_artifact(run_dir, "candidates-pass02.json", {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "RIFT", "candidates": [{"candidate_id": "c02"}]})
        self._write_artifact(run_dir, "search-field-pass02.json", {"schema_version": "pizm-search-field-v1", "stage": "search-field", "field_id": "sf2", "passes": [], "entries": []})
        self._write_artifact(run_dir, "portfolio.json", {"schema_version": "pizm-portfolio-selection-v1", "stage": "portfolio", "route": "AUTO", "auto_target": {"target_type": "P", "target_id": "P1"}, "next_reasoning_move": "DEEP"})
        self._write_artifact(run_dir, "development-v2-P1.json", {"schema_version": "pizm-development-v2", "stage": "development-v2", "target": {"target_type": "P", "target_id": "P1"}})
        self._write_artifact(run_dir, "deep-review-v2-P1.json", {"schema_version": "pizm-deep-review-v2", "stage": "deep-review-v2", "terminal_state": "MODEL_READY"})
        self._write_artifact(run_dir, "design.json", {"schema_version": "pizm-lever-design-v1", "stage": "lever-design"})
        self._write_artifact(run_dir, "review.json", {"schema_version": "pizm-lever-review-v1", "stage": "lever-review", "outcome": "ACCEPTED"})
        acc_file = tmp_path / "acc.json"
        acc_file.write_text(json.dumps({"host_inference_count": 7, "model_repair_count": 0, "checkpoint_retry_count": 0, "semantic_stage_count": 7}), encoding="utf-8")

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "auto-lever-7-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--stage", f"deep-P1={run_dir}",
            "--stage", f"lever-P1={run_dir}",
            "--accounting", str(acc_file),
        )
        assert r.returncode == 0, r.stderr
        manifest = json.loads((workspace["output"] / "session-auto-lever-7-test" / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["accounting"]["semantic_stage_count"] == 7

    def test_regression_auto_terminal_at_portfolio_is_3(self, workspace, tmp_path):
        """AUTO terminal at Portfolio = 3."""
        run_dir = tmp_path / "auto_term_run"
        run_dir.mkdir()
        self._write_artifact(run_dir, "candidates-pass01.json", {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "NORMAL", "candidates": [{"candidate_id": "c01"}]})
        self._write_artifact(run_dir, "candidates-pass02.json", {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "RIFT", "candidates": [{"candidate_id": "c02"}]})
        self._write_artifact(run_dir, "search-field-pass02.json", {"schema_version": "pizm-search-field-v1", "stage": "search-field", "field_id": "sf2", "passes": [], "entries": []})
        self._write_artifact(run_dir, "portfolio.json", {"schema_version": "pizm-portfolio-selection-v1", "stage": "portfolio", "route": "AUTO", "auto_target": {"target_type": "P", "target_id": "P1"}, "next_reasoning_move": "PRESERVE_ONLY"})
        acc_file = tmp_path / "acc.json"
        acc_file.write_text(json.dumps({"host_inference_count": 3, "model_repair_count": 0, "checkpoint_retry_count": 0, "semantic_stage_count": 3}), encoding="utf-8")

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "auto-term-3-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--accounting", str(acc_file),
        )
        assert r.returncode == 0, r.stderr
        manifest = json.loads((workspace["output"] / "session-auto-term-3-test" / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["accounting"]["semantic_stage_count"] == 3

    def test_regression_legacy_bonk_search2_portfolio_deep2_compare_is_6(self, workspace, tmp_path):
        """legacy BONK Search×2 + Portfolio + Deep×2 + Compare = 6."""
        run_dir = tmp_path / "bonk_6_run"
        run_dir.mkdir()
        self._write_artifact(run_dir, "candidates-pass01.json", {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "NORMAL", "candidates": [{"candidate_id": "c01"}]})
        self._write_artifact(run_dir, "candidates-pass02.json", {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "360", "candidates": [{"candidate_id": "c02"}]})
        self._write_artifact(run_dir, "search-field.json", {"schema_version": "pizm-search-field-v1", "stage": "search-field", "field_id": "sf", "passes": [], "entries": []})
        self._write_artifact(run_dir, "portfolio.json", {"schema_version": "pizm-portfolio-selection-v2", "stage": "portfolio", "route": "BONK", "competition_status": "TWO_DEFENSIBLE_BUNDLES", "recommended_competition": {"left_bundle_id": "B1", "right_bundle_id": "B2"}})
        self._write_artifact(run_dir, "development-v2-B1.json", {"schema_version": "pizm-development-v2", "stage": "development-v2", "target": {"target_type": "B", "target_id": "B1"}})
        self._write_artifact(run_dir, "development-v2-B2.json", {"schema_version": "pizm-development-v2", "stage": "development-v2", "target": {"target_type": "B", "target_id": "B2"}})
        self._write_artifact(run_dir, "comparison-review-v1.json", {"schema_version": "pizm-comparison-review-v1", "stage": "comparison-review-v1", "left_target_id": "B1", "right_target_id": "B2", "comparison": {"current_preference": "LEFT"}})
        acc_file = tmp_path / "acc.json"
        acc_file.write_text(json.dumps({"host_inference_count": 6, "model_repair_count": 0, "checkpoint_retry_count": 0, "semantic_stage_count": 6}), encoding="utf-8")

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "bonk-6-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--stage", f"deep-B1={run_dir}",
            "--stage", f"deep-B2={run_dir}",
            "--stage", f"comparison-review={run_dir}",
            "--accounting", str(acc_file),
        )
        assert r.returncode == 0, r.stderr
        manifest = json.loads((workspace["output"] / "session-bonk-6-test" / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["accounting"]["semantic_stage_count"] == 6

    def test_regression_legacy_bonk_plus_lever_is_8(self, workspace, tmp_path):
        """legacy BONK + LEVER = 8."""
        run_dir = tmp_path / "bonk_lever_8_run"
        run_dir.mkdir()
        self._write_artifact(run_dir, "candidates-pass01.json", {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "NORMAL", "candidates": [{"candidate_id": "c01"}]})
        self._write_artifact(run_dir, "candidates-pass02.json", {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "360", "candidates": [{"candidate_id": "c02"}]})
        self._write_artifact(run_dir, "search-field.json", {"schema_version": "pizm-search-field-v1", "stage": "search-field", "field_id": "sf", "passes": [], "entries": []})
        self._write_artifact(run_dir, "portfolio.json", {"schema_version": "pizm-portfolio-selection-v2", "stage": "portfolio", "route": "BONK", "competition_status": "TWO_DEFENSIBLE_BUNDLES", "recommended_competition": {"left_bundle_id": "B1", "right_bundle_id": "B2"}})
        self._write_artifact(run_dir, "development-v2-B1.json", {"schema_version": "pizm-development-v2", "stage": "development-v2", "target": {"target_type": "B", "target_id": "B1"}})
        self._write_artifact(run_dir, "development-v2-B2.json", {"schema_version": "pizm-development-v2", "stage": "development-v2", "target": {"target_type": "B", "target_id": "B2"}})
        self._write_artifact(run_dir, "comparison-review-v1.json", {"schema_version": "pizm-comparison-review-v1", "stage": "comparison-review-v1", "left_target_id": "B1", "right_target_id": "B2", "comparison": {"current_preference": "LEFT"}})
        self._write_artifact(run_dir, "design.json", {"schema_version": "pizm-lever-design-v1", "stage": "lever-design"})
        self._write_artifact(run_dir, "review.json", {"schema_version": "pizm-lever-review-v1", "stage": "lever-review", "outcome": "ACCEPTED"})
        acc_file = tmp_path / "acc.json"
        acc_file.write_text(json.dumps({"host_inference_count": 8, "model_repair_count": 0, "checkpoint_retry_count": 0, "semantic_stage_count": 8}), encoding="utf-8")

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "bonk-lever-8-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--stage", f"deep-B1={run_dir}",
            "--stage", f"deep-B2={run_dir}",
            "--stage", f"comparison-review={run_dir}",
            "--stage", f"lever-B1={run_dir}",
            "--accounting", str(acc_file),
        )
        assert r.returncode == 0, r.stderr
        manifest = json.loads((workspace["output"] / "session-bonk-lever-8-test" / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["accounting"]["semantic_stage_count"] == 8

    def test_regression_new_pack_search3_portfolio_is_4(self, workspace, tmp_path):
        """new PACK Search×3 + Portfolio = 4."""
        run_dir = tmp_path / "pack_run"
        run_dir.mkdir()
        self._write_artifact(run_dir, "candidates-pass01.json", {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "NORMAL", "candidates": [{"candidate_id": "c01"}]})
        self._write_artifact(run_dir, "candidates-pass02.json", {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "360", "candidates": [{"candidate_id": "c02"}]})
        self._write_artifact(run_dir, "candidates-pass03.json", {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "RIFT", "candidates": [{"candidate_id": "c03"}]})
        self._write_artifact(run_dir, "search-field-pass03.json", {"schema_version": "pizm-search-field-v1", "stage": "search-field", "field_id": "sf3", "passes": [], "entries": []})
        self._write_artifact(run_dir, "portfolio.json", {"schema_version": "pizm-portfolio-selection-v1", "stage": "portfolio", "route": "AUTO", "auto_target": {"target_type": "P", "target_id": "P1"}, "next_reasoning_move": "PRESERVE_ONLY"})
        acc_file = tmp_path / "acc.json"
        acc_file.write_text(json.dumps({"host_inference_count": 4, "model_repair_count": 0, "checkpoint_retry_count": 0, "semantic_stage_count": 4}), encoding="utf-8")

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "pack-4-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"pass-03-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--accounting", str(acc_file),
        )
        assert r.returncode == 0, r.stderr
        manifest = json.loads((workspace["output"] / "session-pack-4-test" / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["accounting"]["semantic_stage_count"] == 4

    def test_regression_new_bonk_search3_portfolio_deep2_is_6(self, tmp_path):
        """new BONK Search×3 + Portfolio + Deep×2 = 6 (constructed fixture bundle)."""
        bundle = tmp_path / "bonk_v3_bundle"
        for d in ("pass-01-normal", "pass-02-residual", "pass-03-rift", "search-field", "portfolio", "deep-B1", "deep-B2"):
            (bundle / d).mkdir(parents=True)
        (bundle / "pass-01-normal" / "candidates-pass01.json").write_text("{}")
        (bundle / "pass-02-residual" / "candidates-pass02.json").write_text("{}")
        (bundle / "pass-03-rift" / "candidates-pass03.json").write_text("{}")
        (bundle / "search-field" / "search-field-pass03.json").write_text("{}")
        (bundle / "portfolio" / "portfolio.json").write_text("{}")
        (bundle / "deep-B1" / "development-v2-B1.json").write_text("{}")
        (bundle / "deep-B2" / "development-v2-B2.json").write_text("{}")
        assert _compute_semantic_stage_count(bundle) == 6

    def test_regression_new_bonk_degraded_search3_portfolio_deep1_is_5(self, tmp_path):
        """new BONK degraded Search×3 + Portfolio + Deep×1 = 5 (constructed fixture bundle)."""
        bundle = tmp_path / "bonk_v3_degraded_bundle"
        for d in ("pass-01-normal", "pass-02-residual", "pass-03-rift", "search-field", "portfolio", "deep-B1"):
            (bundle / d).mkdir(parents=True)
        (bundle / "pass-01-normal" / "candidates-pass01.json").write_text("{}")
        (bundle / "pass-02-residual" / "candidates-pass02.json").write_text("{}")
        (bundle / "pass-03-rift" / "candidates-pass03.json").write_text("{}")
        (bundle / "search-field" / "search-field-pass03.json").write_text("{}")
        (bundle / "portfolio" / "portfolio.json").write_text("{}")
        (bundle / "deep-B1" / "development-v2-B1.json").write_text("{}")
        assert _compute_semantic_stage_count(bundle) == 5


# ---------------------------------------------------------------------------
# PACK Route Tests (Wave A: Archive, Accounting, Rendering, HTML refusal)
# ---------------------------------------------------------------------------


class TestPackSessionBundleAndRenderer:
    """Verifies Wave A PACK archive, accounting, markdown renderer, and HTML refusal."""

    def _write_artifact(self, dir_path: Path, filename: str, content: dict) -> Path:
        f = dir_path / filename
        f.write_text(json.dumps(content, indent=2), encoding="utf-8")
        sha_f = dir_path / (filename.rsplit(".", 1)[0] + ".sha256")
        sha_f.write_text(_sha256_hex(f.read_bytes()), encoding="utf-8")
        return f

    def _setup_pack_shared_run_dir(self, run_dir: Path, with_borderline: bool = False) -> dict:
        pass1_candidates = [
            {"candidate_id": "c01", "title": "Initial Candidate 1", "semantic_core": {"claim": "Core Claim 1", "mechanism": "Mech 1"}},
            {"candidate_id": "c02", "title": "Initial Candidate 2", "semantic_core": {"claim": "Core Claim 2", "mechanism": "Mech 2"}},
        ]
        assessments = [
            {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Res1", "nearest_overlap": None, "reason": "Grounding", "plain_explanation": "Plain explanation 1"},
            {"candidate_ref": "pass01:c02", "disposition": "DROP", "standalone_quality": "weak", "unique_residue": "", "nearest_overlap": "pass01:c01", "reason": "Duplicate concept"},
            {"candidate_ref": "pass02:c01", "disposition": "MERGE", "standalone_quality": "strong", "unique_residue": "Res2", "nearest_overlap": "pass01:c01", "reason": "Variant"},
            {"candidate_ref": "pass03:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Res3", "nearest_overlap": None, "reason": "Structural novelty", "plain_explanation": "Plain explanation 3"},
        ]
        if with_borderline:
            pass1_candidates.append(
                {"candidate_id": "c03", "title": "Borderline Candidate 3",
                 "semantic_core": {"claim": "Core Claim 3", "mechanism": "Mech 3"}}
            )
            assessments.append(
                {"candidate_ref": "pass01:c03", "disposition": "BORDERLINE", "standalone_quality": "borderline",
                 "unique_residue": "Res4", "nearest_overlap": "pass01:c01", "reason": "Real residue, weak grounding"}
            )
        c1 = self._write_artifact(run_dir, "candidates-pass01.json", {
            "schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "NORMAL",
            "candidates": pass1_candidates,
        })
        c2 = self._write_artifact(run_dir, "candidates-pass02.json", {
            "schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "360",
            "candidates": [
                {"candidate_id": "c01", "title": "Residual Candidate 1", "semantic_core": {"claim": "Residual Claim 1", "mechanism": "Residual Mech 1"}},
            ],
        })
        c3 = self._write_artifact(run_dir, "candidates-pass03.json", {
            "schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "RIFT",
            "candidates": [
                {"candidate_id": "c01", "title": "Rift Candidate 1", "semantic_core": {"claim": "Rift Claim 1", "mechanism": "Rift Mech 1"}},
            ],
        })
        self._write_artifact(run_dir, "search-field-pass03.json", {
            "schema_version": "pizm-search-field-v1", "stage": "search-field", "field_id": "sf3",
            "passes": [], "entries": ["pass01:c01", "pass01:c02", "pass02:c01", "pass03:c01"],
        })
        port = self._write_artifact(run_dir, "portfolio.json", {
            "schema_version": "pizm-portfolio-selection-v1", "stage": "portfolio", "route": "PACK",
            "field_hash": hashlib.sha256((run_dir / "search-field-pass03.json").read_bytes()).hexdigest(),
            "field_ref": "search-field-pass03.json",
            "candidate_assessments": assessments,
            "bundles": [
                {
                    "bundle_id": "B1",
                    "member_refs": ["pass01:c01", "pass03:c01"],
                    "bundle_thesis": "Integrated dual-pass hypothesis",
                    "composition_gain": "Synergy of initial and rift framing",
                    "internal_tension": "Short vs long term tension",
                    "weakest_link": "Boundary conditions",
                    "new_consequence_or_prediction": "Novel observable prediction",
                }
            ],
            "perspectives": {"P1": "pass01:c01", "P2": "pass03:c01"},
            "high_upside": [
                {"ref": "pass03:c01", "why": "Distant structural reframe", "risk": "Low existing validation"}
            ],
            "next_reasoning_move": None,
            "next_reasoning_rationale": None,
            "information_request": None,
            "rival_shadow": None,
            "auto_target": None,
        })
        return {
            "run_dir": run_dir,
            "c1": c1, "c2": c2, "c3": c3, "portfolio": port,
        }

    def test_pack_honestly_exhausted_final_pass_archives_and_renders(self, workspace, tmp_path):
        """An exhausted pass 3 is still a real pass: the run freezes, archives, and
        renders, the accumulated search field keeps its prior entries, and no
        candidate is invented to satisfy a schema."""
        run_dir = tmp_path / "pack_exhausted_run"
        run_dir.mkdir()
        c1 = self._write_artifact(run_dir, "candidates-pass01.json", {
            "schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "NORMAL",
            "candidates": [
                {"candidate_id": "c01", "title": "Initial One",
                 "semantic_core": {"claim": "Claim 1", "mechanism": "Mech 1"}},
                {"candidate_id": "c02", "title": "Initial Two",
                 "semantic_core": {"claim": "Claim 2", "mechanism": "Mech 2"}},
            ],
        })
        c2 = self._write_artifact(run_dir, "candidates-pass02.json", {
            "schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "360",
            "candidates": [
                {"candidate_id": "c01", "title": "Residual One",
                 "semantic_core": {"claim": "Claim 3", "mechanism": "Mech 3"}},
            ],
        })
        c3 = self._write_artifact(run_dir, "candidates-pass03.json", {
            "schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "RIFT",
            "candidates": [],
            "exhaustion_reason": "No materially distinct grounded frame remained for a rift pass.",
        })
        field_entries = ["pass01:c01", "pass01:c02", "pass02:c01"]
        field = {
            "schema_version": "pizm-search-field-v1", "stage": "search-field", "field_id": "sf3",
            "passes": [
                {"pass_id": "pass01", "candidates_ref": c1.name,
                 "frozen_hash": _sha256_hex(c1.read_bytes())},
                {"pass_id": "pass02", "candidates_ref": c2.name,
                 "frozen_hash": _sha256_hex(c2.read_bytes())},
                {"pass_id": "pass03", "candidates_ref": c3.name,
                 "frozen_hash": _sha256_hex(c3.read_bytes())},
            ],
            "entries": field_entries,
        }
        port = self._write_artifact(run_dir, "search-field-pass03.json", field)
        self._write_artifact(run_dir, "portfolio.json", {
            "schema_version": "pizm-portfolio-selection-v1", "stage": "portfolio", "route": "PACK",
            "field_ref": "search-field-pass03.json",
            "field_hash": _sha256_hex(port.read_bytes()),
            "candidate_assessments": [
                {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong",
                 "unique_residue": "Residue 1", "nearest_overlap": None, "reason": "Grounded",
                 "plain_explanation": "Plain explanation 1"},
                {"candidate_ref": "pass01:c02", "disposition": "DROP", "standalone_quality": "weak",
                 "unique_residue": "", "nearest_overlap": "pass01:c01", "reason": "Duplicate"},
                {"candidate_ref": "pass02:c01", "disposition": "MERGE", "standalone_quality": "strong",
                 "unique_residue": "Residue 2", "nearest_overlap": "pass01:c01", "reason": "Variant"},
            ],
            "bundles": [],
            "perspectives": {"P1": "pass01:c01"},
            "high_upside": [],
            "next_reasoning_move": None,
            "next_reasoning_rationale": None,
            "information_request": None,
            "rival_shadow": None,
            "auto_target": None,
        })

        acc_file = tmp_path / "acc_pack_exhausted.json"
        acc_file.write_text(json.dumps({
            "host_inference_count": 4, "model_repair_count": 0,
            "checkpoint_retry_count": 0, "semantic_stage_count": 4,
        }), encoding="utf-8")

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "pack-exhausted",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"pass-03-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--accounting", str(acc_file),
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-pack-exhausted"
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["accounting"]["semantic_stage_count"] == 4
        assert (bundle / "pass-03-rift" / "candidates-pass03.json").is_file()
        archived_field = json.loads(
            (bundle / "search-field" / "search-field-pass03.json").read_text(encoding="utf-8")
        )
        assert archived_field["entries"] == field_entries

        out_md = tmp_path / "research-pack-exhausted.md"
        render = run_bundle(
            "render", "--run-dir", str(run_dir),
            "--task", "Exhausted three-pass task", "--output", str(out_md),
        )
        assert render.returncode == 0, render.stderr
        text = out_md.read_text(encoding="utf-8")
        assert "### P1 — Initial One (`pass01:c01`)" in text
        assert "Pass 3 — rift" in text

    def test_pack_bundle_pass_isolation_no_cross_leakage(self, workspace, tmp_path):
        """PACK shared run-dir archive isolates pass01, pass02, pass03 without cross-pass leakage."""
        run_dir = tmp_path / "pack_shared_run"
        run_dir.mkdir()
        self._setup_pack_shared_run_dir(run_dir)

        acc_file = tmp_path / "acc_pack.json"
        acc_file.write_text(json.dumps({
            "host_inference_count": 4,
            "model_repair_count": 0,
            "checkpoint_retry_count": 0,
            "semantic_stage_count": 4,
        }), encoding="utf-8")

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "pack-iso-test",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"pass-03-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--accounting", str(acc_file),
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-pack-iso-test"

        # Check isolation
        p1_files = {f.name for f in (bundle / "pass-01-normal").iterdir()}
        assert "candidates-pass01.json" in p1_files
        assert "candidates-pass02.json" not in p1_files
        assert "candidates-pass03.json" not in p1_files

        p2_files = {f.name for f in (bundle / "pass-02-residual").iterdir()}
        assert "candidates-pass02.json" in p2_files
        assert "candidates-pass01.json" not in p2_files
        assert "candidates-pass03.json" not in p2_files

        p3_files = {f.name for f in (bundle / "pass-03-rift").iterdir()}
        assert "candidates-pass03.json" in p3_files
        assert "candidates-pass01.json" not in p3_files
        assert "candidates-pass02.json" not in p3_files

        sf_files = {f.name for f in (bundle / "search-field").iterdir()}
        assert "search-field-pass03.json" in sf_files

        port_files = {f.name for f in (bundle / "portfolio").iterdir()}
        assert "portfolio.json" in port_files

    def test_pack_mandatory_accounting_rejection_and_acceptance(self, workspace, tmp_path):
        """PACK create without --accounting fails closed; with accounting succeeds with stage_count 4."""
        run_dir = tmp_path / "pack_acc_run"
        run_dir.mkdir()
        self._setup_pack_shared_run_dir(run_dir)

        # 1. Without accounting -> rejected
        r_no_acc = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "pack-no-acc",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"pass-03-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
        )
        assert r_no_acc.returncode != 0
        assert "accounting input is required" in r_no_acc.stderr

        # 2. With accounting -> accepted and semantic_stage_count == 4
        acc_file = tmp_path / "acc.json"
        acc_file.write_text(json.dumps({
            "host_inference_count": 4, "model_repair_count": 0, "checkpoint_retry_count": 0,
            "semantic_stage_count": 4,
        }), encoding="utf-8")
        r_acc = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "pack-with-acc",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"pass-03-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--accounting", str(acc_file),
        )
        assert r_acc.returncode == 0, r_acc.stderr
        manifest = json.loads((workspace["output"] / "session-pack-with-acc" / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["accounting"]["semantic_stage_count"] == 4

    def test_pack_markdown_renderer_contract_and_determinism(self, tmp_path):
        """PACK markdown renderer satisfies all 7 contract assertions and is byte-for-byte deterministic."""
        run_dir = tmp_path / "pack_render_run"
        run_dir.mkdir()
        self._setup_pack_shared_run_dir(run_dir)

        out1 = tmp_path / "research-pack-out1.md"
        out2 = tmp_path / "research-pack-out2.md"

        # Render once
        r1 = run_bundle("render", "--run-dir", str(run_dir), "--task", "Analyze organizational trust", "--output", str(out1))
        assert r1.returncode == 0, r1.stderr

        # Render twice
        r2 = run_bundle("render", "--run-dir", str(run_dir), "--task", "Analyze organizational trust", "--output", str(out2))
        assert r2.returncode == 0, r2.stderr

        # 1. Deterministic byte-for-byte
        assert out1.read_bytes() == out2.read_bytes(), "PACK render output is not byte-identical across runs"

        text = out1.read_text(encoding="utf-8")

        # 2. No Deep/Critic requirement and no Deep/Critic sections
        assert "## Deep" not in text
        assert "## Critic" not in text

        # 3. Promoted Perspectives and valid Bundles rendered
        assert "## Curated Perspectives" in text
        assert "P1 — Initial Candidate 1 (`pass01:c01`)" in text
        assert "P2 — Rift Candidate 1 (`pass03:c01`)" in text
        assert "## Bundles" in text
        assert "B1 — P1 + P2" in text
        assert "Integrated dual-pass hypothesis" in text

        # 4. DROP bodies absent (only in curation summary count)
        assert "Initial Candidate 2" not in text, "DROP candidate body leaked into curated perspectives"
        assert "Duplicate concept" not in text, "DROP reason leaked as card"

        # 5. Curation summary present with correct counts
        assert "## Curation summary" in text
        assert "- Raw candidate refs: 4" in text
        assert "- KEEP: 2" in text
        assert "- MERGE: 1" in text
        assert "- BORDERLINE: 0" in text
        assert "- DROP: 1" in text
        assert "- Bundles: 1" in text

        # 6. Explicit non-claims present
        assert "## Explicit non-claims" in text
        assert "any Perspective is true" in text
        assert "any Bundle is validated" in text
        assert "any candidate is a final recommendation" in text
        assert "any causal mechanism has been independently verified" in text
        assert "curation is not a truth ranking" in text

        # 7. No MODEL_READY and no winner
        assert "MODEL_READY" not in text
        assert "Winner" not in text
        assert "auto_target" not in text

    def test_pack_html_unsupported_refusal(self, tmp_path):
        """pizm-session-bundle render-html on a PACK run refuses with non-zero exit and stable error."""
        run_dir = tmp_path / "pack_html_run"
        run_dir.mkdir()
        self._setup_pack_shared_run_dir(run_dir)

        out_html = tmp_path / "run.html"
        r = run_bundle("render-html", "--run-dir", str(run_dir), "--task", "Analyze trust", "--output", str(out_html))
        assert r.returncode != 0
        assert "PACK HTML is not supported in Wave A; use research-pack.md" in r.stderr

    def _pack_create(self, workspace, tmp_path, run_dir, slug, labels, count=4):
        acc_file = tmp_path / f"acc_pack_{slug}.json"
        acc_file.write_text(json.dumps({
            "host_inference_count": count, "model_repair_count": 0,
            "checkpoint_retry_count": 0, "semantic_stage_count": count,
        }), encoding="utf-8")
        argv = [
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", slug,
            "--skill-root", str(workspace["skill"]),
        ]
        for label in labels:
            argv += ["--stage", f"{label}={run_dir}"]
        argv += ["--accounting", str(acc_file)]
        return run_bundle(*argv)

    PACK_STAGES = ("pass-01-normal", "pass-02-residual", "pass-03-rift", "search-field", "portfolio")

    def test_pack_rejects_deep_comparison_and_lever_stages(self, workspace, tmp_path):
        """PACK carries zero Deep/Critic/Comparison/LEVER stages; asking for one fails closed."""
        run_dir = tmp_path / "pack_bad_stage_run"
        run_dir.mkdir()
        self._setup_pack_shared_run_dir(run_dir)

        r_deep = self._pack_create(workspace, tmp_path, run_dir, "pack-bad-deep",
                                   self.PACK_STAGES + ("deep-B1",))
        assert r_deep.returncode != 0
        assert "PACK run forbids deep stages" in r_deep.stderr

        r_comp = self._pack_create(workspace, tmp_path, run_dir, "pack-bad-comp",
                                   self.PACK_STAGES + ("comparison-review",))
        assert r_comp.returncode != 0
        assert "PACK run forbids comparison stages" in r_comp.stderr

        r_lever = self._pack_create(workspace, tmp_path, run_dir, "pack-bad-lever",
                                    self.PACK_STAGES + ("lever-B1",))
        assert r_lever.returncode != 0
        assert "PACK run forbids lever stages" in r_lever.stderr

    def test_pack_requires_exact_stage_set(self, workspace, tmp_path):
        """A PACK archive carries exactly the three Search passes, field, and portfolio."""
        run_dir = tmp_path / "pack_stage_set_run"
        run_dir.mkdir()
        self._setup_pack_shared_run_dir(run_dir)

        r_missing = self._pack_create(
            workspace, tmp_path, run_dir, "pack-missing-stage",
            ("pass-01-normal", "pass-03-rift", "search-field", "portfolio"),
        )
        assert r_missing.returncode != 0
        assert "missing: pass-02-residual" in r_missing.stderr

        r_extra = self._pack_create(
            workspace, tmp_path, run_dir, "pack-extra-stage",
            self.PACK_STAGES + ("pass-04-normal",),
        )
        assert r_extra.returncode != 0
        assert "carries non-PACK stages: pass-04-normal" in r_extra.stderr

    def test_pack_rejects_stray_development_or_review_artifact(self, workspace, tmp_path):
        """A development/review/comparison/lever artifact in a PACK run dir fails closed."""
        run_dir = tmp_path / "pack_stray_run"
        run_dir.mkdir()
        self._setup_pack_shared_run_dir(run_dir)
        (run_dir / "development-v2-B1.json").write_text(json.dumps({"target_id": "B1"}), encoding="utf-8")

        r = self._pack_create(workspace, tmp_path, run_dir, "pack-stray-dev", self.PACK_STAGES)
        assert r.returncode != 0
        assert "PACK run must not carry development/review/comparison/lever artifacts" in r.stderr
        assert "development-v2-B1.json" in r.stderr

    def test_pack_rejects_stray_sidecars_only(self, workspace, tmp_path):
        """Orphan development/review sidecars without their JSON also fail closed."""
        run_dir = tmp_path / "pack_stray_sidecar_run"
        run_dir.mkdir()
        self._setup_pack_shared_run_dir(run_dir)
        for name in ("development-v2-B1.sha256", "development-v2-B1.meta.json",
                     "deep-review-v2-B1.sha256", "comparison-review-v1.meta.json"):
            (run_dir / name).write_text("orphan sidecar", encoding="utf-8")

        r = self._pack_create(workspace, tmp_path, run_dir, "pack-stray-sidecars", self.PACK_STAGES)
        assert r.returncode != 0
        assert "PACK run must not carry development/review/comparison/lever artifacts" in r.stderr
        for name in ("development-v2-B1.sha256", "development-v2-B1.meta.json",
                     "deep-review-v2-B1.sha256", "comparison-review-v1.meta.json"):
            assert name in r.stderr

    def test_pack_renderer_requires_all_three_passes(self, tmp_path):
        """A partial PACK run cannot render a packet: pass02/pass03/final field are mandatory."""
        for missing in ("candidates-pass02.json", "candidates-pass03.json", "search-field-pass03.json"):
            run_dir = tmp_path / f"pack_missing_{missing.replace('.', '_')}"
            run_dir.mkdir()
            self._setup_pack_shared_run_dir(run_dir)
            (run_dir / missing).unlink()
            out = tmp_path / f"pack-missing-{missing}.md"
            r = run_bundle("render", "--run-dir", str(run_dir), "--task", "Analyze trust", "--output", str(out))
            assert r.returncode != 0, f"{missing} unexpectedly rendered"
            assert f"missing artifact: {missing}" in r.stderr

    def test_pack_packet_preserves_borderline_and_merge_territory(self, tmp_path):
        """BORDERLINE cards and MERGE residues reach the handoff; DROP stays count-only."""
        run_dir = tmp_path / "pack_preserved_run"
        run_dir.mkdir()
        self._setup_pack_shared_run_dir(run_dir, with_borderline=True)

        out1 = tmp_path / "pack-preserved-1.md"
        out2 = tmp_path / "pack-preserved-2.md"
        r1 = run_bundle("render", "--run-dir", str(run_dir), "--task", "Analyze trust", "--output", str(out1))
        assert r1.returncode == 0, r1.stderr
        r2 = run_bundle("render", "--run-dir", str(run_dir), "--task", "Analyze trust", "--output", str(out2))
        assert r2.returncode == 0, r2.stderr
        assert out1.read_bytes() == out2.read_bytes()

        text = out1.read_text(encoding="utf-8")
        assert "## Preserved open / merged territory" in text
        # The preserved territory sits between the curated cards and the bundles.
        assert text.index("## Curated Perspectives") < text.index("## Preserved open / merged territory")
        assert text.index("## Preserved open / merged territory") < text.index("## Bundles")

        # BORDERLINE card is preserved (open territory, not a promoted perspective)
        assert "### BORDERLINE — Borderline Candidate 3 (`pass01:c03`)" in text
        assert "BORDERLINE (standalone quality: borderline)" in text
        assert "Res4" in text
        assert "Real residue, weak grounding" in text

        # MERGE residue and its nearest overlap are preserved
        assert "### MERGE — Residual Candidate 1 (`pass02:c01`)" in text
        assert "Res2" in text
        assert "Nearest overlap: pass01:c01" in text
        assert "Variant" in text

        # DROP stays count-only: no body, no reason text
        assert "Initial Candidate 2" not in text
        assert "Duplicate concept" not in text
        assert "- DROP: 1" in text
        assert "- BORDERLINE: 1" in text
        assert "- MERGE: 1" in text


class TestBonkV3ArchiveAndRenderer:
    """Wave B: BONK v3 dual-development archive, accounting, renderer, HTML refusal."""

    def _write_artifact(self, dir_path: Path, filename: str, content: dict) -> Path:
        f = dir_path / filename
        f.write_text(json.dumps(content, indent=2), encoding="utf-8")
        sha_f = dir_path / (filename.rsplit(".", 1)[0] + ".sha256")
        sha_f.write_text(_sha256_hex(f.read_bytes()), encoding="utf-8")
        return f

    def _v3_bundle(self, bid, refs):
        return {
            "bundle_id": bid,
            "member_refs": list(refs),
            "bundle_thesis": f"Bundle thesis {bid}",
            "composition_gain": f"Composition gain {bid}",
            "member_roles": {r: f"role in {bid}" for r in refs},
            "member_ablation": {r: f"{r} removed from {bid}" for r in refs},
            "internal_tension": f"Internal tension {bid}",
            "weakest_link": f"Weakest link {bid}",
            "new_consequence_or_prediction": f"Prediction {bid}",
        }

    def _v3_development(self, target_id, thesis, refs):
        refs = list(refs)
        return {
            "schema_version": "pizm-development-v2",
            "stage": "development-v2",
            "target": {"target_type": "B", "target_id": target_id},
            "identity_lock": {
                "title": f"Title {target_id}",
                "core_claim": f"Core claim {target_id}",
                "structural_shift": f"Structural shift {target_id}",
                "mechanism": f"Mechanism {target_id}",
                "boundary": f"Boundary {target_id}",
                "bundle_id": target_id,
                "member_refs": refs,
            },
            "developed_model": {
                "thesis": thesis,
                "synthesis": f"Developed synthesis prose for {target_id}.",
                "dynamics": f"Dynamics {target_id}",
                "mechanism_chain": ["step one", "step two", "step three"],
                "implications": [f"implication {target_id}"],
                "predictions_or_observables": [f"observable {target_id}"],
                "break_conditions": [f"break condition {target_id}"],
                "unresolved_tensions": [f"tension {target_id}"],
                "evidence_debt": [f"debt {target_id}"],
                "load_bearing_claims": [
                    {"claim": f"claim A {target_id}", "role_in_model": "core",
                     "epistemic_status": "SUPPORTED", "what_would_weaken_or_refute": "x"},
                    {"claim": f"claim B {target_id}", "role_in_model": "durability",
                     "epistemic_status": "SPECULATIVE", "what_would_weaken_or_refute": "y"},
                ],
                "member_contributions": {r: f"{r} contributes" for r in refs},
                "member_ablation": {r: f"{r} removal cost" for r in refs},
            },
        }

    def _setup_v3_run_dir(self, run_dir: Path, mode="DUAL_BUNDLES", target_order=("B1", "B2"),
                          targets_developed=None):
        """Shared v3 run dir: 3 search passes, final field, v3 portfolio, developments."""
        run_dir.mkdir(parents=True, exist_ok=True)
        for i, m in ((1, "NORMAL"), (2, "360"), (3, "RIFT")):
            self._write_artifact(run_dir, f"candidates-pass0{i}.json", {
                "schema_version": "pizm-candidates-v1", "stage": "explore", "mode": m,
                "candidates": [
                    {"candidate_id": "c01", "title": f"Pass{i} Candidate 1",
                     "semantic_core": {"claim": f"Claim p{i}", "mechanism": f"Mech p{i}"}},
                ],
            })
        self._write_artifact(run_dir, "search-field-pass03.json", {
            "schema_version": "pizm-search-field-v1", "stage": "search-field", "field_id": "sf3",
            "passes": [], "entries": ["pass01:c01", "pass02:c01", "pass03:c01"],
        })
        field_hash = _sha256_hex((run_dir / "search-field-pass03.json").read_bytes())

        if mode == "DUAL_BUNDLES":
            dev_targets = [
                {"target_type": "B", "target_id": t, "why_develop": f"develop {t}"}
                for t in target_order
            ]
            material_difference = "B1 changes the causal mechanism; B2 shifts the system boundary."
        else:
            dev_targets = [
                {"target_type": "B", "target_id": target_order[0],
                 "why_develop": "No second materially distinct bundle was defensible."},
            ]
            material_difference = None

        v3_bundles = [self._v3_bundle("B1", ["pass01:c01", "pass02:c01"]),
                      self._v3_bundle("B2", ["pass03:c01", "pass02:c01"])]
        refs_by_id = {b["bundle_id"]: b["member_refs"] for b in v3_bundles}
        self._write_artifact(run_dir, "portfolio.json", {
            "schema_version": "pizm-portfolio-selection-v3", "stage": "portfolio", "route": "BONK",
            "field_ref": "search-field-pass03.json", "field_hash": field_hash,
            "candidate_assessments": [
                {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong",
                 "unique_residue": "res", "nearest_overlap": None, "reason": "grounded"},
                {"candidate_ref": "pass02:c01", "disposition": "KEEP", "standalone_quality": "strong",
                 "unique_residue": "res2", "nearest_overlap": None, "reason": "grounded"},
                {"candidate_ref": "pass03:c01", "disposition": "KEEP", "standalone_quality": "strong",
                 "unique_residue": "res3", "nearest_overlap": None, "reason": "rift novelty"},
            ],
            "bundles": v3_bundles,
            "perspectives": {"P1": "pass01:c01", "P2": "pass02:c01", "P3": "pass03:c01"},
            "high_upside": [],
            "development_mode": mode,
            "development_targets": dev_targets,
            "material_difference": material_difference,
        })
        developed = targets_developed if targets_developed is not None else [
            t["target_id"] for t in dev_targets
        ]
        for t_id in developed:
            self._write_artifact(
                run_dir, f"development-v2-{t_id}.json",
                self._v3_development(
                    t_id, f"Developed thesis for {t_id}",
                    refs_by_id.get(t_id, ["pass01:c01", "pass02:c01"]),
                ),
            )

    def _accounting(self, tmp_path: Path, count: int) -> Path:
        acc = tmp_path / f"acc_v3_{count}.json"
        acc.write_text(json.dumps({
            "host_inference_count": count,
            "model_repair_count": 0,
            "checkpoint_retry_count": 0,
            "semantic_stage_count": count,
        }), encoding="utf-8")
        return acc

    def test_v3_dual_archive_pass_isolation_and_accounting_six(self, workspace, tmp_path):
        """Plan tests 10 & 11: v3 dual archives 6 semantic stages with pass03 isolation."""
        run_dir = tmp_path / "v3_dual_run"
        self._setup_v3_run_dir(run_dir)
        acc = self._accounting(tmp_path, 6)

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "v3-dual-bundle",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"pass-03-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--stage", f"deep-B1={run_dir}",
            "--stage", f"deep-B2={run_dir}",
            "--accounting", str(acc),
        )
        assert r.returncode == 0, r.stderr
        bundle = workspace["output"] / "session-v3-dual-bundle"
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["accounting"]["semantic_stage_count"] == 6

        p1 = {f.name for f in (bundle / "pass-01-normal").iterdir()}
        assert p1 == {"candidates-pass01.json", "candidates-pass01.sha256"}
        p2 = {f.name for f in (bundle / "pass-02-residual").iterdir()}
        assert p2 == {"candidates-pass02.json", "candidates-pass02.sha256"}
        p3 = {f.name for f in (bundle / "pass-03-rift").iterdir()}
        assert p3 == {"candidates-pass03.json", "candidates-pass03.sha256"}
        sf = {f.name for f in (bundle / "search-field").iterdir()}
        assert sf == {"search-field-pass03.json", "search-field-pass03.sha256"}

        d1 = {f.name for f in (bundle / "deep-B1").iterdir()}
        assert d1 == {"development-v2-B1.json", "development-v2-B1.sha256"}
        d2 = {f.name for f in (bundle / "deep-B2").iterdir()}
        assert d2 == {"development-v2-B2.json", "development-v2-B2.sha256"}

    def test_v3_single_archive_accounting_five(self, workspace, tmp_path):
        """Degraded v3 (SINGLE_TARGET) archives 5 semantic stages."""
        run_dir = tmp_path / "v3_single_run"
        self._setup_v3_run_dir(run_dir, mode="SINGLE_TARGET", target_order=("B1",))
        acc = self._accounting(tmp_path, 5)

        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "v3-single-bundle",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"pass-03-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--stage", f"deep-B1={run_dir}",
            "--accounting", str(acc),
        )
        assert r.returncode == 0, r.stderr
        manifest = json.loads(
            (workspace["output"] / "session-v3-single-bundle" / "manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["accounting"]["semantic_stage_count"] == 5

    def test_v3_create_requires_accounting(self, workspace, tmp_path):
        """v3, like PACK/v2, fails closed without --accounting."""
        run_dir = tmp_path / "v3_no_acc_run"
        self._setup_v3_run_dir(run_dir)
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "v3-no-acc",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"pass-03-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--stage", f"deep-B1={run_dir}",
            "--stage", f"deep-B2={run_dir}",
        )
        assert r.returncode != 0
        assert "accounting input is required" in r.stderr

    def test_v3_rejects_comparison_and_lever_stages(self, workspace, tmp_path):
        """v3 has no comparison or LEVER stage; asking for one fails closed."""
        run_dir = tmp_path / "v3_bad_stage_run"
        self._setup_v3_run_dir(run_dir)
        acc = self._accounting(tmp_path, 6)
        base = [
            "--output-root", str(workspace["output"]),
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"pass-03-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--stage", f"deep-B1={run_dir}",
            "--accounting", str(acc),
        ]
        r_comp = run_bundle("create", "--slug", "v3-bad-comp", *base,
                            "--stage", f"comparison-review={run_dir}")
        assert r_comp.returncode != 0
        assert "BONK v3 run forbids comparison stages" in r_comp.stderr

        r_lever = run_bundle("create", "--slug", "v3-bad-lever", *base,
                             "--stage", f"lever-B1={run_dir}")
        assert r_lever.returncode != 0
        assert "BONK v3 run forbids lever stages" in r_lever.stderr

    def test_v3_rejects_stray_review_artifact(self, workspace, tmp_path):
        """A review artifact riding along in a v3 run dir fails the archive closed."""
        run_dir = tmp_path / "v3_stray_review_run"
        self._setup_v3_run_dir(run_dir)
        (run_dir / "review.json").write_text(json.dumps({"terminal_state": "MODEL_READY"}), encoding="utf-8")
        acc = self._accounting(tmp_path, 6)
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "v3-stray-review",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"pass-03-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--stage", f"deep-B1={run_dir}",
            "--stage", f"deep-B2={run_dir}",
            "--accounting", str(acc),
        )
        assert r.returncode != 0
        assert "must not carry review/comparison/lever artifacts" in r.stderr

    def test_v3_rejects_sidecar_only_forbidden_artifacts(self, workspace, tmp_path):
        """Orphan review/comparison/lever sidecars without their JSON still fail closed."""
        run_dir = tmp_path / "v3_sidecar_run"
        self._setup_v3_run_dir(run_dir)
        for name in ("deep-review-v2-B1.sha256", "deep-review-v2-B1.meta.json",
                     "comparison-review-v1.sha256", "review.meta.json"):
            (run_dir / name).write_text("orphan sidecar", encoding="utf-8")
        acc = self._accounting(tmp_path, 6)
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "v3-orphan-sidecars",
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"pass-03-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
            "--stage", f"deep-B1={run_dir}",
            "--stage", f"deep-B2={run_dir}",
            "--accounting", str(acc),
        )
        assert r.returncode != 0
        assert "must not carry review/comparison/lever artifacts" in r.stderr
        for name in ("deep-review-v2-B1.sha256", "deep-review-v2-B1.meta.json",
                     "comparison-review-v1.sha256", "review.meta.json"):
            assert name in r.stderr

    def _v3_create(self, workspace, tmp_path, run_dir, slug, deep_labels, count=6):
        acc = self._accounting(tmp_path, count)
        argv = [
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", slug,
            "--skill-root", str(workspace["skill"]),
            "--stage", f"pass-01-normal={run_dir}",
            "--stage", f"pass-02-residual={run_dir}",
            "--stage", f"pass-03-rift={run_dir}",
            "--stage", f"search-field={run_dir}",
            "--stage", f"portfolio={run_dir}",
        ]
        for label in deep_labels:
            argv += ["--stage", f"deep-{label}={run_dir}"]
        argv += ["--accounting", str(acc)]
        return run_bundle(*argv)

    def test_v3_rejects_extra_deep_target_not_in_portfolio(self, workspace, tmp_path):
        """Portfolio says B1+B2; archiving B1+B3 is a provenance mismatch."""
        run_dir = tmp_path / "v3_extra_deep_run"
        self._setup_v3_run_dir(run_dir, targets_developed=("B1", "B2", "B3"))
        r = self._v3_create(workspace, tmp_path, run_dir, "v3-extra-deep", ("B1", "B3"))
        assert r.returncode != 0
        assert "must equal the frozen development_targets exactly" in r.stderr

    def test_v3_rejects_missing_deep_target(self, workspace, tmp_path):
        """A dual portfolio cannot be archived with only one of its two targets."""
        run_dir = tmp_path / "v3_missing_deep_run"
        self._setup_v3_run_dir(run_dir)
        r = self._v3_create(workspace, tmp_path, run_dir, "v3-missing-deep", ("B1",))
        assert r.returncode != 0
        assert "must equal the frozen development_targets exactly" in r.stderr

    def test_v3_rejects_single_target_run_with_second_deep(self, workspace, tmp_path):
        """SINGLE_TARGET archives exactly one Deep; a second target fails closed."""
        run_dir = tmp_path / "v3_single_extra_run"
        self._setup_v3_run_dir(run_dir, mode="SINGLE_TARGET", target_order=("B1",),
                               targets_developed=("B1", "B2"))
        r = self._v3_create(workspace, tmp_path, run_dir, "v3-single-extra", ("B1", "B2"), count=6)
        assert r.returncode != 0
        assert "must equal the frozen development_targets exactly" in r.stderr

    def test_v3_rejects_development_artifact_with_wrong_target_id(self, workspace, tmp_path):
        """development-v2-B1.json declaring B2 must not be archived as the deep-B1 stage."""
        run_dir = tmp_path / "v3_wrong_content_run"
        self._setup_v3_run_dir(run_dir)
        self._write_artifact(
            run_dir, "development-v2-B1.json",
            self._v3_development("B2", "Mislabelled thesis", ["pass03:c01", "pass02:c01"])
        )
        r = self._v3_create(workspace, tmp_path, run_dir, "v3-wrong-content", ("B1", "B2"))
        assert r.returncode != 0
        assert "declares target 'B2', expected 'B1'" in r.stderr

    def _v3_stage_args(self, run_dir, labels):
        argv = []
        for label in labels:
            argv += ["--stage", f"{label}={run_dir}"]
        return argv

    _V3_BASE_LABELS = (
        "pass-01-normal",
        "pass-02-residual",
        "pass-03-rift",
        "search-field",
        "portfolio",
    )

    @pytest.mark.parametrize(
        "missing",
        ["pass-02-residual", "pass-03-rift", "search-field", "pass-01-normal", "portfolio"],
    )
    def test_v3_archive_requires_every_base_stage(self, workspace, tmp_path, missing):
        """The v3 base topology is mandatory, not implied by the pinned Deep targets."""
        run_dir = tmp_path / f"v3_base_missing_{missing}"
        run_dir.mkdir()
        self._setup_v3_run_dir(run_dir)
        acc = self._accounting(tmp_path, 6)
        labels = [l for l in self._V3_BASE_LABELS if l != missing] + ["deep-B1", "deep-B2"]
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", f"v3-missing-{missing}",
            "--skill-root", str(workspace["skill"]),
            *self._v3_stage_args(run_dir, labels),
            "--accounting", str(acc),
        )
        assert r.returncode != 0
        assert f"missing: {missing}" in r.stderr

    def test_v3_archive_rejects_a_fourth_search_pass(self, workspace, tmp_path):
        """pass-04 is not part of the three-pass v3 route and fails closed."""
        run_dir = tmp_path / "v3_fourth_pass_run"
        run_dir.mkdir()
        self._setup_v3_run_dir(run_dir)
        acc = self._accounting(tmp_path, 6)
        labels = list(self._V3_BASE_LABELS) + ["pass-04-normal", "deep-B1", "deep-B2"]
        r = run_bundle(
            "create",
            "--output-root", str(workspace["output"]),
            "--slug", "v3-fourth-pass",
            "--skill-root", str(workspace["skill"]),
            *self._v3_stage_args(run_dir, labels),
            "--accounting", str(acc),
        )
        assert r.returncode != 0
        assert "non-v3 stages: pass-04-normal" in r.stderr

    def test_v3_archive_rejects_development_frozen_against_a_stale_bundle_identity(
        self, workspace, tmp_path
    ):
        """A Deep artifact frozen before the portfolio existed (or against another
        bundle's members) carries member_refs the frozen bundle does not; the
        archive must fail closed even though the checkpoint never saw it."""
        run_dir = tmp_path / "v3_stale_identity_run"
        run_dir.mkdir()
        self._setup_v3_run_dir(run_dir)
        self._write_artifact(
            run_dir, "development-v2-B1.json",
            self._v3_development("B1", "Thesis against a stale identity",
                                 ["pass03:c01", "pass02:c01"]),
        )
        r = self._v3_create(workspace, tmp_path, run_dir, "v3-stale-identity", ("B1", "B2"))
        assert r.returncode != 0
        assert "the frozen bundle B1 carries" in r.stderr

    def test_v3_archive_rejects_comparative_standing_in_a_development(
        self, workspace, tmp_path
    ):
        """BONK v3 never compares its targets: a bundled Deep that opened a
        comparative channel fails the archive closed."""
        run_dir = tmp_path / "v3_comparative_run"
        run_dir.mkdir()
        self._setup_v3_run_dir(run_dir)
        dev = self._v3_development("B1", "Thesis with a rival",
                                   ["pass01:c01", "pass02:c01"])
        dev["developed_model"]["comparative_standing"] = {
            "rival_ref": "B2",
            "material_difference": "other mechanism",
            "selected_target_advantage": "cheaper",
            "rival_advantage_or_parity": "broader scope",
            "unresolved_competition": "unresolved",
        }
        self._write_artifact(run_dir, "development-v2-B1.json", dev)
        r = self._v3_create(workspace, tmp_path, run_dir, "v3-comparative", ("B1", "B2"))
        assert r.returncode != 0
        assert "BONK v3 never compares its targets" in r.stderr

    def test_v3_renderer_order_determinism_and_contract(self, tmp_path):
        """Plan tests 8, 9, 11 + delta: renderer order follows development_targets."""
        run_dir = tmp_path / "v3_render_run"
        self._setup_v3_run_dir(run_dir, target_order=("B2", "B1"))

        out1 = tmp_path / "v3-pack-1.md"
        out2 = tmp_path / "v3-pack-2.md"
        r1 = run_bundle("render", "--run-dir", str(run_dir), "--task", "Analyze trust", "--output", str(out1))
        assert r1.returncode == 0, r1.stderr
        r2 = run_bundle("render", "--run-dir", str(run_dir), "--task", "Analyze trust", "--output", str(out2))
        assert r2.returncode == 0, r2.stderr
        assert out1.read_bytes() == out2.read_bytes(), "v3 render is not byte-identical across runs"

        text = out1.read_text(encoding="utf-8")
        assert text.startswith("# Pizm BONK Development Pack\n")
        assert "## Original task" in text
        assert "Pass 1 — initial" in text and "Pass 2 — residual" in text and "Pass 3 — rift" in text
        assert "## Curated field" in text
        assert "## Bundles" in text
        assert "### B1 — P1 + P2" in text and "### B2 — P3 + P2" in text

        # Target A/B follow the frozen development_targets order (B2 first).
        a_idx = text.index("## Development Target A")
        b_idx = text.index("## Development Target B")
        assert a_idx < b_idx
        assert "### B2 —" in text[a_idx:b_idx]
        assert "### B1 —" in text[b_idx:]
        assert "Developed thesis for B2" in text[a_idx:b_idx]
        assert "Developed thesis for B1" in text[b_idx:]

        # Required target content
        for needle in (
            "Core claim B1", "Structural shift B1", "Mechanism B1", "Boundary B1",
            "### Mechanism and dynamics", "### Load-bearing claims",
            "### Predictions", "Break conditions:", "### Evidence debt",
        ):
            assert needle in text, f"missing {needle!r} in v3 development pack"

        assert "## Why these two were developed" in text
        assert "B1 changes the causal mechanism; B2 shifts the system boundary." in text

        assert "## Explicit non-claims" in text
        for needle in (
            "no winner selected",
            "models were not compared for truth",
            "no synthesis was performed",
            "no Critic readiness verdict was issued",
            "neither model is considered validated",
        ):
            assert needle in text
        assert "## Suggested downstream task" in text
        assert "## Machine artifacts" in text
        assert "- portfolio.json" in text

    def test_v3_renderer_emits_no_winner_or_comparison_verdict(self, tmp_path):
        """Plan test 9: v3 output carries no preference, winner, or readiness verdict."""
        run_dir = tmp_path / "v3_absence_run"
        self._setup_v3_run_dir(run_dir)
        out = tmp_path / "v3-absence.md"
        r = run_bundle("render", "--run-dir", str(run_dir), "--task", "Analyze trust", "--output", str(out))
        assert r.returncode == 0, r.stderr
        text = out.read_text(encoding="utf-8")

        for forbidden in (
            "MODEL_READY", "Winner", "## Critic", "## Lever", "## Comparison",
            "Current preference", "competition_axis", "auto_target",
            "LEFT", "RIGHT", "synthesize a third",
        ):
            assert forbidden not in text, f"v3 pack leaked {forbidden!r}"

        # Affirmative winner/preference vocabulary must not appear anywhere:
        # every occurrence of "winner"/"prefer" must be an explicit negation.
        for line in text.splitlines():
            lowered = line.lower()
            if "winner" in lowered or "prefer" in lowered:
                assert (
                    "no winner" in lowered
                    or "neither" in lowered
                    or "not contestants" in lowered
                ), f"affirmative verdict language leaked: {line!r}"

    def test_v3_renderer_single_target_and_why(self, tmp_path):
        """SINGLE_TARGET renders one target plus the frozen why-no-second-target prose."""
        run_dir = tmp_path / "v3_single_render_run"
        self._setup_v3_run_dir(run_dir, mode="SINGLE_TARGET", target_order=("B1",))
        out = tmp_path / "v3-single.md"
        r = run_bundle("render", "--run-dir", str(run_dir), "--task", "Analyze trust", "--output", str(out))
        assert r.returncode == 0, r.stderr
        text = out.read_text(encoding="utf-8")
        assert "## Development Target" in text
        assert "## Development Target A" not in text
        assert "## Development Target B" not in text
        assert "### B1 —" in text
        assert "## Why only this target was developed" in text
        assert "No second materially distinct bundle was defensible." in text
        assert "no winner selected" in text

    def test_v3_renderer_requires_every_development_artifact(self, tmp_path):
        """A v3 pack cannot be rendered with a development target missing."""
        run_dir = tmp_path / "v3_missing_dev_run"
        self._setup_v3_run_dir(run_dir, targets_developed=("B1",))
        out = tmp_path / "v3-missing.md"
        r = run_bundle("render", "--run-dir", str(run_dir), "--task", "Analyze trust", "--output", str(out))
        assert r.returncode != 0
        assert "missing artifact: development-v2-B2.json" in r.stderr

    def test_v2_legacy_bonk_with_comparison_and_lever_still_renders(self, tmp_path):
        """Plan tests 1 & 2: legacy v2 + comparison-review-v1 + LEVER stays readable."""
        run_dir = tmp_path / "v2_legacy_run"
        run_dir.mkdir()
        cand = {
            "schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "NORMAL",
            "candidates": [{"candidate_id": "c01", "title": "Legacy One"},
                           {"candidate_id": "c02", "title": "Legacy Two"}],
        }
        (run_dir / "candidates-pass01.json").write_text(json.dumps(cand), encoding="utf-8")
        (run_dir / "candidates-pass01.sha256").write_text(
            _sha256_hex((run_dir / "candidates-pass01.json").read_bytes()), encoding="utf-8")

        portfolio = {
            "schema_version": "pizm-portfolio-selection-v2", "stage": "portfolio", "route": "BONK",
            "field_hash": "h", "competition_status": "TWO_DEFENSIBLE_BUNDLES",
            "recommended_competition": {
                "left_bundle_id": "B1", "right_bundle_id": "B2",
                "competition_axis": "Legacy axis", "discriminating_observation": "Legacy observation",
            },
            "candidate_assessments": [
                {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong",
                 "unique_residue": "r1", "nearest_overlap": None, "reason": "g"},
                {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong",
                 "unique_residue": "r2", "nearest_overlap": None, "reason": "g"},
            ],
            "perspectives": {"P1": "pass01:c01", "P2": "pass01:c02"},
            "bundles": [self._v3_bundle("B1", ["pass01:c01", "pass01:c02"]),
                        self._v3_bundle("B2", ["pass01:c01", "pass01:c02"])],
        }
        (run_dir / "portfolio.json").write_text(json.dumps(portfolio), encoding="utf-8")
        (run_dir / "portfolio.sha256").write_text(
            _sha256_hex((run_dir / "portfolio.json").read_bytes()), encoding="utf-8")

        for t_id in ("B1", "B2"):
            dev = self._v3_development(t_id, f"Legacy thesis {t_id}",
                                       ["pass01:c01", "pass01:c02"])
            (run_dir / f"development-v2-{t_id}.json").write_text(json.dumps(dev), encoding="utf-8")
            (run_dir / f"development-v2-{t_id}.sha256").write_text(
                _sha256_hex((run_dir / f"development-v2-{t_id}.json").read_bytes()), encoding="utf-8")

        comparison = {
            "schema_version": "pizm-comparison-review-v1", "stage": "comparison-review-v1",
            "left_target_id": "B1", "right_target_id": "B2",
            "left_review": {"target_id": "B1", "terminal_state": "MODEL_READY"},
            "right_review": {"target_id": "B2", "terminal_state": "NEED_EVIDENCE"},
            "comparison": {
                "current_preference": "CONDITIONAL", "competition_axis": "Legacy axis",
                "strongest_reason_for_left": "l", "strongest_reason_for_right": "r",
                "shared_evidence_debt": [], "discriminating_observation": "Legacy observation",
                "what_would_change_the_decision": "w",
            },
        }
        (run_dir / "comparison-review-v1.json").write_text(json.dumps(comparison), encoding="utf-8")
        (run_dir / "comparison-review-v1.sha256").write_text(
            _sha256_hex((run_dir / "comparison-review-v1.json").read_bytes()), encoding="utf-8")

        design = {"schema_version": "pizm-lever-design-v1", "stage": "lever",
                  "levers": [{"lever_id": "L1", "intervention_or_test_point": "pilot"}]}
        lever_review = {"schema_version": "pizm-lever-review-v1", "stage": "lever-review",
                        "outcome": "ACCEPTED", "verdicts": [{"lever_id": "L1", "verdict": "ACCEPTED"}]}
        for name, data in (("design.json", design), ("review.json", lever_review)):
            (run_dir / name).write_text(json.dumps(data), encoding="utf-8")
            (run_dir / (name[:-5] + ".sha256")).write_text(
                _sha256_hex((run_dir / name).read_bytes()), encoding="utf-8")

        out = tmp_path / "v2-legacy.md"
        r = run_bundle("render", "--run-dir", str(run_dir), "--task", "Legacy task", "--output", str(out))
        assert r.returncode == 0, r.stderr
        text = out.read_text(encoding="utf-8")
        assert text.startswith("# Prism BONK\n")
        assert "## Deep B1" in text
        assert "## Deep B2" in text
        assert "Legacy thesis B1" in text
        assert "Current preference: **CONDITIONAL**" in text
        assert "## Lever" in text
        assert "ACCEPTED" in text

    def test_v3_html_unsupported_refusal(self, tmp_path):
        """render-html on a v3 run refuses with a stable non-zero error."""
        run_dir = tmp_path / "v3_html_run"
        self._setup_v3_run_dir(run_dir)
        out = tmp_path / "v3-run.html"
        r = run_bundle("render-html", "--run-dir", str(run_dir), "--task", "Analyze trust",
                       "--output", str(out))
        assert r.returncode != 0
        assert "BONK v3 HTML is not supported; use the markdown development pack handoff" in r.stderr
