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
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

BUNDLE_CLI = str(Path(__file__).resolve().parent.parent / "bin" / "pizm-session-bundle")
REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = REPO_ROOT / "prism-runs" / "session-sample-offline-20260824"


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
