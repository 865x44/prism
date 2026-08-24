"""Tests for Perspective Core v0 360 / Repeated 360 (Wave 3).

Covers 360-A–I scripted scenarios from Wave 3 brief and execution contract:
- 360-A: attractor lock breakout
- 360-B: true residual territory
- 360-C: bounded no-new-territory (zero KEEP, NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS)
- 360-D: accumulated constraints (active vs superseded)
- 360-E: topic novelty != mechanism novelty (decorative sci-fi/quantum framing rejected)
- 360-F: NORMAL → 360 → repeated 360 continuity with monotonic P-IDs
- 360-G: meaningful MERGE not rediscovered as novel
- 360-H: old constraint-failed junk does not block future territory
- 360-I: Call A produces prior summary rather than receiving it

Also covers:
- Deterministic territory classification from PassRecords (survivor, meaningful_merge, borderline, strong_redundant_drop)
- Exclusion of constraint failures, inadmissible, and weak candidates from explored territory
- No trace scraping (operates entirely on session model)
- No prose-reason parsing for classification
- Monotonic P-ID numbering across passes
- Trace file verification: prior-summary.json written only for 360 mode
"""

from __future__ import annotations

import json
import uuid
from collections import deque
from pathlib import Path
from typing import Any

import pytest

from prism.perspective_core.explore import run_explore
from prism.perspective_core.models import (
    ConstraintLedger,
    Diagnosis,
    Epistemics,
    ExploreRunResult,
    MergeTarget,
    PassRecord,
    PerspectiveCandidate,
    PerspectiveIdentity,
    PerspectiveRequest,
    PerspectiveSession,
    PerspectiveState,
    ProviderResult,
    ReturnPath,
    SelectionRecord,
    SemanticCore,
    compute_source_hash,
)
from prism.perspective_core.provider import ScriptedProvider, TransportError
from prism.perspective_core.session import SessionStore
from prism.perspective_core.territory import (
    ExploredTerritoryEntry,
    ExploreGenerationResult,
    PriorSummary,
    build_prior_territory,
    render_explored_territory,
    render_prior_summary,
)

FIXTURES_DIR = Path(__file__).parent / "perspective_core" / "fixtures" / "360"


def load_fixture(scenario: str) -> str:
    """Load a 360 scenario fixture source (e.g. '360a')."""
    return (FIXTURES_DIR / f"{scenario}_source.md").read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Test Provider & Helpers
# ─────────────────────────────────────────────────────────────────────────────


class ScriptedTestProvider(ScriptedProvider):
    """Stage-indexed test provider that validates stage order and exhaustiveness."""

    __test__ = False

    def complete(self, prompt: str, *, stage: str, invocation_id: str) -> ProviderResult:
        if stage not in self._queues:
            raise TransportError(f"Unknown stage: {stage}")

        queue = self._queues[stage]
        if not queue:
            raise TransportError(f"Exhausted stage queue: {stage}")

        result = queue.popleft()
        self._call_count += 1

        if result.stage != stage:
            raise TransportError(f"Stage mismatch: expected {result.stage}, got {stage}")

        return ProviderResult(
            invocation_id=invocation_id,
            stage=stage,
            raw_text=result.raw_text,
            model=result.model,
            transport=result.transport,
            duration_ms=result.duration_ms,
            exit_code=result.exit_code,
        )


