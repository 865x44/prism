"""
Prism Hardening & Semantic Regression Test Suite (W2 & W3).

Deterministic offline fixture tests verifying:
- Search Horizon fixtures (H1-H4)
- Portfolio & Bundle fixtures (PF1-PF8)
- Observed Deep/Critic dogfood failure reproduction
- Critic regression cases (CR1-CR10)
- Reasoning Arsenal anti-cargo-cult decline cases (4 cases)
- AUTO end-to-end deterministic offline fixtures (A1-A5)
- FORGE end-to-end deterministic offline fixtures (F1-F6)

All fixtures execute through real `bin/pizm-checkpoint freeze` and
`bin/pizm-session-bundle render` CLIs with zero mocking.
"""
import json
import subprocess
from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_CLI = str(REPO_ROOT / "bin" / "pizm-session-bundle")
CHECKPOINT_CLI = str(REPO_ROOT / "bin" / "pizm-checkpoint")
SKILL_ROOT = REPO_ROOT / "skills" / "pizm"

DEFAULT_TASK = "Improve deployment velocity and platform reliability"


# ---------------------------------------------------------------------------
# CLI Execution Helpers
# ---------------------------------------------------------------------------

def freeze_stage(
    project_root: Path,
    stage: str,
    run_id: str,
    payload: dict,
    target: str = None,
    artifact_suffix: str = None,
) -> subprocess.CompletedProcess:
    """Freeze one stage artifact through the real pizm-checkpoint CLI."""
    fd_input = project_root / f"_in_{stage}_{target or 'main'}_{artifact_suffix or 'main'}.json"
    fd_input.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    cmd = [
        CHECKPOINT_CLI, "freeze",
        "--stage", stage,
        "--run-id", run_id,
        "--input", str(fd_input),
        "--project-root", str(project_root),
        "--skill-root", str(SKILL_ROOT),
    ]
    if target:
        cmd.extend(["--target", target])
    if artifact_suffix:
        cmd.extend(["--artifact-suffix", artifact_suffix])

    res = subprocess.run(cmd, capture_output=True, text=True)
    if fd_input.exists():
        fd_input.unlink()
    return res


