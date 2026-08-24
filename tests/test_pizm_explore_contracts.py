"""
Focused tests for Wave 2 (S2) — Explore staged contracts.

Verifies:
- Backup integrity against immutable pre-edit SHA-256 values
- Staged mirror integrity (byte-identical to installed contracts)
- Blindness (selector rubric absent from generator)
- A1 hygiene (no self-assessment in generator)
- Checkpoint integration (single invocation)
- A2 bounded retry + FOLLOW_UP_CANDIDATE
- Candidate schema structure
- Migration notes completeness
- Mode routing (NORMAL/360/RIFT)
- Selector categorical (no numeric scoring)
- Raw pool hiding
- A5 P-ID monotonicity guard
- Hidden filename not referenced in generator
"""
import hashlib
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALLED_ROOT = Path.home() / ".config" / "opencode" / "skills" / "pizm"
BACKUP_ROOT = REPO_ROOT / "docs" / "pizm-skill-superseded-2026-08-24"
STAGED_ROOT = REPO_ROOT / "docs" / "pizm-skill-staged-2026-08-24"

EXPECTED_BACKUP_SHA256 = {
    "SKILL.md": "9f50a1ff3c9a9116d31d41b4e7f3f3e24d15a72c165d0224f4ad8a73b7b33eeb",
    "references/explore.md": "ecef87bfba639295abfb3119573c710fe356c703e5fe512ad50d884ef96a48dd",
    "references/deep.md": "ed71b8e9aab58e0c1f281e5078efc2e72e8d90cf79c70f9203c7bb189f69423d",
    "agents/openai.yaml": "78aafc68f958699ad4909ac31e6e5ce0d122854664159a8b9aa21ce5310a1148",
}

INSTALLED_EXPLORE = INSTALLED_ROOT / "references" / "explore.md"
INSTALLED_SELECTOR = INSTALLED_ROOT / "references" / "explore-selector.md"
INSTALLED_SKILL = INSTALLED_ROOT / "SKILL.md"
INSTALLED_DEEP = INSTALLED_ROOT / "references" / "deep.md"
INSTALLED_OPENAI = INSTALLED_ROOT / "agents" / "openai.yaml"


@pytest.fixture
def explore_text():
    return INSTALLED_EXPLORE.read_text(encoding="utf-8")


@pytest.fixture
def selector_text():
    return INSTALLED_SELECTOR.read_text(encoding="utf-8")


@pytest.fixture
def skill_text():
    return INSTALLED_SKILL.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Backup integrity
# ---------------------------------------------------------------------------


class TestBackupIntegrity:
    @pytest.mark.parametrize(
        ("relative_path", "expected_sha256"),
        EXPECTED_BACKUP_SHA256.items(),
    )
    def test_pre_edit_backup_hash(self, relative_path, expected_sha256):
        backup = BACKUP_ROOT / relative_path
        assert backup.exists(), f"{relative_path} backup missing"
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == expected_sha256

    def test_explore_backup_is_pre_staging(self):
        backup_text = (BACKUP_ROOT / "references" / "explore.md").read_text(
            encoding="utf-8"
        )
        assert "In staged execution" not in backup_text
        assert "Generator Workflow" not in backup_text
        assert "pizm-candidates-v1" not in backup_text


# ---------------------------------------------------------------------------
# 2. Staged mirror integrity
# ---------------------------------------------------------------------------


class TestStagedMirrorIntegrity:
    def test_explore_mirror_byte_identical(self):
        mirror = STAGED_ROOT / "references" / "explore.md"
        assert mirror.exists(), "staged explore.md mirror missing"
        assert mirror.read_bytes() == INSTALLED_EXPLORE.read_bytes()

    def test_selector_mirror_byte_identical(self):
        mirror = STAGED_ROOT / "references" / "explore-selector.md"
        assert mirror.exists(), "staged explore-selector.md mirror missing"
        assert mirror.read_bytes() == INSTALLED_SELECTOR.read_bytes()


# ---------------------------------------------------------------------------
# 3. Blindness — selector rubric absent from generator
# ---------------------------------------------------------------------------