def make_candidate(
    candidate_id: str = "C1",
    mechanism: str = "test mechanism",
    central_problem: str = "test problem",
    load_bearing_claim: str = "test claim",
    shift: str = "test shift",
    system_boundary: str | None = None,
    agency_model: str | None = None,
    unit_of_analysis: str | None = None,
    temporal_logic: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    """Create a minimal candidate dictionary for responses."""
    base: dict[str, Any] = {
        "candidate_id": candidate_id,
        "semantic_core": {
            "central_problem": central_problem,
            "mechanism": mechanism,
            "load_bearing_claim": load_bearing_claim,
            "central_object": None,
            "unit_of_analysis": unit_of_analysis,
            "system_boundary": system_boundary,
            "agency_model": agency_model,
            "temporal_logic": temporal_logic,
            "key_constraint": None,
            "downstream_consequences": ["consequence 1", "consequence 2"],
        },
        "preserved": ["core problem context"],
        "default_frame": "default framing",
        "blind_spot": "inherent blind spot",
        "operator_ids": [],
        "shift": shift,
        "perspective": f"Perspective based on {mechanism}",
        "new_consequences": ["new consequence 1", "new consequence 2"],
        "return_path": {
            "dimension_changed": "causal mechanism",
            "consequence_chain": ["step 1", "step 2"],
            "why_it_matters": "practical impact",
        },
        "epistemics": {
            "supported": ["grounded in source"],
            "inferred": ["reasonable inference"],
            "speculative": [],
            "unknown": [],
            "break_condition": ["breaks if assumptions fail"],
        },
    }
    base.update(overrides)
    return base


def make_selection(
    candidate_id: str = "C1",
    disposition: str = "KEEP",
    admissible: bool = True,
    constraint_failures: list[str] | None = None,
    standalone_quality: str = "strong",
    marginal_contribution: str = "high",
    structurally_distinct: bool = True,
    merge_target: dict[str, str] | None = None,
    reason: str = "Evaluation explanation",
    **overrides: Any,
) -> dict[str, Any]:
    """Create a minimal selection record dictionary for responses."""
    base: dict[str, Any] = {
        "candidate_id": candidate_id,
        "admissible": admissible,
        "constraint_failures": constraint_failures or [],
        "structurally_distinct": structurally_distinct,
        "novelty_dimensions": ["mechanism"],
        "nearest_candidate_id": None,
        "nearest_existing_p_id": None,
        "standalone_quality": standalone_quality,
        "marginal_contribution": marginal_contribution,
        "disposition": disposition,
        "merge_target": merge_target,
        "reason": reason,
    }
    base.update(overrides)
    return base


def make_prior_summary(
    dominant_mechanisms: list[str] | None = None,
    dominant_boundaries: list[str] | None = None,
    dominant_agency_models: list[str] | None = None,
    dominant_timescales: list[str] | None = None,
    shared_assumptions: list[str] | None = None,
    residual_gap_hypotheses: list[str] | None = None,
) -> dict[str, Any]:
    """Create a PriorSummary dictionary for Call A responses."""
    return {
        "dominant_mechanisms": dominant_mechanisms or ["centralized enforcement"],
        "dominant_boundaries": dominant_boundaries or ["platform boundary"],
        "dominant_agency_models": dominant_agency_models or ["top-down administrator"],
        "dominant_timescales": dominant_timescales or ["real-time synchronous"],
        "shared_assumptions": shared_assumptions or ["central authority is trustworthy"],
        "residual_gap_hypotheses": residual_gap_hypotheses or ["decentralized client-side reputation"],
    }


def make_360_generate_response(
    prior_summary: dict[str, Any],
    diagnosis: dict[str, Any],
    candidates: list[dict[str, Any]],
    invocation_id: str = "gen-360-1",
) -> ProviderResult:
    """Create an EXPLORE_360_GENERATE response."""
    return ProviderResult(
        invocation_id=invocation_id,
        stage="EXPLORE_360_GENERATE",
        raw_text=json.dumps({
            "prior_summary": prior_summary,
            "diagnosis": diagnosis,
            "candidates": candidates,
        }),
        model="test-qwen",
        transport="scripted",
        duration_ms=120,
        exit_code=0,
    )


def make_360_select_response(
    selections: list[dict[str, Any]], invocation_id: str = "sel-360-1"
) -> ProviderResult:
    """Create an EXPLORE_360_SELECT response."""
    return ProviderResult(
        invocation_id=invocation_id,
        stage="EXPLORE_360_SELECT",
        raw_text=json.dumps(selections),
        model="test-qwen",
        transport="scripted",
        duration_ms=100,
        exit_code=0,
    )


def make_normal_generate_response(
    diagnosis: dict[str, Any],
    candidates: list[dict[str, Any]],
    invocation_id: str = "gen-norm-1",
) -> ProviderResult:
    """Create an EXPLORE_GENERATE response."""
    return ProviderResult(
        invocation_id=invocation_id,
        stage="EXPLORE_GENERATE",
        raw_text=json.dumps({
            "diagnosis": diagnosis,
            "candidates": candidates,
        }),
        model="test-qwen",
        transport="scripted",
        duration_ms=100,
        exit_code=0,
    )


def make_normal_select_response(
    selections: list[dict[str, Any]], invocation_id: str = "sel-norm-1"
) -> ProviderResult:
    """Create an EXPLORE_SELECT response."""
    return ProviderResult(
        invocation_id=invocation_id,
        stage="EXPLORE_SELECT",
        raw_text=json.dumps(selections),
        model="test-qwen",
        transport="scripted",
        duration_ms=100,
        exit_code=0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 360-A: Attractor Lock Breakout
# ─────────────────────────────────────────────────────────────────────────────


def test_360_a_attractor_lock(tmp_path: Path) -> None:
    """360-A: Identifies prior dominant framing attractors and breaks out with residual candidate."""
    source = load_fixture("360a")
    objective = "Analyze platform moderation mechanisms and explore alternative structural levers."
    session_store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    # Pass 1: NORMAL exploration establishes dominant centralized attractors (P1, P2)
    p1_gen = make_normal_generate_response(
        diagnosis={"central_problem": "Content moderation", "search_profile": "platform governance", "priority_dimensions": ["filtering"]},
        candidates=[
            make_candidate("C1", mechanism="Automated classifier filtering", central_problem="Content moderation", system_boundary="platform boundary"),
            make_candidate("C2", mechanism="Centralized human review committee", central_problem="Content moderation", system_boundary="platform governance"),
        ],
    )
    p1_sel = make_normal_select_response([
        make_selection("C1", disposition="KEEP", reason="Strong core mechanism"),
        make_selection("C2", disposition="KEEP", reason="Strong governance model"),
    ])

    provider_p1 = ScriptedTestProvider({
        "EXPLORE_GENERATE": deque([p1_gen]),
        "EXPLORE_SELECT": deque([p1_sel]),
    })

    req1 = PerspectiveRequest(source=source, objective=objective, mode="normal")
    res1 = run_explore(req1, session_store=session_store, provider=provider_p1, trace_root=trace_root)
    assert res1.outcome == "OK"
    assert len(res1.kept) == 2
    assert [s.identity.p_id for s in res1.kept] == ["P1", "P2"]
    session_id = res1.session_id

    # Pass 2: 360 residual search identifies the centralized attractor and proposes client-side friction (P3)
    prior_summary = make_prior_summary(
        dominant_mechanisms=["Automated classifier filtering", "Centralized human review committee"],
        dominant_boundaries=["platform boundary", "platform governance"],
        dominant_agency_models=["central platform administrator"],
        dominant_timescales=["synchronous post-time"],
        shared_assumptions=["moderation must occur on platform servers"],
        residual_gap_hypotheses=["client-side temporal delay and peer-attestation protocols"],
    )
    p2_gen = make_360_generate_response(
        prior_summary=prior_summary,
        diagnosis={"central_problem": "Content moderation", "search_profile": "residual client-side architecture", "priority_dimensions": ["client agency"]},
        candidates=[
            make_candidate("C1", mechanism="Client-side temporal propagation delay", central_problem="Information propagation", shift="from server-side filtering to client-side friction"),
        ],
    )
    p2_sel = make_360_select_response([
        make_selection("C1", disposition="KEEP", standalone_quality="strong", marginal_contribution="high", reason="Breaks out of centralized server attractor"),
    ])

    provider_p2 = ScriptedTestProvider({
        "EXPLORE_360_GENERATE": deque([p2_gen]),
        "EXPLORE_360_SELECT": deque([p2_sel]),
    })

    req2 = PerspectiveRequest(source=source, objective=objective, mode="360", session_id=session_id)
    res2 = run_explore(req2, session_store=session_store, provider=provider_p2, trace_root=trace_root)
    assert res2.outcome == "OK"
    assert len(res2.kept) == 1
    assert res2.kept[0].identity.p_id == "P3"
    assert res2.kept[0].identity.identity_core.mechanism == "Client-side temporal propagation delay"

    # Verify session continuity and PassRecord persistence
    session = session_store.load(session_id)
    assert len(session.passes) == 2
    assert session.passes[0].mode == "normal"
    assert session.passes[1].mode == "360"
    assert session.next_p_number == 4


# ─────────────────────────────────────────────────────────────────────────────
# 360-B: True Residual Territory
# ─────────────────────────────────────────────────────────────────────────────


def test_360_b_residual_territory(tmp_path: Path) -> None:
    """360-B: 360 discovers genuine unmapped residual territory."""
    source = load_fixture("360b")
    objective = "Analyze municipal water infrastructure leak detection."
    session_store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    # Pass 1 (NORMAL): P1 acoustic loggers, P2 pressure reduction valves
    p1_gen = make_normal_generate_response(
        diagnosis={"central_problem": "Water leakage", "search_profile": "pipe telemetry", "priority_dimensions": ["acoustics", "hydraulics"]},
        candidates=[
            make_candidate("C1", mechanism="Pipe-mounted acoustic loggers"),
            make_candidate("C2", mechanism="District metered area pressure control"),
        ],
    )
    p1_sel = make_normal_select_response([
        make_selection("C1", disposition="KEEP"),
        make_selection("C2", disposition="KEEP"),
    ])
    provider_p1 = ScriptedTestProvider({
        "EXPLORE_GENERATE": deque([p1_gen]),
        "EXPLORE_SELECT": deque([p1_sel]),
    })
    res1 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="normal"), session_store=session_store, provider=provider_p1, trace_root=trace_root)
    session_id = res1.session_id

    # Pass 2 (360): Residual territory — subterranean soil hydrology transmission
    p2_gen = make_360_generate_response(
        prior_summary=make_prior_summary(
            dominant_mechanisms=["Pipe-mounted acoustic loggers", "District metered area pressure control"],
            residual_gap_hypotheses=["Subterranean soil acoustic impedance profiling"],
        ),
        diagnosis={"central_problem": "Water leakage", "search_profile": "environmental medium", "priority_dimensions": ["soil acoustics"]},
        candidates=[
            make_candidate("C1", mechanism="Subterranean soil moisture impedance tomography", shift="from internal pipe acoustics to surrounding soil medium"),
        ],
    )
    p2_sel = make_360_select_response([
        make_selection("C1", disposition="KEEP", standalone_quality="strong", marginal_contribution="high"),
    ])
    provider_p2 = ScriptedTestProvider({
        "EXPLORE_360_GENERATE": deque([p2_gen]),
        "EXPLORE_360_SELECT": deque([p2_sel]),
    })
    res2 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="360", session_id=session_id), session_store=session_store, provider=provider_p2, trace_root=trace_root)

    assert res2.outcome == "OK"
    assert len(res2.kept) == 1
    assert res2.kept[0].identity.p_id == "P3"