def run_render(run_dir: Path, task: str, output_path: Path) -> subprocess.CompletedProcess:
    """Render run.md from a frozen run directory through the real pizm-session-bundle CLI."""
    cmd = [
        BUNDLE_CLI, "render",
        "--run-dir", str(run_dir),
        "--task", task,
        "--output", str(output_path),
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


# ---------------------------------------------------------------------------
# Payload Generators
# ---------------------------------------------------------------------------

def make_candidates_payload(pass_num: int = 1, candidates: list = None, mode: str = "NORMAL", task: str = DEFAULT_TASK):
    if candidates is None:
        if pass_num == 1:
            candidates = [
                {
                    "candidate_id": "c01",
                    "title": "Async Batch Review Queues",
                    "core_claim": "Decouple review notifications into batched focus windows",
                    "structural_shift": "Shift from continuous interrupts to scheduled batch windows",
                    "mechanism": "PRs queued until scheduled twice-daily review windows",
                    "boundary": "Internal service PRs",
                    "operator_provenance": "represented",
                    "difference_from_prior": "Initial generation",
                },
                {
                    "candidate_id": "c02",
                    "title": "Automated Mechanical Gates",
                    "core_claim": "Reject mechanical errors before human review",
                    "structural_shift": "Shift formatting and lint checks from reviewer to pre-push bot",
                    "mechanism": "Pre-push hook and CI linter gate",
                    "boundary": "Syntax, types, and formatting only",
                    "operator_provenance": "represented",
                    "difference_from_prior": "Initial generation",
                },
            ]
        else:
            candidates = [
                {
                    "candidate_id": "c01",
                    "title": "Synchronous Pair Review Rotation",
                    "core_claim": "Pairing on open PRs resolves context bottlenecks instantly",
                    "structural_shift": "Shift from asynchronous delay to synchronous pairing",
                    "mechanism": "Daily 1-hour pairing block for open PRs",
                    "boundary": "Complex architectural changes",
                    "operator_provenance": "represented",
                    "difference_from_prior": "Introduces synchronous real-time review",
                },
                {
                    "candidate_id": "c02",
                    "title": "Diff Size Strict Quota",
                    "core_claim": "Enforcing 200 LOC ceiling keeps cognitive burden low",
                    "structural_shift": "Shift reviewability responsibility to author",
                    "mechanism": "CI block on diffs exceeding 200 lines",
                    "boundary": "Application code diffs",
                    "operator_provenance": "represented",
                    "difference_from_prior": "Structural constraint on change size",
                },
            ]
    return {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": mode,
        "task": task,
        "candidates": candidates,
    }


def make_search_field_payload(passes: list, entries: list):
    return {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "passes": passes,
        "entries": entries,
    }

def _ref_sort_key(ref):
    """Numeric-aware composite ref key, mirroring the checkpoint/renderer rule."""
    m = re.fullmatch(r"(pass[0-9]{2,}):c([0-9]+)", ref or "")
    if m:
        return (m.group(1), int(m.group(2)), "")
    return ("~", 0, ref or "")


def make_portfolio_payload(
    route: str = "MANUAL",
    field_hash: str = "abc123def456",
    field_ref: str = "search-field.json",
    assessments: list = None,
    bundles: list = None,
    auto_target: dict = None,
    single_target: dict = None,
    prior_bundles: list = None,
    schema_version: str = "pizm-portfolio-selection-v1",
    competition_status: str = None,
    recommended_competition: dict = None,
):
    if schema_version == "pizm-portfolio-selection-v2" and route == "MANUAL":
        route = "BONK"
    if assessments is None:
        assessments = [
            {
                "candidate_ref": "pass01:c01",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "Core insight",
                "nearest_overlap": None,
                "reason": "Clear causal mechanism",
            }
        ]
    payload = {
        "schema_version": schema_version,
        "stage": "portfolio",
        "route": route,
        "field_hash": field_hash,
        "candidate_assessments": assessments,
        "bundles": bundles or [],
    }
    if schema_version == "pizm-portfolio-selection-v1":
        payload["next_reasoning_move"] = "DEEP" if route == "AUTO" else None
        payload["next_reasoning_rationale"] = "Clear causal mechanism" if route == "AUTO" else None
        payload["auto_target"] = auto_target
        payload["information_request"] = None
        payload["rival_shadow"] = None
        kept = sorted(
            (a["candidate_ref"] for a in assessments if a.get("disposition") == "KEEP"),
            key=_ref_sort_key,
        )
        payload["perspectives"] = {f"P{i}": ref for i, ref in enumerate(kept, start=1)}
    if field_ref is not None:
        payload["field_ref"] = field_ref
    if prior_bundles is not None:
        payload["prior_bundles"] = prior_bundles
    if schema_version == "pizm-portfolio-selection-v2":
        comp_st = competition_status or "TWO_DEFENSIBLE_BUNDLES"
        payload["competition_status"] = comp_st
        if comp_st == "NO_SECOND_DEFENSIBLE_BUNDLE":
            payload["recommended_competition"] = None
            payload["single_target"] = single_target or {"target_type": "B", "target_id": "B1"}
        else:
            if isinstance(recommended_competition, dict):
                rc = dict(recommended_competition)
                if "bundle_a" in rc:
                    rc["left_bundle_id"] = rc.pop("bundle_a")
                if "bundle_b" in rc:
                    rc["right_bundle_id"] = rc.pop("bundle_b")
                payload["recommended_competition"] = rc
            else:
                payload["recommended_competition"] = recommended_competition

        # Add perspectives mapping based on keeping candidates
        perspectives = {}
        p_idx = 1
        for a in assessments:
            if a.get("disposition") == "KEEP":
                perspectives[f"P{p_idx}"] = a["candidate_ref"]
                p_idx += 1
        payload["perspectives"] = perspectives
    return payload
def make_development_v2_payload(
    target_type: str = "P",
    target_id: str = "P1",
    member_refs: list = None,
    thesis: str = None,
    synthesis: str = None,
    dynamics: str = None,
    mechanism_chain: list = None,
    claims: list = None,
    predictions: list = None,
    breaks: list = None,
    unresolved_tensions: list = None,
    evidence_debt: list = None,
    member_contributions: dict = None,
    member_ablation: dict = None,
):
    if target_type == "P":
        lock = {
            "p_id": target_id,
            "title": "Async Batch Review Queues",
            "core_claim": "Decouple review notifications into batched focus windows",
            "structural_shift": "Shift from continuous interrupts to scheduled batch windows",
            "mechanism": "PRs queued until scheduled twice-daily review windows",
            "boundary": "Internal service PRs",
        }
    else:
        refs = member_refs or ["pass01:c01", "pass01:c02"]
        lock = {
            "bundle_id": target_id,
            "member_refs": refs,
            "title": f"Integrated System Bundle {target_id}",
            "core_claim": "Combine automated pre-filters with scheduled review windows",
            "structural_shift": "Shift entire review pipeline from reactive interrupts to batched clean flow",
            "mechanism": "Mechanical gate filter followed by async batch queueing",
            "boundary": "All platform repository changes",
        }

    claims_data = claims or [
        {
            "claim": "Context switching is the primary review friction",
            "epistemic_status": "SUPPORTED",
            "role_in_model": "Foundation of async batching thesis",
            "what_would_weaken_or_refute": "Metrics showing interruptions cause negligible delay",
        },
        {
            "claim": "Reviewers adhere consistently to designated focus windows",
            "epistemic_status": "INFERRED",
            "role_in_model": "Behavioral prerequisite for throughput",
            "what_would_weaken_or_refute": "Reviewers continue ad-hoc review habits outside windows",
        },
    ]

    model = {
        "thesis": thesis or "Decoupled batching stabilizes reviewer attention and increases throughput.",
        "synthesis": synthesis or (
            "By eliminating constant ad-hoc notification interrupts and batching review activity "
            "into predictable focus blocks, reviewer attention depth increases and total PR latency drops."
        ),
        "dynamics": dynamics or "Review flow stabilizes into two predictable daily waves.",
        "mechanism_chain": mechanism_chain or [
            "PR submitted and validated by pre-push hooks",
            "PR queued for designated review focus window",
            "Reviewer processes entire queue in focused block without context switching",
        ],
        "implications": ["Predictable review turnaround", "Dramatically lower developer distraction"],
        "predictions_or_observables": predictions or ["PR cycle time reduces by 35%", "Context switches drop 50%"],
        "break_conditions": breaks or ["Urgent hotfixes requiring immediate synchronous review bypass"],
        "unresolved_tensions": unresolved_tensions or (
            ["Balancing urgent PRs against batch window adherence"] if target_type == "P"
            else ["Batch delay vs instant feedback tension across members"]
        ),
        "evidence_debt": evidence_debt or ["Longitudinal data on review window compliance"],
        "load_bearing_claims": claims_data,
        "comparative_standing": None,
        "development_delta": {
            "summary": "Initial development",
            "new_load_bearing_claims": [],
            "strengthened_claims": [],
            "new_causal_arrows_or_mechanisms": [],
            "material_imports": [],
            "scope_expansions": [],
        },
    }

    if target_type == "B":
        refs = member_refs or ["pass01:c01", "pass01:c02"]
        model["member_contributions"] = member_contributions or {
            refs[0]: "Provides the async batch queue mechanism",
            refs[1]: "Provides the pre-filter gatekeeper preventing noise",
        }
        model["member_ablation"] = member_ablation or {
            refs[0]: "Without batch queue, reviewers are constantly interrupted by notifications",
            refs[1]: "Without mechanical filter, focus windows are wasted on formatting issues",
        }

    return {
        "schema_version": "pizm-development-v2",
        "stage": "development-v2",
        "target": {"target_type": target_type, "target_id": target_id},
        "identity_lock": lock,
        "developed_model": model,
    }


def make_deep_review_v2_payload(
    frozen_hash: str,
    target_type: str = "P",
    target_id: str = "P1",
    target_ref: str = None,
    terminal_state: str = "MODEL_READY",
    identity_verified: bool = True,
    countermodel: str = None,
    cheapest_test: str = None,
    reassessments: list = None,
    cross_contradictions: list = None,
    unsupported_specificity: list = None,
    epistemic_laundering: list = None,
    unresolved_contradiction: bool = False,
    identity_drift: str = None,
    cost_relocation: str = None,
    round_trip_skeleton: str = None,
    member_ablation_finding: str = None,
    evidence_debt: list = None,
    verdict_rationale: str = None,
):
    if member_ablation_finding is not None:
        member_abl = member_ablation_finding
    else:
        member_abl = "All member ablations verified non-trivial." if target_type == "B" else None

    if round_trip_skeleton is not None:
        rt_skel = round_trip_skeleton
    else:
        rt_skel = "PR submission -> batched queue -> windowed focus review"

    findings = {
        "cross_field_contradictions": cross_contradictions or [],
        "unsupported_specificity": unsupported_specificity or [],
        "epistemic_laundering": epistemic_laundering or [],
        "unresolved_load_bearing_contradiction": unresolved_contradiction,
        "readiness_blockers": [],
        "readiness_blocker_details": {},
        "identity_drift": identity_drift,
        "cost_relocation": cost_relocation,
        "round_trip_skeleton": rt_skel,
        "member_ablation": member_abl,
    }
    debt = list(evidence_debt or [])
    if unsupported_specificity and not debt:
        debt.append("Empirical evidence required for asserted specificity")

    payload = {
        "schema_version": "pizm-deep-review-v2",
        "stage": "deep-review-v2",
        "frozen_hash": frozen_hash,
        "target_type": target_type,
        "target_id": target_id,
        "terminal_state": terminal_state,
        "identity_verified": identity_verified,
        "independent_countermodel": countermodel or "PR turnaround is primarily bounded by PR size, not notification cadence.",
        "cheapest_discriminating_test": cheapest_test or "Measure review latency across varying PR sizes under batched vs ad-hoc notifications.",
        "load_bearing_reassessment": reassessments or [
            {
                "claim": "Context switching is the primary review friction",
                "critic_epistemic_status": "SUPPORTED",
            },
            {
                "claim": "Reviewers adhere consistently to designated focus windows",
                "critic_epistemic_status": "INFERRED",
            },
        ],
        "findings": findings,
        "evidence_debt": debt,
        "verdict_rationale": verdict_rationale or "Model structure is sound and epistemic boundaries are clear.",
    }
    if terminal_state in ("MODEL_READY", "RETURN_TO_EXPLORE"):
        payload["inquiry_program"] = None
    else:
        payload["inquiry_program"] = {
            "current_leading_models": ["Leading model 1"],
            "unresolved_questions": ["Question 1?"],
            "strongest_live_rival": None,
            "result_that_would_change_model": "Result 1",
            "stop_rule": "Stop 1",
        }
        if not debt:
            debt.append("Evidence required for unverified claims")
            payload["evidence_debt"] = debt
    if target_ref is not None:
        payload["target_ref"] = target_ref
    return payload


def make_comparison_review_payload(
    left_id: str = "B1",
    right_id: str = "B2",
    preference: str = "LEFT",
    b1_terminal: str = "MODEL_READY",
    b2_terminal: str = "MODEL_READY",
    b1_unresolved: bool = False,
    b2_unresolved: bool = False,
    competition_axis: str = "Asynchronous batching vs Synchronous pairing",
    reason_left: str = "Preserves developer flow without requiring schedule synchronization.",
    reason_right: str = "Eliminates queue latency completely through interactive pairing.",
    discriminating_obs: str = "Evaluate team calendar fragmentation and timezone distribution.",
    what_changes: str = "If team is colocated with open calendars, right becomes clearly superior.",
    shared_debt: list = None,
    b1_ref: str = "development-v2-B1.json",
    b1_hash: str = "a" * 64,
    b2_ref: str = "development-v2-B2.json",
    b2_hash: str = "b" * 64,
):
    return {
        "schema_version": "pizm-comparison-review-v1",
        "stage": "comparison-review-v1",
        "left_target_id": left_id,
        "right_target_id": right_id,
        "left_review": {
            "target_id": left_id,
            "development_ref": b1_ref,
            "frozen_hash": b1_hash,
            "terminal_state": b1_terminal,
            "findings": {
                "cross_field_contradictions": [],
                "unsupported_specificity": [],
                "epistemic_laundering": [],
                "unresolved_load_bearing_contradiction": b1_unresolved,
            },
            "load_bearing_reassessment": [
                {
                    "claim": "Context switching is the primary review friction",
                    "critic_epistemic_status": "SUPPORTED",
                }
            ],
            "independent_countermodel": "Review queues inherently cause multi-hour lag regardless of batching.",
            "verdict_rationale": "Left is internally sound and minimizes schedule friction.",
        },
        "right_review": {
            "target_id": right_id,
            "development_ref": b2_ref,
            "frozen_hash": b2_hash,
            "terminal_state": b2_terminal,
            "findings": {
                "cross_field_contradictions": [],
                "unsupported_specificity": [],
                "epistemic_laundering": [],
                "unresolved_load_bearing_contradiction": b2_unresolved,
            },
            "load_bearing_reassessment": [
                {
                    "claim": "Diffs under 200 lines can be reviewed in under 15 minutes",
                    "critic_epistemic_status": "SUPPORTED",
                }
            ],
            "independent_countermodel": "Calendar density and timezone differences make daily pairing unworkable.",
            "verdict_rationale": "Right provides instantaneous turnaround but depends on tight calendar coordination.",
        },
        "comparison": {
            "current_preference": preference,
            "competition_axis": competition_axis,
            "strongest_reason_for_left": reason_left,
            "strongest_reason_for_right": reason_right,
            "discriminating_observation": discriminating_obs,
            "what_would_change_the_decision": what_changes,
            "shared_evidence_debt": shared_debt or ["Longitudinal study of engineering satisfaction under both paradigms"],
        },
    }

def make_lever_design_payload():
    return {
        "schema_version": "pizm-lever-design-v1",
        "stage": "lever",
        "levers": [
            {
                "lever_id": "L1",
                "intervention_or_test_point": "Implement automated pre-push lint gate on main repo",
                "model_link": "Filters trivial errors before batch review focus window",
                "minimum_bounded_move": "Deploy pre-push hook configuration to 1 team repo for 1 sprint",
                "expected_observation_or_response": "Zero lint/format comments in code reviews during trial",
                "disconfirming_signal": "Engineers bypass hook with --no-verify or spend >5min fixing local hook errors",
                "stop_condition": "Hook failure rate > 10% on valid commits",
                "remaining_assumptions": "Developer local Node.js environments are homogeneous",
            }
        ],
    }


def make_lever_review_payload(frozen_hash: str = "abc123def456", outcome: str = "LEVER", verdict: str = "ACCEPT"):
    verdicts = (
        [{"lever_id": "L1", "verdict": verdict, "verdict_rationale": "Bounded, disconfirmable, low cost."}]
        if outcome == "LEVER" else []
    )
    return {
        "schema_version": "pizm-lever-review-v1",
        "stage": "lever",
        "frozen_hash": frozen_hash,
        "outcome": outcome,
        "verdicts": verdicts,
        "synthesis": "Lever L1 satisfies all safety and falsifiability criteria.",
    }

# ===========================================================================
# 1. Search Horizon Fixtures (H1-H4)
# ===========================================================================

class TestSearchHorizon:
    """Deterministic regression fixtures for search horizon assumptions."""

    def test_h1_late_composition(self, tmp_path):
        """H1: Pass 1 borderline candidate combines with Pass 2 candidate to form a strong Bundle.
        Verifies late promotion succeeds while raw history remains untouched.
        """
        run_id = "h1-late-comp"
        # Pass 1: candidate c01 is borderline standalone
        p1 = make_candidates_payload(pass_num=1)
        res1 = freeze_stage(tmp_path, "explore", run_id, p1)
        assert res1.returncode == 0, res1.stderr

        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        p1_hash = (run_dir / "candidates.sha256").read_text().strip()
        p1_bytes_orig = (run_dir / "candidates.json").read_bytes()

        # Archive pass01 artifact
        (run_dir / "candidates-pass01.json").write_bytes(p1_bytes_orig)
        (run_dir / "candidates-pass01.sha256").write_text(p1_hash, encoding="utf-8")
        (run_dir / "candidates.json").unlink()
        (run_dir / "candidates.sha256").unlink()
        (run_dir / "candidates.meta.json").unlink()

        # Pass 2: new candidate appears
        p2 = make_candidates_payload(pass_num=2)
        res2 = freeze_stage(tmp_path, "explore", run_id, p2)
        assert res2.returncode == 0, res2.stderr
        p2_hash = (run_dir / "candidates.sha256").read_text().strip()

        (run_dir / "candidates-pass02.json").write_bytes((run_dir / "candidates.json").read_bytes())
        (run_dir / "candidates-pass02.sha256").write_text(p2_hash, encoding="utf-8")
        (run_dir / "candidates.json").write_bytes(p1_bytes_orig)
        (run_dir / "candidates.sha256").write_text(p1_hash, encoding="utf-8")

        # Search field manifest references both passes in append-only order
        sf = make_search_field_payload(
            passes=[
                {"pass_id": "pass01", "candidates_ref": "candidates-pass01.json", "frozen_hash": p1_hash},
                {"pass_id": "pass02", "candidates_ref": "candidates-pass02.json", "frozen_hash": p2_hash},
            ],
            entries=["pass01:c01", "pass01:c02", "pass02:c01", "pass02:c02"],
        )
        res_sf = freeze_stage(tmp_path, "search-field", run_id, sf)
        assert res_sf.returncode == 0, res_sf.stderr
        sf_hash = (run_dir / "search-field.sha256").read_text().strip()

        # Portfolio: pass01:c01 (borderline standalone) + pass02:c01 form strong Bundle B1
        assessments = [
            {"candidate_ref": "pass01:c01", "disposition": "BORDERLINE", "standalone_quality": "borderline", "unique_residue": "Async batching", "nearest_overlap": None, "reason": "Weak standalone but strong catalyst"},
            {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Lint gate", "nearest_overlap": None, "reason": "Mechanical gate"},
            {"candidate_ref": "pass02:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Pairing rotation", "nearest_overlap": None, "reason": "Synchronous speed"},
            {"candidate_ref": "pass02:c02", "disposition": "DROP", "standalone_quality": "weak", "unique_residue": "Size cap", "nearest_overlap": None, "reason": "Overly rigid"},
        ]
        bundle_b1 = {
            "bundle_id": "B1",
            "member_refs": ["pass01:c01", "pass02:c01"],
            "bundle_thesis": "Hybrid Async Queue with Synchronous Escalation",
            "composition_gain": "Combines async throughput with synchronous speed for blocked items",
            "new_consequence_or_prediction": "Average review latency drops below 4 hours",
            "internal_tension": "Deciding when to escalate from async to pairing",
            "weakest_link": "Pair availability during peak sprint days",
            "member_roles": {"pass01:c01": "Default async pipeline", "pass02:c01": "Escalation pairing block"},
            "member_ablation": {
                "pass01:c01": "Without async queue, pairing blocks are overwhelmed by minor PRs",
                "pass02:c01": "Without pairing escalation, complex PRs stall in async queues",
            },
        }
        port = make_portfolio_payload(
            field_hash=sf_hash,
            assessments=assessments,
            bundles=[bundle_b1],
            route="AUTO",
            auto_target={"target_type": "B", "target_id": "B1", "rationale": "Late composition creates superior model"},
        )
        res_port = freeze_stage(tmp_path, "portfolio", run_id, port)
        assert res_port.returncode == 0, res_port.stderr

        # Check raw history untouched
        assert (run_dir / "candidates-pass01.json").read_bytes() == p1_bytes_orig

    def test_h2_residual_paraphrase_failure(self, tmp_path):
        """H2: Pass 2 produces near-cousin paraphrase of Pass 1 candidate.
        Portfolio validator accepts explicit MERGE with nearest_overlap and rejects fake breadth.
        """
        run_id = "h2-paraphrase"
        p1 = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p1)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        p1_hash = (run_dir / "candidates.sha256").read_text().strip()

        # Pass 2 candidate is a mere paraphrase of pass01:c01
        p2_candidates = [
            {
                "candidate_id": "c01",
                "title": "Scheduled Review Windows",
                "core_claim": "Review PRs at fixed times rather than on demand",
                "structural_shift": "Shift notifications to scheduled batches",
                "mechanism": "Time-blocked PR reviewing",
                "boundary": "Team internal PRs",
                "operator_provenance": "represented",
                "difference_from_prior": "Rephrased async queue concept",
            }
        ]
        p2 = make_candidates_payload(pass_num=2, candidates=p2_candidates)
        freeze_stage(tmp_path, "explore", run_id, p2, artifact_suffix="pass02")
        p2_hash = (run_dir / "candidates-pass02.sha256").read_text().strip()

        sf = make_search_field_payload(
            passes=[
                {"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": p1_hash},
                {"pass_id": "pass02", "candidates_ref": "candidates-pass02.json", "frozen_hash": p2_hash},
            ],
            entries=["pass01:c01", "pass01:c02", "pass02:c01"],
        )
        freeze_stage(tmp_path, "search-field", run_id, sf)
        sf_hash = (run_dir / "search-field.sha256").read_text().strip()

        # Portfolio explicitly flags MERGE into pass01:c01 with empty unique residue
        assessments = [
            {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Async batching", "nearest_overlap": None, "reason": "Original model"},
            {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Lint gate", "nearest_overlap": None, "reason": "Mechanical gate"},
            {"candidate_ref": "pass02:c01", "disposition": "MERGE", "standalone_quality": "weak", "unique_residue": "", "nearest_overlap": "pass01:c01", "reason": "Paraphrase of pass01:c01; no unique residue"},
        ]
        port = make_portfolio_payload(
            field_hash=sf_hash,
            assessments=assessments,
            bundles=[],
            route="AUTO",
            auto_target={"target_type": "P", "target_id": "P1", "rationale": "Select original candidate P1"},
        )
        res_port = freeze_stage(tmp_path, "portfolio", run_id, port)
        assert res_port.returncode == 0, res_port.stderr

    def test_h3_new_causal_family(self, tmp_path):
        """H3: Pass 2 reveals a materially different causal mechanism/boundary.
        Portfolio recognizes genuine new territory with substantial unique residue and no overlap.
        """
        run_id = "h3-new-family"
        p1 = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p1)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        p1_hash = (run_dir / "candidates.sha256").read_text().strip()

        # Pass 2 reveals orthogonal organizational routing mechanism
        p2_candidates = [
            {
                "candidate_id": "c01",
                "title": "Code Ownership Micro-Routing",
                "core_claim": "Route reviews strictly by modified AST node ownership rather than directory",
                "structural_shift": "Shift from repo-level ownership to fine-grained semantic symbol ownership",
                "mechanism": "AST parser generates targeted single-expert review ping",
                "boundary": "Cross-module refactorings",
                "operator_provenance": "represented",
                "difference_from_prior": "Orthogonal causal axis: semantic routing vs batch timing",
            }
        ]
        p2 = make_candidates_payload(pass_num=2, candidates=p2_candidates)
        freeze_stage(tmp_path, "explore", run_id, p2, artifact_suffix="pass02")
        p2_hash = (run_dir / "candidates-pass02.sha256").read_text().strip()

        sf = make_search_field_payload(
            passes=[
                {"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": p1_hash},
                {"pass_id": "pass02", "candidates_ref": "candidates-pass02.json", "frozen_hash": p2_hash},
            ],
            entries=["pass01:c01", "pass01:c02", "pass02:c01"],
        )
        freeze_stage(tmp_path, "search-field", run_id, sf)
        sf_hash = (run_dir / "search-field.sha256").read_text().strip()

        assessments = [
            {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Temporal batching", "nearest_overlap": None, "reason": "Time-domain pacing"},
            {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Mechanical filtering", "nearest_overlap": None, "reason": "Gatekeeper"},
            {"candidate_ref": "pass02:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Semantic AST routing", "nearest_overlap": None, "reason": "Genuine new causal family in semantic domain"},
        ]
        port = make_portfolio_payload(
            field_hash=sf_hash,
            assessments=assessments,
            bundles=[],
            route="AUTO",
            auto_target={"target_type": "P", "target_id": "P3", "rationale": "Explore genuine new territory P3"},
        )
        res_port = freeze_stage(tmp_path, "portfolio", run_id, port)
        assert res_port.returncode == 0, res_port.stderr

    def test_h4_identity_stability(self, tmp_path):
        """H4: Identity stability across successive passes and portfolio evaluations.
        P-IDs and B-IDs remain stable; renumbering or mutating historical IDs fails closed.
        """
        run_id = "h4-id-stability"
        p1 = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p1)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        p1_hash = (run_dir / "candidates.sha256").read_text().strip()

        sf = make_search_field_payload(
            passes=[{"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": p1_hash}],
            entries=["pass01:c01", "pass01:c02"],
        )
        freeze_stage(tmp_path, "search-field", run_id, sf)
        sf_hash = (run_dir / "search-field.sha256").read_text().strip()

        assessments = [
            {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Async batching", "nearest_overlap": None, "reason": "Strong model"},
            {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Lint gate", "nearest_overlap": None, "reason": "Mechanical gate"},
        ]
        bundle_b1 = {
            "bundle_id": "B1",
            "member_refs": ["pass01:c01", "pass01:c02"],
            "bundle_thesis": "Integrated review gate and batch queue",
            "composition_gain": "Filters noise then batches focus",
            "new_consequence_or_prediction": "Review speed doubles",
            "internal_tension": "Queue latency vs gate strictness",
            "weakest_link": "Hook compatibility",
            "member_roles": {"pass01:c01": "Queue", "pass01:c02": "Filter"},
            "member_ablation": {"pass01:c01": "Queue disappears", "pass01:c02": "Filter disappears"},
        }
        # First portfolio with prior_bundles=[] -> produces B1
        port1 = make_portfolio_payload(
            field_hash=sf_hash,
            assessments=assessments,
            bundles=[bundle_b1],
            route="MANUAL",
            prior_bundles=[],
        )
        res1 = freeze_stage(tmp_path, "portfolio", run_id, port1)
        assert res1.returncode == 0, res1.stderr

        # Later portfolio attempting to renumber B1 to B2 must fail closed
        bundle_b_renumbered = dict(bundle_b1, bundle_id="B2")
        port_bad = make_portfolio_payload(
            field_hash=sf_hash,
            assessments=assessments,
            bundles=[bundle_b_renumbered],
            route="MANUAL",
            prior_bundles=[bundle_b1],
        )
        (run_dir / "portfolio.json").unlink()
        (run_dir / "portfolio.sha256").unlink()
        (run_dir / "portfolio.meta.json").unlink()
        res_bad = freeze_stage(tmp_path, "portfolio", run_id, port_bad)
        assert res_bad.returncode != 0
        assert "deterministic B-ID assignment violated" in res_bad.stderr


# ===========================================================================
# 2. Portfolio & Bundle Fixtures (PF1-PF8)
# ===========================================================================

class TestPortfolioAndBundle:
    """Fixtures PF1-PF8 testing schema, validator, ablation, composition gain, and rivalry."""

    def test_pf1_twelve_superficially_strong_candidates_with_real_overlap(self, tmp_path):
        """PF1: 12 superficially strong candidates in search field; judge maps pairwise overlap,
        merging redundant candidates and preserving only genuine unique residues.
        """
        run_id = "pf1-twelve-cands"
        candidates = [
            {
                "candidate_id": f"c{i:02d}",
                "title": f"Candidate Strategy {i}",
                "core_claim": f"Strategy {i} optimizing review throughput",
                "structural_shift": f"Structural shift {i}",
                "mechanism": f"Mechanism {i}",
                "boundary": "Team internal",
                "operator_provenance": "represented",
                "difference_from_prior": f"Variation {i}",
            }
            for i in range(1, 13)
        ]
        p = make_candidates_payload(pass_num=1, candidates=candidates)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        cand_hash = (run_dir / "candidates.sha256").read_text().strip()

        sf = make_search_field_payload(
            passes=[{"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": cand_hash}],
            entries=[f"pass01:c{i:02d}" for i in range(1, 13)],
        )
        freeze_stage(tmp_path, "search-field", run_id, sf)
        sf_hash = (run_dir / "search-field.sha256").read_text().strip()

        # Assessments: c01, c05, c09 are distinct KEEP; others are MERGE/DROP with nearest_overlap
        assessments = []
        for i in range(1, 13):
            cid = f"c{i:02d}"
            ref = f"pass01:{cid}"
            if i in (1, 5, 9):
                assessments.append({
                    "candidate_ref": ref,
                    "disposition": "KEEP",
                    "standalone_quality": "strong",
                    "unique_residue": f"Core distinct mechanism {i}",
                    "nearest_overlap": None,
                    "reason": f"Distinct paradigm {i}",
                })
            elif i in (2, 3, 4):
                assessments.append({
                    "candidate_ref": ref,
                    "disposition": "MERGE",
                    "standalone_quality": "strong",
                    "unique_residue": "",
                    "nearest_overlap": "pass01:c01",
                    "reason": "Sub-variant of c01",
                })
            elif i in (6, 7, 8):
                assessments.append({
                    "candidate_ref": ref,
                    "disposition": "MERGE",
                    "standalone_quality": "strong",
                    "unique_residue": "",
                    "nearest_overlap": "pass01:c05",
                    "reason": "Sub-variant of c05",
                })
            else:
                assessments.append({
                    "candidate_ref": ref,
                    "disposition": "DROP",
                    "standalone_quality": "weak",
                    "unique_residue": "",
                    "nearest_overlap": "pass01:c09",
                    "reason": "Redundant and low leverage",
                })

        port = make_portfolio_payload(
            field_hash=sf_hash,
            assessments=assessments,
            bundles=[],
            route="MANUAL",
        )
        res = freeze_stage(tmp_path, "portfolio", run_id, port)
        assert res.returncode == 0, res.stderr

    def test_pf2_valid_three_member_bundle_composition_gain(self, tmp_path):
        """PF2: Valid 3-member Bundle with clear composition gain, explicit member roles,
        and all 3 member ablations present and distinct.
        """
        run_id = "pf2-valid-3member"
        candidates = [
            {"candidate_id": "c01", "title": "Lint Gate", "core_claim": "Pre-filter", "structural_shift": "Bot gate", "mechanism": "CI bot", "boundary": "Formatting", "operator_provenance": "represented", "difference_from_prior": "Init"},
            {"candidate_id": "c02", "title": "Batch Queue", "core_claim": "Async batch", "structural_shift": "Scheduled review", "mechanism": "Windows", "boundary": "Team PRs", "operator_provenance": "represented", "difference_from_prior": "Init"},
            {"candidate_id": "c03", "title": "Pair Escalation", "core_claim": "Sync pair", "structural_shift": "Live review", "mechanism": "Pair block", "boundary": "Stalled PRs", "operator_provenance": "represented", "difference_from_prior": "Init"},
        ]
        p = make_candidates_payload(pass_num=1, candidates=candidates)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        cand_hash = (run_dir / "candidates.sha256").read_text().strip()

        sf = make_search_field_payload(
            passes=[{"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": cand_hash}],
            entries=["pass01:c01", "pass01:c02", "pass01:c03"],
        )
        freeze_stage(tmp_path, "search-field", run_id, sf)
        sf_hash = (run_dir / "search-field.sha256").read_text().strip()

        assessments = [
            {"candidate_ref": f"pass01:c0{i}", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": f"Residue {i}", "nearest_overlap": None, "reason": f"Solid candidate {i}"}
            for i in range(1, 4)
        ]
        bundle = {
            "bundle_id": "B1",
            "member_refs": ["pass01:c01", "pass01:c02", "pass01:c03"],
            "bundle_thesis": "Three-tier filter, batch, and escalation architecture",
            "composition_gain": "Filters eliminate noise, batching normalizes review volume, escalation unblocks complex PRs",
            "new_consequence_or_prediction": "Median review cycle drops to under 3 hours with zero stale PRs",
            "internal_tension": "Escalation threshold sensitivity vs pairing schedule availability",
            "weakest_link": "Engineers ignoring async queue and escalating immediately",
            "member_roles": {
                "pass01:c01": "Mechanical pre-filter",
                "pass01:c02": "Primary async throughput cadence",
                "pass01:c03": "Synchronous escalation path for blocked PRs",
            },
            "member_ablation": {
                "pass01:c01": "Without lint gate, batch windows are flooded with formatting discussions",
                "pass01:c02": "Without batch queue, engineers face constant notification interrupts",
                "pass01:c03": "Without pairing escalation, high-complexity PRs sit idle for days",
            },
        }
        port = make_portfolio_payload(
            field_hash=sf_hash,
            assessments=assessments,
            bundles=[bundle],
            route="MANUAL",
        )
        res = freeze_stage(tmp_path, "portfolio", run_id, port)
        assert res.returncode == 0, res.stderr

    def test_pf3_fake_thematic_cluster_rejected(self, tmp_path):
        """PF3: Fake thematic cluster lacking real member ablation fails closed."""
        run_id = "pf3-fake-cluster"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        cand_hash = (run_dir / "candidates.sha256").read_text().strip()

        sf = make_search_field_payload(
            passes=[{"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": cand_hash}],
            entries=["pass01:c01", "pass01:c02"],
        )
        freeze_stage(tmp_path, "search-field", run_id, sf)
        sf_hash = (run_dir / "search-field.sha256").read_text().strip()

        assessments = [
            {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Async", "nearest_overlap": None, "reason": "Good"},
            {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Lint", "nearest_overlap": None, "reason": "Good"},
        ]
        # Fake cluster with empty/missing member ablation keys fails validator
        bundle_fake = {
            "bundle_id": "B1",
            "member_refs": ["pass01:c01", "pass01:c02"],
            "bundle_thesis": "Generic developer tooling bundle",
            "composition_gain": "Both tools help developers",
            "new_consequence_or_prediction": "Things improve",
            "internal_tension": "None",
            "weakest_link": "None",
            "member_roles": {"pass01:c01": "tool A", "pass01:c02": "tool B"},
            "member_ablation": {"pass01:c01": "Tool A is gone"},  # Missing pass01:c02
        }
        port = make_portfolio_payload(
            field_hash=sf_hash,
            assessments=assessments,
            bundles=[bundle_fake],
            route="MANUAL",
        )
        res = freeze_stage(tmp_path, "portfolio", run_id, port)
        assert res.returncode != 0
        assert "member_ablation" in res.stderr

    def test_pf4_bundle_containing_removable_passenger(self, tmp_path):
        """PF4: Bundle containing a removable passenger whose ablation does not alter thesis."""
        run_id = "pf4-passenger"
        candidates = [
            {"candidate_id": "c01", "title": "Batch Queue", "core_claim": "Async batch", "structural_shift": "Shift", "mechanism": "Queue", "boundary": "Team", "operator_provenance": "represented", "difference_from_prior": "Init"},
            {"candidate_id": "c02", "title": "Lint Gate", "core_claim": "Pre-filter", "structural_shift": "Shift", "mechanism": "Gate", "boundary": "Team", "operator_provenance": "represented", "difference_from_prior": "Init"},
            {"candidate_id": "c03", "title": "Slack Emoji Bot", "core_claim": "React with party parrot on PR merge", "structural_shift": "Celebration", "mechanism": "Webhook", "boundary": "Slack", "operator_provenance": "represented", "difference_from_prior": "Init"},
        ]
        p = make_candidates_payload(pass_num=1, candidates=candidates)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        cand_hash = (run_dir / "candidates.sha256").read_text().strip()

        sf = make_search_field_payload(
            passes=[{"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": cand_hash}],
            entries=["pass01:c01", "pass01:c02", "pass01:c03"],
        )
        freeze_stage(tmp_path, "search-field", run_id, sf)
        sf_hash = (run_dir / "search-field.sha256").read_text().strip()

        assessments = [
            {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Queue", "nearest_overlap": None, "reason": "Core"},
            {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Filter", "nearest_overlap": None, "reason": "Core"},
            {"candidate_ref": "pass01:c03", "disposition": "KEEP", "standalone_quality": "weak", "unique_residue": "Cosmetic emoji", "nearest_overlap": None, "reason": "Trivial"},
        ]
        # In development-v2, ablation for B1 must explicitly record that c03 is a passenger
        dev = make_development_v2_payload(
            target_type="B",
            target_id="B1",
            member_refs=["pass01:c01", "pass01:c02", "pass01:c03"],
            member_contributions={
                "pass01:c01": "Core queueing mechanism",
                "pass01:c02": "Pre-filtering mechanism",
                "pass01:c03": "Cosmetic notification decoration",
            },
            member_ablation={
                "pass01:c01": "Without queue, review latency collapses into ad-hoc chaos",
                "pass01:c02": "Without filter, focus blocks are polluted with lint noise",
                "pass01:c03": "Without emoji bot, model thesis and performance are completely unchanged (passenger)",
            },
        )
        res_dev = freeze_stage(tmp_path, "development-v2", run_id, dev, target="B1")
        assert res_dev.returncode == 0, res_dev.stderr

        # Critic flags the passenger in findings.member_ablation
        dev_hash = (run_dir / "development-v2-B1.sha256").read_text().strip()
        rev = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            target_type="B",
            target_id="B1",
            terminal_state="NEED_EVIDENCE",
            member_ablation_finding="Passenger detected: pass01:c03 removal causes zero loss of causal explanatory power.",
            verdict_rationale="Bundle must excise pass01:c03 passenger before achieving MODEL_READY.",
        )
        res_rev = freeze_stage(tmp_path, "deep-review-v2", run_id, rev, target="B1")
        assert res_rev.returncode == 0, res_rev.stderr

    def test_pf5_two_interesting_bundles_that_do_not_compete(self, tmp_path):
        """PF5: Two Bundles addressing orthogonal non-rival concerns (e.g. backend CI vs frontend bundle size).
        Portfolio correctly selects NO_SECOND_DEFENSIBLE_BUNDLE; recommended_competition must be null.
        """
        run_id = "pf5-orthogonal-bundles"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        cand_hash = (run_dir / "candidates.sha256").read_text().strip()

        sf = make_search_field_payload(
            passes=[{"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": cand_hash}],
            entries=["pass01:c01", "pass01:c02"],
        )
        freeze_stage(tmp_path, "search-field", run_id, sf)
        sf_hash = (run_dir / "search-field.sha256").read_text().strip()

        assessments = [
            {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Async batching", "nearest_overlap": None, "reason": "Backend PR review"},
            {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Automated lint", "nearest_overlap": None, "reason": "Mechanical check"},
        ]
        b1 = {
            "bundle_id": "B1",
            "member_refs": ["pass01:c01", "pass01:c02"],
            "bundle_thesis": "Backend PR throughput pipeline",
            "composition_gain": "Clean integration of lint and batching",
            "new_consequence_or_prediction": "Backend PR velocity doubles",
            "internal_tension": "Batch window timing",
            "weakest_link": "Developer window compliance",
            "member_roles": {"pass01:c01": "Queue", "pass01:c02": "Filter"},
            "member_ablation": {"pass01:c01": "Queue lost", "pass01:c02": "Filter lost"},
        }
        port_v2 = make_portfolio_payload(
            field_hash=sf_hash,
            assessments=assessments,
            bundles=[b1],
            route="MANUAL",
            schema_version="pizm-portfolio-selection-v2",
            competition_status="NO_SECOND_DEFENSIBLE_BUNDLE",
            recommended_competition=None,
        )
        res = freeze_stage(tmp_path, "portfolio", run_id, port_v2)
        assert res.returncode == 0, res.stderr

    def test_pf6_two_competing_bundles_different_predictions(self, tmp_path):
        """PF6: Two competing Bundles with rival mechanisms and distinct predictions.
        Portfolio correctly sets TWO_DEFENSIBLE_BUNDLES with valid competition axis and discriminating test.
        """
        run_id = "pf6-competing-bundles"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        cand_hash = (run_dir / "candidates.sha256").read_text().strip()

        sf = make_search_field_payload(
            passes=[{"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": cand_hash}],
            entries=["pass01:c01", "pass01:c02"],
        )
        freeze_stage(tmp_path, "search-field", run_id, sf)
        sf_hash = (run_dir / "search-field.sha256").read_text().strip()

        assessments = [
            {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Async batching", "nearest_overlap": None, "reason": "Async model"},
            {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Automated lint", "nearest_overlap": None, "reason": "Mechanical gate"},
        ]
        b1 = {
            "bundle_id": "B1",
            "member_refs": ["pass01:c01", "pass01:c02"],
            "bundle_thesis": "Asynchronous automated batching pipeline",
            "composition_gain": "Reduces context switching interruptions",
            "new_consequence_or_prediction": "Total developer deep work hours increase by 30%",
            "internal_tension": "Queue wait vs focus",
            "weakest_link": "Window adherence",
            "member_roles": {"pass01:c01": "Queue", "pass01:c02": "Filter"},
            "member_ablation": {"pass01:c01": "Loss of queue", "pass01:c02": "Loss of filter"},
        }
        b2 = {
            "bundle_id": "B2",
            "member_refs": ["pass01:c01", "pass01:c02"],
            "bundle_thesis": "Real-time synchronous review pairing",
            "composition_gain": "Instant interactive feedback eliminates latency",
            "new_consequence_or_prediction": "PR cycle time drops to under 1 hour",
            "internal_tension": "Calendar fragmentation vs review speed",
            "weakest_link": "Schedule coordination",
            "member_roles": {"pass01:c01": "Pairing schedule", "pass01:c02": "Pre-pairing check"},
            "member_ablation": {"pass01:c01": "Loss of pairing", "pass01:c02": "Loss of check"},
        }
        rec_comp = {
            "bundle_a": "B1",
            "bundle_b": "B2",
            "competition_axis": "Asynchronous focus protection vs Synchronous latency elimination",
            "discriminating_observation": "Measure team meeting density and distribution across timezones.",
            "discriminating_question": "Does calendar fragmentation make pairing unworkable or is async latency unacceptable?",
        }
        port_v2 = make_portfolio_payload(
            field_hash=sf_hash,
            assessments=assessments,
            bundles=[b1, b2],
            route="MANUAL",
            schema_version="pizm-portfolio-selection-v2",
            competition_status="TWO_DEFENSIBLE_BUNDLES",
            recommended_competition=rec_comp,
        )
        res = freeze_stage(tmp_path, "portfolio", run_id, port_v2)
        assert res.returncode == 0, res.stderr

    def test_pf7_cost_relocation_identified(self, tmp_path):
        """PF7: Candidate/Bundle appears to solve the problem but merely relocates cost to another team.
        Critic records non-empty cost_relocation finding.
        """
        run_id = "pf7-cost-relocation"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        cand_hash = (run_dir / "candidates.sha256").read_text().strip()

        sf = make_search_field_payload(
            passes=[{"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": cand_hash}],
            entries=["pass01:c01", "pass01:c02"],
        )
        freeze_stage(tmp_path, "search-field", run_id, sf)

        dev = make_development_v2_payload(
            target_type="P",
            target_id="P1",
            thesis="Mandate that all PR reviews must be approved by the core platform infrastructure team.",
        )
        freeze_stage(tmp_path, "development-v2", run_id, dev)
        dev_hash = (run_dir / "development-v2.sha256").read_text().strip()

        rev = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            target_type="P",
            target_id="P1",
            terminal_state="NEED_EVIDENCE",
            cost_relocation="Review burden is not reduced; it is merely transferred entirely onto the platform team, creating an acute bottleneck.",
            verdict_rationale="Cost relocation must be resolved before model is ready.",
        )
        res_rev = freeze_stage(tmp_path, "deep-review-v2", run_id, rev)
        assert res_rev.returncode == 0, res_rev.stderr

    def test_pf8_borderline_candidate_valuable_only_in_composition(self, tmp_path):
        """PF8: Candidate evaluated as BORDERLINE standalone becomes valuable only in composition.
        Validator accepts BORDERLINE disposition and successful bundle inclusion.
        """
        run_id = "pf8-borderline-catalyst"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        cand_hash = (run_dir / "candidates.sha256").read_text().strip()

        sf = make_search_field_payload(
            passes=[{"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": cand_hash}],
            entries=["pass01:c01", "pass01:c02"],
        )
        freeze_stage(tmp_path, "search-field", run_id, sf)
        sf_hash = (run_dir / "search-field.sha256").read_text().strip()

        assessments = [
            {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Async batching", "nearest_overlap": None, "reason": "Strong throughput foundation"},
            {"candidate_ref": "pass01:c02", "disposition": "BORDERLINE", "standalone_quality": "borderline", "unique_residue": "Strict lint gate", "nearest_overlap": None, "reason": "Mediocre standalone, but essential gate for batching"},
        ]
        bundle = {
            "bundle_id": "B1",
            "member_refs": ["pass01:c01", "pass01:c02"],
            "bundle_thesis": "Lint-gated batch review system",
            "composition_gain": "Borderline lint gate acts as essential noise filter for batch review queue",
            "new_consequence_or_prediction": "Review throughput doubles with zero developer complaints about formatting",
            "internal_tension": "Strict gate rejection vs author workflow speed",
            "weakest_link": "Hook configuration drift",
            "member_roles": {"pass01:c01": "Primary throughput queue", "pass01:c02": "Noise suppression catalyst"},
            "member_ablation": {
                "pass01:c01": "Without batch queue, developers face ad-hoc interrupts",
                "pass01:c02": "Without lint gate, batch focus blocks are ruined by formatting debates",
            },
        }
        port = make_portfolio_payload(
            field_hash=sf_hash,
            assessments=assessments,
            bundles=[bundle],
            route="MANUAL",
        )
        res = freeze_stage(tmp_path, "portfolio", run_id, port)
        assert res.returncode == 0, res.stderr


# ===========================================================================
# 3. Observed Deep/Critic Dogfood Reproduction & CR1-CR10
# ===========================================================================

class TestObservedDogfoodReproduction:
    """Sanitized reproduction fixture of observed dogfood failure mode."""

    def test_observed_dogfood_failure_reproduction(self, tmp_path):
        """Reproduction: Development minimizes an objection and introduces unsupported specificity.
        Critic independently reassesses objection, flags unsupported specificity and evidence debt,
        and refuses automatic MODEL_READY.
        """
        run_id = "dogfood-repro"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        # Development introduces hyper-specific unproven claim
        claims = [
            {
                "claim": "Context switching latency follows an exact 23-minute biological refractory period",
                "epistemic_status": "SPECULATIVE",
                "role_in_model": "Core timing parameter",
                "what_would_weaken_or_refute": "Neuroscience data showing variable recovery times",
            },
            {
                "claim": "Pre-push hooks reduce AST parsing overhead by exactly 87.4%",
                "epistemic_status": "SUPPORTED",
                "role_in_model": "Performance claim",
                "what_would_weaken_or_refute": "Benchmark results under 80%",
            },
        ]
        dev = make_development_v2_payload(
            target_type="P",
            target_id="P1",
            claims=claims,
            mechanism_chain=[
                "PR triggers notification interrupt",
                "Engineer incurs exact 23-minute refractory cognitive recovery period",
                "Batching PRs restores 100% of cognitive bandwidth",
            ],
        )
        freeze_stage(tmp_path, "development-v2", run_id, dev)
        dev_hash = (run_dir / "development-v2.sha256").read_text().strip()

        # Critic independently reassesses, demoting status, flagging unsupported specificity, adding debt
        rev = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            target_type="P",
            target_id="P1",
            terminal_state="NEED_EVIDENCE",  # Honest stop, not MODEL_READY
            reassessments=[
                {
                    "claim": "Context switching latency follows an exact 23-minute biological refractory period",
                    "critic_epistemic_status": "SPECULATIVE",
                },
                {
                    "claim": "Pre-push hooks reduce AST parsing overhead by exactly 87.4%",
                    "critic_epistemic_status": "UNKNOWN",  # Demoted from SUPPORTED due to lack of proof
                },
            ],
            unsupported_specificity=[
                "Asserted exact 23-minute biological refractory period without empirical basis",
                "Asserted 87.4% exact AST parsing overhead reduction without reproducible benchmark",
            ],
            evidence_debt=[
                "Run direct developer attention assay or cite peer-reviewed literature",
                "Execute local AST benchmark on production codebases to measure actual savings",
            ],
            verdict_rationale="Development asserted unsupported specificity; model must collect evidence before MODEL_READY.",
        )
        res_rev = freeze_stage(tmp_path, "deep-review-v2", run_id, rev)
        assert res_rev.returncode == 0, res_rev.stderr


class TestCriticRegression:
    """CR1-CR12 deterministic critic contracts and validator couplings."""

    def test_cr1_direct_cross_field_contradiction_blocks_model_ready(self, tmp_path):
        """CR1: Unresolved cross-field contradiction strictly blocks MODEL_READY."""
        run_id = "cr1-contradiction"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(target_type="P", target_id="P1")
        freeze_stage(tmp_path, "development-v2", run_id, dev)
        dev_hash = (run_dir / "development-v2.sha256").read_text().strip()

        # Contradiction + MODEL_READY fails closed
        rev_bad = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            terminal_state="MODEL_READY",
            unresolved_contradiction=True,
            cross_contradictions=["Claim 1 asserts zero async lag while Claim 2 asserts 4-hour batch window delay"],
        )
        res_bad = freeze_stage(tmp_path, "deep-review-v2", run_id, rev_bad)
        assert res_bad.returncode != 0
        assert "unresolved_load_bearing_contradiction" in res_bad.stderr

        # Contradiction + NEED_EVIDENCE passes
        rev_ok = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            terminal_state="NEED_EVIDENCE",
            unresolved_contradiction=True,
            cross_contradictions=["Claim 1 asserts zero async lag while Claim 2 asserts 4-hour batch window delay"],
        )
        res_ok = freeze_stage(tmp_path, "deep-review-v2", run_id, rev_ok)
        assert res_ok.returncode == 0, res_ok.stderr

    def test_cr2_epistemic_laundering_flagged_and_reassessed(self, tmp_path):
        """CR2: Critic catches and records epistemic laundering."""
        run_id = "cr2-laundering"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(target_type="P", target_id="P1")
        freeze_stage(tmp_path, "development-v2", run_id, dev)
        dev_hash = (run_dir / "development-v2.sha256").read_text().strip()

        rev = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            terminal_state="NEED_EVIDENCE",
            epistemic_laundering=["Developer marked speculative customer adoption assumption as SUPPORTED"],
            reassessments=[
                {"claim": "Context switching is the primary review friction", "critic_epistemic_status": "SPECULATIVE"},
                {"claim": "Reviewers adhere consistently to designated focus windows", "critic_epistemic_status": "UNKNOWN"},
            ],
            evidence_debt=["Verify actual developer adoption rate in telemetry"],
        )
        res = freeze_stage(tmp_path, "deep-review-v2", run_id, rev)
        assert res.returncode == 0, res.stderr

    def test_cr3_fake_break_condition_flagged(self, tmp_path):
        """CR3: Critic identifies fake/non-falsifiable break condition."""
        run_id = "cr3-fake-break"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(
            target_type="P",
            target_id="P1",
            breaks=["Model breaks if engineers simply do not like using it"],
        )
        freeze_stage(tmp_path, "development-v2", run_id, dev)
        dev_hash = (run_dir / "development-v2.sha256").read_text().strip()

        rev = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            terminal_state="NEED_EVIDENCE",
            countermodel="Break condition is unfalsifiable and subjective; real failure mode is silent bypassing via Slack DMs.",
            cheapest_test="Instrument PR merge logs to detect unreviewed commits.",
            evidence_debt=["Define measurable disconfirming metric on bypass rate"],
        )
        res = freeze_stage(tmp_path, "deep-review-v2", run_id, rev)
        assert res.returncode == 0, res.stderr

    def test_cr4_strong_independent_countermodel(self, tmp_path):
        """CR4: Checkpoint enforces non-empty independent countermodel."""
        run_id = "cr4-countermodel"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(target_type="P", target_id="P1")
        freeze_stage(tmp_path, "development-v2", run_id, dev)
        dev_hash = (run_dir / "development-v2.sha256").read_text().strip()

        rev_bad = make_deep_review_v2_payload(frozen_hash=dev_hash, countermodel="   ")
        res_bad = freeze_stage(tmp_path, "deep-review-v2", run_id, rev_bad)
        assert res_bad.returncode != 0
        assert "independent_countermodel" in res_bad.stderr

    def test_cr5_bundle_passenger_member_in_critic(self, tmp_path):
        """CR5: Critic evaluates and reports Bundle passenger members."""
        run_id = "cr5-passenger-eval"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(target_type="B", target_id="B1")
        freeze_stage(tmp_path, "development-v2", run_id, dev, target="B1")
        dev_hash = (run_dir / "development-v2-B1.sha256").read_text().strip()

        # Bundle target requires non-empty member_ablation in findings
        rev_bad = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            target_type="B",
            target_id="B1",
            member_ablation_finding="",
        )
        res_bad = freeze_stage(tmp_path, "deep-review-v2", run_id, rev_bad, target="B1")
        assert res_bad.returncode != 0
        assert "member_ablation" in res_bad.stderr

    def test_cr6_cost_relocation_in_critic(self, tmp_path):
        """CR6: Critic explicitly captures cost relocation in findings."""
        run_id = "cr6-cost-relocation"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(target_type="P", target_id="P1")
        freeze_stage(tmp_path, "development-v2", run_id, dev)
        dev_hash = (run_dir / "development-v2.sha256").read_text().strip()

        rev = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            cost_relocation="Review overhead is shifted upstream onto individual committers writing exhaustive design docs.",
        )
        res = freeze_stage(tmp_path, "deep-review-v2", run_id, rev)
        assert res.returncode == 0, res.stderr

    def test_cr7_weak_round_trip_skeleton_fails_closed(self, tmp_path):
        """CR7: Critic requires non-empty round_trip_skeleton."""
        run_id = "cr7-skeleton"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(target_type="P", target_id="P1")
        freeze_stage(tmp_path, "development-v2", run_id, dev)
        dev_hash = (run_dir / "development-v2.sha256").read_text().strip()

        rev_bad = make_deep_review_v2_payload(frozen_hash=dev_hash, round_trip_skeleton="")
        res_bad = freeze_stage(tmp_path, "deep-review-v2", run_id, rev_bad)
        assert res_bad.returncode != 0
        assert "round_trip_skeleton" in res_bad.stderr

    def test_cr8_discriminating_test_required(self, tmp_path):
        """CR8: Cheapest discriminating test is mandatory in critic record."""
        run_id = "cr8-test-required"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(target_type="P", target_id="P1")
        freeze_stage(tmp_path, "development-v2", run_id, dev)
        dev_hash = (run_dir / "development-v2.sha256").read_text().strip()

        rev_bad = make_deep_review_v2_payload(frozen_hash=dev_hash, cheapest_test="   ")
        res_bad = freeze_stage(tmp_path, "deep-review-v2", run_id, rev_bad)
        assert res_bad.returncode != 0
        assert "cheapest_discriminating_test" in res_bad.stderr

    def test_cr9_genuinely_model_ready(self, tmp_path):
        """CR9: Well-supported model with no contradictions cleanly achieves MODEL_READY."""
        run_id = "cr9-ready"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(target_type="P", target_id="P1")
        freeze_stage(tmp_path, "development-v2", run_id, dev)
        dev_hash = (run_dir / "development-v2.sha256").read_text().strip()

        rev = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            terminal_state="MODEL_READY",
            identity_verified=True,
            unresolved_contradiction=False,
            verdict_rationale="All causal steps validated and grounded.",
        )
        res = freeze_stage(tmp_path, "deep-review-v2", run_id, rev)
        assert res.returncode == 0, res.stderr

    def test_cr10_genuinely_need_evidence(self, tmp_path):
        """CR10: Inferred claims with open epistemic debt cleanly achieve NEED_EVIDENCE."""
        run_id = "cr10-need-evidence"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(target_type="P", target_id="P1")
        freeze_stage(tmp_path, "development-v2", run_id, dev)
        dev_hash = (run_dir / "development-v2.sha256").read_text().strip()

        rev = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            terminal_state="NEED_EVIDENCE",
            identity_verified=True,
            evidence_debt=["Empirical validation on 3 sprint retrospectives required"],
            verdict_rationale="Model is promising but requires longitudinal evidence.",
        )
        res = freeze_stage(tmp_path, "deep-review-v2", run_id, rev)
        assert res.returncode == 0, res.stderr

    def test_cr11_speculative_central_mechanism_yields_need_evidence(self, tmp_path):
        """CR11: Speculative central mechanism with unresolved contradiction forces NEED_EVIDENCE."""
        run_id = "cr11-speculative-central"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(target_type="P", target_id="P1")
        freeze_stage(tmp_path, "development-v2", run_id, dev)
        dev_hash = (run_dir / "development-v2.sha256").read_text().strip()

        # B1 blocker with MODEL_READY fails closed
        rev_bad = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            terminal_state="MODEL_READY",
            unresolved_contradiction=True,
            reassessments=[
                {"claim": "Primary causal driver operates via tacit knowledge gap", "critic_epistemic_status": "SPECULATIVE"}
            ],
            evidence_debt=["Empirical telemetry on tacit knowledge transfer lag required"],
            verdict_rationale="Central claim is speculative but trying to mark ready.",
        )
        res_bad = freeze_stage(tmp_path, "deep-review-v2", run_id, rev_bad)
        assert res_bad.returncode != 0
        assert "unresolved_load_bearing_contradiction" in res_bad.stderr

        # B1 blocker with NEED_EVIDENCE passes
        rev_ok = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            terminal_state="NEED_EVIDENCE",
            unresolved_contradiction=True,
            reassessments=[
                {"claim": "Primary causal driver operates via tacit knowledge gap", "critic_epistemic_status": "SPECULATIVE"}
            ],
            evidence_debt=["Empirical telemetry on tacit knowledge transfer lag required"],
            verdict_rationale="Central mechanism is speculative; gate enforced -> NEED_EVIDENCE.",
        )
        res_ok = freeze_stage(tmp_path, "deep-review-v2", run_id, rev_ok)
        assert res_ok.returncode == 0, res_ok.stderr

    def test_cr12_night_drift_critic_gate_enforcement(self, tmp_path):
        """CR12: Night Drift defect profile (3/4 speculative, laundering, countermodel) enforces gate."""
        run_id = "cr12-night-drift"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(target_type="B", target_id="B8")
        freeze_stage(tmp_path, "development-v2", run_id, dev, target="B8")
        dev_hash = (run_dir / "development-v2-B8.sha256").read_text().strip()

        reassessments = [
            {"claim": "Author experienced night without choice forks", "critic_epistemic_status": "SUPPORTED"},
            {"claim": "Self-report codes night as repetition", "critic_epistemic_status": "SPECULATIVE"},
            {"claim": "7 AM debrief functions to close loop", "critic_epistemic_status": "SPECULATIVE"},
            {"claim": "Explanatory frame relocates guilt", "critic_epistemic_status": "SPECULATIVE"},
        ]
        debts = [
            "Check independent witness corroboration",
            "Measure chronometric lag across debrief",
            "Test alternative fatigue model against journal log",
            "Validate whether guilt shift altered subsequent routine",
        ]
        laundering = [
            "Synthesis speaks with higher certainty than census where 3/4 claims are speculative."
        ]
        countermodel = "Chronological fatigue inertia without recursive orbit."

        # Attempting MODEL_READY with unresolved contradiction fails closed
        rev_bad = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            target_type="B",
            target_id="B8",
            terminal_state="MODEL_READY",
            unresolved_contradiction=True,
            reassessments=reassessments,
            countermodel=countermodel,
            epistemic_laundering=laundering,
            member_ablation_finding="All members contribute distinct structural facets.",
            evidence_debt=debts,
            verdict_rationale="Attempting MODEL_READY despite 3/4 speculative claims and countermodel.",
        )
        res_bad = freeze_stage(tmp_path, "deep-review-v2", run_id, rev_bad, target="B8")
        assert res_bad.returncode != 0
        assert "unresolved_load_bearing_contradiction" in res_bad.stderr

        # Honest gate enforcement: NEED_EVIDENCE succeeds
        rev_ok = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            target_type="B",
            target_id="B8",
            terminal_state="NEED_EVIDENCE",
            unresolved_contradiction=True,
            reassessments=reassessments,
            countermodel=countermodel,
            epistemic_laundering=laundering,
            member_ablation_finding="All members contribute distinct structural facets.",
            evidence_debt=debts,
            verdict_rationale="Gate enforced: 3/4 speculative claims and stronger countermodel require NEED_EVIDENCE.",
        )
        res_ok = freeze_stage(tmp_path, "deep-review-v2", run_id, rev_ok, target="B8")
        assert res_ok.returncode == 0, res_ok.stderr


