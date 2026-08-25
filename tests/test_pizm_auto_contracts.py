"""
Contract tests for Pizm AUTO v1 (Slice C3).

Covers test IDs:
- A1: Explicit `/pizm auto` legal; manual modes remain non-auto
- A2: Exactly one auto_target happy path renders fine (P target and B target)
- A3: Invalid primary variants (missing target, bad type, unpromoted P,
      unproposed B, secondary/fallback keys, MANUAL route) -> fail closed
- A4: Single-target rule asserted in auto.md; selector samples contain no
      secondary/fallback keys
- A5: ANALYTICAL -> no LEVER (conditional logic + ambiguity default)
- A6: ACTION_OR_DECISION + MODEL_READY -> same LEVER primitive (reuse-not-duplicate)
- A7: Non-ready Deep -> honest stop rules asserted
- A8: Forbidden constructs absent (no secondary_candidate, no fallback branch,
      no DECIDE stage, no auto-360/RIFT loops)
- A9: FINAL + run.md are deterministic zero-model assembly (template present,
      no tool-call instructions inside the template)
- A10: Budgets fail closed (semantic stages 4/6, repair ceilings, BUDGET_EXHAUSTED)
- A11: One Search / one Deep only: no second-Search / second-Deep constructs
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


def run_render_cli(run_dir, task, output):
    return subprocess.run(
        [
            sys.executable,
            BUNDLE_CLI,
            "render",
            "--run-dir",
            str(run_dir),
            "--task",
            task,
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
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


# ---------------------------------------------------------------------------
# Frozen-artifact fixtures (hand-written; the renderer reads them directly)
# ---------------------------------------------------------------------------


def valid_explore_candidates():
    return {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c01",
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
                "candidate_id": "c02",
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


def valid_auto_portfolio(target_type: str = "P", target_id: str = "P1"):
    return {
        "schema_version": "pizm-portfolio-selection-v1",
        "stage": "portfolio",
        "route": "AUTO",
        "field_hash": "a" * 64,
        "candidate_assessments": [
            {
                "candidate_ref": "pass01:c01",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "Latency-to-batching mechanism no other candidate carries",
                "nearest_overlap": None,
                "reason": "Clear causal mechanism linking latency to batch sizing",
            },
            {
                "candidate_ref": "pass01:c02",
                "disposition": "DROP",
                "standalone_quality": "weak",
                "unique_residue": "",
                "nearest_overlap": None,
                "reason": "Generic platitude lacking structural mechanism",
            },
        ],
        "bundles": [],
        "auto_target": {"target_type": target_type, "target_id": target_id},
    }


def valid_auto_portfolio_bundle_target():
    port = valid_auto_portfolio("B", "B1")
    port["candidate_assessments"][1]["disposition"] = "KEEP"
    port["bundles"] = [
        {
            "bundle_id": "B1",
            "member_refs": ["pass01:c01", "pass01:c02"],
            "bundle_thesis": "Latency and coordination load form one scheduling system",
            "composition_gain": "Predicts batch oscillation neither member predicts alone",
            "new_consequence_or_prediction": "Batch size tracks meeting cadence",
            "internal_tension": "Meetings reduce batching need while adding load",
            "weakest_link": "c02 grounding is thin",
            "member_roles": {"pass01:c01": "mechanism core", "pass01:c02": "counter-mechanism"},
            "member_ablation": {"pass01:c01": "loses mechanism", "pass01:c02": "loses tension"},
        }
    ]
    return port


def valid_development_v2(target_type: str = "P", target_id: str = "P1"):
    if target_type == "P":
        identity_lock = {
            "p_id": target_id,
            "title": "Feedback Latency Constraint",
            "core_claim": "Feedback latency drives batch inflation",
            "structural_shift": "Capacity -> feedback frequency",
            "mechanism": "Slow reviews induce batching",
            "boundary": "Round-trip exceeds task duration",
        }
    else:
        identity_lock = {
            "bundle_id": target_id,
            "member_refs": ["pass01:c01", "pass01:c02"],
            "title": "Scheduling System Bundle",
            "core_claim": "Latency and coordination form one scheduler",
            "structural_shift": "Two pressures unified",
            "mechanism": "Latency batches work; meetings reset it",
            "boundary": "Small orgs exempt",
        }
    model = {
        "thesis": "Review latency is the hidden scheduler of engineering output.",
        "synthesis": (
            "When review round-trips exceed task duration, engineers rationally batch "
            "changes, which inflates review size, which further slows reviews: a "
            "self-reinforcing queue that no capacity fix dissolves."
        ),
        "dynamics": "The loop equilibrates at the maximum batch size the culture tolerates.",
        "mechanism_chain": [
            "Review latency rises",
            "Workers batch changes to amortize switching",
            "Reviews grow larger and slower",
        ],
        "implications": ["Small-batch mandates fail without latency fixes"],
        "predictions_or_observables": [
            "Batch size correlates with review latency",
            "Latency reduction shrinks batches within weeks",
        ],
        "break_conditions": ["Async review cultures"],
        "unresolved_tensions": [],
        "evidence_debt": ["Measure latency-batch correlation on real logs"],
        "load_bearing_claims": [
            {
                "claim": "Batching is rational amortization",
                "role_in_model": "core mechanism",
                "what_would_weaken_or_refute": "Batch size unchanged when latency varies",
                "epistemic_status": "INFERRED",
            },
            {
                "claim": "Three-day turnaround observed",
                "role_in_model": "grounding anchor",
                "what_would_weaken_or_refute": "Logs show sub-day turnaround",
                "epistemic_status": "SUPPORTED",
            },
        ],
    }
    if target_type == "B":
        members = identity_lock["member_refs"]
        model["unresolved_tensions"] = ["Meeting time trades off against batch time"]
        model["member_contributions"] = {m: f"{m} contributes its mechanism" for m in members}
        model["member_ablation"] = {m: f"removing {m} loses its residue" for m in members}
    return {
        "schema_version": "pizm-development-v2",
        "stage": "development-v2",
        "target": {"target_type": target_type, "target_id": target_id},
        "identity_lock": identity_lock,
        "developed_model": model,
    }


def valid_deep_review_v2(target_type: str = "P", target_id: str = "P1"):
    findings = {
        "cross_field_contradictions": [],
        "unsupported_specificity": [],
        "epistemic_laundering": [],
        "unresolved_load_bearing_contradiction": False,
        "identity_drift": None,
        "cost_relocation": None,
        "round_trip_skeleton": "latency -> batching -> larger diffs -> slower reviews",
    }
    if target_type == "B":
        findings["member_ablation"] = "Both members load-bearing; ablation reasoning holds."
    return {
        "schema_version": "pizm-deep-review-v2",
        "stage": "deep-review-v2",
        "frozen_hash": "b" * 64,
        "target_type": target_type,
        "target_id": target_id,
        "terminal_state": "MODEL_READY",
        "identity_verified": True,
        "independent_countermodel": (
            "Batching could be status ritual rather than latency response."
        ),
        "cheapest_discriminating_test": "Correlate per-developer batch size with observed latency.",
        "load_bearing_reassessment": [
            {
                "claim": "Batching is rational amortization",
                "critic_epistemic_status": "INFERRED",
            }
        ],
        "findings": findings,
        "evidence_debt": [],
        "verdict_rationale": "Mechanism survives the countermodel; predictions observable.",
    }


def valid_lever_design():
    return {
        "schema_version": "pizm-lever-design-v1",
        "stage": "lever",
        "levers": [
            {
                "lever_id": "L1",
                "intervention_or_test_point": "Cap synchronous meeting hours per week",
                "model_link": "Coordination pressure feeds the latency loop",
                "minimum_bounded_move": "One team, two weeks",
                "expected_observation_or_response": "Batch size drops measurably",
                "disconfirming_signal": "No change in batch size",
                "stop_condition": "Two cycles without effect",
                "remaining_assumptions": "Teams report hours honestly",
            }
        ],
    }


def valid_lever_review(outcome: str = "LEVER"):
    verdict = {"lever_id": "L1", "verdict": "ACCEPT"} if outcome == "LEVER" else None
    record = {
        "schema_version": "pizm-lever-review-v1",
        "stage": "lever",
        "frozen_hash": "c" * 64,
        "outcome": outcome,
        "verdicts": [v for v in (verdict,) if v],
        "verdict_rationale": "Move is bounded and observable." if outcome == "LEVER" else "Nothing decision-relevant to try.",
    }
    return record


def write_frozen(tmp_path, name, data):
    raw = json.dumps(data, indent=2).encode("utf-8")
    (tmp_path / name).write_bytes(raw)
    (tmp_path / (name[: -len(".json")] + ".sha256")).write_text(
        _sha256_hex(raw), encoding="ascii"
    )


def make_frozen_run(
    tmp_path: Path,
    *,
    portfolio=None,
    development=None,
    review=None,
    with_lever=False,
    lever_outcome="LEVER",
):
    tmp_path.mkdir(parents=True, exist_ok=True)
    write_frozen(tmp_path, "candidates.json", valid_explore_candidates())
    write_frozen(tmp_path, "portfolio.json", portfolio or valid_auto_portfolio())
    write_frozen(tmp_path, "development-v2.json", development or valid_development_v2())
    write_frozen(tmp_path, "deep-review-v2.json", review or valid_deep_review_v2())
    if with_lever:
        write_frozen(tmp_path, "design.json", valid_lever_design())
        write_frozen(tmp_path, "review.json", valid_lever_review(lever_outcome))
    return tmp_path


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
# A2: Exactly one auto_target happy path renders fine (P and B)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("target", [("P", "P1"), ("B", "B1")])
def test_a2_exactly_one_auto_target_happy_path_renders_ok(tmp_path, target):
    ttype, tid = target
    run_dir = make_frozen_run(
        tmp_path / f"run_{ttype}",
        portfolio=(
            valid_auto_portfolio()
            if ttype == "P"
            else valid_auto_portfolio_bundle_target()
        ),
        development=valid_development_v2(ttype, tid),
        review=valid_deep_review_v2(ttype, tid),
        with_lever=True,
    )
    out = tmp_path / f"run_{ttype}" / "run.md"
    res = run_render_cli(run_dir, "Reduce PR cycle time", out)
    assert res.returncode == 0, f"Expected 0, got {res.returncode}. Stderr: {res.stderr}"
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "# Prism AUTO" in text
    assert "## Task" in text
    assert "Reduce PR cycle time" in text
    assert f"## Selected model" in text
    assert tid in text


# ---------------------------------------------------------------------------
# A3: Invalid primary variants fail closed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutation,expected_substring",
    [
        ({"omit_target": True}, "BAD_AUTO_TARGET"),
        ({"auto_target": None}, "BAD_AUTO_TARGET"),
        ({"auto_target": {"target_type": "C", "target_id": "P1"}}, "BAD_AUTO_TARGET"),
        ({"auto_target": {"target_type": "P", "target_id": "P7"}}, "BAD_AUTO_TARGET"),
        ({"auto_target": {"target_type": "P", "target_id": "B1"}}, "BAD_AUTO_TARGET"),
        ({"auto_target": {"target_type": "B", "target_id": "B9"}}, "BAD_AUTO_TARGET"),
        ({"secondary_candidate_id": "c02"}, "BAD_AUTO_TARGET"),
        ({"fallback_candidate": "c02"}, "BAD_AUTO_TARGET"),
        ({"route": "MANUAL"}, "AUTO portfolio"),
        ({"schema_version": "pizm-auto-selection-v1"}, "schema_version must be"),
    ],
)
def test_a3_invalid_primary_variants_fail_closed(tmp_path, mutation, expected_substring):
    portfolio = valid_auto_portfolio()
    if mutation.get("omit_target"):
        del portfolio["auto_target"]
    else:
        portfolio.update(mutation)

    run_dir = make_frozen_run(tmp_path / "run_bad", portfolio=portfolio)
    out = tmp_path / "out.md"
    res = run_render_cli(run_dir, "Reduce PR cycle time", out)
    assert res.returncode != 0
    assert expected_substring in res.stderr


# ---------------------------------------------------------------------------
# A4: Single-target rule asserted; selector samples contain no secondary keys
# ---------------------------------------------------------------------------


def test_a4_single_target_rule_and_no_secondary_fallback_keys(auto_md_text, selector_md_text):
    # Single-target rule asserted in auto.md (updated single-Deep rule: P or B)
    assert "exactly one nominated target (P or B)" in auto_md_text
    assert "Single Deep only" in auto_md_text

    # Extract JSON code blocks from selector_md_text and check for absence of
    # secondary/fallback keys
    json_blocks = re.findall(r"```json\s*(\{.*?\})\s*```", selector_md_text, re.DOTALL)
    assert len(json_blocks) >= 2, "Expected at least 2 json schema samples in explore-selector.md"

    for block in json_blocks:
        data = json.loads(block)
        assert "secondary_candidate" not in data
        assert "secondary_candidate_id" not in data
        assert "fallback" not in data
        assert "fallback_candidate" not in data


# ---------------------------------------------------------------------------
# A5: ANALYTICAL -> no LEVER
# ---------------------------------------------------------------------------


def test_a5_analytical_model_ready_no_lever(auto_md_text):
    # Conditional logic present
    assert 'task_orientation == "ANALYTICAL"' in auto_md_text
    assert "Do not invoke LEVER" in auto_md_text
    # Ambiguity defaults to ANALYTICAL without a classifier call
    assert "default to `ANALYTICAL`" in auto_md_text
    assert "no classifier call" in auto_md_text

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
    assert "no auto-360" in auto_md_text.lower()


# ---------------------------------------------------------------------------
# A9: FINAL + run.md deterministic zero-model assembly
# ---------------------------------------------------------------------------


def test_a9_final_and_runmd_zero_model_deterministic(auto_md_text):
    assert "DETERMINISTIC ASSEMBLY" in auto_md_text
    assert "Zero Model Invocations" in auto_md_text
    assert "increments neither `semantic_stage_count` nor `host_inference_count`" in auto_md_text
    assert "ZERO tool-call model turns" in auto_md_text
    assert "STOP and replan" in auto_md_text

    # run.md rendering named as equally deterministic and zero-model
    assert "byte-identical output for identical frozen inputs, zero model calls" in auto_md_text
    assert "bin/pizm-session-bundle render" in auto_md_text
    assert "reads ONLY frozen checkpoint artifacts" in auto_md_text

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

    # Semantic stage budget: base 4, optional LEVER brings it to 6
    assert "= 4 semantic stages" in auto_md_text
    assert "= 6 semantic stages total" in auto_md_text
    # Repairs accounted separately, bounded
    assert "accounted separately" in auto_md_text
    assert "max 1 model repair per stage" in auto_md_text
    assert "max 2 model repairs" in auto_md_text
    assert "No unbounded retries" in auto_md_text


# ---------------------------------------------------------------------------
# A11: One Search / one Deep only
# ---------------------------------------------------------------------------


def test_a11_one_search_one_deep_only(auto_md_text):
    # The pipeline names exactly one Search pass and forbids residual/re-judgment
    assert "ONE initial Search pass" in auto_md_text
    assert "no residual Search, no second Search" in auto_md_text
    assert "Search(residual)" not in auto_md_text
    # Exactly one nominated target is deepened; no second Deep exists
    assert "no second Deep" in auto_md_text
    assert "Single Deep only" in auto_md_text
    # Honest-stop reinforces: no other search primitive starts afterward
    assert "No other search or refinement primitive starts afterward" in auto_md_text
