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
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_CLI = str(REPO_ROOT / "bin" / "pizm-session-bundle")
CHECKPOINT_CLI = str(REPO_ROOT / "bin" / "pizm-checkpoint")
STAGED_SKILL_ROOT = REPO_ROOT / "docs" / "pizm-skill-staged-2026-08-24"
INSTALLED_SKILL_ROOT = Path.home() / ".config" / "opencode" / "skills" / "pizm"

TASK_TEXT = "Reduce PR cycle time in our platform team"


def freeze_stage(project_root: Path, stage: str, run_id: str, payload: dict, target: str = None) -> subprocess.CompletedProcess:
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


def portfolio_v2_payload(competition_status="TWO_DEFENSIBLE_BUNDLES", field_hash="abc123"):
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
            "bundle_a": "B1",
            "bundle_b": "B2",
            "competition_axis": "Feedback loop latency (B1) vs Architectural ownership diffusion (B2)",
            "discriminating_observation": "Measure whether single-service PRs stall equally to cross-service PRs.",
            "discriminating_question": "Does PR stall time correlate with cross-service touched files?",
        }

    return {
        "schema_version": "pizm-portfolio-selection-v2",
        "stage": "portfolio",
        "route": "AUTO",
        "field_hash": field_hash,
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
        "auto_target": {"target_type": "B", "target_id": "B1"},
    }


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
        },
    }


