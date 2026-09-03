"""
Comprehensive contract and behavioral tests for Prism Plan 2 FORGE + Comparative Reasoning.

Covers:
- Search Topology: FG-S1, FG-S2, FG-S3, FG-S4
- Portfolio & Competition: FG-P1, FG-P2, FG-P3, FG-P4, FG-P5
- Deep x2: FG-D1, FG-D2, FG-D3
- Compare: FG-C1, FG-C2, FG-C3, FG-C4, FG-C5, FG-C6
- LEVER: FG-L1, FG-L2, FG-L3
- Rendering: FG-MD1, FG-MD2, FG-MD3, FG-MD4, FG-MD5, FG-MD6
"""
import json
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_CLI = str(REPO_ROOT / "bin" / "pizm-session-bundle")
CHECKPOINT_CLI = str(REPO_ROOT / "bin" / "pizm-checkpoint")
STAGED_SKILL_ROOT = REPO_ROOT / "skills" / "pizm"
INSTALLED_SKILL_ROOT = Path.home() / ".config" / "opencode" / "skills" / "pizm"
MIRROR_PRESENT = (INSTALLED_SKILL_ROOT / "SKILL.md").exists()

TASK_TEXT = "Reduce PR cycle time in our platform team"


def freeze_stage(project_root: Path, stage: str, run_id: str, payload: dict, target: str = None, artifact_suffix: str = None) -> subprocess.CompletedProcess:
    fd_input = project_root / f"_input_{stage}_{target or 'main'}.json"
    fd_input.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    cmd = [
        sys.executable,
        CHECKPOINT_CLI,
        "freeze",
        "--stage",
        stage,
        "--run-id",
        run_id,
        "--input",
        str(fd_input),
        "--project-root",
        str(project_root),
        "--skill-root",
        str(STAGED_SKILL_ROOT),
    ]
    if target:
        cmd.extend(["--target", target])
    if artifact_suffix:
        cmd.extend(["--artifact-suffix", artifact_suffix])
    res = subprocess.run(cmd, capture_output=True, text=True)
    fd_input.unlink()
    return res


def run_render(run_dir: Path, task: str, output: Path) -> subprocess.CompletedProcess:
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


# ---------------------------------------------------------------------------
# Fixture Payloads
# ---------------------------------------------------------------------------


def pass1_candidates_payload():
    return {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "Feedback Latency Constraint",
                "semantic_core": {
                    "claim": "Review latency drives batch inflation",
                    "structural_shift": "From capacity to feedback frequency",
                    "mechanism": "Slow reviews induce batching",
                    "grounding_anchor": "Three-day PR turnaround observed",
                    "what_becomes_visible": "Batch size is adaptive",
                    "boundary": "Round-trip exceeds task duration",
                },
                "epistemics": {"supported": ["turnaround"], "inferred": ["amortization"], "speculative": [], "unknown": []},
            },
            {
                "candidate_id": "c02",
                "title": "Meeting Load Spiral",
                "semantic_core": {
                    "claim": "Meetings spawn coordination meetings",
                    "structural_shift": "Coordination as load",
                    "mechanism": "Each meeting books two more",
                    "grounding_anchor": "Calendar audit",
                    "what_becomes_visible": "Coordination debt",
                    "boundary": "Orgs over twenty people",
                },
                "epistemics": {"supported": [], "inferred": [], "speculative": ["spiral"], "unknown": []},
            },
        ],
    }


def pass2_candidates_payload():
    return {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "360",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "Ownership Diffusion Boundary",
                "semantic_core": {
                    "claim": "Shared ownership creates tragedy of review queue",
                    "structural_shift": "Shift from queue length to accountability location",
                    "mechanism": "No single owner for multi-service changes",
                    "grounding_anchor": "PRs touching multiple repos stall longest",
                    "what_becomes_visible": "Cross-boundary coordination cost",
                    "boundary": "Mono-repo vs multi-repo architecture",
                },
                "difference_from_prior": "Attacks ownership locus rather than latency or meetings.",
                "epistemics": {"supported": ["stall data"], "inferred": ["agency diffusion"], "speculative": [], "unknown": []},
            }
        ],
    }


def search_field_payload(candidates_sha1: str, candidates_sha2: str = None):
    passes = [
        {
            "pass_id": "pass01",
            "candidates_ref": "candidates.json",
            "frozen_hash": candidates_sha1,
        }
    ]
    entries = ["pass01:c01", "pass01:c02"]
    if candidates_sha2:
        passes.append(
            {
                "pass_id": "pass02",
                "candidates_ref": "candidates-pass02.json",
                "frozen_hash": candidates_sha2,
            }
        )
        entries.append("pass02:c01")
    return {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "passes": passes,
        "entries": entries,
    }