# ─────────────────────────────────────────────────────────────────────────────
# 360-C: Bounded No-New Territory
# ─────────────────────────────────────────────────────────────────────────────


def test_360_c_bounded_no_new_territory(tmp_path: Path) -> None:
    """360-C: When no candidate provides marginal value, returns bounded NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS."""
    source = load_fixture("360c")
    objective = "Analyze standardized single-unit warehouse facility."
    session_store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    # Pass 1: creates P1
    p1_gen = make_normal_generate_response(
        diagnosis={"central_problem": "Warehouse storage", "search_profile": "inventory routing", "priority_dimensions": ["pallet turnover"]},
        candidates=[make_candidate("C1", mechanism="ABC inventory turnover zoning")],
    )
    p1_sel = make_normal_select_response([make_selection("C1", disposition="KEEP")])
    provider_p1 = ScriptedTestProvider({
        "EXPLORE_GENERATE": deque([p1_gen]),
        "EXPLORE_SELECT": deque([p1_sel]),
    })
    res1 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="normal"), session_store=session_store, provider=provider_p1, trace_root=trace_root)
    session_id = res1.session_id
    assert res1.kept[0].identity.p_id == "P1"

    # Pass 2: Candidates are redundant or weak -> DROP/MERGE -> 0 KEEP
    p2_gen = make_360_generate_response(
        prior_summary=make_prior_summary(dominant_mechanisms=["ABC inventory turnover zoning"]),
        diagnosis={"central_problem": "Warehouse storage", "search_profile": "exhausted domain", "priority_dimensions": []},
        candidates=[
            make_candidate("C1", mechanism="ABC inventory turnover with color coding"),
            make_candidate("C2", mechanism="Fixed rack height inspection"),
        ],
    )
    p2_sel = make_360_select_response([
        make_selection("C1", disposition="MERGE", merge_target={"kind": "perspective", "target_id": "P1"}, standalone_quality="strong", marginal_contribution="none", reason="Identical to P1 with cosmetic color tags"),
        make_selection("C2", disposition="DROP", standalone_quality="weak", marginal_contribution="none", reason="No causal perspective mechanism"),
    ])
    provider_p2 = ScriptedTestProvider({
        "EXPLORE_360_GENERATE": deque([p2_gen]),
        "EXPLORE_360_SELECT": deque([p2_sel]),
    })
    res2 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="360", session_id=session_id), session_store=session_store, provider=provider_p2, trace_root=trace_root)

    assert res2.outcome == "NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS"
    assert res2.kept == []
    assert res2.rendered == ""

    # Verify session remains consistent and next_p_number is unchanged
    session = session_store.load(session_id)
    assert len(session.passes) == 2
    assert session.next_p_number == 2  # Still 2 because no P2 was registered


# ─────────────────────────────────────────────────────────────────────────────
# 360-D: Accumulated Constraints
# ─────────────────────────────────────────────────────────────────────────────