# ===========================================================================
# 4. Reasoning Arsenal Anti-Cargo-Cult Cases
# ===========================================================================

class TestReasoningArsenalAntiCargoCult:
    """Anti-cargo-cult regression fixtures: schemas allow model to decline techniques cleanly."""

    def test_arsenal_decline_no_stable_binding_constraint(self, tmp_path):
        """Case 1: No single stable binding constraint -> model declines TOC moves."""
        run_id = "arsenal-decline-toc"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(
            target_type="P",
            target_id="P1",
            thesis="Distributed optimization without a single binding bottleneck.",
            unresolved_tensions=["No single constraint binds throughput; friction is diffusely distributed across all stages."],
        )
        res = freeze_stage(tmp_path, "development-v2", run_id, dev)
        assert res.returncode == 0, res.stderr

    def test_arsenal_decline_no_useful_systems_archetype(self, tmp_path):
        """Case 2: No useful systems archetype applies -> model declines archetype moves."""
        run_id = "arsenal-decline-archetype"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(
            target_type="P",
            target_id="P1",
            thesis="Simple linear pipeline without archetype dynamic structures.",
            dynamics="Purely feedforward linear stage pipeline with zero oscillatory feedback loops.",
        )
        res = freeze_stage(tmp_path, "development-v2", run_id, dev)
        assert res.returncode == 0, res.stderr

    def test_arsenal_decline_no_real_contradiction_to_dissolve(self, tmp_path):
        """Case 3: No real contradiction to dissolve -> model declines TRIZ contradiction moves."""
        run_id = "arsenal-decline-triz"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(
            target_type="P",
            target_id="P1",
            thesis="Standard quantitative tradeoff optimization rather than qualitative contradiction.",
            unresolved_tensions=["Tradeoff is smooth and continuous; no sharp contradiction exists."],
        )
        res = freeze_stage(tmp_path, "development-v2", run_id, dev)
        assert res.returncode == 0, res.stderr

    def test_arsenal_decline_no_feedback_loop_adds_explanatory_value(self, tmp_path):
        """Case 4: No feedback loop adds explanatory value -> model declines feedback moves."""
        run_id = "arsenal-decline-feedback"
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"

        dev = make_development_v2_payload(
            target_type="P",
            target_id="P1",
            thesis="One-shot mechanical filtering step.",
            mechanism_chain=[
                "Developer runs git push",
                "Pre-push hook parses modified files",
                "Non-compliant changes blocked locally",
            ],
        )
        res = freeze_stage(tmp_path, "development-v2", run_id, dev)
        assert res.returncode == 0, res.stderr