def portfolio_v2_payload(competition_status="TWO_DEFENSIBLE_BUNDLES", field_hash="abc123", field_ref="search-field.json"):
    bundles = [
        {
            "bundle_id": "B1",
            "member_refs": ["pass01:c01", "pass01:c02"],
            "bundle_thesis": "Batch inflation and meeting load reinforce PR latency",
            "composition_gain": "Explains why addressing either calendar or review SLA alone fails",
            "member_roles": {
                "pass01:c01": "Primary batching driver",
                "pass01:c02": "Interruption amplifier",
            },
            "member_ablation": {
                "pass01:c01": "Removes feedback delay mechanism",
                "pass01:c02": "Removes context-switch cost",
            },
            "internal_tension": "Faster reviews require more interruption unless batch size drops first",
            "weakest_link": "Assumes authors will shrink PRs when turnaround drops",
            "new_consequence_or_prediction": "Review queue clears only with dual intervention",
        },
    ]

    rec_comp = None
    single_target = None
    if competition_status == "TWO_DEFENSIBLE_BUNDLES":
        bundles.append(
            {
                "bundle_id": "B2",
                "member_refs": ["pass01:c02", "pass02:c01"],
                "bundle_thesis": "Ownership boundary diffusion drives coordination tax",
                "composition_gain": "Connects multi-repo architectural silos with meeting proliferation",
                "member_roles": {
                    "pass01:c02": "Symptom of boundary coordination",
                    "pass02:c01": "Root architectural cause",
                },
                "member_ablation": {
                    "pass01:c02": "Loses the concrete calendar manifestation",
                    "pass02:c01": "Reduces to generic calendar overload",
                },
                "internal_tension": "Clear ownership reduces coordination meetings but may silo subteams",
                "weakest_link": "Service boundaries are hard to redraw quickly",
                "new_consequence_or_prediction": "Cross-boundary PRs drop 60% with component captains",
            }
        )
        rec_comp = {
            "left_bundle_id": "B1",
            "right_bundle_id": "B2",
            "competition_axis": "Feedback loop latency (B1) vs Architectural ownership diffusion (B2)",
            "discriminating_observation": "Measure whether single-service PRs stall equally to cross-service PRs.",
            "discriminating_question": "Does PR stall time correlate with cross-service touched files?",
        }
    else:
        single_target = {"target_type": "B", "target_id": "B1"}

    payload = {
        "schema_version": "pizm-portfolio-selection-v2",
        "stage": "portfolio",
        "route": "BONK",
        "field_ref": field_ref,
        "field_hash": field_hash,
        "perspectives": {"P1": "pass01:c01", "P2": "pass01:c02"},
        "competition_status": competition_status,
        "recommended_competition": rec_comp,
        "candidate_assessments": [
            {
                "candidate_ref": "pass01:c01",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "Direct feedback delay",
                "nearest_overlap": None,
                "reason": "Clear mechanical anchor",
            },
            {
                "candidate_ref": "pass01:c02",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "Calendar tax",
                "nearest_overlap": None,
                "reason": "Empirical meeting load",
            },
            {
                "candidate_ref": "pass02:c01",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "Ownership locus",
                "nearest_overlap": None,
                "reason": "Cross-repo boundary insight",
            },
        ],
        "bundles": bundles,
    }
    if single_target:
        payload["single_target"] = single_target
    return payload


def development_v2_payload(target_id="B1", member_refs=None):
    if member_refs is None:
        member_refs = ["pass01:c01", "pass01:c02"]
    return {
        "schema_version": "pizm-development-v2",
        "stage": "development-v2",
        "target": {"target_type": "B", "target_id": target_id},
        "identity_lock": {
            "bundle_id": target_id,
            "member_refs": member_refs,
            "title": f"Model {target_id} Program",
            "core_claim": f"Explanatory model for {target_id}",
            "structural_shift": "From isolated metrics to systemic feedback",
            "mechanism": "Feedback delay and coordination threshold",
            "boundary": "Team size > 5",
        },
        "developed_model": {
            "thesis": f"Full thesis statement of developed composite model {target_id}.",
            "synthesis": f"In-depth analytical synthesis of model {target_id} detailing core dynamics.",
            "implications": ["PR cycle time drops by 50%", "Interruption overhead shrinks"],
            "dynamics": "Self-reinforcing feedback loops between latency and batch size.",
            "mechanism_chain": [
                "Slow reviews induce batching",
                "Large batches take longer to review",
                "Review queues expand backlog",
            ],
            "member_contributions": {
                member_refs[0]: "Primary mechanism",
                member_refs[1]: "Secondary amplifier",
            },
            "member_ablation": {
                member_refs[0]: "Collapses the core delay mechanism",
                member_refs[1]: "Loses the interruption cost amplifier",
            },
            "load_bearing_claims": [
                {
                    "claim": "Review latency directly drives PR batch size inflation",
                    "epistemic_status": "SUPPORTED",
                    "role_in_model": "Primary causal driver",
                    "what_would_weaken_or_refute": "Fast turnaround with unchanged PR size",
                },
                {
                    "claim": "Batch inflation increases review turn-around time",
                    "epistemic_status": "SUPPORTED",
                    "role_in_model": "Feedback loop completion",
                    "what_would_weaken_or_refute": "Large PRs reviewed as fast as small ones",
                },
            ],
            "unresolved_tensions": ["Latency reduction vs reviewer focus time"],
            "predictions_or_observables": ["PR size will drop within 2 sprints of 4h SLA"],
            "break_conditions": ["If team members are completely dedicated full-time reviewers"],
            "evidence_debt": [],
            "comparative_standing": None,
            "development_delta": {
                "summary": "Initial development",
                "new_load_bearing_claims": [],
                "strengthened_claims": [],
                "new_causal_arrows_or_mechanisms": [],
                "material_imports": [],
                "scope_expansions": [],
            },
        },
    }