def test_360_d_accumulated_constraints(tmp_path: Path) -> None:
    """360-D: Respects accumulated and superseded constraints across multiple passes."""
    source = load_fixture("360d")
    objective = "Analyze clinical trial biomarker protocols."
    session_store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    ledger = ConstraintLedger()
    ledger.add(constraint_id="C_NO_ANIMAL", value="Must not extrapolate from animal models", kind="hard")
    ledger.add(constraint_id="C_SAMPLE_SIZE", value="Prefer sample size > 50", kind="preference")

    # Pass 1 (NORMAL) with initial ledger -> creates P1
    p1_gen = make_normal_generate_response(
        diagnosis={"central_problem": "Biomarker stratification", "search_profile": "human oncology trials", "priority_dimensions": ["genomic profiling"]},
        candidates=[make_candidate("C1", mechanism="Genomic biomarker cohort enrichment")],
    )
    p1_sel = make_normal_select_response([make_selection("C1", disposition="KEEP")])
    provider_p1 = ScriptedTestProvider({
        "EXPLORE_GENERATE": deque([p1_gen]),
        "EXPLORE_SELECT": deque([p1_sel]),
    })
    req1 = PerspectiveRequest(source=source, objective=objective, mode="normal", constraint_ledger=ledger)
    res1 = run_explore(req1, session_store=session_store, provider=provider_p1, trace_root=trace_root)
    session_id = res1.session_id

    # Update ledger: supersede C_SAMPLE_SIZE and add hard constraint C_SURROGATE
    session = session_store.load(session_id)
    session.constraint_ledger.add(constraint_id="C_SAMPLE_SIZE", value="Sample size must exceed 200", kind="hard")
    session.constraint_ledger.add(constraint_id="C_SURROGATE", value="Must use validated surrogate endpoints", kind="hard")
    session_store.save(session)

    # Pass 2 (360): C1 violates hard constraint C_NO_ANIMAL -> DROP; C2 compliant -> KEEP
    p2_gen = make_360_generate_response(
        prior_summary=make_prior_summary(dominant_mechanisms=["Genomic biomarker cohort enrichment"]),
        diagnosis={"central_problem": "Biomarker stratification", "search_profile": "surrogate validation", "priority_dimensions": ["surrogates"]},
        candidates=[
            make_candidate("C1", mechanism="Murine pre-clinical model extrapolation"),
            make_candidate("C2", mechanism="Circulating tumor DNA early clearance kinetics"),
        ],
    )
    p2_sel = make_360_select_response([
        make_selection("C1", disposition="DROP", admissible=False, constraint_failures=["C_NO_ANIMAL"], standalone_quality="strong", marginal_contribution="none", reason="Violates animal model hard constraint"),
        make_selection("C2", disposition="KEEP", admissible=True, constraint_failures=[], standalone_quality="strong", marginal_contribution="high", reason="Compliant with all active constraints"),
    ])
    provider_p2 = ScriptedTestProvider({
        "EXPLORE_360_GENERATE": deque([p2_gen]),
        "EXPLORE_360_SELECT": deque([p2_sel]),
    })
    res2 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="360", session_id=session_id), session_store=session_store, provider=provider_p2, trace_root=trace_root)

    assert res2.outcome == "OK"
    assert len(res2.kept) == 1
    assert res2.kept[0].identity.p_id == "P2"
    assert res2.kept[0].identity.identity_core.mechanism == "Circulating tumor DNA early clearance kinetics"


# ─────────────────────────────────────────────────────────────────────────────
# 360-E: Topic Novelty != Mechanism Novelty
# ─────────────────────────────────────────────────────────────────────────────


def test_360_e_topic_novelty_not_mechanism_novelty(tmp_path: Path) -> None:
    """360-E: Decorative topical shift with identical mechanism is rejected (MERGE/DROP)."""
    source = load_fixture("360e")
    objective = "Analyze engineering knowledge transfer."
    session_store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    # Pass 1: P1 is central documentation repository
    p1_gen = make_normal_generate_response(
        diagnosis={"central_problem": "Knowledge transfer", "search_profile": "documentation", "priority_dimensions": ["codification"]},
        candidates=[make_candidate("C1", mechanism="Centralized digital documentation wiki", system_boundary="firm repository", agency_model="top-down archivist")],
    )
    p1_sel = make_normal_select_response([make_selection("C1", disposition="KEEP")])
    provider_p1 = ScriptedTestProvider({
        "EXPLORE_GENERATE": deque([p1_gen]),
        "EXPLORE_SELECT": deque([p1_sel]),
    })
    res1 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="normal"), session_store=session_store, provider=provider_p1, trace_root=trace_root)
    session_id = res1.session_id

    # Pass 2:
    # C1: "Quantum Holographic Neural Knowledge Graph" — same mechanism as P1 (centralized storage).
    # C2: "Dual-track apprentice failure forensics" — genuine novel mechanism (tacit behavioral reflection).
    p2_gen = make_360_generate_response(
        prior_summary=make_prior_summary(dominant_mechanisms=["Centralized digital documentation wiki"]),
        diagnosis={"central_problem": "Knowledge transfer", "search_profile": "tacit transfer", "priority_dimensions": ["apprenticeship"]},
        candidates=[
            make_candidate("C1", mechanism="Quantum Holographic Neural Knowledge Mesh", system_boundary="firm repository", agency_model="top-down archivist"),
            make_candidate("C2", mechanism="Dual-track apprentice failure forensics", system_boundary="mentor-apprentice pair", agency_model="paired reflective practitioners"),
        ],
    )
    p2_sel = make_360_select_response([
        make_selection("C1", disposition="MERGE", merge_target={"kind": "perspective", "target_id": "P1"}, standalone_quality="strong", marginal_contribution="none", reason="Topic novelty only; identical causal mechanism and agency to P1"),
        make_selection("C2", disposition="KEEP", standalone_quality="strong", marginal_contribution="high", reason="Genuinely novel tacit mechanism and distinct agency model"),
    ])
    provider_p2 = ScriptedTestProvider({
        "EXPLORE_360_GENERATE": deque([p2_gen]),
        "EXPLORE_360_SELECT": deque([p2_sel]),
    })
    res2 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="360", session_id=session_id), session_store=session_store, provider=provider_p2, trace_root=trace_root)

    assert res2.outcome == "OK"
    assert len(res2.kept) == 1
    assert res2.kept[0].identity.p_id == "P2"
    assert res2.kept[0].identity.identity_core.mechanism == "Dual-track apprentice failure forensics"


# ─────────────────────────────────────────────────────────────────────────────
# 360-F: NORMAL → 360 → Repeated 360 Continuity
# ─────────────────────────────────────────────────────────────────────────────


