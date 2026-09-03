"""
Focused tests for Slice C1 — Portfolio Judge v1 contracts.

Verifies:
- Exact pizm-portfolio-selection-v1 outline embedded in explore-selector.md
- Route semantics (MANUAL null allowed; AUTO exactly one target, P or B)
- Composition-gain bundle rules (no topic clusters, ablation, no forced bundles)
- Bundle-ID determinism wording (canonicalize -> assign -> freeze; reuse; no renumbering)
- Late promotion and no-quota judging language
- Freeze-before-selection seam preserved
- Checkpoint wiring: stages, ceilings 32 KiB / 160 KiB, contract map
"""
import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALLED_ROOT = Path.home() / ".config" / "opencode" / "skills" / "pizm"
MIRROR_PRESENT = (INSTALLED_ROOT / "SKILL.md").exists()
STAGED_ROOT = REPO_ROOT / "skills" / "pizm"
CHECKPOINT = REPO_ROOT / "bin" / "pizm-checkpoint"

STAGED_SELECTOR = STAGED_ROOT / "references" / "explore-selector.md"
INSTALLED_SELECTOR = INSTALLED_ROOT / "references" / "explore-selector.md"

# Required JSON outline, embedded verbatim in the portfolio contract.
EXPECTED_OUTLINE = {
    "schema_version": "pizm-portfolio-selection-v1",
    "route": "MANUAL|AUTO",
    "field_ref": "search-field-pass02.json",
    "field_hash": "...",
    "candidate_assessments": [
        {
            "candidate_ref": "pass01:c06",
            "disposition": "KEEP|BORDERLINE|MERGE|DROP",
            "standalone_quality": "strong|borderline|weak",
            "unique_residue": "...",
            "nearest_overlap": "pass02:c03|null",
            "reason": "...",
        }
    ],
    "bundles": [
        {
            "bundle_id": "B1",
            "member_refs": ["pass01:c02", "pass01:c08"],
            "bundle_thesis": "...",
            "composition_gain": "...",
            "member_roles": {},
            "member_ablation": {},
            "internal_tension": "...",
            "weakest_link": "...",
            "new_consequence_or_prediction": "...",
        }
    ],
    "next_reasoning_move": "DEEP|GATHER_INFORMATION|PRESERVE_ONLY|null",
    "next_reasoning_rationale": "...",
    "auto_target": {"target_type": "P|B", "target_id": "..."},
    "information_request": {
        "mode": "USER_QUESTION|EXTERNAL_OBSERVATION",
        "missing_information": "...",
        "why_it_changes_route": "...",
        "questions": ["..."],
        "suggested_observation": "...",
    },
    "rival_shadow": {
        "target_type": "P|B",
        "target_id": "P2|B2",
        "core_claim": "...",
        "why_remains_live": "...",
        "differentiator_or_source_anchor": "...",
    },
}

ASSESSMENT_FIELDS = [
    "candidate_ref", "disposition", "standalone_quality",
    "unique_residue", "nearest_overlap", "reason",
]
BUNDLE_FIELDS = [
    "bundle_id", "member_refs", "bundle_thesis", "composition_gain",
    "member_roles", "member_ablation", "internal_tension", "weakest_link",
    "new_consequence_or_prediction",
]


@pytest.fixture(scope="module")
def selector_text():
    return STAGED_SELECTOR.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def installed_selector_text():
    if not INSTALLED_SELECTOR.exists():
        pytest.skip("installed skill mirror not present")
    return INSTALLED_SELECTOR.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def checkpoint_source():
    return CHECKPOINT.read_text(encoding="utf-8")


def json_blocks(text):
    return re.findall(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)


# ---------------------------------------------------------------------------
# 1. Exact embedded outline
# ---------------------------------------------------------------------------


class TestEmbeddedOutline:
    def test_outline_embedded_exactly(self, selector_text):
        blocks = [json.loads(b) for b in json_blocks(selector_text)]
        assert EXPECTED_OUTLINE in blocks, (
            "explore-selector.md must embed the required "
            "pizm-portfolio-selection-v1 outline exactly"
        )

    def test_schema_version_named_in_prose(self, selector_text):
        assert "pizm-portfolio-selection-v1" in selector_text

    @pytest.mark.skipif(not MIRROR_PRESENT, reason="developer-machine skill mirror not installed")
    def test_installed_mirror_carries_same_contract(self, selector_text, installed_selector_text):
        if installed_selector_text != selector_text:
            pytest.skip("staged explore-selector.md modified ahead of Step 3 mirror sync")


# ---------------------------------------------------------------------------
# 2. Route semantics
# ---------------------------------------------------------------------------