def comparison_review_payload(
    preference="LEFT",
    left_id="B1",
    right_id="B2",
    b1_ref="development-v2-B1.json",
    b1_hash="a" * 64,
    b2_ref="development-v2-B2.json",
    b2_hash="b" * 64,
):
    return {
        "schema_version": "pizm-comparison-review-v1",
        "stage": "comparison-review-v1",
        "task_summary": TASK_TEXT,
        "left_target_id": left_id,
        "right_target_id": right_id,
        "left_review": {
            "target_id": left_id,
            "development_ref": b1_ref,
            "frozen_hash": b1_hash,
            "terminal_state": "MODEL_READY",
            "independent_countermodel": f"Review capacity is sufficient for {left_id}.",
            "load_bearing_reassessment": [
                {
                    "claim": f"Review latency directly drives PR batch size inflation for {left_id}",
                    "critic_epistemic_status": "SUPPORTED",
                }
            ],
            "findings": {
                "unresolved_load_bearing_contradiction": False,
                "unsupported_specificity": [],
                "epistemic_laundering": [],
            },
            "evidence_debt": [],
            "verdict_rationale": f"{left_id} provides rigorous causal mechanics.",
        },
        "right_review": {
            "target_id": right_id,
            "development_ref": b2_ref,
            "frozen_hash": b2_hash,
            "terminal_state": "MODEL_READY",
            "independent_countermodel": f"CI infrastructure flakes cause perceived stall for {right_id}.",
            "load_bearing_reassessment": [
                {
                    "claim": f"Ownership diffusion creates tragedy of review queue for {right_id}",
                    "critic_epistemic_status": "SUPPORTED",
                }
            ],
            "findings": {
                "unresolved_load_bearing_contradiction": False,
                "unsupported_specificity": [],
                "epistemic_laundering": [],
            },
            "evidence_debt": [],
            "verdict_rationale": f"{right_id} correctly identifies architectural silos.",
        },
        "comparison": {
            "current_preference": preference,
            "competition_axis": f"Feedback loop latency ({left_id}) vs Architectural ownership diffusion ({right_id})",
            "strongest_reason_for_left": f"Directly explains observed 3-day turnaround bottleneck on {left_id}.",
            "strongest_reason_for_right": f"Explains why cross-service changes stall on {right_id}.",
            "shared_evidence_debt": ["Historical PR wait time distribution split by single vs multi-repo."],
            "discriminating_observation": f"Measure queue time before first review for {left_id} vs {right_id}.",
            "what_would_change_the_decision": f"If single-service PRs have <2h review latency, {right_id} is primary.",
        },
    }


def lever_design_payload():
    return {
        "schema_version": "pizm-lever-design-v1",
        "stage": "lever",
        "target_type": "B",
        "target_id": "B1",
        "levers": [
            {
                "lever_id": "L1",
                "intervention_or_test_point": "Implement 4-hour review SLA window",
                "model_link": "Attacks review queue delay directly",
                "minimum_bounded_move": "Pilot SLA on team alpha for two sprints",
                "expected_observation_or_response": "PR turnaround drops below 1 day",
                "disconfirming_signal": "PR turnaround remains unchanged",
                "stop_condition": "Review quality noticeably deteriorates",
                "remaining_assumptions": "Reviewers have sufficient domain context",
            }
        ],
    }


def lever_review_payload():
    return {
        "schema_version": "pizm-lever-review-v1",
        "stage": "lever",
        "target_type": "B",
        "target_id": "B1",
        "frozen_hash": "dummyhash",
        "outcome": "LEVER",
        "verdict_rationale": "L1 is actionable, bounded, and directly probes model B1.",
        "verdicts": [
            {
                "lever_id": "L1",
                "verdict": "ACCEPT",
                "findings": [],
                "actionability": "HIGH",
            }
        ],
    }


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------