def test_360_f_continuity_normal_to_360_to_repeated_360(tmp_path: Path) -> None:
    """360-F: Monotonic P-ID allocation across NORMAL -> 360 -> repeated 360."""
    source = load_fixture("360f")
    objective = "Analyze power grid frequency regulation and renewable integration."
    session_store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    # Pass 1 (NORMAL): creates P1, P2
    p1_gen = make_normal_generate_response(
        diagnosis={"central_problem": "Grid stability", "search_profile": "inertia", "priority_dimensions": ["fast response"]},
        candidates=[
            make_candidate("C1", mechanism="Synthetic inertia algorithms from wind turbines"),
            make_candidate("C2", mechanism="Fast-responding battery storage reserves"),
        ],
    )
    p1_sel = make_normal_select_response([
        make_selection("C1", disposition="KEEP"),
        make_selection("C2", disposition="KEEP"),
    ])
    provider_p1 = ScriptedTestProvider({
        "EXPLORE_GENERATE": deque([p1_gen]),
        "EXPLORE_SELECT": deque([p1_sel]),
    })
    res1 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="normal"), session_store=session_store, provider=provider_p1, trace_root=trace_root)
    assert [s.identity.p_id for s in res1.kept] == ["P1", "P2"]
    session_id = res1.session_id

    # Pass 2 (360): creates P3
    p2_gen = make_360_generate_response(
        prior_summary=make_prior_summary(dominant_mechanisms=["Synthetic inertia", "Battery storage"]),
        diagnosis={"central_problem": "Grid stability", "search_profile": "demand side", "priority_dimensions": ["consumer loads"]},
        candidates=[
            make_candidate("C1", mechanism="Sub-second industrial cryogenic load curtailment"),
        ],
    )
    p2_sel = make_360_select_response([
        make_selection("C1", disposition="KEEP", standalone_quality="strong", marginal_contribution="high"),
    ])
    provider_p2 = ScriptedTestProvider({
        "EXPLORE_360_GENERATE": deque([p2_gen]),
        "EXPLORE_360_SELECT": deque([p2_sel]),
    })
    res2 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="360", session_id=session_id), session_store=session_store, provider=provider_p2, trace_root=trace_root)
    assert [s.identity.p_id for s in res2.kept] == ["P3"]

    # Pass 3 (Repeated 360): creates P4
    p3_gen = make_360_generate_response(
        prior_summary=make_prior_summary(dominant_mechanisms=["Synthetic inertia", "Battery storage", "Industrial load curtailment"]),
        diagnosis={"central_problem": "Grid stability", "search_profile": "topological re-routing", "priority_dimensions": ["transmission topology"]},
        candidates=[
            make_candidate("C1", mechanism="Dynamic transmission line switching for transient impedance redistribution"),
        ],
    )
    p3_sel = make_360_select_response([
        make_selection("C1", disposition="KEEP", standalone_quality="strong", marginal_contribution="high"),
    ])
    provider_p3 = ScriptedTestProvider({
        "EXPLORE_360_GENERATE": deque([p3_gen]),
        "EXPLORE_360_SELECT": deque([p3_sel]),
    })
    res3 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="360", session_id=session_id), session_store=session_store, provider=provider_p3, trace_root=trace_root)
    assert [s.identity.p_id for s in res3.kept] == ["P4"]

    # Verify session final state
    session = session_store.load(session_id)
    assert list(session.perspectives.keys()) == ["P1", "P2", "P3", "P4"]
    assert session.next_p_number == 5
    assert len(session.passes) == 3
    assert [p.mode for p in session.passes] == ["normal", "360", "360"]


# ─────────────────────────────────────────────────────────────────────────────
# 360-G: Meaningful MERGE Not Rediscovered
# ─────────────────────────────────────────────────────────────────────────────


def test_360_g_meaningful_merge_not_rediscovered(tmp_path: Path) -> None:
    """360-G: Candidates merged in Pass 1 are captured in territory and not accepted as novel in Pass 2."""
    source = load_fixture("360g")
    objective = "Analyze urban transit signal priority corridor optimization."
    session_store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    # Pass 1 (NORMAL): C1 -> KEEP (P1); C2 -> MERGE into C1 (meaningful merge)
    p1_gen = make_normal_generate_response(
        diagnosis={"central_problem": "Transit signal priority", "search_profile": "signal preemption", "priority_dimensions": ["optical sensors"]},
        candidates=[
            make_candidate("C1", mechanism="Roadside optical vehicle detection preemption"),
            make_candidate("C2", mechanism="Roadside infrared transceiver beacon preemption"),
        ],
    )
    p1_sel = make_normal_select_response([
        make_selection("C1", disposition="KEEP", standalone_quality="strong", marginal_contribution="high"),
        make_selection("C2", disposition="MERGE", merge_target={"kind": "candidate", "target_id": "C1"}, standalone_quality="strong", marginal_contribution="low", reason="Infrared beacon is structurally identical optical preemption"),
    ])
    provider_p1 = ScriptedTestProvider({
        "EXPLORE_GENERATE": deque([p1_gen]),
        "EXPLORE_SELECT": deque([p1_sel]),
    })
    res1 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="normal"), session_store=session_store, provider=provider_p1, trace_root=trace_root)
    session_id = res1.session_id

    # Verify territory reconstruction derives the meaningful_merge
    session = session_store.load(session_id)
    territory = build_prior_territory(session)
    assert len(territory) == 2
    assert any(e.source_kind == "survivor" and e.source_id == "P1" for e in territory)
    assert any(e.source_kind == "meaningful_merge" and e.source_id == "C2" for e in territory)

    # Pass 2 (360): Candidate C1 attempts to re-propose infrared beacons -> Call B marks MERGE
    p2_gen = make_360_generate_response(
        prior_summary=make_prior_summary(dominant_mechanisms=["Roadside optical preemption", "Infrared transceiver preemption"]),
        diagnosis={"central_problem": "Transit signal priority", "search_profile": "residual corridor", "priority_dimensions": []},
        candidates=[
            make_candidate("C1", mechanism="Infrared emitter transceiver signal extension"),
        ],
    )
    p2_sel = make_360_select_response([
        make_selection("C1", disposition="MERGE", merge_target={"kind": "perspective", "target_id": "P1"}, standalone_quality="strong", marginal_contribution="none", reason="Infrared preemption already in explored meaningful territory"),
    ])
    provider_p2 = ScriptedTestProvider({
        "EXPLORE_360_GENERATE": deque([p2_gen]),
        "EXPLORE_360_SELECT": deque([p2_sel]),
    })
    res2 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="360", session_id=session_id), session_store=session_store, provider=provider_p2, trace_root=trace_root)
    assert res2.outcome == "NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS"
    assert res2.kept == []