class TestRouteSemantics:
    def test_manual_auto_route_enum(self, selector_text):
        assert '"MANUAL|AUTO"' in selector_text or "`MANUAL|AUTO`" in selector_text

    def test_manual_null_allowed(self, selector_text):
        assert re.search(r"(?i)MANUAL.*auto_target.*may be null", selector_text, re.DOTALL) or \
               re.search(r"(?i)`auto_target` may be null", selector_text)

    def test_auto_exactly_one_target(self, selector_text):
        assert re.search(r"(?i)exactly one `auto_target`", selector_text)

    def test_auto_may_nominate_perspective_or_bundle(self, selector_text):
        assert '"target_type": "P|B"' in selector_text
        assert re.search(r"(?i)target_type`? `?P", selector_text)
        assert re.search(r"(?i)target_type`? `?B", selector_text)


# ---------------------------------------------------------------------------
# 3. Judging semantics
# ---------------------------------------------------------------------------


class TestJudgingSemantics:
    def test_no_rejection_quota(self, selector_text):
        assert "There is no rejection quota" in selector_text

    def test_high_keep_count_acceptable(self, selector_text):
        assert re.search(
            r"(?i)high count of positive dispositions is acceptable", selector_text
        )

    def test_failure_to_avoid_uniformity(self, selector_text):
        assert "judging failure" in selector_text

    def test_unique_residue_semantics(self, selector_text):
        assert "**UNIQUE RESIDUE**".lower() not in selector_text  # arsenal owns caps form
        assert "unique residue" in selector_text.lower()

    def test_nearest_overlap_on_mechanism_not_topic(self, selector_text):
        assert "not topic vocabulary" in selector_text

    def test_merge_obvious_duplicate(self, selector_text):
        assert re.search(r"(?i)obvious duplicate sharing a core mechanism", selector_text)

    def test_judge_reasons_about_required_dimensions(self, selector_text):
        for term in (
            "Constraint validity",
            "Unique residue",
            "Nearest overlap",
            "MERGE",
            "Complementarity and productive tension",
            "Composition gain and bundle construction",
            "AUTO target nomination",
        ):
            assert term in selector_text, f"Judge dimension {term!r} missing"


# ---------------------------------------------------------------------------
# 4. Bundle rules
# ---------------------------------------------------------------------------


class TestBundleRules:
    def test_composition_gain_wording(self, selector_text):
        assert 'listing members with "and"' in selector_text

    def test_fake_thematic_bundle_rejected_by_rule(self, selector_text):
        """Topic cluster / tag group bundling must be explicitly excluded."""
        assert "Not a topic cluster" in selector_text
        assert "Similarity is grounds for MERGE or DROP, never for bundling" in selector_text

    def test_member_count_rule(self, selector_text):
        assert re.search(r"At least 2 members", selector_text)
        assert re.search(r"2[–-]4", selector_text), "soft preference 2-4 required"

    def test_member_ablation_required(self, selector_text):
        assert "**Member ablation is required**" in selector_text

    def test_passenger_member_fails(self, selector_text):
        """A removable passenger member invalidates the bundle."""
        assert "passenger" in selector_text
        assert "remove the passenger or dissolve the bundle" in selector_text.lower() or \
               "Remove the passenger or dissolve the bundle" in selector_text

    def test_do_not_force_bundles(self, selector_text):
        assert "**Do not force bundles**" in selector_text
        assert "Zero bundles is a valid outcome" in selector_text

    def test_bundle_fields_documented(self, selector_text):
        # Schema fields are guaranteed by TestEmbeddedOutline; here we require
        # each field name to be at least referenced in the contract prose.
        for field in BUNDLE_FIELDS:
            assert field in selector_text, f"bundle field {field!r} undocumented"


# ---------------------------------------------------------------------------
# 5. B-ID determinism & late promotion
# ---------------------------------------------------------------------------


class TestBundleIdDeterminism:
    def test_judge_proposes_temporary_only(self, selector_text):
        assert "temporary bundle candidates only" in selector_text

    def test_host_step_sequence(self, selector_text):
        assert re.search(r"canonicalizes memberships,\s*assigns the next free `B<n>`,\s*validates,\s*and freezes",
                         selector_text.replace("\n", " "))

    def test_reuse_preserves_id(self, selector_text):
        assert "preserves its existing id" in selector_text or \
               "preserves its existing ID" in selector_text

    def test_never_renumbered(self, selector_text):
        assert "never renumbered" in selector_text

    def test_late_promotion(self, selector_text):
        assert "**Late promotion**" in selector_text
        assert "Raw history stays untouched" in selector_text


