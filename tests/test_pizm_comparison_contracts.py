"""
Tests for Comparison Review and Comparator Contracts (FG-C1..FG-C6, FG-D3, CMP-SEAM-1..6, BID-1..4).

Covers:
- pizm-comparison-review-v1 schema validation
- Supported preference states: LEFT, RIGHT, CONDITIONAL, UNRESOLVED (FG-C1..FG-C4)
- Discriminating observation requirement (FG-C5)
- Unresolved load-bearing contradiction blocks preference symmetrically (FG-C6, BID-4)
- Seam check: both development artifacts must freeze before comparison (FG-D3, CMP-SEAM-6)
- Payload ceiling: >128 KiB rejected
- Named tests CMP-SEAM-1..6 (reveal ordering, sidecar tamper, target mismatch, contract purity)
- Named tests BID-1..4 (arbitrary B3/B7, canonical B1/B2, legacy rejection, coupling symmetry)
"""
import json
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_CLI = str(REPO_ROOT / "bin" / "pizm-checkpoint")
SKILL_ROOT = str(REPO_ROOT / "skills" / "pizm")


def valid_review(target_id="B1", dev_ref=None, dev_hash=None):
    if dev_ref is None:
        dev_ref = f"development-v2-{target_id}.json"
    return {
        "target_id": target_id,
        "development_ref": dev_ref,
        "frozen_hash": dev_hash or ("a" * 64),
        "terminal_state": "MODEL_READY",
        "independent_countermodel": f"Countermodel against {target_id}",
        "load_bearing_reassessment": [
            {
                "claim": f"Primary claim for {target_id}",
                "critic_epistemic_status": "SUPPORTED",
            }
        ],
        "findings": {
            "unresolved_load_bearing_contradiction": False,
            "unsupported_specificity": [],
            "epistemic_laundering": [],
        },
        "evidence_debt": [],
        "verdict_rationale": f"Strong analysis for {target_id}.",
    }


def valid_comparison_payload(
    left_id="B1",
    right_id="B2",
    preference="LEFT",
    left_ref=None,
    left_hash=None,
    right_ref=None,
    right_hash=None,
):
    return {
        "schema_version": "pizm-comparison-review-v1",
        "stage": "comparison-review-v1",
        "task_summary": "Reduce PR cycle time in platform team",
        "left_target_id": left_id,
        "right_target_id": right_id,
        "left_review": valid_review(target_id=left_id, dev_ref=left_ref, dev_hash=left_hash),
        "right_review": valid_review(target_id=right_id, dev_ref=right_ref, dev_hash=right_hash),
        "comparison": {
            "current_preference": preference,
            "competition_axis": f"{left_id} latency vs {right_id} coordination tax",
            "strongest_reason_for_left": f"Why {left_id} is primary",
            "strongest_reason_for_right": f"Why {right_id} is primary",
            "shared_evidence_debt": ["Historical PR wait time distribution."],
            "discriminating_observation": "Measure queue time before first review.",
            "what_would_change_the_decision": "If first review latency is <2 hours, right is primary.",
        },
    }