# ─────────────────────────────────────────────────────────────────────────────
# 360-H: Old Constraint-Failed Junk Does Not Block Future Territory
# ─────────────────────────────────────────────────────────────────────────────


def test_360_h_constraint_failed_junk_not_blocking(tmp_path: Path) -> None:
    """360-H: A candidate that failed constraints in Pass 1 is excluded from territory and does not block valid future candidates."""
    source = load_fixture("360h")
    objective = "Analyze satellite constellation deorbit protocols."
    session_store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    # Pass 1: C1 is KEEP (P1); C2 violates hard constraint and is DROPPED
    p1_gen = make_normal_generate_response(
        diagnosis={"central_problem": "Deorbit disposal", "search_profile": "propulsion vs passive", "priority_dimensions": ["propulsive burns"]},
        candidates=[
            make_candidate("C1", mechanism="Dedicated perigee-lowering chemical propulsion burn"),
            make_candidate("C2", mechanism="Atmospheric drag sail deployment with prohibited toxic propellant"),
        ],
    )
    p1_sel = make_normal_select_response([
        make_selection("C1", disposition="KEEP"),
        make_selection("C2", disposition="DROP", admissible=False, constraint_failures=["PROHIBITED_TOXIC_PROPELLANT"], reason="Hard constraint violation"),
    ])
    provider_p1 = ScriptedTestProvider({
        "EXPLORE_GENERATE": deque([p1_gen]),
        "EXPLORE_SELECT": deque([p1_sel]),
    })
    res1 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="normal"), session_store=session_store, provider=provider_p1, trace_root=trace_root)
    session_id = res1.session_id

    # Verify territory excludes the constraint-failed C2
    session = session_store.load(session_id)
    territory = build_prior_territory(session)
    assert len(territory) == 1
    assert territory[0].source_kind == "survivor"
    assert territory[0].source_id == "P1"

    # Pass 2 (360): Clean non-toxic drag sail is proposed -> KEEP (P2)
    p2_gen = make_360_generate_response(
        prior_summary=make_prior_summary(dominant_mechanisms=["Chemical propulsion burn"]),
        diagnosis={"central_problem": "Deorbit disposal", "search_profile": "passive drag", "priority_dimensions": ["drag sails"]},
        candidates=[
            make_candidate("C1", mechanism="Passive deployable polyimide drag sail without propellant"),
        ],
    )
    p2_sel = make_360_select_response([
        make_selection("C1", disposition="KEEP", admissible=True, constraint_failures=[], standalone_quality="strong", marginal_contribution="high", reason="Clean passive drag mechanism compliant with all constraints"),
    ])
    provider_p2 = ScriptedTestProvider({
        "EXPLORE_360_GENERATE": deque([p2_gen]),
        "EXPLORE_360_SELECT": deque([p2_sel]),
    })
    res2 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="360", session_id=session_id), session_store=session_store, provider=provider_p2, trace_root=trace_root)

    assert res2.outcome == "OK"
    assert len(res2.kept) == 1
    assert res2.kept[0].identity.p_id == "P2"
    assert res2.kept[0].identity.identity_core.mechanism == "Passive deployable polyimide drag sail without propellant"


# ─────────────────────────────────────────────────────────────────────────────
# 360-I: Call A Produces Prior Summary Rather Than Receiving It
# ─────────────────────────────────────────────────────────────────────────────


class CapturingScriptedProvider(ScriptedTestProvider):
    """Provider that captures prompts for contract verification."""

    def __init__(self, queues: dict[str, deque[ProviderResult]]):
        super().__init__(queues)
        self.captured_prompts: list[tuple[str, str]] = []

    def complete(self, prompt: str, *, stage: str, invocation_id: str) -> ProviderResult:
        self.captured_prompts.append((stage, prompt))
        return super().complete(prompt, stage=stage, invocation_id=invocation_id)


def test_360_i_call_a_produces_prior_summary(tmp_path: Path) -> None:
    """360-I: Call A receives raw meaningful territory, produces PriorSummary, and trace records prior-summary.json."""
    source = load_fixture("360i")
    objective = "Analyze heterogeneous chiplet thermal management."
    session_store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    # Pass 1 (NORMAL)
    p1_gen = make_normal_generate_response(
        diagnosis={"central_problem": "Chiplet thermal hotspots", "search_profile": "microfluidics", "priority_dimensions": ["cooling channels"]},
        candidates=[make_candidate("C1", mechanism="Embedded microfluidic interposer cooling channels")],
    )
    p1_sel = make_normal_select_response([make_selection("C1", disposition="KEEP")])
    provider_p1 = CapturingScriptedProvider({
        "EXPLORE_GENERATE": deque([p1_gen]),
        "EXPLORE_SELECT": deque([p1_sel]),
    })
    res1 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="normal"), session_store=session_store, provider=provider_p1, trace_root=trace_root)
    session_id = res1.session_id

    # Verify NORMAL trace did NOT write prior-summary.json
    run1_dir = trace_root / res1.run_id
    assert not (run1_dir / "prior-summary.json").exists()

    # Pass 2 (360)
    expected_prior_summary = make_prior_summary(
        dominant_mechanisms=["Embedded microfluidic interposer cooling channels"],
        dominant_boundaries=["silicon interposer"],
        residual_gap_hypotheses=["Thermal gradient-aware task scheduling"],
    )
    p2_gen = make_360_generate_response(
        prior_summary=expected_prior_summary,
        diagnosis={"central_problem": "Chiplet thermal hotspots", "search_profile": "workload dispatch", "priority_dimensions": ["scheduler"]},
        candidates=[make_candidate("C1", mechanism="Thermal gradient-aware workload dispatch")],
    )
    p2_sel = make_360_select_response([make_selection("C1", disposition="KEEP")])
    provider_p2 = CapturingScriptedProvider({
        "EXPLORE_360_GENERATE": deque([p2_gen]),
        "EXPLORE_360_SELECT": deque([p2_sel]),
    })
    res2 = run_explore(PerspectiveRequest(source=source, objective=objective, mode="360", session_id=session_id), session_store=session_store, provider=provider_p2, trace_root=trace_root)

    # 1. Verify Call A prompt: contains raw meaningful territory, does NOT contain precomputed PriorSummary
    gen_call = next(p for s, p in provider_p2.captured_prompts if s == "EXPLORE_360_GENERATE")
    assert "Meaningful explored territory history" in gen_call
    assert "Embedded microfluidic interposer cooling channels" in gen_call
    assert "Dominant mechanisms:" not in gen_call  # Prior summary is not precomputed in Call A prompt

    # 2. Verify Call B prompt: received the PriorSummary produced by Call A
    sel_call = next(p for s, p in provider_p2.captured_prompts if s == "EXPLORE_360_SELECT")
    assert "Prior summary & residual hypotheses" in sel_call
    assert "Embedded microfluidic interposer cooling channels" in sel_call
    assert "Thermal gradient-aware task scheduling" in sel_call

    # 3. Verify 360 trace wrote prior-summary.json
    run2_dir = trace_root / res2.run_id
    prior_summary_file = run2_dir / "prior-summary.json"
    assert prior_summary_file.exists()
    saved_summary = json.loads(prior_summary_file.read_text(encoding="utf-8"))
    assert saved_summary["dominant_mechanisms"] == ["Embedded microfluidic interposer cooling channels"]
    assert saved_summary["residual_gap_hypotheses"] == ["Thermal gradient-aware task scheduling"]