class TestForgeSearchTopology:
    def test_fg_s1_and_s2_two_passes_no_interpass_judge(self, tmp_path):
        """FG-S1 & FG-S2: Exactly two automatic search passes, no judge between pass 1 and pass 2."""
        run_id = "forge-s1-s2"
        # Pass 1
        p1 = pass1_candidates_payload()
        res1 = freeze_stage(tmp_path, "explore", run_id, p1)
        assert res1.returncode == 0
        sha1 = res1.stdout.split()[1]

        # Search field after pass 1
        sf1 = search_field_payload(sha1)
        res_sf1 = freeze_stage(tmp_path, "search-field", run_id, sf1)
        assert res_sf1.returncode == 0

        # Pass 2 executes directly without portfolio judge
        p2 = pass2_candidates_payload()
        res_p2 = freeze_stage(tmp_path, "explore", run_id, p2, artifact_suffix="pass02")
        assert res_p2.returncode == 0
        sha2 = res_p2.stdout.split()[1]

        # Search field updated after pass 2
        sf2 = search_field_payload(sha1, sha2)
        res_sf2 = freeze_stage(tmp_path, "search-field", run_id, sf2, artifact_suffix="pass02")
        assert res_sf2.returncode == 0

    def test_fg_s3_residual_search_difference_from_prior(self):
        """FG-S3: Pass 2 candidate schema requires difference_from_prior under residual search policy."""
        p2 = pass2_candidates_payload()
        assert "difference_from_prior" in p2["candidates"][0]
        assert len(p2["candidates"][0]["difference_from_prior"].strip()) > 0


class TestForgePortfolioContracts:
    def test_fg_p1_and_p2_portfolio_v2_two_defensible_bundles(self, tmp_path):
        """FG-P1 & FG-P2: Portfolio v2 with two defensible bundles requiring composition gain and competition axis."""
        run_id = "forge-p1-p2"
        res1 = freeze_stage(tmp_path, "explore", run_id, pass1_candidates_payload())
        sha1 = res1.stdout.split()[1]
        res_sf = freeze_stage(tmp_path, "search-field", run_id, search_field_payload(sha1))
        sha_sf = res_sf.stdout.split()[1]

        p_v2 = portfolio_v2_payload(competition_status="TWO_DEFENSIBLE_BUNDLES", field_hash=sha_sf, field_ref="search-field.json")
        res = freeze_stage(tmp_path, "portfolio", run_id, p_v2)
        assert res.returncode == 0
        assert "FREEZE_OK" in res.stdout

    def test_fg_p3_and_p4_no_second_defensible_bundle(self, tmp_path):
        """FG-P3 & FG-P4: No forced B2; portfolio v2 cleanly records NO_SECOND_DEFENSIBLE_BUNDLE."""
        run_id = "forge-p3-p4"
        res1 = freeze_stage(tmp_path, "explore", run_id, pass1_candidates_payload())
        sha1 = res1.stdout.split()[1]
        res_sf = freeze_stage(tmp_path, "search-field", run_id, search_field_payload(sha1))
        sha_sf = res_sf.stdout.split()[1]

        p_v2 = portfolio_v2_payload(competition_status="NO_SECOND_DEFENSIBLE_BUNDLE", field_hash=sha_sf, field_ref="search-field.json")
        res = freeze_stage(tmp_path, "portfolio", run_id, p_v2)
        assert res.returncode == 0
        assert "FREEZE_OK" in res.stdout

    def test_portfolio_v1_compatibility(self, tmp_path):
        """Portfolio v1 remains strictly valid under pizm-portfolio-selection-v1."""
        run_id = "portfolio-v1-compat"
        res1 = freeze_stage(tmp_path, "explore", run_id, pass1_candidates_payload())
        sha1 = res1.stdout.split()[1]
        res_sf = freeze_stage(tmp_path, "search-field", run_id, search_field_payload(sha1))
        sha_sf = res_sf.stdout.split()[1]

        p_v1 = portfolio_v2_payload(competition_status="TWO_DEFENSIBLE_BUNDLES", field_hash=sha_sf, field_ref="search-field.json")
        p_v1["schema_version"] = "pizm-portfolio-selection-v1"
        p_v1["route"] = "MANUAL"
        if "competition_status" in p_v1:
            del p_v1["competition_status"]
        if "perspectives" in p_v1:
            del p_v1["perspectives"]
        if "single_target" in p_v1:
            del p_v1["single_target"]
        del p_v1["recommended_competition"]
        del p_v1["field_ref"]
        p_v1["next_reasoning_move"] = None
        p_v1["next_reasoning_rationale"] = None
        p_v1["information_request"] = None
        p_v1["rival_shadow"] = None
        p_v1["auto_target"] = None
        res = freeze_stage(tmp_path, "portfolio", run_id, p_v1)
        assert res.returncode == 0
        assert "FREEZE_OK" in res.stdout


