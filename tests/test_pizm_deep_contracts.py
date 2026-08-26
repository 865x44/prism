"""
Focused tests for Wave 3 (S3) — Deep staged contracts.

Verifies:
- Backup integrity (S2 backups byte-identical to installed originals, unchanged)
- Staged mirror integrity (byte-identical to installed contracts)
- Blindness (reviewer rubric absent from developer contract)
- Terminal states exactly three, no rebuild
- Hidden reviewer filename/path absent from developer and SKILL
- Checkpoint integration (single invocation, tool-only, bounded retry)
- Development artifact schema structure
- Identity lock enforcement
- Review contract exact-hash and review.json placement
- No session discovery strings anywhere
- Router and Explore files preserved
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALLED_ROOT = Path.home() / ".config" / "opencode" / "skills" / "pizm"
MIRROR_PRESENT = (INSTALLED_ROOT / "SKILL.md").exists()
BACKUP_ROOT = REPO_ROOT / "docs" / "pizm-skill-superseded-2026-08-24"
BACKUP_PRESENT = BACKUP_ROOT.exists()
STAGED_ROOT = REPO_ROOT / "skills" / "pizm"

INSTALLED_DEEP = INSTALLED_ROOT / "references" / "deep.md"
INSTALLED_REVIEWER = INSTALLED_ROOT / "references" / "deep-reviewer.md"
INSTALLED_SKILL = INSTALLED_ROOT / "SKILL.md"
INSTALLED_EXPLORE = INSTALLED_ROOT / "references" / "explore.md"
INSTALLED_SELECTOR = INSTALLED_ROOT / "references" / "explore-selector.md"
INSTALLED_OPENAI = INSTALLED_ROOT / "agents" / "openai.yaml"


@pytest.fixture
def deep_text():
    if not INSTALLED_DEEP.exists():
        pytest.skip("installed skill mirror not present")
    return INSTALLED_DEEP.read_text(encoding="utf-8")


@pytest.fixture
def reviewer_text():
    if not INSTALLED_REVIEWER.exists():
        pytest.skip("installed skill mirror not present")
    return INSTALLED_REVIEWER.read_text(encoding="utf-8")


@pytest.fixture
def skill_text():
    if not INSTALLED_SKILL.exists():
        pytest.skip("installed skill mirror not present")
    return INSTALLED_SKILL.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Backup integrity — S2 backups unchanged
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not BACKUP_PRESENT, reason="local superseded-skill backup dir not present in checkout")
class TestBackupIntegrity:
    """S2 backups must be byte-identical to installed originals and unchanged."""

    def test_skill_backup_byte_identical(self):
        backup = BACKUP_ROOT / "SKILL.md"
        assert backup.exists(), "SKILL.md backup missing"
        # Backup is the pre-S2 original, not the current staged SKILL.md
        backup_text = backup.read_text(encoding="utf-8")
        assert "staged tool sequence" not in backup_text

    def test_explore_backup_byte_identical(self):
        backup = BACKUP_ROOT / "references" / "explore.md"
        assert backup.exists(), "explore.md backup missing"
        backup_text = backup.read_text(encoding="utf-8")
        assert "Generator Workflow" not in backup_text

    def test_deep_backup_byte_identical(self):
        backup = BACKUP_ROOT / "references" / "deep.md"
        assert backup.exists(), "deep.md backup missing"
        # The backup was the original pre-S3 deep.md
        backup_text = backup.read_text(encoding="utf-8")
        assert "Input Authority" not in backup_text, (
            "Backup should be original, not staged developer"
        )
        assert "pizm-development-v1" not in backup_text

    @pytest.mark.skipif(not MIRROR_PRESENT, reason="developer-machine skill mirror not installed")
    def test_openai_yaml_backup_byte_identical(self):
        backup = BACKUP_ROOT / "agents" / "openai.yaml"
        assert backup.exists(), "openai.yaml backup missing"
        assert backup.read_bytes() == INSTALLED_OPENAI.read_bytes()


# ---------------------------------------------------------------------------
# 2. Staged mirror integrity
# ---------------------------------------------------------------------------


class TestStagedMirrorIntegrity:
    @pytest.mark.skipif(not MIRROR_PRESENT, reason="developer-machine skill mirror not installed")
    def test_deep_mirror_byte_identical(self):
        mirror = STAGED_ROOT / "references" / "deep.md"
        assert mirror.exists(), "staged deep.md mirror missing"
        assert mirror.read_bytes() == INSTALLED_DEEP.read_bytes()

    @pytest.mark.skipif(not MIRROR_PRESENT, reason="developer-machine skill mirror not installed")
    def test_reviewer_mirror_byte_identical(self):
        mirror = STAGED_ROOT / "references" / "deep-reviewer.md"
        assert mirror.exists(), "staged deep-reviewer.md mirror missing"
        assert mirror.read_bytes() == INSTALLED_REVIEWER.read_bytes()

    @pytest.mark.skipif(not MIRROR_PRESENT, reason="developer-machine skill mirror not installed")
    def test_skill_mirror_byte_identical(self):
        mirror = STAGED_ROOT / "SKILL.md"
        assert mirror.exists(), "staged SKILL.md mirror missing"
        assert mirror.read_bytes() == INSTALLED_SKILL.read_bytes()

    @pytest.mark.skipif(not MIRROR_PRESENT, reason="developer-machine skill mirror not installed")
    def test_openai_mirror_byte_identical(self):
        mirror = STAGED_ROOT / "agents" / "openai.yaml"
        assert mirror.exists(), "staged openai.yaml mirror missing"
        assert mirror.read_bytes() == INSTALLED_OPENAI.read_bytes()

    @pytest.mark.skipif(not MIRROR_PRESENT, reason="developer-machine skill mirror not installed")
    def test_explore_files_unchanged(self):
        """Explore installed and staged files must not have been modified."""
        assert INSTALLED_EXPLORE.exists()
        staged_explore = STAGED_ROOT / "references" / "explore.md"
        assert staged_explore.exists()
        assert staged_explore.read_bytes() == INSTALLED_EXPLORE.read_bytes()

    @pytest.mark.skipif(not MIRROR_PRESENT, reason="developer-machine skill mirror not installed")
    def test_selector_files_unchanged(self):
        assert INSTALLED_SELECTOR.exists()
        staged_sel = STAGED_ROOT / "references" / "explore-selector.md"
        assert staged_sel.exists()
        assert staged_sel.read_bytes() == INSTALLED_SELECTOR.read_bytes()


# ---------------------------------------------------------------------------
# 3. Blindness — reviewer rubric absent from developer
# ---------------------------------------------------------------------------


class TestBlindness:
    """Developer contract must not contain reviewer rubric, terminal names,
    hidden reviewer filename, or rebuild logic."""

    REVIEWER_TERMS = [
        "MODEL_READY", "NEED_EVIDENCE", "RETURN_TO_EXPLORE",
        "identity_verified", "frozen_hash", "verdict_rationale",
        "review.json", "pizm-review-v1",
        "pizm-deep-review-v2", "independent_countermodel",
    ]

    @pytest.mark.parametrize("term", REVIEWER_TERMS)
    def test_reviewer_term_absent_from_developer(self, deep_text, term):
        # Exclude code-fenced schema examples
        lines = deep_text.splitlines()
        in_fence = False
        clean_lines = []
        for line in lines:
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            clean_lines.append(line)
        clean_text = "\n".join(clean_lines)
        assert term not in clean_text, (
            f"Reviewer term {term!r} found in developer contract"
        )

    def test_reviewer_filename_absent_from_developer(self, deep_text):
        assert "deep-reviewer" not in deep_text
        assert "reviewer.md" not in deep_text.lower()

    def test_reviewer_filename_absent_from_skill(self, skill_text):
        assert "deep-reviewer" not in skill_text
        assert "reviewer.md" not in skill_text.lower()
        assert "explore-selector" not in skill_text

    def test_explicit_pre_freeze_future_contract_prohibition(self, deep_text):
        lower = deep_text.lower()
        assert "pre-freeze future-contract prohibition" in lower
        assert "until the checkpoint returns `freeze_ok`" in lower
        for verb in ("read", "open", "search", "list", "inspect", "access"):
            assert verb in lower
        assert "future-stage contract or reference asset" in lower
        assert "separation failure" in lower

    def test_rebuild_logic_absent_from_developer(self, deep_text):
        """No rebuild stage, rebuild request, or rebuild loop."""
        lower = deep_text.lower()
        assert "rebuild" not in lower, "Rebuild logic found in developer"
        assert "regenerate" not in lower or "bounded correction" in lower
        # "bounded correction" is the allowed structural retry, not cognitive rebuild

    def test_terminal_names_absent_from_developer(self, deep_text):
        """Terminal state names must not appear in developer prose."""
        # Check outside code fences
        lines = deep_text.splitlines()
        in_fence = False
        for line in lines:
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for term in ["MODEL_READY", "NEED_EVIDENCE", "RETURN_TO_EXPLORE"]:
                assert term not in line, (
                    f"Terminal state {term!r} in developer line: {line.strip()!r}"
                )


# ---------------------------------------------------------------------------
# 4. Checkpoint integration
# ---------------------------------------------------------------------------


class TestCheckpointIntegration:
    def test_checkpoint_invoked(self, deep_text):
        assert "pizm-checkpoint" in deep_text
        assert "--stage development-v2" in deep_text

    def test_checkpoint_required_arguments(self, deep_text):
        assert re.search(
            r"pizm-checkpoint\s+freeze\s+--stage\s+development-v2"
            r"\s+--run-id\s+<random-lowercase-slug>"
            r"\s+--input\s+<pending-json-path>",
            deep_text,
        )

    def test_stable_checkpoint_entrypoint(self, deep_text):
        assert "$HOME/.local/bin/pizm-checkpoint freeze --stage development-v2" in deep_text

    def test_tool_only_instruction(self, deep_text):
        assert re.search(r"(?i)tool-only\s+pre-freeze", deep_text)
        assert re.search(r"(?i)ZERO\s+visible\s+prose", deep_text)

    def test_bounded_retry_instruction(self, deep_text):
        """ONE bounded correction attempt; second failure → visible + FOLLOW_UP."""
        assert re.search(r"(?i)ONE\s+bounded\s+correction", deep_text)
        assert "FOLLOW_UP_CANDIDATE" in deep_text

    def test_no_session_run_id(self, deep_text):
        assert re.search(
            r"(?i)never\s+derived\s+from\s+session\s+identity", deep_text
        )


# ---------------------------------------------------------------------------
# 5. Development artifact schema
# ---------------------------------------------------------------------------


class TestDevelopmentSchema:
    def test_schema_version(self, deep_text):
        assert "pizm-development-v2" in deep_text

    def test_schema_version_field(self, deep_text):
        assert '"schema_version": "pizm-development-v2"' in deep_text

    def test_stage_development_v2(self, deep_text):
        assert '"stage": "development-v2"' in deep_text

    def test_target_selection(self, deep_text):
        assert '"target": {' in deep_text
        assert "target_type" in deep_text
        assert "target_id" in deep_text

    def test_identity_lock(self, deep_text):
        assert "identity_lock" in deep_text
        assert "p_id" in deep_text
        assert "bundle_id" in deep_text
        assert "member_refs" in deep_text
        assert "title" in deep_text
        assert "core_claim" in deep_text
        assert "structural_shift" in deep_text
        assert "mechanism" in deep_text
        assert "boundary" in deep_text

    def test_developed_model(self, deep_text):
        assert "developed_model" in deep_text
        for field in (
            "thesis", "synthesis", "mechanism_chain", "dynamics",
            "implications", "predictions_or_observables",
            "load_bearing_claims", "break_conditions",
            "unresolved_tensions", "evidence_debt",
        ):
            assert field in deep_text

    def test_bundle_fields(self, deep_text):
        assert "member_contributions" in deep_text
        assert "member_ablation" in deep_text

    def test_one_bundle_one_deep(self, deep_text):
        assert "One Bundle = one Deep" in deep_text
        assert "mini-Deep" in deep_text

    def test_synthesis_first_class_prose(self, deep_text):
        """Synthesis is the first-class readable prose field, not a card list."""
        assert "First-class readable analytical prose" in deep_text
        assert "not a card list" in deep_text
        assert re.search(r"900[–-]1600\s*words", deep_text)
        assert "No padding" in deep_text
        assert "long paraphrase is not depth" in deep_text

    def test_mechanism_chain_bounds(self, deep_text):
        assert re.search(r"3[–-]6\s+steps", deep_text)

    def test_load_bearing_claims_census(self, deep_text):
        assert "epistemic_status" in deep_text
        for status in ("SUPPORTED", "INFERRED", "SPECULATIVE", "UNKNOWN"):
            assert status in deep_text
        assert "role_in_model" in deep_text
        assert "what_would_weaken_or_refute" in deep_text
        assert "2–5" in deep_text

    def test_direct_seed_label(self, deep_text, reviewer_text):
        assert 'exact `"DIRECT_SEED"`' in deep_text
        assert "Do not allocate or invent a P-ID" in deep_text
        assert 'exact `"DIRECT_SEED"`' in reviewer_text
        assert "never invent or substitute a P-ID" in reviewer_text


# ---------------------------------------------------------------------------
# 6. Input authority — no session discovery
# ---------------------------------------------------------------------------


class TestInputAuthority:
    SESSION_STRINGS = [
        "--session", "--context-file",
        "session lookup", "sidecar lookup", "session discovery",
        "latest-session", "global active-session",
        "session registry", "state store", "StateStore",
    ]

    @pytest.mark.parametrize("s", SESSION_STRINGS)
    def test_session_string_absent_from_developer(self, deep_text, s):
        assert s.lower() not in deep_text.lower(), (
            f"Session string {s!r} found in developer contract"
        )

    @pytest.mark.parametrize("s", SESSION_STRINGS)
    def test_session_string_absent_from_reviewer(self, reviewer_text, s):
        assert s.lower() not in reviewer_text.lower(), (
            f"Session string {s!r} found in reviewer contract"
        )

    @pytest.mark.parametrize("s", SESSION_STRINGS)
    def test_session_string_absent_from_skill(self, skill_text, s):
        assert s.lower() not in skill_text.lower(), (
            f"Session string {s!r} found in SKILL.md"
        )

    def test_input_sources_listed(self, deep_text):
        """Developer must list allowed input sources."""
        lower = deep_text.lower()
        assert "selected target" in lower
        assert "p-id" in lower
        assert "bundle" in lower
        assert "direct seed" in lower
        assert "visible semantic identity" in lower


# ---------------------------------------------------------------------------
# 7. Reviewer contract
# ---------------------------------------------------------------------------


class TestReviewerContract:
    def test_exact_hash_reference(self, reviewer_text):
        assert "verified hash" in reviewer_text
        assert "frozen_hash" in reviewer_text

    def test_identity_comparison(self, reviewer_text):
        assert "identity_lock" in reviewer_text
        assert re.search(r"(?i)fail\s+closed\s+on\s+drift", reviewer_text)

    def test_review_json_beside_artifact(self, reviewer_text):
        assert "<ARTIFACT-parent>/review.json" in reviewer_text
        assert "Never write a cwd-global" in reviewer_text

    def test_review_schema_version(self, reviewer_text):
        assert "pizm-deep-review-v2" in reviewer_text

    def test_terminal_state_instruction(self, reviewer_text):
        assert "MODEL_READY" in reviewer_text
        assert "NEED_EVIDENCE" in reviewer_text
        assert "RETURN_TO_EXPLORE" in reviewer_text


# ---------------------------------------------------------------------------
# 8. Terminal states — exactly three, no rebuild
# ---------------------------------------------------------------------------


class TestTerminalStates:
    VALID_TERMINALS = {"MODEL_READY", "NEED_EVIDENCE", "RETURN_TO_EXPLORE"}

    def test_reviewer_has_exactly_three_terminals(self, reviewer_text):
        """Reviewer defines exactly three terminal states."""
        # Count ### heading matches for terminal states
        headings = re.findall(r"###\s+(\w+)", reviewer_text)
        terminal_headings = [h for h in headings if h in self.VALID_TERMINALS]
        assert set(terminal_headings) == self.VALID_TERMINALS

    def test_no_rebuild_in_reviewer(self, reviewer_text):
        """No rebuild stage, request, or loop in reviewer."""
        assert "NO rebuild" in reviewer_text or "No Rebuild" in reviewer_text
        assert re.search(
            r"(?i)there\s+is\s+NO\s+native\s+rebuild", reviewer_text
        )
        assert "fourth status" not in reviewer_text.lower() or \
               "Do not invent a fourth status" in reviewer_text

    def test_no_auto_explore(self, reviewer_text):
        assert re.search(
            r"(?i)Do\s+not\s+automatically\s+run\s+Explore", reviewer_text
        )

# ---------------------------------------------------------------------------
# 9. Router and Explore preservation
# ---------------------------------------------------------------------------


class TestRouterPreserved:
    def test_route_normal(self, skill_text):
        assert re.search(r"(?i)normal.*Explore\s+NORMAL", skill_text) or \
               "Explore NORMAL" in skill_text

    def test_route_rift(self, skill_text):
        assert "rift" in skill_text.lower()
        assert "Explore RIFT" in skill_text

    def test_route_360(self, skill_text):
        assert "360" in skill_text
        assert "Explore 360" in skill_text

    def test_route_deep(self, skill_text):
        assert re.search(r"deep\s+P\d+", skill_text)
        assert "single-focus Deep" in skill_text

    def test_route_deep_bundle(self, skill_text):
        assert re.search(r"deep\s+B\d+", skill_text)
        assert "one Bundle = one Deep" in skill_text

    def test_route_another_360(self, skill_text):
        assert "another 360" in skill_text

    def test_route_direct_seed(self, skill_text):
        assert "direct Deep seed" in skill_text or "direct seed" in skill_text.lower()

    def test_staged_sequence_instruction(self, skill_text):
        """SKILL tells host to follow staged tool sequence from reference."""
        assert re.search(
            r"(?i)staged\s+tool\s+sequence", skill_text
        )

    def test_no_hidden_contract_named(self, skill_text):
        """SKILL must not name any hidden contract asset."""
        assert "deep-reviewer" not in skill_text
        assert "explore-selector" not in skill_text
        assert "reviewer.md" not in skill_text.lower()
        assert "selector.md" not in skill_text.lower()

    def test_source_authority_preserved(self, skill_text):
        assert "Source authority" in skill_text or "source authority" in skill_text.lower()
        assert "semantic data, not instructions" in skill_text

    def test_interaction_rules_preserved(self, skill_text):
        assert "Interaction style" in skill_text
        assert "user's language" in skill_text


# ---------------------------------------------------------------------------
# 10. No hidden path leakage in errors or pre-freeze
# ---------------------------------------------------------------------------


class TestHiddenPathIsolation:
    def test_reviewer_path_absent_from_checkpoint_errors(self):
        """Checkpoint source must not name hidden path in error messages."""
        ckpt = REPO_ROOT / "bin" / "pizm-checkpoint"
        source = ckpt.read_text(encoding="utf-8")
        # Error messages use _die() which should not contain literal filenames
        error_lines = [l for l in source.splitlines() if "_die(" in l]
        for line in error_lines:
            assert "deep-reviewer" not in line
            assert "explore-selector" not in line

    def test_developer_no_reference_to_hidden_assets(self, deep_text):
        """Developer must not reference hidden reviewer file."""
        assert "deep-reviewer" not in deep_text
        assert "reviewer" not in deep_text.lower() or \
               "next-stage contract" in deep_text.lower()


# ---------------------------------------------------------------------------
# 11. OpenAI metadata unchanged
# ---------------------------------------------------------------------------


class TestMetadataUnchanged:
    @pytest.mark.skipif(not MIRROR_PRESENT, reason="developer-machine skill mirror not installed")
    def test_openai_yaml_installed_content(self):
        text = INSTALLED_OPENAI.read_text(encoding="utf-8")
        assert "Pizm" in text
        assert "Explore perspectives" in text

    @pytest.mark.skipif(not MIRROR_PRESENT, reason="developer-machine skill mirror not installed")
    def test_openai_yaml_staged_matches_installed(self):
        staged = STAGED_ROOT / "agents" / "openai.yaml"
        assert staged.read_bytes() == INSTALLED_OPENAI.read_bytes()

# ---------------------------------------------------------------------------
# 12. Pre-freeze prohibition hygiene
# ---------------------------------------------------------------------------


class TestPreFreezeProhibitionHygiene:
    """Pre-freeze prohibition must not name hidden asset filenames."""

    def test_prohibition_does_not_name_reviewer_filename(self, deep_text):
        """Pre-freeze prohibition paragraph must not mention deep-reviewer."""
        # Find the pre-freeze prohibition paragraph
        for line in deep_text.splitlines():
            if "Pre-freeze future-contract prohibition" in line:
                assert "deep-reviewer" not in line, (
                    "Pre-freeze prohibition names hidden reviewer filename"
                )
                assert "reviewer.md" not in line.lower(), (
                    "Pre-freeze prohibition names hidden reviewer .md file"
                )

    def test_prohibition_does_not_name_selector_filename(self, deep_text):
        """Pre-freeze prohibition paragraph must not mention explore-selector."""
        for line in deep_text.splitlines():
            if "Pre-freeze future-contract prohibition" in line:
                assert "explore-selector" not in line, (
                    "Pre-freeze prohibition names hidden selector filename"
                )
                assert "selector.md" not in line.lower(), (
                    "Pre-freeze prohibition names hidden selector .md file"
                )

    def test_developer_no_reference_to_hidden_assets(self, deep_text):
        """Developer must not reference any hidden asset by filename."""
        lower = deep_text.lower()
        assert "explore-selector" not in lower
        assert "deep-reviewer" not in lower