class TestBlindness:
    SELECTOR_TERMS = [
        "KEEP", "DROP", "MERGE", "BORDERLINE",
        "standalone_quality", "marginal_contribution", "disposition",
    ]

    @pytest.mark.parametrize("term", SELECTOR_TERMS)
    def test_selector_term_absent_from_generator(self, explore_text, term):
        # Exclude migration-notes block and code fences for schema examples
        lines = explore_text.splitlines()
        in_migration = False
        clean_lines = []
        for line in lines:
            if line.strip().startswith("<!-- migration-notes"):
                in_migration = True
                continue
            if in_migration and line.strip() == "-->":
                in_migration = False
                continue
            if in_migration:
                continue
            clean_lines.append(line)
        clean_text = "\n".join(clean_lines)
        assert term not in clean_text, (
            f"Selector term {term!r} found in generator contract"
        )

    def test_selector_term_absent_from_skill(self, skill_text):
        for term in self.SELECTOR_TERMS:
            assert term not in skill_text, (
                f"Selector term {term!r} found in SKILL.md"
            )

    def test_explicit_pre_freeze_future_contract_prohibition(self, explore_text):
        lower = explore_text.lower()
        assert "pre-freeze future-contract prohibition" in lower
        assert "until the checkpoint returns `freeze_ok`" in lower
        for verb in ("read", "open", "search", "list", "inspect", "access"):
            assert verb in lower
        assert "future-stage contract or reference asset" in lower
        assert "separation failure" in lower


# ---------------------------------------------------------------------------
# 4. A1 hygiene — no self-assessment in generator
# ---------------------------------------------------------------------------


class TestA1Hygiene:
    SELF_ASSESSMENT_PATTERNS = [
        r"(?i)\bself[- ]?assess",
        r"(?i)\bself[- ]?evaluat",
        r"(?i)\bself[- ]?scor",
        r"(?i)\bpredicted\s+(KEEP|DROP|MERGE)",
        r"(?i)\branking\s+hint",
        r"(?i)\bweakest\s+candidate",
        r"(?i)\bstrongest\s+candidate",
        r"(?i)\bconfidence\s+percent",
    ]

    @pytest.mark.parametrize("pattern", SELF_ASSESSMENT_PATTERNS)
    def test_no_self_assessment_in_generator(self, explore_text, pattern):
        # Check line-by-line, skipping lines that are prohibition instructions
        for line in explore_text.splitlines():
            stripped = line.strip()
            # Skip prohibition/instruction lines (these reference the banned terms)
            if stripped.startswith("- Do not ") or stripped.startswith("Do not "):
                continue
            assert not re.search(pattern, line), (
                f"Self-assessment pattern {pattern!r} found in generator line: {line!r}"
            )


# ---------------------------------------------------------------------------
# 5. Checkpoint integration — exactly one invocation
# ---------------------------------------------------------------------------


class TestCheckpointIntegration:
    def test_checkpoint_invoked(self, explore_text):
        assert "pizm-checkpoint freeze --stage explore" in explore_text

    def test_checkpoint_invoked_exactly_once(self, explore_text):
        count = explore_text.count("pizm-checkpoint freeze --stage explore")
        assert count == 1, f"Expected 1 checkpoint invocation, found {count}"

    def test_stable_checkpoint_entrypoint(self, explore_text):
        assert "$HOME/.local/bin/pizm-checkpoint freeze --stage explore" in explore_text
        assert "bin/pizm-checkpoint freeze --stage explore" in explore_text


    def test_tool_only_pre_freeze_turn(self, explore_text):
        """Verify generator requires tool-only turn with ZERO visible prose"""
        assert "ZERO visible prose" in explore_text or "ZERO prose" in explore_text, \
            "Generator must state pre-freeze turn contains ZERO visible prose"
        assert "ONLY tool calls" in explore_text or "only tool calls" in explore_text, \
            "Generator must state pre-freeze turn contains ONLY tool calls"

    def test_run_id_slug_not_session(self, explore_text):
        """Verify run-id is timestamp/random slug, never session-derived"""
        assert "slug" in explore_text, "Generator must specify slug for run-id"
        assert "timestamp" in explore_text or "random" in explore_text, \
            "Generator must specify timestamp or random slug for run-id"
        assert "never derived from session" in explore_text or "never session" in explore_text or "not session" in explore_text.lower(), \
            "Generator must explicitly prohibit session-derived run-id"

# ---------------------------------------------------------------------------
# 6. A2 bounded retry + FOLLOW_UP_CANDIDATE
# ---------------------------------------------------------------------------


class TestA2FailurePath:
    def test_bounded_retry_mentioned(self, explore_text):
        assert re.search(r"(?i)ONE\s+bounded\s+regeneration", explore_text) or \
               re.search(r"(?i)one\s+bounded\s+retry", explore_text) or \
               re.search(r"(?i)second\s+time", explore_text)

    def test_follow_up_candidate_on_failure(self, explore_text):
        assert "FOLLOW_UP_CANDIDATE" in explore_text

    def test_no_further_retries(self, explore_text):
        assert re.search(r"(?i)without\s+further\s+retries", explore_text) or \
               re.search(r"(?i)stop\s+execution", explore_text)


# ---------------------------------------------------------------------------
# 7. Candidate schema structure
# ---------------------------------------------------------------------------