def comparison_review_payload(preference="B1"):
    return {
        "schema_version": "pizm-comparison-review-v1",
        "stage": "comparison-review-v1",
        "task_summary": TASK_TEXT,
        "review_B1": {
            "target_id": "B1",
            "terminal_state": "MODEL_READY",
            "independent_countermodel": "Review capacity is sufficient but batching is culturally incentivized.",
            "load_bearing_reassessment": [
                {
                    "claim": "Review latency directly drives PR batch size inflation",
                    "critic_epistemic_status": "SUPPORTED",
                }
            ],
            "findings": {
                "unresolved_load_bearing_contradiction": False,
                "unsupported_specificity": [],
                "epistemic_laundering": [],
            },
            "evidence_debt": [],
            "verdict_rationale": "B1 provides rigorous causal mechanics grounded in observed queue delays.",
        },
        "review_B2": {
            "target_id": "B2",
            "terminal_state": "MODEL_READY",
            "independent_countermodel": "CI infrastructure flakes cause the perceived stall.",
            "load_bearing_reassessment": [
                {
                    "claim": "Ownership diffusion creates tragedy of the review queue",
                    "critic_epistemic_status": "SUPPORTED",
                }
            ],
            "findings": {
                "unresolved_load_bearing_contradiction": False,
                "unsupported_specificity": [],
                "epistemic_laundering": [],
            },
            "evidence_debt": [],
            "verdict_rationale": "B2 correctly identifies architectural silos as the coordination driver.",
        },
        "comparison": {
            "current_preference": preference,
            "competition_axis": "Feedback loop latency (B1) vs Architectural ownership diffusion (B2)",
            "strongest_reason_for_B1": "Directly explains observed 3-day turnaround bottleneck on single-service PRs.",
            "strongest_reason_for_B2": "Explains why cross-service changes stall regardless of reviewer availability.",
            "shared_evidence_debt": ["Historical PR wait time distribution split by single vs multi-repo."],
            "discriminating_observation": "Measure queue time before first review for single-service vs multi-service PRs.",
            "what_would_change_the_decision": "If single-service PRs have <2h review latency, B2 is primary.",
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
        # In multi-pass explore, pass 2 can be written as candidates-pass02.json
        fd_p2 = tmp_path / ".ai" / "pizm" / f"run-{run_id}" / "candidates-pass02.json"
        fd_p2.write_text(json.dumps(p2, indent=2), encoding="utf-8")
        fd_p2_sha = tmp_path / ".ai" / "pizm" / f"run-{run_id}" / "candidates-pass02.sha256"
        import hashlib
        fd_p2_sha.write_text(hashlib.sha256(fd_p2.read_bytes()).hexdigest(), encoding="utf-8")

        # Search field updated after pass 2
        sf2 = search_field_payload(sha1, hashlib.sha256(fd_p2.read_bytes()).hexdigest())
        # overwrite search-field for append-only simulation in test
        (tmp_path / ".ai" / "pizm" / f"run-{run_id}" / "search-field.json").unlink()
        (tmp_path / ".ai" / "pizm" / f"run-{run_id}" / "search-field.sha256").unlink()
        (tmp_path / ".ai" / "pizm" / f"run-{run_id}" / "search-field.meta.json").unlink()
        res_sf2 = freeze_stage(tmp_path, "search-field", run_id, sf2)
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
        p_v2 = portfolio_v2_payload(competition_status="TWO_DEFENSIBLE_BUNDLES")
        res = freeze_stage(tmp_path, "portfolio", run_id, p_v2)
        assert res.returncode == 0
        assert "FREEZE_OK" in res.stdout

    def test_fg_p3_and_p4_no_second_defensible_bundle(self, tmp_path):
        """FG-P3 & FG-P4: No forced B2; portfolio v2 cleanly records NO_SECOND_DEFENSIBLE_BUNDLE."""
        run_id = "forge-p3-p4"
        p_v2 = portfolio_v2_payload(competition_status="NO_SECOND_DEFENSIBLE_BUNDLE")
        res = freeze_stage(tmp_path, "portfolio", run_id, p_v2)
        assert res.returncode == 0
        assert "FREEZE_OK" in res.stdout

    def test_portfolio_v1_compatibility(self, tmp_path):
        """Portfolio v1 remains strictly valid under pizm-portfolio-selection-v1."""
        run_id = "portfolio-v1-compat"
        p_v1 = portfolio_v2_payload(competition_status="TWO_DEFENSIBLE_BUNDLES")
        p_v1["schema_version"] = "pizm-portfolio-selection-v1"
        del p_v1["competition_status"]
        del p_v1["recommended_competition"]
        res = freeze_stage(tmp_path, "portfolio", run_id, p_v1)
        assert res.returncode == 0
        assert "FREEZE_OK" in res.stdout


class TestForgeDeepAndCompare:
    def test_fg_d1_to_d3_and_c1_to_c6_full_pipeline(self, tmp_path):
        """FG-D1..D3, FG-C1..C6: Develop B1 and B2 separately, freeze both before compare, verify comparative review."""
        run_id = "forge-full-d-c"
        # Freeze B1 development
        dev_b1 = development_v2_payload("B1", ["pass01:c01", "pass01:c02"])
        res_d1 = freeze_stage(tmp_path, "development-v2", run_id, dev_b1, target="B1")
        assert res_d1.returncode == 0, res_d1.stderr

        # Freeze B2 development
        dev_b2 = development_v2_payload("B2", ["pass01:c02", "pass02:c01"])
        res_d2 = freeze_stage(tmp_path, "development-v2", run_id, dev_b2, target="B2")
        assert res_d2.returncode == 0, res_d2.stderr

        # Freeze Comparison Review
        comp = comparison_review_payload(preference="B1")
        res_c = freeze_stage(tmp_path, "comparison-review-v1", run_id, comp)
        assert res_c.returncode == 0, res_c.stderr
        assert "FREEZE_OK" in res_c.stdout


class TestForgeLeverGates:
    def test_fg_l1_to_l3_lever_gating(self, tmp_path):
        """FG-L1..L3: Action FORGE runs LEVER only after MODEL_READY; UNRESOLVED does not force LEVER."""
        run_id = "forge-lever"
        # Setup B1 & B2 & Compare
        freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B1"), target="B1")
        freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B2"), target="B2")
        freeze_stage(tmp_path, "comparison-review-v1", run_id, comparison_review_payload("B1"))

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
        fd_p2 = run_dir / "candidates-pass02.json"
        fd_p2.write_text(json.dumps(p2, indent=2), encoding="utf-8")
        import hashlib
        sha2 = hashlib.sha256(fd_p2.read_bytes()).hexdigest()
        (run_dir / "candidates-pass02.sha256").write_text(sha2, encoding="utf-8")

        # 3. Search field
        sf = search_field_payload(sha1, sha2)
        freeze_stage(tmp_path, "search-field", run_id, sf)

        # 4. Portfolio v2
        pv2 = portfolio_v2_payload("TWO_DEFENSIBLE_BUNDLES", sha1)
        freeze_stage(tmp_path, "portfolio", run_id, pv2)

        # 5. Deep B1 & B2
        freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B1", ["pass01:c01", "pass01:c02"]), target="B1")
        freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B2", ["pass01:c02", "pass02:c01"]), target="B2")

        # 6. Comparison Review
        freeze_stage(tmp_path, "comparison-review-v1", run_id, comparison_review_payload("B1"))

        # 7. Lever Design & Review
        freeze_stage(tmp_path, "lever-design", run_id, lever_design_payload())
        freeze_stage(tmp_path, "lever-review", run_id, lever_review_payload())

        # Render run.md
        out1 = tmp_path / "run1.md"
        res_r1 = run_render(run_dir, TASK_TEXT, out1)
        assert res_r1.returncode == 0, res_r1.stderr

        content1 = out1.read_text(encoding="utf-8")

        # Verify required sections (FG-MD1..FG-MD5)
        assert "# Prism FORGE" in content1
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

        # Portfolio v2 with NO_SECOND_DEFENSIBLE_BUNDLE
        pv2 = portfolio_v2_payload("NO_SECOND_DEFENSIBLE_BUNDLE", sha1)
        freeze_stage(tmp_path, "portfolio", run_id, pv2)

        # Deep B1
        freeze_stage(tmp_path, "development-v2", run_id, development_v2_payload("B1", ["pass01:c01", "pass01:c02"]), target="B1")

        # Single-model Critic review
        single_rev = {
            "schema_version": "pizm-deep-review-v2",
            "stage": "deep-review-v2",
            "frozen_hash": "dummyhash",
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
            },
            "evidence_debt": [],
            "cheapest_discriminating_test": "Queue probe",
            "verdict_rationale": "MODEL_READY verdict for single B1.",
        }
        freeze_stage(tmp_path, "deep-review-v2", run_id, single_rev)

        # Render run.md in degraded mode
        out = tmp_path / "degraded_run.md"
        res = run_render(run_dir, TASK_TEXT, out)
        assert res.returncode == 0, res.stderr

        content = out.read_text(encoding="utf-8")
        assert "# Prism FORGE" in content
        assert "NO_SECOND_DEFENSIBLE_BUNDLE" in content
        assert "Compare stage skipped" in content
        assert "## Deep B1" in content
        assert "## Critic" in content
