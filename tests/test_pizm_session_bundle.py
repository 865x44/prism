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
        assert "accounting input is required for AUTO/FORGE" in r.stderr


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
        assert manifest["accounting"]["semantic_stage_count"] == 7
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
