"""
Contract tests for Pizm Single-Branch AUTO v0 (Release 3).

Covers test IDs:
- A1: Explicit AUTO legal; manual modes remain non-auto
- A2: Exactly one nominated KEEP happy path (pizm-auto-selection-v1 bundles OK)
- A3: Invalid primary variants (not in kept, disposition not KEEP, missing field, second ID) -> BAD_AUTO_SELECTION
- A4: Single-Deep rule asserted in auto.md; schema sample contains no secondary/fallback keys
- A5: ANALYTICAL MODEL_READY -> no LEVER (conditional logic + template assertion)
- A6: ACTION_OR_DECISION MODEL_READY -> same LEVER primitive (reuse-not-duplicate)
- A7: Non-ready Deep -> honest stop rules asserted
- A8: Forbidden constructs absent (no secondary_candidate, no fallback branch, no DECIDE stage, no auto-360/RIFT)
- A9: FINAL zero model invocation (deterministic template, no tool-call/freeze instructions)
- A10: Budgets fail closed (BUDGET_EXHAUSTED semantics, ceilings 8 and 10)
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = REPO_ROOT / "docs" / "pizm-skill-staged-2026-08-24"
BUNDLE_CLI = str(REPO_ROOT / "bin" / "pizm-session-bundle")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_bundle_cli(cmd_args, cwd=None):
    return subprocess.run(
        [sys.executable, BUNDLE_CLI, *cmd_args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


@pytest.fixture
def skill_md_text():
    return (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")


@pytest.fixture
def auto_md_text():
    return (SKILL_ROOT / "references" / "auto.md").read_text(encoding="utf-8")


@pytest.fixture
def selector_md_text():
    return (SKILL_ROOT / "references" / "explore-selector.md").read_text(encoding="utf-8")


def valid_explore_candidates():
    return {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c1",
                "title": "Feedback Latency Constraint",
                "semantic_core": {
                    "claim": "Feedback latency across org boundaries drives batch inflation",
                    "structural_shift": "Shifts model from resource capacity to feedback frequency",
                    "mechanism": "Slow reviews induce workers to batch changes to amortize context switching",
                    "grounding_anchor": "Observed 3-day PR turnaround in project log",
                    "what_becomes_visible": "Batch size is an adaptive response to review delay",
                    "boundary": "Applies when review round-trip exceeds task duration",
                },
                "epistemics": {
                    "supported": ["3-day PR turnaround"],
                    "inferred": ["Context switching amortization"],
                    "speculative": [],
                    "unknown": [],
                },
            },
            {
                "candidate_id": "c2",
                "title": "Generic Process Guidance",
                "semantic_core": {
                    "claim": "Better communication improves velocity",
                    "structural_shift": "Generic reframing",
                    "mechanism": "More meetings improve alignment",
                    "grounding_anchor": "General observation",
                    "what_becomes_visible": "Communication matters",
                    "boundary": "Universal",
                },
                "epistemics": {
                    "supported": [],
                    "inferred": ["General alignment"],
                    "speculative": [],
                    "unknown": [],
                },
            },
        ],
    }


def valid_auto_selection(frozen_hash: str, orientation: str = "ACTION_OR_DECISION"):
    return {
        "schema_version": "pizm-auto-selection-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "frozen_hash": frozen_hash,
        "dispositions": [
            {
                "candidate_id": "c1",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "marginal_contribution": "high",
                "reason": "Clear causal mechanism linking latency to batch sizing",
            },
            {
                "candidate_id": "c2",
                "disposition": "DROP",
                "standalone_quality": "weak",
                "marginal_contribution": "none",
                "reason": "Generic platitude lacking structural mechanism",
            },
        ],
        "kept": ["c1"],
        "merged": [],
        "next_free_p": "P2",
        "auto_primary_candidate_id": "c1",
        "task_orientation": orientation,
    }


def make_explore_stage(stage_dir: Path, selection_data: dict):
    stage_dir.mkdir(parents=True, exist_ok=True)
    cands = valid_explore_candidates()
    cand_bytes = json.dumps(cands, indent=2).encode("utf-8")
    (stage_dir / "candidates.json").write_bytes(cand_bytes)
    cand_hash = _sha256_hex(cand_bytes)
    (stage_dir / "candidates.sha256").write_text(cand_hash + "\n", encoding="utf-8")

    if selection_data.get("frozen_hash") == "__AUTO__":
        selection_data["frozen_hash"] = cand_hash
    sel_bytes = json.dumps(selection_data, indent=2).encode("utf-8")
    (stage_dir / "selection.json").write_bytes(sel_bytes)


# ---------------------------------------------------------------------------
# A1: Explicit AUTO legal; manual modes remain non-auto
# ---------------------------------------------------------------------------


def test_a1_explicit_auto_legal_and_manual_modes_non_auto(skill_md_text, auto_md_text):
    # SKILL.md routing must declare explicit /pizm auto route
    assert "/pizm auto <task>" in skill_md_text
    assert "references/auto.md" in skill_md_text

    # SKILL.md must state AUTO executes only via explicit delegation
    assert "AUTO executes only via explicit `/pizm auto <task>` user delegation" in skill_md_text
    assert "manual modes never trigger it" in skill_md_text

    # Manual mode invariants preserved verbatim in SKILL.md
    assert (
        "After Explore, do not force a next step or choose a perspective for the user; "
        "branch commit remains the user's."
    ) in skill_md_text
    assert (
        "Manual Explore/Deep never auto-chain; /pizm lever is a user-requested exception continuing only from MODEL_READY."
    ) in skill_md_text

    # auto.md must state explicit delegation requirement
    assert "AUTO executes ONLY via explicit `/pizm auto <task>` user delegation" in auto_md_text
    assert "Manual Pizm modes" in auto_md_text
    assert "NEVER trigger or emulate AUTO behavior" in auto_md_text


# ---------------------------------------------------------------------------
# A2: Exactly one nominated KEEP happy path
# ---------------------------------------------------------------------------


def test_a2_exactly_one_nominated_keep_bundles_ok(tmp_path):
    stage_dir = tmp_path / "stage_explore"
    sel = valid_auto_selection(frozen_hash="__AUTO__", orientation="ACTION_OR_DECISION")
    make_explore_stage(stage_dir, sel)

    input_file = tmp_path / "input.md"
    input_file.write_text("Source task description", encoding="utf-8")
    output_root = tmp_path / "bundles"

    res = run_bundle_cli(
        [
            "create",
            "--output-root",
            str(output_root),
            "--slug",
            "a2-happy-path",
            "--skill-root",
            str(SKILL_ROOT),
            "--input",
            str(input_file),
            "--stage",
            f"pass-01-normal={stage_dir}",
        ]
    )
    assert res.returncode == 0, f"Expected 0, got {res.returncode}. Stderr: {res.stderr}"
    assert "BUNDLE_OK" in res.stdout
    bundle_manifest = output_root / "session-a2-happy-path" / "manifest.json"
    assert bundle_manifest.exists()


# ---------------------------------------------------------------------------
# A3: Invalid primary variants rejected with BAD_AUTO_SELECTION
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutation,expected_substring",
    [
        (
            {"auto_primary_candidate_id": "c3"},  # not in kept list
            "BAD_AUTO_SELECTION",
        ),
        (
            {"auto_primary_candidate_id": "c2"},  # c2 has disposition DROP
            "BAD_AUTO_SELECTION",
        ),
        (
            {"auto_primary_candidate_id": None},  # non-string
            "BAD_AUTO_SELECTION",
        ),
        (
            {"auto_primary_candidate_id": ""},  # empty string
            "BAD_AUTO_SELECTION",
        ),
        (
            {"omit_primary": True},  # missing field
            "BAD_AUTO_SELECTION",
        ),
        (
            {"task_orientation": "INVALID_CHOICE"},  # bad enum
            "BAD_AUTO_SELECTION",
        ),
        (
            {"omit_orientation": True},  # missing orientation
            "BAD_AUTO_SELECTION",
        ),
        (
            {"secondary_candidate_id": "c2"},  # forbidden secondary key
            "BAD_AUTO_SELECTION",
        ),
    ],
)
def test_a3_invalid_primary_variants_bad_auto_selection(tmp_path, mutation, expected_substring):
    stage_dir = tmp_path / f"stage_{abs(hash(str(mutation)))}"
    sel = valid_auto_selection(frozen_hash="__AUTO__")

    if mutation.get("omit_primary"):
        del sel["auto_primary_candidate_id"]
    elif mutation.get("omit_orientation"):
        del sel["task_orientation"]
    else:
        sel.update(mutation)

    make_explore_stage(stage_dir, sel)
    input_file = tmp_path / "input.md"
    input_file.write_text("Source task description", encoding="utf-8")
    output_root = tmp_path / f"bundles_{abs(hash(str(mutation)))}"

    res = run_bundle_cli(
        [
            "create",
            "--output-root",
            str(output_root),
            "--slug",
            "a3-reject",
            "--skill-root",
            str(SKILL_ROOT),
            "--input",
            str(input_file),
            "--stage",
            f"pass-01-normal={stage_dir}",
        ]
    )
    assert res.returncode != 0
    assert expected_substring in res.stderr


# ---------------------------------------------------------------------------
# A4: Single-Deep rule asserted; schema sample contains no secondary/fallback keys
# ---------------------------------------------------------------------------


def test_a4_single_deep_rule_and_no_secondary_fallback_keys(auto_md_text, selector_md_text):
    # Single-Deep rule asserted in auto.md
    assert "single-Deep-only rule" in auto_md_text
    assert "Single Deep only" in auto_md_text or "single Deep only" in auto_md_text

    # Extract JSON code blocks from selector_md_text and check for absence of secondary/fallback keys
    json_blocks = re.findall(r"```json\s*(\{.*?\})\s*```", selector_md_text, re.DOTALL)
    assert len(json_blocks) >= 2, "Expected at least 2 json schema samples in explore-selector.md"

    for block in json_blocks:
        data = json.loads(block)
        assert "secondary_candidate" not in data
        assert "secondary_candidate_id" not in data
        assert "fallback" not in data
        assert "fallback_candidate" not in data


# ---------------------------------------------------------------------------
# A5: ANALYTICAL MODEL_READY -> no LEVER
# ---------------------------------------------------------------------------


def test_a5_analytical_model_ready_no_lever(auto_md_text):
    # Conditional logic present
    assert 'task_orientation == "ANALYTICAL"' in auto_md_text or 'task_orientation=ANALYTICAL' in auto_md_text
    assert "Do not invoke LEVER" in auto_md_text

    # Template contains conditional for LEVER
    assert "IF LEVER executed" in auto_md_text
    assert 'task_orientation == "ACTION_OR_DECISION"' in auto_md_text
    assert 'terminal_state == "MODEL_READY"' in auto_md_text


# ---------------------------------------------------------------------------
# A6: ACTION_OR_DECISION MODEL_READY -> same LEVER primitive
# ---------------------------------------------------------------------------


def test_a6_action_model_ready_same_lever_primitive(auto_md_text):
    # Stated reuse of identical prompts/logic with zero duplication
    assert "same manual LEVER primitive" in auto_md_text
    assert "zero duplication" in auto_md_text
    assert "references/lever.md" in auto_md_text
    assert "references/lever-reviewer.md" in auto_md_text


# ---------------------------------------------------------------------------
# A7: Non-ready Deep -> honest stop
# ---------------------------------------------------------------------------


def test_a7_non_ready_deep_honest_stop(auto_md_text):
    assert "Honest-Stop Rules" in auto_md_text
    assert "terminal_state == \"NEED_EVIDENCE\"" in auto_md_text
    assert "terminal_state == \"RETURN_TO_EXPLORE\"" in auto_md_text
    assert "stop honestly" in auto_md_text.lower()
    assert "No other search or refinement primitive starts afterward" in auto_md_text


# ---------------------------------------------------------------------------
# A8: Forbidden constructs absent
# ---------------------------------------------------------------------------


def test_a8_forbidden_constructs_absent(auto_md_text, selector_md_text):
    # Selector appendix is after the markdown divider
    assert "## AUTO Mode Selection Extension" in selector_md_text
    appendix_text = selector_md_text.split("## AUTO Mode Selection Extension")[1]

    # No secondary_candidate concept anywhere
    assert "secondary_candidate" not in auto_md_text
    assert "secondary_candidate" not in appendix_text

    # No DECIDE stage in pipeline or selector
    assert "DECIDE" not in auto_md_text
    assert "DECIDE" not in appendix_text

    # No fallback execution branch
    assert "fallback" not in auto_md_text
    assert "fallback" not in appendix_text
    # No auto-triggered 360/RIFT loops
    assert "auto-360" in auto_md_text or "auto-360/RIFT" in auto_md_text
    assert "no auto-360" in auto_md_text.lower()

# ---------------------------------------------------------------------------
# A9: FINAL zero model invocation
# ---------------------------------------------------------------------------


def test_a9_final_zero_model_invocation(auto_md_text):
    assert "DETERMINISTIC ASSEMBLY" in auto_md_text
    assert "Zero Model Invocations" in auto_md_text
    assert "increments neither `semantic_stage_count` nor `host_inference_count`" in auto_md_text
    assert "ZERO tool-call model turns" in auto_md_text
    assert "STOP and replan" in auto_md_text

    # Fixed template structure present
    assert "Fixed FINAL Assembly Template" in auto_md_text
    assert "## 1. Nominated Perspective" in auto_md_text
    assert "## 2. Developed Model Summary" in auto_md_text
    assert "## 3. Deep Review Verdict" in auto_md_text

    # Ensure template does not include tool call commands
    template_section = auto_md_text.split("### Fixed FINAL Assembly Template")[1]
    assert "pizm-checkpoint" not in template_section
    assert "--stage" not in template_section


# ---------------------------------------------------------------------------
# A10: Budgets fail closed and ceilings
# ---------------------------------------------------------------------------


def test_a10_budgets_fail_closed_and_ceilings(auto_md_text):
    assert "BUDGET_EXHAUSTED" in auto_md_text
    assert "Fail-Closed Budget Enforcement" in auto_md_text
    assert "Do not reveal unreached future-stage contracts" in auto_md_text

    # Ceilings numbers present
    assert "8 host inferences" in auto_md_text
    assert "10 host inferences" in auto_md_text
    assert "max 1 model repair" in auto_md_text
    assert "max 2 model repairs" in auto_md_text