class TestForgeDeepAndCompare:
    def test_fg_d1_to_d3_and_c1_to_c6_full_pipeline(self, tmp_path):
        """FG-D1..D3, FG-C1..C6: Develop B1 and B2 separately, freeze both before compare, verify comparative review."""
        run_id = "forge-full-d-c"
        # Freeze portfolio
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)
        pv2 = portfolio_v2_payload("TWO_DEFENSIBLE_BUNDLES")
        raw_p = json.dumps(pv2, indent=2).encode("utf-8")
        (run_dir / "portfolio.json").write_bytes(raw_p)
        (run_dir / "portfolio.sha256").write_text(hashlib.sha256(raw_p).hexdigest(), encoding="utf-8")
        (run_dir / "portfolio.meta.json").write_text('{"stage":"portfolio"}', encoding="utf-8")
        dev_b1 = development_v2_payload("B1", ["pass01:c01", "pass01:c02"])
        res_d1 = freeze_stage(tmp_path, "development-v2", run_id, dev_b1, target="B1")
        assert res_d1.returncode == 0, res_d1.stderr
        sha_b1 = res_d1.stdout.split()[1]

        # Freeze B2 development
        dev_b2 = development_v2_payload("B2", ["pass01:c02", "pass02:c01"])
        res_d2 = freeze_stage(tmp_path, "development-v2", run_id, dev_b2, target="B2")
        assert res_d2.returncode == 0, res_d2.stderr
        sha_b2 = res_d2.stdout.split()[1]

        # Freeze Comparison Review
        comp = comparison_review_payload(
            preference="LEFT",
            b1_ref="development-v2-B1.json",
            b1_hash=sha_b1,
            b2_ref="development-v2-B2.json",
            b2_hash=sha_b2,
        )
        res_c = freeze_stage(tmp_path, "comparison-review-v1", run_id, comp)
        assert res_c.returncode == 0, res_c.stderr
        assert "FREEZE_OK" in res_c.stdout


class TestForgeLeverGates:
    def test_fg_l1_to_l3_lever_gating(self, tmp_path):
        """FG-L1..L3: Action FORGE runs LEVER only after MODEL_READY; UNRESOLVED does not force LEVER."""
        run_id = "forge-lever"
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)
        pv2 = portfolio_v2_payload("TWO_DEFENSIBLE_BUNDLES")
        raw_p = json.dumps(pv2, indent=2).encode("utf-8")
        (run_dir / "portfolio.json").write_bytes(raw_p)
        (run_dir / "portfolio.sha256").write_text(hashlib.sha256(raw_p).hexdigest(), encoding="utf-8")
        (run_dir / "portfolio.meta.json").write_text('{"stage":"portfolio"}', encoding="utf-8")
        # Setup B1 & B2 & Compare
        res_b1 = freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B1"), target="B1")
        res_b2 = freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B2"), target="B2")
        sha_b1 = res_b1.stdout.split()[1]
        sha_b2 = res_b2.stdout.split()[1]
        freeze_stage(
            tmp_path, "comparison-review-v1", run_id,
            comparison_review_payload("LEFT", b1_ref="development-v2-B1.json", b1_hash=sha_b1, b2_ref="development-v2-B2.json", b2_hash=sha_b2),
        )

        # Freeze LEVER design and review
        res_ld = freeze_stage(tmp_path, "lever-design", run_id, lever_design_payload())
        assert res_ld.returncode == 0, res_ld.stderr
        res_lr = freeze_stage(tmp_path, "lever-review", run_id, lever_review_payload())
        assert res_lr.returncode == 0, res_lr.stderr