# ─────────────────────────────────────────────────────────────────────────────
# Territory reconstruction unit tests
# ─────────────────────────────────────────────────────────────────────────────


def test_build_prior_territory_classification() -> None:
    """Verify all 4 source kinds are correctly derived and non-qualifying entries are excluded."""
    # Construct a session with various candidate types
    cand_keep = make_candidate("C1", mechanism="Mech 1")
    cand_merge = make_candidate("C2", mechanism="Mech 2")
    cand_borderline = make_candidate("C3", mechanism="Mech 3")
    cand_drop_strong = make_candidate("C4", mechanism="Mech 4")
    cand_drop_weak = make_candidate("C5", mechanism="Mech 5")
    cand_constraint_fail = make_candidate("C6", mechanism="Mech 6")

    cands = [
        PerspectiveCandidate.from_dict(c)
        for c in [cand_keep, cand_merge, cand_borderline, cand_drop_strong, cand_drop_weak, cand_constraint_fail]
    ]

    selections = [
        SelectionRecord.from_dict(make_selection("C1", disposition="KEEP", standalone_quality="strong", marginal_contribution="high")),
        SelectionRecord.from_dict(make_selection("C2", disposition="MERGE", merge_target={"kind": "candidate", "target_id": "C1"}, standalone_quality="borderline", marginal_contribution="low")),
        SelectionRecord.from_dict(make_selection("C3", disposition="BORDERLINE", standalone_quality="borderline", marginal_contribution="medium")),
        SelectionRecord.from_dict(make_selection("C4", disposition="DROP", standalone_quality="strong", marginal_contribution="none")),
        SelectionRecord.from_dict(make_selection("C5", disposition="DROP", standalone_quality="weak", marginal_contribution="none")),
        SelectionRecord.from_dict(make_selection("C6", disposition="DROP", admissible=False, constraint_failures=["HARD_FAIL"], standalone_quality="strong", marginal_contribution="none")),
    ]

    pass_record = PassRecord(
        pass_id="pass-1",
        mode="normal",
        created_at="2026-08-24T00:00:00Z",
        diagnosis=Diagnosis(central_problem="test", search_profile="test", priority_dimensions=[]),
        candidates=cands,
        selections=selections,
        kept_p_ids=["P1"],
        provider_invocation_ids=["inv-1"],
        trace_ref="run-1",
    )

    session = PerspectiveSession(
        session_id="sess-1",
        source_hash="hash",
        objective="obj",
        constraint_ledger=ConstraintLedger(),
        next_p_number=2,
        perspectives={"P1": PerspectiveState(
            identity=PerspectiveIdentity(p_id="P1", candidate_id="C1", identity_core=cands[0].semantic_core),
            current_version=1,
            epistemics=cands[0].epistemics,
            deep_refs=[],
        )},
        passes=[pass_record],
        deep_runs=[],
    )

    territory = build_prior_territory(session)

    # Expected 4 entries: survivor, meaningful_merge, borderline, strong_redundant_drop
    assert len(territory) == 4

    kinds = [e.source_kind for e in territory]
    assert kinds == ["survivor", "meaningful_merge", "borderline", "strong_redundant_drop"]

    survivor = next(e for e in territory if e.source_kind == "survivor")
    assert survivor.source_id == "P1"
    assert survivor.disposition == "KEEP"

    merge = next(e for e in territory if e.source_kind == "meaningful_merge")
    assert merge.source_id == "C2"
    assert merge.disposition == "MERGE"

    borderline = next(e for e in territory if e.source_kind == "borderline")
    assert borderline.source_id == "C3"
    assert borderline.disposition == "BORDERLINE"

    drop = next(e for e in territory if e.source_kind == "strong_redundant_drop")
    assert drop.source_id == "C4"
    assert drop.disposition == "DROP"

    # C5 (weak) and C6 (constraint fail) must NOT be present
    assert not any(e.source_id == "C5" for e in territory)
    assert not any(e.source_id == "C6" for e in territory)