class TestCandidateSchema:
    def test_schema_version(self, explore_text):
        assert "pizm-candidates-v1" in explore_text

    def test_stage_field(self, explore_text):
        assert '"stage": "explore"' in explore_text

    def test_mode_field(self, explore_text):
        assert "NORMAL|360|RIFT" in explore_text

    def test_candidates_array(self, explore_text):
        assert '"candidates"' in explore_text

    def test_candidate_id(self, explore_text):
        assert '"candidate_id"' in explore_text

    def test_semantic_core(self, explore_text):
        assert '"semantic_core"' in explore_text

    def test_semantic_core_fields(self, explore_text):
        for field in ["claim", "structural_shift", "mechanism",
                       "grounding_anchor", "what_becomes_visible", "boundary"]:
            assert f'"{field}"' in explore_text, f"Missing semantic_core field: {field}"

    def test_epistemics(self, explore_text):
        assert '"epistemics"' in explore_text
        for cat in ["supported", "inferred", "speculative", "unknown"]:
            assert f'"{cat}"' in explore_text, f"Missing epistemics category: {cat}"

    def test_break_condition(self, explore_text):
        assert "break_condition" in explore_text

    def test_difference_from_prior_360(self, explore_text):
        assert "difference_from_prior" in explore_text

    def test_rift_extras(self, explore_text):
        assert "rift_extras" in explore_text


# ---------------------------------------------------------------------------
# 8. Migration notes
# ---------------------------------------------------------------------------


class TestMigrationNotes:
    def test_migration_notes_present(self, explore_text):
        assert "<!-- migration-notes" in explore_text

    def test_migration_notes_cover_epistemics(self, explore_text):
        assert re.search(r"epistemics:\s*kept", explore_text)

    def test_migration_notes_cover_break_condition(self, explore_text):
        assert re.search(r"break_condition:\s*kept", explore_text)

    def test_migration_notes_cover_return_path(self, explore_text):
        assert re.search(r"return_path:\s*RIFT", explore_text)

    def test_migration_notes_cover_default_frame(self, explore_text):
        assert re.search(r"default_frame:\s*derived", explore_text)

    def test_migration_notes_cover_blind_spot(self, explore_text):
        assert re.search(r"blind_spot:\s*represented", explore_text)

    def test_migration_notes_cover_operator_provenance(self, explore_text):
        assert re.search(r"operator provenance:\s*represented", explore_text, re.I)


# ---------------------------------------------------------------------------
# 9. Routing preserved — NORMAL/360/RIFT
# ---------------------------------------------------------------------------


class TestRoutingPreserved:
    @pytest.mark.parametrize("mode", ["NORMAL", "360", "RIFT"])
    def test_mode_present(self, explore_text, mode):
        assert f"### {mode}" in explore_text, f"Mode {mode} missing from generator"


# ---------------------------------------------------------------------------
# 10. Selector categorical — no numeric scoring
# ---------------------------------------------------------------------------



class TestSelectorCategorical:
    DISPOSITIONS = ["KEEP", "BORDERLINE", "MERGE", "DROP"]

    @pytest.mark.parametrize("disp", DISPOSITIONS)
    def test_disposition_present(self, selector_text, disp):
        assert disp in selector_text

    def test_no_numeric_scoring(self, selector_text):
        numeric_patterns = [
            r"(?i)\bnumeric\s+score",
            r"(?i)\bscore\s+arithmetic",
            r"(?i)\btop[- ]?N",
            r"(?i)\branking\s+formula",
            r"\b[0-9]+\s*/\s*[0-9]+\s*(score|point)",
        ]
        # Check line-by-line, skipping prohibition lines
        for line in selector_text.splitlines():
            stripped = line.strip()
            if "Strict Prohibition" in stripped or "Do NOT use" in stripped:
                continue
            for pat in numeric_patterns:
                assert not re.search(pat, line), \
                    f"Numeric scoring pattern {pat!r} found in selector line: {line!r}"

    def test_strict_prohibition_numeric(self, selector_text):
        assert "Do NOT use numeric scores" in selector_text

    def test_standalone_quality_enum_values(self, selector_text):
        """Verify standalone_quality uses Core enum: strong|borderline|weak"""
        assert re.search(r'standalone_quality.*strong\|borderline\|weak', selector_text), \
            "standalone_quality must be strong|borderline|weak (Core enum)"
        # Check for removed enum values (should NOT be present in schema)
        schema_match = re.search(r'```json\s*\{.*?"standalone_quality".*?\}\s*```', selector_text, re.DOTALL)
        if schema_match:
            schema_text = schema_match.group(0)
            assert 'adequate' not in schema_text, "adequate is not a valid standalone_quality value"
            assert 'decorative' not in schema_text, "decorative is not a valid standalone_quality value"

    def test_marginal_contribution_enum_values(self, selector_text):
        """Verify marginal_contribution uses Core enum: high|medium|low|none"""
        assert re.search(r'marginal_contribution.*high\|medium\|low\|none', selector_text), \
            "marginal_contribution must be high|medium|low|none (Core enum)"
        # Check for removed enum values (should NOT be present in schema)
        schema_match = re.search(r'```json\s*\{.*?"marginal_contribution".*?\}\s*```', selector_text, re.DOTALL)
        if schema_match:
            schema_text = schema_match.group(0)
            assert 'distinct' not in schema_text, "distinct is not a valid marginal_contribution value"
            assert 'incremental' not in schema_text, "incremental is not a valid marginal_contribution value"
            assert 'redundant' not in schema_text, "redundant is not a valid marginal_contribution value"
            assert 'noise' not in schema_text, "noise is not a valid marginal_contribution value"

    def test_tool_only_selection_json_write(self, selector_text):
        """Selector writes selection evidence beside the frozen pool, never cwd-global."""
        has_selection_json = "selection.json" in selector_text
        has_tool_write = re.search(
            r"tool.?call|via tool|write.*tool|tool.*write",
            selector_text,
            re.IGNORECASE,
        )
        assert has_selection_json and has_tool_write, (
            "Selector must require writing selection.json via tool call, not visible prose"
        )
        assert "<ARTIFACT-parent>/selection.json" in selector_text
        assert "Never write a cwd-global `selection.json`" in selector_text


