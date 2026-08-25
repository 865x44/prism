"""
Tests for Slice Plan 2 — Comparison Review and Comparator Contracts (FG-C1..FG-C6, FG-D3).

Covers:
- pizm-comparison-review-v1 schema validation
- Four supported preference states: B1, B2, CONDITIONAL, UNRESOLVED (FG-C1..FG-C4)
- Discriminating observation requirement (FG-C5)
- Unresolved load-bearing contradiction blocks preference (FG-C6)
- Seam check: both B1 and B2 development artifacts must freeze before comparison (FG-D3)
- Payload ceiling: >128 KiB rejected
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_CLI = str(REPO_ROOT / "bin" / "pizm-checkpoint")
SKILL_ROOT = str(REPO_ROOT / "docs" / "pizm-skill-staged-2026-08-24")


def valid_review_b1():
    return {
        "target_id": "B1",
        "terminal_state": "MODEL_READY",
        "independent_countermodel": "Review capacity is sufficient but batching is culturally incentivized.",
        "load_bearing_reassessment": [
            {
                "claim": "Review latency drives batch inflation",
                "critic_epistemic_status": "SUPPORTED",
            }
        ],
        "findings": {
            "unresolved_load_bearing_contradiction": False,
            "unsupported_specificity": [],
            "epistemic_laundering": [],
        },
        "evidence_debt": [],
        "verdict_rationale": "Strong structural analysis with verified feedback mechanisms.",
    }


def valid_review_b2():
    return {
        "target_id": "B2",
        "terminal_state": "MODEL_READY",
        "independent_countermodel": "Tooling and CI overhead dominates coordination cost.",
        "load_bearing_reassessment": [
            {
                "claim": "Coordination tax grows quadratically with team size",
                "critic_epistemic_status": "SUPPORTED",
            }
        ],
        "findings": {
            "unresolved_load_bearing_contradiction": False,
            "unsupported_specificity": [],
            "epistemic_laundering": [],
        },
        "evidence_debt": [],
        "verdict_rationale": "Defensible coordination bottleneck model.",
    }


def valid_comparison_payload(preference="B1"):
    return {
        "schema_version": "pizm-comparison-review-v1",
        "stage": "comparison-review-v1",
        "task_summary": "Reduce PR cycle time in platform team",
        "review_B1": valid_review_b1(),
        "review_B2": valid_review_b2(),
        "comparison": {
            "current_preference": preference,
            "competition_axis": "Feedback loop latency vs Coordination overhead tax",
            "strongest_reason_for_B1": "Directly explains observed 3-day turnaround bottleneck.",
            "strongest_reason_for_B2": "Explains meeting proliferation across subteams.",
            "shared_evidence_debt": ["Historical PR wait time distribution by author team."],
            "discriminating_observation": "Measure queue time before first review vs total review duration.",
            "what_would_change_the_decision": "If first review latency is <2 hours, coordination overhead model B2 is primary.",
        },
    }


def valid_development_payload(target_id="B1", member_refs=None):
    if member_refs is None:
        member_refs = ["pass01:c01", "pass01:c02"]
    return {
        "schema_version": "pizm-development-v2",
        "stage": "development-v2",
        "target": {"target_type": "B", "target_id": target_id},
        "identity_lock": {
            "bundle_id": target_id,
            "member_refs": member_refs,
            "title": f"Bundle {target_id} Strategy",
            "core_claim": f"Primary mechanism for {target_id}",
            "structural_shift": "Shift focus to structural feedback",
            "mechanism": "Feedback loop latency",
            "boundary": "Platform team size > 5",
        },
        "developed_model": {
            "thesis": f"Core thesis of developed bundle {target_id}",
            "synthesis": "Full analytical synthesis explaining mechanism.",
            "implications": ["Faster cycle time"],
            "dynamics": "Self-reinforcing feedback loops",
            "mechanism_chain": ["Step 1", "Step 2", "Step 3"],
            "member_contributions": {member_refs[0]: "Base mechanism", member_refs[1]: "Amplifier"},
            "member_ablation": {member_refs[0]: "Collapses base", member_refs[1]: "Loses amplification"},
            "load_bearing_claims": [
                {
                    "claim": "Review latency drives batch inflation",
                    "epistemic_status": "SUPPORTED",
                    "role_in_model": "Primary driver",
                    "what_would_weaken_or_refute": "Fast reviews without smaller batches",
                },
                {
                    "claim": "Batch inflation increases review turn-around time",
                    "epistemic_status": "SUPPORTED",
                    "role_in_model": "Feedback mechanism",
                    "what_would_weaken_or_refute": "Large PRs reviewed as fast as small ones",
                },
            ],
            "unresolved_tensions": ["Latency vs coordination trade-off"],
            "predictions_or_observables": ["Batches shrink when review SLA < 4h"],
            "break_conditions": ["If reviewers have dedicated uninterrupted focus time"],
            "evidence_debt": [],
        },
    }


def freeze_file(project_root, stage, run_id, payload, target=None):
    fd = project_root / f"_input_{stage}_{target or 'main'}.json"
    fd.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    cmd = [
        sys.executable,
        CHECKPOINT_CLI,
        "freeze",
        "--stage",
        stage,
        "--run-id",
        run_id,
        "--input",
        str(fd),
        "--project-root",
        str(project_root),
        "--skill-root",
        SKILL_ROOT,
    ]
    if target:
        cmd.extend(["--target", target])
    res = subprocess.run(cmd, capture_output=True, text=True)
    fd.unlink()
    return res


class TestComparisonContracts:
    @pytest.mark.parametrize("pref", ["B1", "B2", "CONDITIONAL", "UNRESOLVED"])
    def test_fg_c1_to_c4_supported_preferences(self, tmp_path, pref):
        """FG-C1..FG-C4: Comparator supports B1, B2, CONDITIONAL, and UNRESOLVED."""
        run_id = f"comp-pref-{pref.lower()}"
        # Freeze B1 and B2 developments first to satisfy seam
        res1 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B1"), target="B1")
        assert res1.returncode == 0, res1.stderr
        res2 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B2"), target="B2")
        assert res2.returncode == 0, res2.stderr

        # Freeze comparison review
        comp_payload = valid_comparison_payload(preference=pref)
        res_comp = freeze_file(tmp_path, "comparison-review-v1", run_id, comp_payload)
        assert res_comp.returncode == 0, res_comp.stderr
        assert "FREEZE_OK" in res_comp.stdout

    def test_fg_c5_discriminating_observation_required(self, tmp_path):
        """FG-C5: Discriminating observation is required."""
        run_id = "comp-disc-obs"
        freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B1"), target="B1")
        freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B2"), target="B2")

        # Empty discriminating observation
        payload = valid_comparison_payload()
        payload["comparison"]["discriminating_observation"] = ""
        res = freeze_file(tmp_path, "comparison-review-v1", run_id, payload)
        assert res.returncode != 0
        assert "discriminating_observation must be non-empty string" in res.stderr

    def test_fg_c6_unresolved_contradiction_blocks_preference(self, tmp_path):
        """FG-C6: Unresolved load-bearing problem blocks preference."""
        run_id = "comp-block-pref"
        freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B1"), target="B1")
        freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B2"), target="B2")

        # B1 has unresolved contradiction but preference claims B1
        payload = valid_comparison_payload(preference="B1")
        payload["review_B1"]["findings"]["unresolved_load_bearing_contradiction"] = True
        payload["review_B1"]["terminal_state"] = "NEED_EVIDENCE"  # cannot be MODEL_READY with contradiction
        res = freeze_file(tmp_path, "comparison-review-v1", run_id, payload)
        assert res.returncode != 0
        assert "preference B1 is forbidden while B1 review has unresolved_load_bearing_contradiction" in res.stderr

        # Return to explore on B1 also blocks preference B1
        payload2 = valid_comparison_payload(preference="B1")
        payload2["review_B1"]["terminal_state"] = "RETURN_TO_EXPLORE"
        res2 = freeze_file(tmp_path, "comparison-review-v1", run_id, payload2)
        assert res2.returncode != 0
        assert "preference B1 is forbidden while B1 review terminal_state is RETURN_TO_EXPLORE" in res2.stderr

    def test_fg_d3_seam_enforcement_missing_developments(self, tmp_path):
        """FG-D3: Fail closed when either B1 or B2 freeze is missing."""
        run_id = "comp-seam-missing"
        # Neither B1 nor B2 frozen
        res = freeze_file(tmp_path, "comparison-review-v1", run_id, valid_comparison_payload())
        assert res.returncode != 0
        assert "seam check failed" in res.stderr

        # Only B1 frozen
        freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B1"), target="B1")
        res2 = freeze_file(tmp_path, "comparison-review-v1", run_id, valid_comparison_payload())
        assert res2.returncode != 0
        assert "seam check failed" in res2.stderr

    def test_payload_ceiling_exceeded(self, tmp_path):
        """Payload ceiling >128 KiB (131072 bytes) causes fail-closed rejection."""
        run_id = "comp-ceiling"
        freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B1"), target="B1")
        freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B2"), target="B2")

        payload = valid_comparison_payload()
        payload["task_summary"] = "x" * 140000
        res = freeze_file(tmp_path, "comparison-review-v1", run_id, payload)
        assert res.returncode != 0
        assert "PAYLOAD_TOO_LARGE" in res.stderr