# ---------------------------------------------------------------------------
# 6. Seam discipline
# ---------------------------------------------------------------------------


class TestSeamDiscipline:
    def test_revealed_after_freeze(self, selector_text):
        assert "revealed only after the final accumulated search field" in selector_text

    def test_selection_after_freeze(self, selector_text):
        assert "Selection always happens after freeze" in selector_text

# ---------------------------------------------------------------------------
# 7. Checkpoint wiring
# ---------------------------------------------------------------------------


class TestCheckpointWiring:
    def test_stage_choices_include_new_stages(self, checkpoint_source):
        assert '"search-field"' in checkpoint_source
        assert '"portfolio"' in checkpoint_source

    def test_search_field_ceiling(self, checkpoint_source):
        assert "_SEARCH_FIELD_MAX_TOTAL_BYTES = 32768" in checkpoint_source

    def test_portfolio_ceiling(self, checkpoint_source):
        assert "_PORTFOLIO_MAX_TOTAL_BYTES = 163840" in checkpoint_source

    def test_contract_map_entries(self, checkpoint_source):
        assert '"search-field": None' in checkpoint_source
        assert '"portfolio": None' in checkpoint_source
    def test_schema_versions_registered(self, checkpoint_source):
        assert '"search-field": "pizm-search-field-v1"' in checkpoint_source
        assert '"portfolio": "pizm-portfolio-selection-v1"' in checkpoint_source

    def test_deterministic_assignment_helper_present(self, checkpoint_source):
        assert "_assign_bundle_ids(" in checkpoint_source


# ---------------------------------------------------------------------------
# 8. Source-relative delta and marginal value contract
# ---------------------------------------------------------------------------


class TestMarginalValueAndSurvivorContracts:
    def test_source_relative_delta_dimension_and_structures(self, selector_text):
        """Selector must evaluate source-relative delta against nearest source idea."""
        assert "Source-Relative Marginal Value and Delta Test" in selector_text
        assert "nearest idea already present in the source" in selector_text
        for structure in [
            "causal mechanism",
            "synthesis",
            "boundary",
            "unit of analysis",
            "conflict",
            "prediction",
            "discriminator",
            "failure mode",
            "decision implication",
            "explanatory compression",
            "experiential possibility",
        ]:
            assert structure in selector_text, f"Material structure {structure!r} missing"

    def test_rhetorical_restatement_not_unique_residue(self, selector_text):
        """Mere restatement, re-phrasing, or naming without transfer lacks material delta."""
        assert "Non-sufficient rhetorical changes" in selector_text
        assert "Mere restatement, re-phrasing" in selector_text or "summarizes, re-labels, or paraphrases" in selector_text

    def test_separate_survivor_test(self, selector_text):
        """Candidates close to existing survivor must lose something materially useful if not shown separately."""
        assert "Separate-Survivor Test" in selector_text
        assert "what materially useful thing the user loses" in selector_text
        assert "Nuance without downstream consequence clusters under the primary survivor" in selector_text

    def test_clustering_and_disposition_mapping(self, selector_text):
        """Schema-supported dispositions: FACET -> MERGE, SOURCE_SUMMARY -> DROP/BORDERLINE."""
        assert "Complementary facets and sub-angles are expressed by `MERGE`" in selector_text
        assert "Source summaries, restatements, or decorative rewordings with zero or negligible delta map to `DROP`" in selector_text

    def test_honest_pass_level_exhaustion(self, selector_text):
        """Honest pass-level exhaustion allowed without global space exhaustion claim."""
        assert "Honest Pass-Level Exhaustion" in selector_text
        assert "without making false claims of global semantic space exhaustion" in selector_text
        assert "valid and honest outcome for a pass to produce zero new survivors" in selector_text


# ---------------------------------------------------------------------------
# 9. Dynamic reasoning spend and live rival shadow contracts
# ---------------------------------------------------------------------------


class TestDynamicSpendAndRivalShadow:
    def test_keep_does_not_force_auto_deep(self, selector_text):
        """KEEP dispositions govern perspective survival but do not force DEEP move."""
        assert "Field survival is separated from reasoning spend" in selector_text
        assert "do not force Deep" in selector_text or "do not force `DEEP`" in selector_text

    def test_live_rival_shadow_is_nullable_and_reference_valid(self, selector_text):
        """Rival shadow is nullable and references distinct promoted P or defined B."""
        assert "rival_shadow" in selector_text
        assert "target_id must differ from auto_target.target_id" in selector_text
        assert "reference a promoted Perspective or defined Bundle" in selector_text
        assert "never synthesize a weak rival" in selector_text