# ===========================================================================
# 5. AUTO End-to-End Fixtures (A1-A5)
# ===========================================================================

class TestAutoEndToEndFixtures:
    """A1-A5 end-to-end AUTO fixtures with real freeze and render execution."""

    def _setup_auto_base(self, tmp_path: Path, run_id: str, target_type: str = "P", target_id: str = "P1", terminal_state: str = "MODEL_READY", with_lever: bool = False):
        p = make_candidates_payload(pass_num=1)
        freeze_stage(tmp_path, "explore", run_id, p)
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        cand_hash = (run_dir / "candidates.sha256").read_text().strip()

        sf = make_search_field_payload(
            passes=[{"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": cand_hash}],
            entries=["pass01:c01", "pass01:c02"],
        )
        freeze_stage(tmp_path, "search-field", run_id, sf)
        sf_hash = (run_dir / "search-field.sha256").read_text().strip()

        assessments = [
            {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Async", "nearest_overlap": None, "reason": "Good"},
            {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Lint", "nearest_overlap": None, "reason": "Good"},
        ]
        bundles = []
        if target_type == "B":
            bundles = [{
                "bundle_id": "B1",
                "member_refs": ["pass01:c01", "pass01:c02"],
                "bundle_thesis": "Integrated review system",
                "composition_gain": "Combines lint and batching",
                "new_consequence_or_prediction": "Fast turnaround",
                "internal_tension": "Window timing",
                "weakest_link": "Window adherence",
                "member_roles": {"pass01:c01": "Queue", "pass01:c02": "Filter"},
                "member_ablation": {"pass01:c01": "Queue gone", "pass01:c02": "Filter gone"},
            }]

        port = make_portfolio_payload(
            field_hash=sf_hash,
            assessments=assessments,
            bundles=bundles,
            route="AUTO",
            auto_target={"target_type": target_type, "target_id": target_id, "rationale": "Top priority model"},
        )
        freeze_stage(tmp_path, "portfolio", run_id, port)

        dev = make_development_v2_payload(target_type=target_type, target_id=target_id)
        freeze_stage(tmp_path, "development-v2", run_id, dev)
        dev_hash = (run_dir / "development-v2.sha256").read_text().strip()

        rev = make_deep_review_v2_payload(
            frozen_hash=dev_hash,
            target_type=target_type,
            target_id=target_id,
            terminal_state=terminal_state,
        )
        freeze_stage(tmp_path, "deep-review-v2", run_id, rev)
        if with_lever and terminal_state == "MODEL_READY":
            ld = make_lever_design_payload()
            freeze_stage(tmp_path, "lever-design", run_id, ld)
            design_hash = (run_dir / "design.sha256").read_text().strip()
            lr = make_lever_review_payload(frozen_hash=design_hash)
            freeze_stage(tmp_path, "lever-review", run_id, lr)

        return run_dir
    def test_a1_auto_chooses_standalone_p(self, tmp_path):
        """A1: AUTO chooses standalone candidate P. Real freeze + render."""
        run_id = "a1-auto-standalone-p"
        run_dir = self._setup_auto_base(tmp_path, run_id, target_type="P", target_id="P1")
        out_md = tmp_path / "run.md"
        res = run_render(run_dir, DEFAULT_TASK, out_md)
        assert res.returncode == 0, res.stderr
        content = out_md.read_text(encoding="utf-8")
        assert "# Prism AUTO" in content
        assert "## Task" in content
        assert "## Search" in content
        assert "## Portfolio" in content
        assert "## Selected" in content
        assert "- Selected: P1 — Async Batch Review Queues" in content
        assert "## Deep" in content
        assert "## Critic" in content
        assert "## Final" in content
        assert "- Terminal state: MODEL_READY" in content
        assert "- Lever: not executed" in content

    def test_a2_auto_chooses_bundle_b(self, tmp_path):
        """A2: AUTO chooses Bundle B. Real freeze + render."""
        run_id = "a2-auto-bundle-b"
        run_dir = self._setup_auto_base(tmp_path, run_id, target_type="B", target_id="B1")
        out_md = tmp_path / "run.md"
        res = run_render(run_dir, DEFAULT_TASK, out_md)
        assert res.returncode == 0, res.stderr
        content = out_md.read_text(encoding="utf-8")
        assert "# Prism AUTO" in content
        assert "## Bundles" in content
        assert "### B1 — P1 + P2" in content
        assert "- Selected: B1 — Integrated System Bundle B1" in content
        assert "Member contributions (bundle):" in content
        assert "Member ablation (bundle):" in content

    def test_a3_auto_analytical_no_lever(self, tmp_path):
        """A3: AUTO analytical task orientation -> MODEL_READY without LEVER."""
        run_id = "a3-auto-analytical"
        run_dir = self._setup_auto_base(tmp_path, run_id, target_type="P", target_id="P1", with_lever=False)
        out_md = tmp_path / "run.md"
        res = run_render(run_dir, "Analyze root causes of PR latency", out_md)
        assert res.returncode == 0, res.stderr
        content = out_md.read_text(encoding="utf-8")
        assert "## Lever" not in content
        assert "- Lever: not executed (orientation/terminal-state gate not met)" in content

    def test_a4_auto_action_oriented_justified_lever(self, tmp_path):
        """A4: AUTO action-oriented task orientation -> MODEL_READY with justified LEVER."""
        run_id = "a4-auto-action-lever"
        run_dir = self._setup_auto_base(tmp_path, run_id, target_type="P", target_id="P1", with_lever=True)
        out_md = tmp_path / "run.md"
        res = run_render(run_dir, "Implement intervention to cut PR cycle time in half", out_md)
        assert res.returncode == 0, res.stderr
        content = out_md.read_text(encoding="utf-8")
        assert "## Lever" in content
        assert "### L1" in content
        assert "Outcome: **LEVER**" in content
        assert "- Lever: LEVER (1 accepted of 1)" in content

    def test_a5_auto_deep_ends_need_evidence_honest_stop(self, tmp_path):
        """A5: AUTO Deep ends in NEED_EVIDENCE -> honest stop, no LEVER executed."""
        run_id = "a5-auto-need-evidence"
        run_dir = self._setup_auto_base(tmp_path, run_id, target_type="P", target_id="P1", terminal_state="NEED_EVIDENCE", with_lever=False)
        out_md = tmp_path / "run.md"
        res = run_render(run_dir, DEFAULT_TASK, out_md)
        assert res.returncode == 0, res.stderr
        content = out_md.read_text(encoding="utf-8")
        assert "Honest stop: NEED_EVIDENCE" in content
        assert "- Terminal state: NEED_EVIDENCE" in content
        assert "- Lever: not executed (orientation/terminal-state gate not met)" in content


# ===========================================================================
# 6. FORGE End-to-End Fixtures (F1-F6)
# ===========================================================================

class TestForgeEndToEndFixtures:
    """F1-F6 end-to-end FORGE fixtures with real freeze and render execution."""

    def _setup_forge_base(
        self,
        tmp_path: Path,
        run_id: str,
        competition_status: str = "TWO_DEFENSIBLE_BUNDLES",
        comp_preference: str = "LEFT",
        with_lever: bool = False,
    ):
        p1 = make_candidates_payload(pass_num=1)
        res1 = freeze_stage(tmp_path, "explore", run_id, p1, artifact_suffix="pass01")
        assert res1.returncode == 0, res1.stderr
        run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
        p1_hash = (run_dir / "candidates-pass01.sha256").read_text().strip()

        p2 = make_candidates_payload(pass_num=2)
        res2 = freeze_stage(tmp_path, "explore", run_id, p2, artifact_suffix="pass02")
        assert res2.returncode == 0, res2.stderr
        p2_hash = (run_dir / "candidates-pass02.sha256").read_text().strip()
        sf = make_search_field_payload(
            passes=[
                {"pass_id": "pass01", "candidates_ref": "candidates-pass01.json", "frozen_hash": p1_hash},
                {"pass_id": "pass02", "candidates_ref": "candidates-pass02.json", "frozen_hash": p2_hash},
            ],
            entries=["pass01:c01", "pass01:c02", "pass02:c01", "pass02:c02"],
        )
        freeze_stage(tmp_path, "search-field", run_id, sf)
        sf_hash = (run_dir / "search-field.sha256").read_text().strip()

        assessments = [
            {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Async queue", "nearest_overlap": None, "reason": "Async foundation"},
            {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Lint filter", "nearest_overlap": None, "reason": "Mechanical gate"},
            {"candidate_ref": "pass02:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Pairing rotation", "nearest_overlap": None, "reason": "Sync speed"},
            {"candidate_ref": "pass02:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Diff cap", "nearest_overlap": None, "reason": "Size cap"},
        ]
        b1 = {
            "bundle_id": "B1",
            "member_refs": ["pass01:c01", "pass01:c02"],
            "bundle_thesis": "Asynchronous automated batching system",
            "composition_gain": "Pre-filters noise then batches focus windows",
            "new_consequence_or_prediction": "Reviewer focus increases without scheduling overhead",
            "internal_tension": "Queue latency vs focus",
            "weakest_link": "Window adherence",
            "member_roles": {"pass01:c01": "Queue", "pass01:c02": "Filter"},
            "member_ablation": {"pass01:c01": "Queue lost", "pass01:c02": "Filter lost"},
        }
        b2 = {
            "bundle_id": "B2",
            "member_refs": ["pass02:c01", "pass02:c02"],
            "bundle_thesis": "Synchronous capped pairing system",
            "composition_gain": "Combines strict diff limits with dedicated daily pairing blocks",
            "new_consequence_or_prediction": "Zero queue latency for all active changes",
            "internal_tension": "Calendar overhead vs speed",
            "weakest_link": "Timezone overlap",
            "member_roles": {"pass02:c01": "Pairing", "pass02:c02": "Diff cap"},
            "member_ablation": {"pass02:c01": "Pairing lost", "pass02:c02": "Cap lost"},
        }

        if competition_status == "TWO_DEFENSIBLE_BUNDLES":
            rec_comp = {
                "left_bundle_id": "B1",
                "right_bundle_id": "B2",
                "competition_axis": "Asynchronous batching vs Synchronous pairing",
                "discriminating_observation": "Measure engineering calendar density and distribution across timezones.",
                "discriminating_question": "Does calendar fragmentation make pairing impossible or does async lag dominate?",
            }
            bundles = [b1, b2]
        else:
            rec_comp = None
            bundles = [b1]

        port_v2 = make_portfolio_payload(
            field_hash=sf_hash,
            assessments=assessments,
            bundles=bundles,
            route="BONK",
            schema_version="pizm-portfolio-selection-v2",
            competition_status=competition_status,
            recommended_competition=rec_comp,
        )
        freeze_stage(tmp_path, "portfolio", run_id, port_v2)

        # Deep B1
        dev_b1 = make_development_v2_payload(
            target_type="B",
            target_id="B1",
            member_refs=["pass01:c01", "pass01:c02"],
            thesis="Async queueing stabilizes attention when noise is filtered.",
        )
        freeze_stage(tmp_path, "development-v2", run_id, dev_b1, target="B1")

        if competition_status == "TWO_DEFENSIBLE_BUNDLES":
            # Deep B2
            dev_b2 = make_development_v2_payload(
                target_type="B",
                target_id="B2",
                member_refs=["pass02:c01", "pass02:c02"],
                thesis="Synchronous pairing on small diffs eliminates review queues entirely.",
            )
            freeze_stage(tmp_path, "development-v2", run_id, dev_b2, target="B2")

            sha_b1 = (run_dir / "development-v2-B1.sha256").read_text().strip()
            sha_b2 = (run_dir / "development-v2-B2.sha256").read_text().strip()
            # Comparison Review
            comp = make_comparison_review_payload(
                preference=comp_preference,
                b1_ref="development-v2-B1.json",
                b1_hash=sha_b1,
                b2_ref="development-v2-B2.json",
                b2_hash=sha_b2,
            )
            freeze_stage(tmp_path, "comparison-review-v1", run_id, comp)
        else:
            # Single-model deep review
            dev_hash = (run_dir / "development-v2-B1.sha256").read_text().strip()
            single_rev = make_deep_review_v2_payload(
                frozen_hash=dev_hash,
                target_type="B",
                target_id="B1",
                target_ref="development-v2-B1.json",
                terminal_state="MODEL_READY",
            )
            freeze_stage(tmp_path, "deep-review-v2", run_id, single_rev)
        if with_lever and comp_preference in ("LEFT", "RIGHT"):
            ld = make_lever_design_payload()
            freeze_stage(tmp_path, "lever-design", run_id, ld)
            design_hash = (run_dir / "design.sha256").read_text().strip()
            lr = make_lever_review_payload(frozen_hash=design_hash)
            freeze_stage(tmp_path, "lever-review", run_id, lr)

        return run_dir

    def test_f1_two_defensible_competing_bundles(self, tmp_path):
        """F1: Two defensible competing Bundles B1 and B2. Real freeze + render."""
        run_id = "f1-two-defensible"
        run_dir = self._setup_forge_base(tmp_path, run_id, competition_status="TWO_DEFENSIBLE_BUNDLES", comp_preference="LEFT")
        out_md = tmp_path / "run.md"
        res = run_render(run_dir, DEFAULT_TASK, out_md)
        assert res.returncode == 0, res.stderr
        content = out_md.read_text(encoding="utf-8")
        assert "# Prism BONK" in content
        assert "## Search Pass 1" in content
        assert "## Search Pass 2" in content
        assert "## Portfolio" in content
        assert "## Bundles" in content
        assert "## Why these models compete" in content
        assert "## Deep B2" in content
        assert "## Critic and Comparison" in content
        assert "- Current preference: **LEFT**" in content
        assert "## Final" in content
        assert "- Current preference: LEFT" in content

    def test_f2_one_defensible_bundle_only(self, tmp_path):
        """F2: One defensible Bundle only (NO_SECOND_DEFENSIBLE_BUNDLE). Real freeze + render."""
        run_id = "f2-one-bundle"
        run_dir = self._setup_forge_base(tmp_path, run_id, competition_status="NO_SECOND_DEFENSIBLE_BUNDLE")
        out_md = tmp_path / "run.md"
        res = run_render(run_dir, DEFAULT_TASK, out_md)
        assert res.returncode == 0, res.stderr
        content = out_md.read_text(encoding="utf-8")
        assert "# Prism BONK" in content
        assert "## Deep B1" in content
        assert "## Deep B2" not in content  # No fake B2
        assert "- Outcome: NO_SECOND_DEFENSIBLE_BUNDLE" in content

    def test_f3_comparison_conditional(self, tmp_path):
        """F3: Comparison CONDITIONAL preference with explicit boundary conditions."""
        run_id = "f3-conditional"
        run_dir = self._setup_forge_base(tmp_path, run_id, comp_preference="CONDITIONAL")
        out_md = tmp_path / "run.md"
        res = run_render(run_dir, DEFAULT_TASK, out_md)
        assert res.returncode == 0, res.stderr
        content = out_md.read_text(encoding="utf-8")
        assert "- Current preference: **CONDITIONAL**" in content
        assert "- Current preference: CONDITIONAL" in content

    def test_f4_comparison_unresolved(self, tmp_path):
        """F4: Comparison UNRESOLVED outcome without forced winner."""
        run_id = "f4-unresolved"
        run_dir = self._setup_forge_base(tmp_path, run_id, comp_preference="UNRESOLVED")
        out_md = tmp_path / "run.md"
        res = run_render(run_dir, DEFAULT_TASK, out_md)
        assert res.returncode == 0, res.stderr
        content = out_md.read_text(encoding="utf-8")
        assert "- Current preference: **UNRESOLVED**" in content
        assert "- Current preference: UNRESOLVED" in content

    def test_f5_action_oriented_forge_justified_lever(self, tmp_path):
        """F5: Action-oriented FORGE with justified LEVER."""
        run_id = "f5-action-lever"
        run_dir = self._setup_forge_base(tmp_path, run_id, comp_preference="LEFT", with_lever=True)
        out_md = tmp_path / "run.md"
        res = run_render(run_dir, "Implement immediate intervention to halve PR cycle time", out_md)
        assert res.returncode == 0, res.stderr
        content = out_md.read_text(encoding="utf-8")
        assert "## Lever" in content
        assert "### L1" in content
        assert "Outcome: **LEVER**" in content
        assert "- Lever: LEVER (1 accepted of 1)" in content
    def test_f6_analytical_forge_no_lever(self, tmp_path):
        """F6: Analytical FORGE with no LEVER executed."""
        run_id = "f6-analytical-no-lever"
        run_dir = self._setup_forge_base(tmp_path, run_id, comp_preference="LEFT", with_lever=False)
        out_md = tmp_path / "run.md"
        res = run_render(run_dir, "Analyze strategic tradeoffs between sync and async review", out_md)
        assert res.returncode == 0, res.stderr
        content = out_md.read_text(encoding="utf-8")
        assert "## Lever" not in content
        assert "- Lever: not executed (orientation/terminal-state gate not met)" in content