def extract_freeze_hash(res):
    for line in res.stdout.splitlines():
        if line.startswith("FREEZE_OK "):
            return line.split()[1].strip()
    return None


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
                    "claim": f"Review latency drives batch inflation for {target_id}",
                    "epistemic_status": "SUPPORTED",
                    "role_in_model": "Primary driver",
                    "what_would_weaken_or_refute": "Fast reviews without smaller batches",
                },
                {
                    "claim": f"Batch inflation increases turnaround for {target_id}",
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


def valid_portfolio_v2_payload(left_id="B1", right_id="B2", field_hash="abc123"):
    return {
        "schema_version": "pizm-portfolio-selection-v2",
        "stage": "portfolio",
        "route": "FORGE",
        "field_ref": "search-field.json",
        "field_hash": field_hash,
        "candidate_assessments": [
            {
                "candidate_ref": "pass01:c01",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "Direct latency observation",
                "nearest_overlap": None,
                "reason": "Clear anchor",
            },
            {
                "candidate_ref": "pass01:c02",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "Coordination load",
                "nearest_overlap": None,
                "reason": "Secondary anchor",
            },
        ],
        "bundles": [
            {
                "bundle_id": left_id,
                "member_refs": ["pass01:c01", "pass01:c02"],
                "bundle_thesis": f"Thesis for {left_id}",
                "composition_gain": f"Gain for {left_id}",
                "new_consequence_or_prediction": "Predictable cycle",
                "internal_tension": "Tension 1",
                "weakest_link": "Link 1",
                "member_roles": {
                    "pass01:c01": "Primary driver",
                    "pass01:c02": "Amplifier",
                },
                "member_ablation": {
                    "pass01:c01": "Collapses bundle",
                    "pass01:c02": "Weakens amplification",
                },
            },
            {
                "bundle_id": right_id,
                "member_refs": ["pass01:c01", "pass01:c02"],
                "bundle_thesis": f"Thesis for {right_id}",
                "composition_gain": f"Gain for {right_id}",
                "new_consequence_or_prediction": "Alternative prediction",
                "internal_tension": "Tension 2",
                "weakest_link": "Link 2",
                "member_roles": {
                    "pass01:c01": "Context provider",
                    "pass01:c02": "Core driver",
                },
                "member_ablation": {
                    "pass01:c01": "Reduces context",
                    "pass01:c02": "Collapses mechanism",
                },
            },
        ],
        "perspectives": {
            "P1": "pass01:c01",
            "P2": "pass01:c02",
        },
        "competition_status": "TWO_DEFENSIBLE_BUNDLES",
        "recommended_competition": {
            "left_bundle_id": left_id,
            "right_bundle_id": right_id,
            "competition_axis": f"Feedback latency ({left_id}) vs Coordination tax ({right_id})",
            "discriminating_observation": "Measure PR turnaround under isolated SLA.",
        },
    }


def freeze_file(project_root, stage, run_id, payload, target=None, artifact_suffix=None):
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
    if artifact_suffix:
        cmd.extend(["--artifact-suffix", artifact_suffix])
    res = subprocess.run(cmd, capture_output=True, text=True)
    fd.unlink()
    return res

def freeze_forge_portfolio(project_root, run_id, left_id="B1", right_id="B2"):
    pv2 = valid_portfolio_v2_payload(left_id=left_id, right_id=right_id)
    run_dir = project_root / ".ai" / "pizm" / f"run-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(pv2, indent=2).encode("utf-8")
    (run_dir / "portfolio.json").write_bytes(raw)
    (run_dir / "portfolio.sha256").write_text(hashlib.sha256(raw).hexdigest(), encoding="utf-8")
    (run_dir / "portfolio.meta.json").write_text('{"stage":"portfolio"}', encoding="utf-8")

class TestComparisonContracts:
    @pytest.mark.parametrize("pref", ["LEFT", "RIGHT", "CONDITIONAL", "UNRESOLVED"])
    def test_fg_c1_to_c4_supported_preferences(self, tmp_path, pref):
        """FG-C1..FG-C4: Comparator supports LEFT, RIGHT, CONDITIONAL, and UNRESOLVED."""
        run_id = f"comp-pref-{pref.lower()}"
        freeze_forge_portfolio(tmp_path, run_id, "B1", "B2")
        res1 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B1"), target="B1")
        assert res1.returncode == 0, res1.stderr
        hash_b1 = extract_freeze_hash(res1)
        res2 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B2"), target="B2")
        assert res2.returncode == 0, res2.stderr
        hash_b2 = extract_freeze_hash(res2)

        comp_payload = valid_comparison_payload(
            left_id="B1",
            right_id="B2",
            preference=pref,
            left_hash=hash_b1,
            right_hash=hash_b2,
        )
        res_comp = freeze_file(tmp_path, "comparison-review-v1", run_id, comp_payload)
        assert res_comp.returncode == 0, res_comp.stderr
        assert "FREEZE_OK" in res_comp.stdout

    def test_fg_c5_discriminating_observation_required(self, tmp_path):
        """FG-C5: Discriminating observation is required."""
        run_id = "comp-disc-obs"
        freeze_forge_portfolio(tmp_path, run_id, "B1", "B2")
        res1 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B1"), target="B1")
        assert res1.returncode == 0, res1.stderr
        hash_b1 = extract_freeze_hash(res1)
        res2 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B2"), target="B2")
        assert res2.returncode == 0, res2.stderr
        hash_b2 = extract_freeze_hash(res2)

        payload = valid_comparison_payload(left_id="B1", right_id="B2", left_hash=hash_b1, right_hash=hash_b2)
        payload["comparison"]["discriminating_observation"] = ""
        res = freeze_file(tmp_path, "comparison-review-v1", run_id, payload)
        assert res.returncode != 0
        assert "discriminating_observation must be non-empty string" in res.stderr

    def test_fg_c6_unresolved_contradiction_blocks_preference(self, tmp_path):
        """FG-C6: Unresolved load-bearing problem blocks preference."""
        run_id = "comp-block-pref"
        freeze_forge_portfolio(tmp_path, run_id, "B1", "B2")
        res1 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B1"), target="B1")
        assert res1.returncode == 0, res1.stderr
        hash_b1 = extract_freeze_hash(res1)
        res2 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B2"), target="B2")
        assert res2.returncode == 0, res2.stderr
        hash_b2 = extract_freeze_hash(res2)

        # LEFT has unresolved contradiction but preference claims LEFT
        payload = valid_comparison_payload(left_id="B1", right_id="B2", preference="LEFT", left_hash=hash_b1, right_hash=hash_b2)
        payload["left_review"]["findings"]["unresolved_load_bearing_contradiction"] = True
        payload["left_review"]["terminal_state"] = "NEED_EVIDENCE"
        res = freeze_file(tmp_path, "comparison-review-v1", run_id, payload)
        assert res.returncode != 0
        assert "preference LEFT is forbidden while left review has unresolved_load_bearing_contradiction" in res.stderr

        # Return to explore on LEFT also blocks preference LEFT
        payload2 = valid_comparison_payload(left_id="B1", right_id="B2", preference="LEFT", left_hash=hash_b1, right_hash=hash_b2)
        payload2["left_review"]["terminal_state"] = "RETURN_TO_EXPLORE"
        res2 = freeze_file(tmp_path, "comparison-review-v1", run_id, payload2)
        assert res2.returncode != 0
        assert "preference LEFT is forbidden while left review terminal_state is RETURN_TO_EXPLORE" in res2.stderr

    def test_fg_d3_seam_enforcement_missing_developments(self, tmp_path):
        """FG-D3: Fail closed when either LEFT or RIGHT freeze is missing."""
        run_id = "comp-seam-missing"
        freeze_forge_portfolio(tmp_path, run_id, "B1", "B2")
        res = freeze_file(tmp_path, "comparison-review-v1", run_id, valid_comparison_payload())
        assert "references missing file" in res.stderr

        res1 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B1"), target="B1")
        assert res1.returncode == 0, res1.stderr
        hash_b1 = extract_freeze_hash(res1)
        res2 = freeze_file(
            tmp_path,
            "comparison-review-v1",
            run_id,
            valid_comparison_payload(left_id="B1", right_id="B2", left_hash=hash_b1),
        )
        assert res2.returncode != 0
        assert "references missing file" in res2.stderr

    def test_payload_ceiling_exceeded(self, tmp_path):
        """Payload ceiling >128 KiB (131072 bytes) causes fail-closed rejection."""
        run_id = "comp-ceiling"
        freeze_forge_portfolio(tmp_path, run_id, "B1", "B2")
        res1 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B1"), target="B1")
        assert res1.returncode == 0, res1.stderr
        hash_b1 = extract_freeze_hash(res1)
        res2 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B2"), target="B2")
        assert res2.returncode == 0, res2.stderr
        hash_b2 = extract_freeze_hash(res2)

        payload = valid_comparison_payload(left_id="B1", right_id="B2", left_hash=hash_b1, right_hash=hash_b2)
        payload["task_summary"] = "x" * 140000
        res = freeze_file(tmp_path, "comparison-review-v1", run_id, payload)
        assert res.returncode != 0
        assert "PAYLOAD_TOO_LARGE" in res.stderr


class TestCmpSeam:
    """CMP-SEAM-1..6: Stage ordering, hidden comparative contract, sidecar integrity, and target matches."""

    def test_cmp_seam_1_first_deep_no_comparison_contract(self, tmp_path):
        """CMP-SEAM-1: First selected Deep freeze emits no comparison contract text."""
        run_id = "seam-1"
        # Freeze search-field and portfolio selecting B3 and B7
        cand = {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "NORMAL", "candidates": [
            {"candidate_id": "c01", "title": "C1", "semantic_core": {"claim": "A", "structural_shift": "B", "mechanism": "C", "grounding_anchor": "D", "what_becomes_visible": "E", "boundary": "F"}, "epistemics": {"supported": ["A"], "inferred": [], "speculative": [], "unknown": []}},
            {"candidate_id": "c02", "title": "C2", "semantic_core": {"claim": "A2", "structural_shift": "B2", "mechanism": "C2", "grounding_anchor": "D2", "what_becomes_visible": "E2", "boundary": "F2"}, "epistemics": {"supported": ["A2"], "inferred": [], "speculative": [], "unknown": []}},
        ]}
        rcand = freeze_file(tmp_path, "explore", run_id, cand)
        sha_cand = extract_freeze_hash(rcand)
        sf = {"schema_version": "pizm-search-field-v1", "stage": "search-field", "passes": [{"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": sha_cand}], "entries": ["pass01:c01", "pass01:c02"]}
        rsf = freeze_file(tmp_path, "search-field", run_id, sf)
        sha_sf = extract_freeze_hash(rsf)

        pv2 = valid_portfolio_v2_payload(left_id="B3", right_id="B7", field_hash=sha_sf)
        freeze_file(tmp_path, "portfolio", run_id, pv2)

        # Freeze first development (B3)
        res_b3 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B3"), target="B3")
        assert res_b3.returncode == 0, res_b3.stderr
        assert "FREEZE_OK" in res_b3.stdout
        assert "--- NEXT CONTRACT ---" not in res_b3.stdout
        assert "deep-compare" not in res_b3.stdout

    def test_cmp_seam_2_second_deep_reveals_comparison_contract(self, tmp_path):
        """CMP-SEAM-2: Second verified selected Deep freeze reveals references/deep-compare.md."""
        run_id = "seam-2"
        cand = {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "NORMAL", "candidates": [
            {"candidate_id": "c01", "title": "C1", "semantic_core": {"claim": "A", "structural_shift": "B", "mechanism": "C", "grounding_anchor": "D", "what_becomes_visible": "E", "boundary": "F"}, "epistemics": {"supported": ["A"], "inferred": [], "speculative": [], "unknown": []}},
            {"candidate_id": "c02", "title": "C2", "semantic_core": {"claim": "A2", "structural_shift": "B2", "mechanism": "C2", "grounding_anchor": "D2", "what_becomes_visible": "E2", "boundary": "F2"}, "epistemics": {"supported": ["A2"], "inferred": [], "speculative": [], "unknown": []}},
        ]}
        rcand = freeze_file(tmp_path, "explore", run_id, cand)
        sha_cand = extract_freeze_hash(rcand)
        sf = {"schema_version": "pizm-search-field-v1", "stage": "search-field", "passes": [{"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": sha_cand}], "entries": ["pass01:c01", "pass01:c02"]}
        rsf = freeze_file(tmp_path, "search-field", run_id, sf)
        sha_sf = extract_freeze_hash(rsf)

        pv2 = valid_portfolio_v2_payload(left_id="B3", right_id="B7", field_hash=sha_sf)
        freeze_file(tmp_path, "portfolio", run_id, pv2)

        # Freeze first (B3)
        res_b3 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B3"), target="B3")
        assert res_b3.returncode == 0
        assert "--- NEXT CONTRACT ---" not in res_b3.stdout

        # Freeze second (B7)
        res_b7 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B7"), target="B7")
        assert res_b7.returncode == 0, res_b7.stderr
        assert "FREEZE_OK" in res_b7.stdout
        assert "--- NEXT CONTRACT ---" in res_b7.stdout
        assert "Pizm Comparative Reviewer" in res_b7.stdout

    def test_cmp_seam_3_tampered_sidecar_prevents_comparison(self, tmp_path):
        """CMP-SEAM-3: Corrupted or tampered peer sha256 sidecar fails closed."""
        run_id = "seam-3"
        freeze_forge_portfolio(tmp_path, run_id, "B3", "B7")
        res_b3 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B3"), target="B3")
        sha_b3 = extract_freeze_hash(res_b3)
        res_b7 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B7"), target="B7")
        sha_b7 = extract_freeze_hash(res_b7)

        # Tamper B3 sidecar
        sidecar_b3 = tmp_path / ".ai" / "pizm" / f"run-{run_id}" / "development-v2-B3.sha256"
        sidecar_b3.write_text("0" * 64, encoding="utf-8")

        comp = valid_comparison_payload(left_id="B3", right_id="B7", left_hash=sha_b3, right_hash=sha_b7)
        res_comp = freeze_file(tmp_path, "comparison-review-v1", run_id, comp)
        assert res_comp.returncode != 0
        assert "sidecar hash mismatch" in res_comp.stderr

    def test_cmp_seam_4_wrong_target_peer_fails_comparison(self, tmp_path):
        """CMP-SEAM-4: Wrong target in development artifact fails comparison freeze."""
        run_id = "seam-4"
        freeze_forge_portfolio(tmp_path, run_id, "B3", "B7")
        res_b3 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B3"), target="B3")
        sha_b3 = extract_freeze_hash(res_b3)

        # Freeze development targeting B8 but named development-v2-B7.json
        payload_wrong = valid_development_payload("B8")
        raw_wrong = json.dumps(payload_wrong, indent=2).encode("utf-8")
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        (run_dir / "development-v2-B7.json").write_bytes(raw_wrong)
        (run_dir / "development-v2-B7.sha256").write_text(hashlib.sha256(raw_wrong).hexdigest(), encoding="utf-8")
        (run_dir / "development-v2-B7.meta.json").write_text('{"stage":"development-v2"}', encoding="utf-8")
        sha_b7 = hashlib.sha256(raw_wrong).hexdigest()
        comp = valid_comparison_payload(left_id="B3", right_id="B7", left_hash=sha_b3, right_hash=sha_b7)
        res_comp = freeze_file(tmp_path, "comparison-review-v1", run_id, comp)
        assert res_comp.returncode != 0
        assert "target mismatch" in res_comp.stderr

    def test_cmp_seam_5_reviewer_has_no_comparative_contract(self):
        """CMP-SEAM-5: Single-model deep-reviewer.md contains no comparative contract terms."""
        reviewer_text = (Path(SKILL_ROOT) / "references" / "deep-reviewer.md").read_text(encoding="utf-8")
        forbidden = [
            "pizm-comparison-review-v1",
            "review_B1",
            "review_B2",
            "left_review",
            "right_review",
            "current_preference",
            "Comparator Role",
            "strongest_reason_for_",
        ]
        for term in forbidden:
            assert term not in reviewer_text, f"Forbidden term {term!r} found in deep-reviewer.md"

    def test_cmp_seam_6_stage_order_compare_before_both_deeps_fails(self, tmp_path):
        """CMP-SEAM-6: Stage order enforced: attempting comparison before both deeps fails closed."""
        run_id = "seam-6"
        freeze_forge_portfolio(tmp_path, run_id, "B1", "B2")
        res_b1 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B1"), target="B1")
        sha_b1 = extract_freeze_hash(res_b1)

        comp = valid_comparison_payload(left_id="B1", right_id="B2", left_hash=sha_b1, right_hash="b" * 64)
        res_comp = freeze_file(tmp_path, "comparison-review-v1", run_id, comp)
        assert res_comp.returncode != 0
        assert "references missing file" in res_comp.stderr


class TestBidArbitraryAndRejection:
    """BID-1..4: Arbitrary B-IDs, legacy rejection, and symmetrical preference couplings."""

    def test_bid_1_arbitrary_b3_b7_success(self, tmp_path):
        """BID-1: Arbitrary bundle IDs (e.g. B3, B7) succeed throughout the pipeline."""
        run_id = "bid-1"
        freeze_forge_portfolio(tmp_path, run_id, "B3", "B7")
        res3 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B3"), target="B3")
        assert res3.returncode == 0
        hash3 = extract_freeze_hash(res3)

        res7 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B7"), target="B7")
        assert res7.returncode == 0
        hash7 = extract_freeze_hash(res7)

        comp = valid_comparison_payload(left_id="B3", right_id="B7", preference="LEFT", left_hash=hash3, right_hash=hash7)
        res_comp = freeze_file(tmp_path, "comparison-review-v1", run_id, comp)
        assert res_comp.returncode == 0, res_comp.stderr
        assert "FREEZE_OK" in res_comp.stdout

    def test_bid_2_canonical_b1_b2_success(self, tmp_path):
        """BID-2: Canonical B1 and B2 bundle IDs succeed."""
        run_id = "bid-2"
        freeze_forge_portfolio(tmp_path, run_id, "B1", "B2")
        res1 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B1"), target="B1")
        assert res1.returncode == 0
        hash1 = extract_freeze_hash(res1)

        res2 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B2"), target="B2")
        assert res2.returncode == 0
        hash2 = extract_freeze_hash(res2)

        comp = valid_comparison_payload(left_id="B1", right_id="B2", preference="RIGHT", left_hash=hash1, right_hash=hash2)
        res_comp = freeze_file(tmp_path, "comparison-review-v1", run_id, comp)
        assert res_comp.returncode == 0, res_comp.stderr
        assert "FREEZE_OK" in res_comp.stdout

    def test_bid_3_legacy_keys_and_preferences_rejected(self, tmp_path):
        """BID-3: Legacy review_B1/B2 keys, strongest_reason_for_B1/B2, and B1/B2 preferences are rejected."""
        run_id = "bid-3"
        freeze_forge_portfolio(tmp_path, run_id, "B1", "B2")
        res1 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B1"), target="B1")
        hash1 = extract_freeze_hash(res1)
        res2 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B2"), target="B2")
        hash2 = extract_freeze_hash(res2)

        # Legacy review_B1 key
        p1 = valid_comparison_payload(left_id="B1", right_id="B2", left_hash=hash1, right_hash=hash2)
        p1["review_B1"] = p1["left_review"]
        res_p1 = freeze_file(tmp_path, "comparison-review-v1", run_id, p1)
        assert res_p1.returncode != 0
        assert "legacy review_B1/review_B2 fields are forbidden" in res_p1.stderr

        # Legacy preference "B1"
        p2 = valid_comparison_payload(left_id="B1", right_id="B2", left_hash=hash1, right_hash=hash2)
        p2["comparison"]["current_preference"] = "B1"
        res_p2 = freeze_file(tmp_path, "comparison-review-v1", run_id, p2)
        assert res_p2.returncode != 0
        assert "comparison.current_preference must be one of" in res_p2.stderr

        # Legacy strongest_reason_for_B1
        p3 = valid_comparison_payload(left_id="B1", right_id="B2", left_hash=hash1, right_hash=hash2)
        p3["comparison"]["strongest_reason_for_B1"] = "some reason"
        res_p3 = freeze_file(tmp_path, "comparison-review-v1", run_id, p3)
        assert res_p3.returncode != 0
        assert "legacy strongest_reason_for_B1/B2 keys are forbidden" in res_p3.stderr

    def test_bid_4_preference_couplings_both_sides(self, tmp_path):
        """BID-4: Preference couplings work symmetrically on LEFT and RIGHT."""
        run_id = "bid-4"
        freeze_forge_portfolio(tmp_path, run_id, "B1", "B2")
        res1 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B1"), target="B1")
        hash1 = extract_freeze_hash(res1)
        res2 = freeze_file(tmp_path, "development-v2", run_id, valid_development_payload("B2"), target="B2")
        hash2 = extract_freeze_hash(res2)

        # RIGHT review has unresolved contradiction and preference is RIGHT -> rejected
        p_right_contra = valid_comparison_payload(left_id="B1", right_id="B2", preference="RIGHT", left_hash=hash1, right_hash=hash2)
        p_right_contra["right_review"]["findings"]["unresolved_load_bearing_contradiction"] = True
        p_right_contra["right_review"]["terminal_state"] = "NEED_EVIDENCE"
        res = freeze_file(tmp_path, "comparison-review-v1", run_id, p_right_contra)
        assert res.returncode != 0
        assert "preference RIGHT is forbidden while right review has unresolved_load_bearing_contradiction" in res.stderr

        # But preference LEFT is allowed when RIGHT has contradiction
        p_left_valid = valid_comparison_payload(left_id="B1", right_id="B2", preference="LEFT", left_hash=hash1, right_hash=hash2)
        p_left_valid["right_review"]["findings"]["unresolved_load_bearing_contradiction"] = True
        p_left_valid["right_review"]["terminal_state"] = "NEED_EVIDENCE"
        res_left = freeze_file(tmp_path, "comparison-review-v1", run_id, p_left_valid)
        assert res_left.returncode == 0, res_left.stderr