def test_no_prose_reason_parsing() -> None:
    """Verify that territory derivation depends only on structured fields, not prose keywords."""
    cand = PerspectiveCandidate.from_dict(make_candidate("C1", mechanism="Mech 1"))
    
    # Candidate with deceptive reason prose saying "MERGE" but disposition is DROP with weak quality
    sel_deceptive = SelectionRecord.from_dict(make_selection(
        "C1",
        disposition="DROP",
        standalone_quality="weak",
        marginal_contribution="none",
        reason="We should definitely MERGE this survivor because it is a KEEP",
    ))

    pass_record = PassRecord(
        pass_id="pass-1",
        mode="normal",
        created_at="2026-08-24T00:00:00Z",
        diagnosis=Diagnosis(central_problem="test", search_profile="test", priority_dimensions=[]),
        candidates=[cand],
        selections=[sel_deceptive],
        kept_p_ids=[],
        provider_invocation_ids=[],
        trace_ref="run-1",
    )

    session = PerspectiveSession(
        session_id="sess-1",
        source_hash="hash",
        objective="obj",
        constraint_ledger=ConstraintLedger(),
        next_p_number=1,
        perspectives={},
        passes=[pass_record],
        deep_runs=[],
    )

    territory = build_prior_territory(session)
    assert len(territory) == 0  # Not included because structured fields indicate weak DROP


def test_prior_summary_and_territory_serialization() -> None:
    """Verify serialization round-trips for 360 data structures."""
    summary = PriorSummary(
        dominant_mechanisms=["m1", "m2"],
        dominant_boundaries=["b1"],
        dominant_agency_models=["a1"],
        dominant_timescales=["t1"],
        shared_assumptions=["s1"],
        residual_gap_hypotheses=["g1", "g2"],
    )
    summary_dict = summary.to_dict()
    summary_back = PriorSummary.from_dict(summary_dict)
    assert summary_back == summary

    entry = ExploredTerritoryEntry(
        semantic_core=SemanticCore(central_problem="cp", mechanism="m", load_bearing_claim="lbc"),
        source_kind="meaningful_merge",
        source_id="C1",
        source_pass_id="pass-1",
        disposition="MERGE",
        reason="Merged due to overlap",
    )
    entry_dict = entry.to_dict()
    entry_back = ExploredTerritoryEntry.from_dict(entry_dict)
    assert entry_back == entry

    rendered_terr = render_explored_territory([entry])
    assert "[MEANINGFUL_MERGE]" in rendered_terr
    assert "Mechanism: m" in rendered_terr

    rendered_sum = render_prior_summary(summary)
    assert "m1, m2" in rendered_sum
    assert "g1, g2" in rendered_sum


def test_build_prior_territory_merge_target_validation() -> None:
    """Verify that MERGE target existence is strictly enforced by namespace.

    - candidate target must exist in that PassRecord's candidate IDs and not be self
    - perspective target must exist in session.perspectives
    - non-existent candidate target, self candidate target, and non-existent perspective target do not enter territory
    """
    cand1 = make_candidate("C1", mechanism="Mech 1")
    cand_valid_cand = make_candidate("C2", mechanism="Mech 2")
    cand_invalid_cand = make_candidate("C3", mechanism="Mech 3")
    cand_self_cand = make_candidate("C4", mechanism="Mech 4")
    cand_valid_persp = make_candidate("C5", mechanism="Mech 5")
    cand_invalid_persp = make_candidate("C6", mechanism="Mech 6")

    cands = [
        PerspectiveCandidate.from_dict(c)
        for c in [
            cand1,
            cand_valid_cand,
            cand_invalid_cand,
            cand_self_cand,
            cand_valid_persp,
            cand_invalid_persp,
        ]
    ]

    selections = [
        SelectionRecord.from_dict(make_selection(
            "C1", disposition="KEEP", standalone_quality="strong", marginal_contribution="high"
        )),
        SelectionRecord.from_dict(make_selection(
            "C2", disposition="MERGE", merge_target={"kind": "candidate", "target_id": "C1"}, standalone_quality="strong", marginal_contribution="low"
        )),
        SelectionRecord.from_dict(make_selection(
            "C3", disposition="MERGE", merge_target={"kind": "candidate", "target_id": "C999"}, standalone_quality="strong", marginal_contribution="low"
        )),
        SelectionRecord.from_dict(make_selection(
            "C4", disposition="MERGE", merge_target={"kind": "candidate", "target_id": "C4"}, standalone_quality="strong", marginal_contribution="low"
        )),
        SelectionRecord.from_dict(make_selection(
            "C5", disposition="MERGE", merge_target={"kind": "perspective", "target_id": "P1"}, standalone_quality="strong", marginal_contribution="low"
        )),
        SelectionRecord.from_dict(make_selection(
            "C6", disposition="MERGE", merge_target={"kind": "perspective", "target_id": "P999"}, standalone_quality="strong", marginal_contribution="low"
        )),
    ]

    pass_record = PassRecord(
        pass_id="pass-1",
        mode="normal",
        created_at="2026-08-24T00:00:00Z",
        diagnosis=Diagnosis(central_problem="test", search_profile="test", priority_dimensions=[]),
        candidates=cands,
        selections=selections,
        kept_p_ids=["P1"],
        provider_invocation_ids=["inv-1"],
        trace_ref="run-1",
    )

    session = PerspectiveSession(
        session_id="sess-1",
        source_hash="hash",
        objective="obj",
        constraint_ledger=ConstraintLedger(),
        next_p_number=2,
        perspectives={
            "P1": PerspectiveState(
                identity=PerspectiveIdentity(p_id="P1", candidate_id="C1", identity_core=cands[0].semantic_core),
                current_version=1,
                epistemics=cands[0].epistemics,
                deep_refs=[],
            )
        },
        passes=[pass_record],
        deep_runs=[],
    )

    territory = build_prior_territory(session)

    # C1 is KEEP -> survivor (source_id P1)
    # C2 is MERGE with candidate C1 (exists) -> meaningful_merge (source_id C2)
    # C3 is MERGE with candidate C999 (does not exist) -> excluded
    # C4 is MERGE with candidate C4 (self) -> excluded
    # C5 is MERGE with perspective P1 (exists in session.perspectives) -> meaningful_merge (source_id C5)
    # C6 is MERGE with perspective P999 (does not exist in session.perspectives) -> excluded
    assert len(territory) == 3
    source_ids = [e.source_id for e in territory]
    assert source_ids == ["P1", "C2", "C5"]

    # Verify invalid entries are absent
    assert not any(e.source_id == "C3" for e in territory)
    assert not any(e.source_id == "C4" for e in territory)
    assert not any(e.source_id == "C6" for e in territory)