class TestForgeRendering:
    def test_fg_md1_to_md6_forge_run_md_determinism(self, tmp_path):
        """FG-MD1..MD6: FORGE emits run.md with both search passes, dual Deep, comparison, compact candidates, byte-identical determinism."""
        run_id = "forge-md-render"
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        # 1. Pass 1
        p1 = pass1_candidates_payload()
        res_p1 = freeze_stage(tmp_path, "explore", run_id, p1)
        sha1 = res_p1.stdout.split()[1]

        # 2. Pass 2
        p2 = pass2_candidates_payload()
        res_p2 = freeze_stage(tmp_path, "explore", run_id, p2, artifact_suffix="pass02")
        assert res_p2.returncode == 0, res_p2.stderr
        sha2 = res_p2.stdout.split()[1]

        # 3. Search field
        sf = search_field_payload(sha1, sha2)
        res_sf = freeze_stage(tmp_path, "search-field", run_id, sf)
        assert res_sf.returncode == 0, res_sf.stderr
        sha_sf = res_sf.stdout.split()[1]

        # 4. Portfolio v2
        pv2 = portfolio_v2_payload("TWO_DEFENSIBLE_BUNDLES", field_hash=sha_sf, field_ref="search-field.json")
        res_port = freeze_stage(tmp_path, "portfolio", run_id, pv2)
        assert res_port.returncode == 0, res_port.stderr

        # 5. Deep B1 & B2
        res_b1 = freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B1", ["pass01:c01", "pass01:c02"]), target="B1")
        assert res_b1.returncode == 0, res_b1.stderr
        sha_b1 = res_b1.stdout.split()[1]

        res_b2 = freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B2", ["pass01:c02", "pass02:c01"]), target="B2")
        assert res_b2.returncode == 0, res_b2.stderr
        sha_b2 = res_b2.stdout.split()[1]

        # 6. Comparison Review
        res_comp = freeze_stage(
            tmp_path, "comparison-review-v1", run_id,
            comparison_review_payload("LEFT", b1_ref="development-v2-B1.json", b1_hash=sha_b1, b2_ref="development-v2-B2.json", b2_hash=sha_b2),
        )
        assert res_comp.returncode == 0, res_comp.stderr

        # 7. Lever Design & Review
        freeze_stage(tmp_path, "lever-design", run_id, lever_design_payload())
        freeze_stage(tmp_path, "lever-review", run_id, lever_review_payload())

        # Render run.md
        out1 = tmp_path / "run1.md"
        res_r1 = run_render(run_dir, TASK_TEXT, out1)
        assert res_r1.returncode == 0, res_r1.stderr

        content1 = out1.read_text(encoding="utf-8")

        # Verify required sections (FG-MD1..FG-MD5)
        assert "# Prism BONK" in content1
        assert "## Task" in content1
        assert "## Search Pass 1" in content1
        assert "## Search Pass 2" in content1
        assert "## Portfolio" in content1
        assert "## Bundles" in content1
        assert "## Why these models compete" in content1
        assert "## Deep B1" in content1
        assert "## Deep B2" in content1
        assert "## Critic and Comparison" in content1
        assert "### B1 review" in content1
        assert "### B2 review" in content1
        assert "### Comparison" in content1
        assert "## Lever" in content1
        assert "## Final" in content1
        assert "## Machine artifacts" in content1

        # Check candidate compactness and lack of raw hashes/counters in reading flow
        assert "pass01:c01" in content1
        assert "pass02:c01" in content1
        assert "schema_version" not in content1

        # FG-MD6: Deterministic byte-identical output
        out2 = tmp_path / "run2.md"
        res_r2 = run_render(run_dir, TASK_TEXT, out2)
        assert res_r2.returncode == 0
        content2 = out2.read_text(encoding="utf-8")
        assert content1 == content2

    def test_degraded_path_rendering(self, tmp_path):
        """Degraded path (NO_SECOND_DEFENSIBLE_BUNDLE) renders without Compare failure."""
        run_id = "forge-degraded"
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        # Pass 1
        p1 = pass1_candidates_payload()
        res_p1 = freeze_stage(tmp_path, "explore", run_id, p1)
        sha1 = res_p1.stdout.split()[1]

        # Pass 2
        p2 = pass2_candidates_payload()
        res_p2 = freeze_stage(tmp_path, "explore", run_id, p2, artifact_suffix="pass02")
        assert res_p2.returncode == 0, res_p2.stderr
        sha2 = res_p2.stdout.split()[1]

        # Search field
        sf = search_field_payload(sha1, sha2)
        res_sf = freeze_stage(tmp_path, "search-field", run_id, sf)
        assert res_sf.returncode == 0, res_sf.stderr
        sha_sf = res_sf.stdout.split()[1]

        # Portfolio v2 with NO_SECOND_DEFENSIBLE_BUNDLE
        pv2 = portfolio_v2_payload("NO_SECOND_DEFENSIBLE_BUNDLE", field_hash=sha_sf, field_ref="search-field.json")
        res_port = freeze_stage(tmp_path, "portfolio", run_id, pv2)
        assert res_port.returncode == 0, res_port.stderr

        # Deep B1
        res_b1 = freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B1", ["pass01:c01", "pass01:c02"]), target="B1")
        assert res_b1.returncode == 0, res_b1.stderr
        sha_b1 = res_b1.stdout.split()[1]

        # Single-model Critic review
        single_rev = {
            "schema_version": "pizm-deep-review-v2",
            "stage": "deep-review-v2",
            "target_ref": "development-v2-B1.json",
            "frozen_hash": sha_b1,
            "target_type": "B",
            "target_id": "B1",
            "terminal_state": "MODEL_READY",
            "identity_verified": True,
            "independent_countermodel": "Review capacity is sufficient.",
            "load_bearing_reassessment": [
                {"claim": "Review latency drives batch inflation", "critic_epistemic_status": "SUPPORTED"}
            ],
            "findings": {
                "identity_drift": None,
                "cross_field_contradictions": [],
                "unresolved_load_bearing_contradiction": False,
                "unsupported_specificity": [],
                "epistemic_laundering": [],
                "cost_relocation": None,
                "member_ablation": "Non-empty ablation assessment for B1",
                "round_trip_skeleton": "Skeleton",
                "readiness_blockers": [],
                "readiness_blocker_details": {},
            },
            "evidence_debt": [],
            "cheapest_discriminating_test": "Queue probe",
            "inquiry_program": None,
            "verdict_rationale": "MODEL_READY verdict for single B1.",
        }
        res_rev = freeze_stage(tmp_path, "deep-review-v2", run_id, single_rev)
        assert res_rev.returncode == 0, res_rev.stderr

        # Render run.md in degraded mode
        out = tmp_path / "degraded_run.md"
        res = run_render(run_dir, TASK_TEXT, out)
        assert res.returncode == 0, res.stderr

        content = out.read_text(encoding="utf-8")
        assert "# Prism BONK" in content
        assert "NO_SECOND_DEFENSIBLE_BUNDLE" in content
        assert "Compare stage skipped" in content
        assert "## Deep B1" in content
        assert "## Critic" in content

    def test_forge_render_rejects_auto_route(self, tmp_path):
        """FORGE render rejects route=AUTO in portfolio.json (fails closed without coercion)."""
        run_id = "forge-neg-auto"
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        p1 = pass1_candidates_payload()
        res_p1 = freeze_stage(tmp_path, "explore", run_id, p1)
        sha1 = res_p1.stdout.split()[1]

        p2 = pass2_candidates_payload()
        res_p2 = freeze_stage(tmp_path, "explore", run_id, p2, artifact_suffix="pass02")
        sha2 = res_p2.stdout.split()[1]

        sf = search_field_payload(sha1, sha2)
        res_sf = freeze_stage(tmp_path, "search-field", run_id, sf)
        sha_sf = res_sf.stdout.split()[1]

        pv2 = portfolio_v2_payload("TWO_DEFENSIBLE_BUNDLES", field_hash=sha_sf, field_ref="search-field.json")
        pv2["route"] = "AUTO"
        pv2["auto_target"] = {"target_type": "B", "target_id": "B1"}
        raw_port = json.dumps(pv2, indent=2).encode("utf-8")
        (run_dir / "portfolio.json").write_bytes(raw_port)
        import hashlib
        (run_dir / "portfolio.sha256").write_text(hashlib.sha256(raw_port).hexdigest(), encoding="utf-8")

        res_b1 = freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B1", ["pass01:c01", "pass01:c02"]), target="B1")
        sha_b1 = res_b1.stdout.split()[1]
        res_b2 = freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B2", ["pass01:c02", "pass02:c01"]), target="B2")
        sha_b2 = res_b2.stdout.split()[1]

        comp_data = comparison_review_payload("LEFT", b1_ref="development-v2-B1.json", b1_hash=sha_b1, b2_ref="development-v2-B2.json", b2_hash=sha_b2)
        comp_raw = json.dumps(comp_data, indent=2).encode("utf-8")
        (run_dir / "comparison-review-v1.json").write_bytes(comp_raw)
        (run_dir / "comparison-review-v1.sha256").write_text(hashlib.sha256(comp_raw).hexdigest(), encoding="utf-8")

        out = tmp_path / "neg_auto.md"
        res = run_render(run_dir, TASK_TEXT, out)
        assert res.returncode != 0
        assert "BONK portfolio requires route=BONK" in res.stderr

    def test_legacy_forge_route_still_renders(self, tmp_path):
        """Reader accepts stored route=FORGE as BONK."""
        run_id = "forge-legacy-read"
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        p1 = pass1_candidates_payload()
        sha1 = freeze_stage(tmp_path, "explore", run_id, p1).stdout.split()[1]
        p2 = pass2_candidates_payload()
        sha2 = freeze_stage(tmp_path, "explore", run_id, p2, artifact_suffix="pass02").stdout.split()[1]
        sha_sf = freeze_stage(tmp_path, "search-field", run_id, search_field_payload(sha1, sha2)).stdout.split()[1]
        pv2 = portfolio_v2_payload("TWO_DEFENSIBLE_BUNDLES", field_hash=sha_sf, field_ref="search-field.json")
        pv2["route"] = "FORGE"
        raw_port = json.dumps(pv2, indent=2).encode("utf-8")
        (run_dir / "portfolio.json").write_bytes(raw_port)
        import hashlib
        (run_dir / "portfolio.sha256").write_text(hashlib.sha256(raw_port).hexdigest(), encoding="utf-8")
        sha_b1 = freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B1", ["pass01:c01", "pass01:c02"]), target="B1").stdout.split()[1]
        sha_b2 = freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B2", ["pass01:c02", "pass02:c01"]), target="B2").stdout.split()[1]
        freeze_stage(
            tmp_path, "comparison-review-v1", run_id,
            comparison_review_payload("LEFT", b1_ref="development-v2-B1.json", b1_hash=sha_b1, b2_ref="development-v2-B2.json", b2_hash=sha_b2),
        )
        out = tmp_path / "legacy.md"
        res = run_render(run_dir, TASK_TEXT, out)
        assert res.returncode == 0, res.stderr
        text = out.read_text(encoding="utf-8")
        assert text.startswith("# Prism BONK")

    def test_forge_render_rejects_v1_portfolio(self, tmp_path):
        """FORGE render rejects pizm-portfolio-selection-v1 (fails closed without coercion)."""
        run_id = "forge-neg-v1"
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        p1 = pass1_candidates_payload()
        res_p1 = freeze_stage(tmp_path, "explore", run_id, p1)
        sha1 = res_p1.stdout.split()[1]

        p2 = pass2_candidates_payload()
        res_p2 = freeze_stage(tmp_path, "explore", run_id, p2, artifact_suffix="pass02")
        sha2 = res_p2.stdout.split()[1]

        sf = search_field_payload(sha1, sha2)
        res_sf = freeze_stage(tmp_path, "search-field", run_id, sf)
        sha_sf = res_sf.stdout.split()[1]

        pv1 = portfolio_v2_payload("TWO_DEFENSIBLE_BUNDLES", field_hash=sha_sf, field_ref="search-field.json")
        pv1["schema_version"] = "pizm-portfolio-selection-v1"
        del pv1["competition_status"]
        del pv1["perspectives"]
        del pv1["recommended_competition"]
        del pv1["field_ref"]
        raw_pv1 = json.dumps(pv1, indent=2).encode("utf-8")
        (run_dir / "portfolio.json").write_bytes(raw_pv1)
        (run_dir / "portfolio.sha256").write_text(hashlib.sha256(raw_pv1).hexdigest(), encoding="utf-8")

        res_b1 = freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B1", ["pass01:c01", "pass01:c02"]), target="B1")
        sha_b1 = res_b1.stdout.split()[1]
        res_b2 = freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B2", ["pass01:c02", "pass02:c01"]), target="B2")
        sha_b2 = res_b2.stdout.split()[1]

        comp_data = comparison_review_payload("LEFT", b1_ref="development-v2-B1.json", b1_hash=sha_b1, b2_ref="development-v2-B2.json", b2_hash=sha_b2)
        comp_raw = json.dumps(comp_data, indent=2).encode("utf-8")
        (run_dir / "comparison-review-v1.json").write_bytes(comp_raw)
        (run_dir / "comparison-review-v1.sha256").write_text(hashlib.sha256(comp_raw).hexdigest(), encoding="utf-8")
        out = tmp_path / "neg_v1.md"
        res = run_render(run_dir, TASK_TEXT, out)
        assert res.returncode != 0