class TestRawPoolHiding:
    def test_hide_raw_pool_instruction(self, selector_text):
        assert re.search(r"(?i)hide\s+raw\s+pool", selector_text) or \
               re.search(r"(?i)never\s+show\s+the\s+raw\s+candidate\s+pool", selector_text)

    def test_present_only_survivors(self, selector_text):
        assert re.search(r"(?i)only\s+kept\s+and\s+merged", selector_text) or \
               re.search(r"(?i)present\s+only\s+survivors", selector_text) or \
               re.search(r"(?i)render\s+only\s+survivors", selector_text)


# ---------------------------------------------------------------------------
# 12. A5 P-ID monotonicity guard
# ---------------------------------------------------------------------------


class TestA5PIDGuard:
    def test_next_free_p_instruction(self, selector_text):
        assert "Next free P: P<n>" in selector_text

    def test_derive_max_p(self, selector_text):
        assert re.search(r"(?i)derive\s+(the\s+)?current\s+max", selector_text)

    def test_strictly_increasing(self, selector_text):
        assert re.search(r"(?i)strictly\s+increasing", selector_text)


# ---------------------------------------------------------------------------
# 13. Hidden filename not referenced in generator
# ---------------------------------------------------------------------------


class TestHiddenFileNotNamed:
    def test_selector_filename_absent_from_generator(self, explore_text):
        assert "explore-selector" not in explore_text

    def test_selector_filename_absent_from_skill(self, skill_text):
        assert "explore-selector" not in skill_text

    def test_selector_md_extension_absent_from_generator(self, explore_text):
        # Ensure no reference to any selector .md file by common names
        assert "-selector.md" not in explore_text


# ---------------------------------------------------------------------------
# 14. Pre-freeze prohibition must not name hidden filenames
# ---------------------------------------------------------------------------


class TestPreFreezeProhibitionHygiene:
    """The explicit pre-freeze prohibition text must not reveal hidden asset filenames."""

    def test_prohibition_does_not_name_selector_filename(self, explore_text):
        """Pre-freeze prohibition paragraph must not mention explore-selector."""
        # Extract the prohibition paragraph (starts with "Pre-freeze future-contract")
        for line in explore_text.splitlines():
            if "Pre-freeze future-contract prohibition" in line:
                assert "explore-selector" not in line, (
                    "Pre-freeze prohibition names hidden selector filename"
                )
                assert "selector.md" not in line.lower(), (
                    "Pre-freeze prohibition names hidden selector .md file"
                )

    def test_prohibition_does_not_name_reviewer_filename(self, explore_text):
        """Pre-freeze prohibition paragraph must not mention deep-reviewer."""
        for line in explore_text.splitlines():
            if "Pre-freeze future-contract prohibition" in line:
                assert "deep-reviewer" not in line, (
                    "Pre-freeze prohibition names hidden reviewer filename"
                )
                assert "reviewer.md" not in line.lower(), (
                    "Pre-freeze prohibition names hidden reviewer .md file"
                )

    def test_generator_no_reference_to_hidden_assets(self, explore_text):
        """Generator must not reference any hidden asset by filename."""
        lower = explore_text.lower()
        assert "explore-selector" not in lower
        assert "deep-reviewer" not in lower