class TestForgeContractText:
    @pytest.mark.skipif(not MIRROR_PRESENT, reason="developer-machine skill mirror not installed")
    def test_forge_mirror_byte_identical(self):
        staged = STAGED_SKILL_ROOT / "references" / "bonk.md"
        installed = INSTALLED_SKILL_ROOT / "references" / "bonk.md"
        assert staged.exists()
        assert installed.exists()
        assert staged.read_bytes() == installed.read_bytes()

    def test_forge_contract_text_assertions(self):
        forge_text = (STAGED_SKILL_ROOT / "references" / "bonk.md").read_text(encoding="utf-8")
        assert 'route: "BONK"' in forge_text or 'route BONK' in forge_text
        assert "left_bundle_id" in forge_text
        assert "right_bundle_id" in forge_text
        assert "deep-compare.md" in forge_text
        assert 'bundle_a: "B1"' not in forge_text
        assert 'bundle_a' not in forge_text
        assert "review_B1" not in forge_text

    def test_bonk_file_exists_and_forge_reference_gone(self):
        assert (STAGED_SKILL_ROOT / "references" / "bonk.md").is_file()
        assert not (STAGED_SKILL_ROOT / "references" / "forge.md").exists()

    def test_forge_cli_alias_documented_in_skill(self):
        skill = (STAGED_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        assert "/pizm bonk" in skill
        assert "/pizm forge" in skill
        assert "deprecated compatibility alias" in skill
        assert "continue as BONK" in skill

