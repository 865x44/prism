"""Tests for Perspective Core v0 RIFT exploration (Wave 4).

Covers R1-R4 scenarios and execution contract invariants:
- R1: decorative strangeness → DROP
- R2: transferred mechanism + return path → KEEP
- R3: distant analogy violating source constraint → DROP
- R4: free-lane candidate without operator ID → allowed
- Schema repair on RIFT_GENERATE and RIFT_SELECT
- Exhausted repair failure raises ValueError
- Source hash mismatch fails closed
- Objective immutability fails closed
- Session continuity and monotonic P-ID allocation (NORMAL -> RIFT -> RIFT)
- Complete trace fidelity and relative trace references
- Bounded NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS on empty candidates
- BORDERLINE persisted in pass record without P-ID / rendering
- MERGE target validation (candidate and perspective targets)
- Inadmissible KEEP validation failure
- CLI integration with injected provider
- Prompt asset verification for donor-vocabulary ablation and binding constraints
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from prism.perspective_core.cli import main
from prism.perspective_core.models import (
    ConstraintEntry,
    ConstraintLedger,
    PerspectiveRequest,
    ProviderResult,
)
from prism.perspective_core.prompts import prompt_path
from prism.perspective_core.provider import ScriptedProvider, TransportError
from prism.perspective_core.rift import run_rift
from prism.perspective_core.session import SessionStore
from prism.perspective_core.trace import TraceWriter

FIXTURES_DIR = Path(__file__).parent / "perspective_core" / "fixtures" / "rift"


def load_fixture(scenario: str) -> str:
    """Load a RIFT scenario fixture source (e.g. 'r1')."""
    return (FIXTURES_DIR / f"{scenario}_source.md").read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Test Provider & Helpers
# ─────────────────────────────────────────────────────────────────────────────


class ScriptedTestProvider(ScriptedProvider):
    """Test provider that validates stage sequence without strict invocation_id checking."""

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

        return result


def make_scripted_factory(responses_by_stage: dict[str, list[ProviderResult]]):
    """Create a provider factory for CLI injection."""

    def factory():
        return ScriptedTestProvider(responses_by_stage)

    return factory


def make_rift_generate_response(
    diagnosis: dict[str, Any],
    candidates: list[dict[str, Any]],
    invocation_id: str = "gen-rift-1",
) -> ProviderResult:
    """Create a RIFT_GENERATE response."""
    return ProviderResult(
        invocation_id=invocation_id,
        stage="RIFT_GENERATE",
        raw_text=json.dumps({"diagnosis": diagnosis, "candidates": candidates}),
        model="test-model",
        transport="scripted",
        duration_ms=100,
        exit_code=0,
    )


def make_rift_select_response(
    selections: list[dict[str, Any]], invocation_id: str = "sel-rift-1"
) -> ProviderResult:
    """Create a RIFT_SELECT response."""
    return ProviderResult(
        invocation_id=invocation_id,
        stage="RIFT_SELECT",
        raw_text=json.dumps(selections),
        model="test-model",
        transport="scripted",
        duration_ms=100,
        exit_code=0,
    )


def make_candidate(
    candidate_id: str = "C1",
    mechanism: str = "test transferred mechanism",
    central_problem: str = "test problem",
    shift: str = "test shift",
    operator_ids: list[str] | None = None,
    dimension_changed: str = "test dimension",
    consequence_chain: list[str] | None = None,
    why_it_matters: str = "test why it matters",
    **overrides: Any,
) -> dict[str, Any]:
    """Create a minimal candidate dictionary for RIFT."""
    base = {
        "semantic_core": {
            "central_problem": central_problem,
            "mechanism": mechanism,
            "load_bearing_claim": "test claim",
            "central_object": None,
            "unit_of_analysis": None,
            "system_boundary": None,
            "agency_model": None,
            "temporal_logic": None,
            "key_constraint": None,
            "downstream_consequences": ["consequence 1"],
        },
        "preserved": ["core problem context"],
        "default_frame": "default standard frame",
        "blind_spot": "test blind spot",
        "operator_ids": operator_ids if operator_ids is not None else [],
        "shift": shift,
        "perspective": f"Reframing around {mechanism}",
        "new_consequences": ["novel consequence"],
        "return_path": {
            "dimension_changed": dimension_changed,
            "consequence_chain": consequence_chain or ["step 1", "step 2"],
            "why_it_matters": why_it_matters,
        },
        "epistemics": {
            "supported": ["source basis"],
            "inferred": ["structural link"],
            "speculative": [],
            "unknown": [],
            "break_condition": ["when assumptions fail"],
        },
    }
    base.update(overrides)
    return base


def make_selection(
    candidate_id: str,
    disposition: str = "KEEP",
    merge_target: dict[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    """Create a minimal selection record dictionary for RIFT."""
    base = {
        "candidate_id": candidate_id,
        "admissible": True,
        "constraint_failures": [],
        "structurally_distinct": True,
        "novelty_dimensions": ["mechanism", "agency_distribution"],
        "nearest_candidate_id": None,
        "nearest_existing_p_id": None,
        "standalone_quality": "strong",
        "marginal_contribution": "high",
        "disposition": disposition,
        "merge_target": merge_target,
        "reason": "Test selection reason",
    }
    base.update(overrides)
    return base


def make_diagnosis() -> dict[str, Any]:
    """Create a minimal diagnosis dictionary."""
    return {
        "central_problem": "Test central problem",
        "search_profile": "High conceptual distance cross-domain structural transfer",
        "priority_dimensions": ["mechanism", "agency_distribution", "temporal_logic"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# R1: Decorative Strangeness → DROP
# ─────────────────────────────────────────────────────────────────────────────


def test_r1_decorative_strangeness_drop(tmp_path: Path) -> None:
    """R1: Decorative metaphor without new mechanism fails donor ablation and is DROPped."""
    source_text = load_fixture("r1")
    store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    # C1 is a decorative metaphor ("Quantum Superposition Incident Field")
    # Ablation reveals it's just standard log inspection with quantum jargon.
    candidates = [
        make_candidate(
            "C1",
            mechanism="Quantum wave function collapse of microservice status registers",
            central_problem="Microservice outage diagnosis",
            shift="Treating services as quantum superposition states",
            operator_ids=["OP_CROSS_DOMAIN_TRANSFER"],
            dimension_changed="Vocabulary",
            consequence_chain=["Read logs with quantum terms"],
            why_it_matters="No practical difference in outage resolution",
        )
    ]

    selections = [
        make_selection(
            "C1",
            disposition="DROP",
            structurally_distinct=False,
            standalone_quality="weak",
            marginal_contribution="none",
            reason=(
                "Fails donor-vocabulary ablation. Removing quantum terminology leaves only "
                "standard log inspection and post-mortem review. No novel mechanism or actionable return path."
            ),
        )
    ]

    provider = ScriptedTestProvider({
        "RIFT_GENERATE": [make_rift_generate_response(make_diagnosis(), candidates)],
        "RIFT_SELECT": [make_rift_select_response(selections)],
    })

    req = PerspectiveRequest(
        source=source_text,
        objective="Find novel structural framings for recurring outage incidents",
        mode="rift",
    )

    result = run_rift(req, session_store=store, provider=provider, trace_root=trace_root)

    assert result.outcome == "NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS"
    assert len(result.kept) == 0
    assert result.rendered == ""

    # Verify session has no perspectives
    session = store.load(result.session_id)
    assert len(session.perspectives) == 0
    assert session.next_p_number == 1

    # Verify DROP is recorded in pass record
    assert len(session.passes) == 1
    assert session.passes[0].mode == "rift"
    assert len(session.passes[0].selections) == 1
    assert session.passes[0].selections[0].disposition == "DROP"
    assert "ablation" in session.passes[0].selections[0].reason


# ─────────────────────────────────────────────────────────────────────────────
# R2: Transferred Mechanism + Return Path → KEEP
# ─────────────────────────────────────────────────────────────────────────────


def test_r2_transferred_mechanism_keep(tmp_path: Path) -> None:
    """R2: Cross-domain transferred mechanism with concrete return path passes ablation and is KEEPt."""
    source_text = load_fixture("r2")
    store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    # C1 transfers immune clearance kinetics to documentation decay:
    # Commit-velocity-dependent decay timer triggers automated verification probes in CI.
    candidates = [
        make_candidate(
            "C1",
            mechanism="Commit-velocity-dependent documentation clearance half-life with CI verification probes",
            central_problem="Documentation staleness and decay in fast-moving repos",
            shift="From reactive periodic human audit to proactive commit-velocity decay triggers",
            operator_ids=["OP_CROSS_DOMAIN_TRANSFER"],
            dimension_changed="Verification trigger mechanism",
            consequence_chain=[
                "Each doc node assigned decay half-life inversely proportional to touched module commit rate",
                "Expired doc nodes trigger automated assertion tests during PR builds",
                "Outdated docs block deployment until validated by author",
            ],
            why_it_matters="Eliminates documentation decay continuously without manual company-wide audit drives",
        )
    ]

    selections = [
        make_selection(
            "C1",
            disposition="KEEP",
            admissible=True,
            constraint_failures=[],
            structurally_distinct=True,
            standalone_quality="strong",
            marginal_contribution="high",
            reason=(
                "Passes donor-vocabulary ablation. Removing biological immune terms leaves a concrete "
                "commit-velocity decay algorithm and CI probe mechanism with clear operational return path."
            ),
        )
    ]

    provider = ScriptedTestProvider({
        "RIFT_GENERATE": [make_rift_generate_response(make_diagnosis(), candidates)],
        "RIFT_SELECT": [make_rift_select_response(selections)],
    })

    req = PerspectiveRequest(
        source=source_text,
        objective="Solve documentation staleness",
        mode="rift",
    )

    result = run_rift(req, session_store=store, provider=provider, trace_root=trace_root)

    assert result.outcome == "OK"
    assert len(result.kept) == 1
    assert result.kept[0].identity.p_id == "P1"
    assert result.kept[0].identity.identity_core.mechanism == (
        "Commit-velocity-dependent documentation clearance half-life with CI verification probes"
    )
    assert "P1" in result.rendered
    assert "From reactive periodic human audit to proactive commit-velocity decay triggers" in result.rendered
    assert (
        "Commit-velocity-dependent documentation clearance half-life with CI verification probes"
        in result.rendered
    )
    assert (
        "Eliminates documentation decay continuously without manual company-wide audit drives"
        in result.rendered
    )

    # Verify session updated
    session = store.load(result.session_id)
    assert len(session.perspectives) == 1
    assert "P1" in session.perspectives
    assert session.next_p_number == 2


# ─────────────────────────────────────────────────────────────────────────────
# R3: Distant Analogy Violating Source Constraint → DROP
# ─────────────────────────────────────────────────────────────────────────────


def test_r3_constraint_violation_drop(tmp_path: Path) -> None:
    """R3: Distant transfer candidate violating hard source constraint is marked inadmissible and DROPped."""
    source_text = load_fixture("r3")
    store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    # Ledger with hard offline constraint
    ledger = ConstraintLedger(
        entries=[
            ConstraintEntry(
                constraint_id="C_OFFLINE",
                value="Sensor nodes must operate completely air-gapped with zero wireless transmission or cloud telemetry",
                kind="hard",
                status="active",
            )
        ]
    )

    # Candidate proposes continuous cloud swarm telemetry
    candidates = [
        make_candidate(
            "C1",
            mechanism="Cloud-coordinated swarm gradient optimization with high-frequency telemetry relay",
            central_problem="Sensor power optimization",
            shift="Offloading local optimization to central server swarm coordinator",
        )
    ]

    selections = [
        make_selection(
            "C1",
            disposition="DROP",
            admissible=False,
            constraint_failures=[
                "Violates hard constraint C_OFFLINE: requires high-frequency wireless telemetry to cloud"
            ],
            structurally_distinct=True,
            standalone_quality="weak",
            marginal_contribution="none",
            reason="Inadmissible: violates mandatory air-gapped / zero wireless transmission constraint.",
        )
    ]

    provider = ScriptedTestProvider({
        "RIFT_GENERATE": [make_rift_generate_response(make_diagnosis(), candidates)],
        "RIFT_SELECT": [make_rift_select_response(selections)],
    })

    req = PerspectiveRequest(
        source=source_text,
        objective="Optimize remote sensor battery life",
        mode="rift",
        constraint_ledger=ledger,
    )

    result = run_rift(req, session_store=store, provider=provider, trace_root=trace_root)

    assert result.outcome == "NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS"
    assert len(result.kept) == 0

    session = store.load(result.session_id)
    assert len(session.perspectives) == 0
    assert len(session.passes[0].selections[0].constraint_failures) == 1
    assert session.passes[0].selections[0].admissible is False


# ─────────────────────────────────────────────────────────────────────────────
# R4: Operator-Free Free-Lane Candidate → Allowed & Kept
# ─────────────────────────────────────────────────────────────────────────────


def test_r4_free_lane_candidate_allowed(tmp_path: Path) -> None:
    """R4: Candidate with empty operator_ids (free-lane) is valid, parsed, and registered as KEEP."""
    source_text = load_fixture("r4")
    store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    # Candidate without any operator ID (free-lane search)
    candidates = [
        make_candidate(
            "C1",
            mechanism="Downstream queue backpressure metering via dynamic green-wave wavefront inversion",
            central_problem="Cascading traffic gridlock across urban intersection grids",
            shift="Shifting flow control from upstream supply throttling to downstream storage capacity reservations",
            operator_ids=[],  # Explicit free-lane
            dimension_changed="Control flow directionality",
            consequence_chain=[
                "Downstream detector signals block saturation",
                "Upstream green signal truncated before queue spills into intersection",
                "Cross-street flow preserved without cascade lock",
            ],
            why_it_matters="Prevents full-grid deadlock with zero physical infrastructure changes",
        )
    ]

    selections = [
        make_selection(
            "C1",
            disposition="KEEP",
            admissible=True,
            constraint_failures=[],
            structurally_distinct=True,
            standalone_quality="strong",
            marginal_contribution="high",
            reason="High-quality free-lane perspective with concrete physical mechanism and clear return path.",
        )
    ]

    provider = ScriptedTestProvider({
        "RIFT_GENERATE": [make_rift_generate_response(make_diagnosis(), candidates)],
        "RIFT_SELECT": [make_rift_select_response(selections)],
    })

    req = PerspectiveRequest(
        source=source_text,
        objective="Prevent urban cascade gridlock",
        mode="rift",
    )

    result = run_rift(req, session_store=store, provider=provider, trace_root=trace_root)

    assert result.outcome == "OK"
    assert len(result.kept) == 1
    assert result.kept[0].identity.p_id == "P1"
    assert "P1" in result.rendered

    session = store.load(result.session_id)
    assert "P1" in session.perspectives
    assert session.perspectives["P1"].identity.p_id == "P1"
    assert session.perspectives["P1"].identity.candidate_id == "C1"

    # Verify candidate persisted with empty operator_ids in PassRecord history
    assert len(session.passes) == 1
    assert len(session.passes[0].candidates) == 1
    assert session.passes[0].candidates[0].candidate_id == "C1"
    assert session.passes[0].candidates[0].operator_ids == []
    assert session.passes[0].kept_p_ids == ["P1"]
    assert session.passes[0].selections[0].disposition == "KEEP"


# ─────────────────────────────────────────────────────────────────────────────
# Schema Repair Tests (Call A & Call B)
# ─────────────────────────────────────────────────────────────────────────────


def test_rift_schema_repair_generate(tmp_path: Path) -> None:
    """Schema repair recovers from malformed RIFT_GENERATE response via SCHEMA_REPAIR:RIFT_GENERATE."""
    source_text = load_fixture("r2")
    store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    candidates = [
        make_candidate(
            "C1",
            mechanism="Commit-velocity decay timers",
            central_problem="Documentation staleness",
        )
    ]
    selections = [make_selection("C1", disposition="KEEP")]

    # Malformed generate response then valid repair response
    bad_generate = ProviderResult(
        invocation_id="gen-bad",
        stage="RIFT_GENERATE",
        raw_text="NOT JSON AT ALL {{{",
        model="test-model",
        transport="scripted",
        duration_ms=50,
        exit_code=0,
    )
    good_generate_repair = ProviderResult(
        invocation_id="gen-repair",
        stage="SCHEMA_REPAIR:RIFT_GENERATE",
        raw_text=json.dumps({"diagnosis": make_diagnosis(), "candidates": candidates}),
        model="test-model",
        transport="scripted",
        duration_ms=100,
        exit_code=0,
    )
    select_res = make_rift_select_response(selections, invocation_id="sel-1")

    provider = ScriptedTestProvider({
        "RIFT_GENERATE": [bad_generate],
        "SCHEMA_REPAIR:RIFT_GENERATE": [good_generate_repair],
        "RIFT_SELECT": [select_res],
    })

    req = PerspectiveRequest(
        source=source_text,
        objective="Solve documentation staleness",
        mode="rift",
    )

    result = run_rift(req, session_store=store, provider=provider, trace_root=trace_root)
    assert result.outcome == "OK"
    assert len(result.kept) == 1

    # Verify provider invocations in trace record both the failed and repair invocations
    session = store.load(result.session_id)
    invocations = session.passes[0].provider_invocation_ids
    assert "gen-bad" in invocations
    assert "gen-repair" in invocations
    assert "sel-1" in invocations


def test_rift_schema_repair_select(tmp_path: Path) -> None:
    """Schema repair recovers from malformed RIFT_SELECT response via SCHEMA_REPAIR:RIFT_SELECT."""
    source_text = load_fixture("r2")
    store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    candidates = [
        make_candidate(
            "C1",
            mechanism="Commit-velocity decay timers",
            central_problem="Documentation staleness",
        )
    ]
    selections = [make_selection("C1", disposition="KEEP")]

    gen_res = make_rift_generate_response(make_diagnosis(), candidates, invocation_id="gen-1")
    bad_select = ProviderResult(
        invocation_id="sel-bad",
        stage="RIFT_SELECT",
        raw_text="INVALID SELECTIONS ARRAY",
        model="test-model",
        transport="scripted",
        duration_ms=50,
        exit_code=0,
    )
    good_select_repair = ProviderResult(
        invocation_id="sel-repair",
        stage="SCHEMA_REPAIR:RIFT_SELECT",
        raw_text=json.dumps(selections),
        model="test-model",
        transport="scripted",
        duration_ms=100,
        exit_code=0,
    )

    provider = ScriptedTestProvider({
        "RIFT_GENERATE": [gen_res],
        "RIFT_SELECT": [bad_select],
        "SCHEMA_REPAIR:RIFT_SELECT": [good_select_repair],
    })

    req = PerspectiveRequest(
        source=source_text,
        objective="Solve documentation staleness",
        mode="rift",
    )

    result = run_rift(req, session_store=store, provider=provider, trace_root=trace_root)
    assert result.outcome == "OK"
    assert len(result.kept) == 1

    session = store.load(result.session_id)
    invocations = session.passes[0].provider_invocation_ids
    assert "gen-1" in invocations
    assert "sel-bad" in invocations
    assert "sel-repair" in invocations


def test_rift_exhausted_repair_fails(tmp_path: Path) -> None:
    """When both primary call and schema repair fail, ValueError is raised."""
    source_text = load_fixture("r2")
    store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    bad_1 = ProviderResult(
        invocation_id="gen-bad1",
        stage="RIFT_GENERATE",
        raw_text="BAD 1",
        model="test-model",
        transport="scripted",
        duration_ms=50,
        exit_code=0,
    )
    bad_2 = ProviderResult(
        invocation_id="gen-bad2",
        stage="SCHEMA_REPAIR:RIFT_GENERATE",
        raw_text="BAD 2",
        model="test-model",
        transport="scripted",
        duration_ms=50,
        exit_code=0,
    )

    provider = ScriptedTestProvider({
        "RIFT_GENERATE": [bad_1],
        "SCHEMA_REPAIR:RIFT_GENERATE": [bad_2],
    })

    req = PerspectiveRequest(
        source=source_text,
        objective="Solve documentation staleness",
        mode="rift",
    )

    with pytest.raises(ValueError, match="Stage RIFT_GENERATE failed after repair"):
        run_rift(req, session_store=store, provider=provider, trace_root=trace_root)


# ─────────────────────────────────────────────────────────────────────────────
# Session Integrity, Immutability & Monotonicity
# ─────────────────────────────────────────────────────────────────────────────


def test_rift_source_hash_mismatch_fails(tmp_path: Path) -> None:
    """RIFT run against existing session with modified source fails closed."""
    source_1 = load_fixture("r1")
    source_2 = load_fixture("r2")
    store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    session = store.create(session_id="sess-mismatch", source=source_1, objective="Same objective")

    provider = ScriptedTestProvider({})

    req = PerspectiveRequest(
        source=source_2,  # Different source text!
        objective="Same objective",
        mode="rift",
        session_id="sess-mismatch",
    )

    with pytest.raises(ValueError, match="Request source hash .* does not match stored session source hash"):
        run_rift(req, session_store=store, provider=provider, trace_root=trace_root)


def test_rift_objective_mismatch_fails(tmp_path: Path) -> None:
    """RIFT run against existing session with modified objective fails closed."""
    source = load_fixture("r1")
    store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    session = store.create(session_id="sess-obj-mismatch", source=source, objective="Initial objective")

    provider = ScriptedTestProvider({})

    req = PerspectiveRequest(
        source=source,
        objective="Changed objective!",
        mode="rift",
        session_id="sess-obj-mismatch",
    )

    with pytest.raises(ValueError, match="Request objective .* does not match immutable session objective"):
        run_rift(req, session_store=store, provider=provider, trace_root=trace_root)


def test_rift_session_continuity_monotonic_p_ids(tmp_path: Path) -> None:
    """Monotonic P-ID allocation across multiple passes in same session."""
    source = load_fixture("r2")
    store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    # Pass 1: RIFT generates P1
    c1 = make_candidate("C1", mechanism="Mechanism 1", central_problem="Problem 1")
    s1 = make_selection("C1", disposition="KEEP")

    provider1 = ScriptedTestProvider({
        "RIFT_GENERATE": [make_rift_generate_response(make_diagnosis(), [c1])],
        "RIFT_SELECT": [make_rift_select_response([s1])],
    })

    req1 = PerspectiveRequest(source=source, objective="Test objective", mode="rift", session_id="multi-pass")
    res1 = run_rift(req1, session_store=store, provider=provider1, trace_root=trace_root)
    assert res1.kept[0].identity.p_id == "P1"

    # Pass 2: RIFT generates P2
    c2 = make_candidate("C1", mechanism="Mechanism 2", central_problem="Problem 2")
    s2 = make_selection("C1", disposition="KEEP")

    provider2 = ScriptedTestProvider({
        "RIFT_GENERATE": [make_rift_generate_response(make_diagnosis(), [c2])],
        "RIFT_SELECT": [make_rift_select_response([s2])],
    })

    req2 = PerspectiveRequest(source=source, objective="Test objective", mode="rift", session_id="multi-pass")
    res2 = run_rift(req2, session_store=store, provider=provider2, trace_root=trace_root)
    assert res2.kept[0].identity.p_id == "P2"

    session = store.load("multi-pass")
    assert session.next_p_number == 3
    assert set(session.perspectives.keys()) == {"P1", "P2"}
    assert len(session.passes) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Trace Fidelity & Relative Trace Reference
# ─────────────────────────────────────────────────────────────────────────────


def test_rift_trace_artifacts_and_relative_ref(tmp_path: Path) -> None:
    """Verify all trace JSON artifacts are created and PassRecord contains relative trace ref."""
    source = load_fixture("r4")
    store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    candidates = [make_candidate("C1", mechanism="Flow metering", central_problem="Gridlock")]
    selections = [make_selection("C1", disposition="KEEP")]

    provider = ScriptedTestProvider({
        "RIFT_GENERATE": [make_rift_generate_response(make_diagnosis(), candidates)],
        "RIFT_SELECT": [make_rift_select_response(selections)],
    })

    req = PerspectiveRequest(source=source, objective="Test objective", mode="rift")
    result = run_rift(req, session_store=store, provider=provider, trace_root=trace_root)

    run_trace_dir = trace_root / result.run_id
    assert run_trace_dir.exists()

    expected_files = [
        "request.json",
        "constraints.json",
        "session-before.json",
        "diagnosis.json",
        "candidates.json",
        "selection.json",
        "validation.json",
        "session-after.json",
        "result.json",
        "provider-invocations.json",
    ]
    for filename in expected_files:
        assert (run_trace_dir / filename).exists(), f"Missing trace artifact: {filename}"

    session = store.load(result.session_id)
    assert session.passes[0].trace_ref == result.run_id


# ─────────────────────────────────────────────────────────────────────────────
# BORDERLINE & MERGE Dispositions
# ─────────────────────────────────────────────────────────────────────────────


def test_rift_borderline_persisted_without_p_id(tmp_path: Path) -> None:
    """BORDERLINE disposition is persisted in PassRecord but assigned NO P-ID and not rendered."""
    source = load_fixture("r2")
    store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    candidates = [make_candidate("C1", mechanism="Marginal mechanism", central_problem="Problem")]
    selections = [
        make_selection(
            "C1",
            disposition="BORDERLINE",
            admissible=True,
            constraint_failures=[],
            structurally_distinct=True,
            standalone_quality="borderline",
            marginal_contribution="low",
            reason="Borderline standalone quality, retained in internal history only.",
        )
    ]

    provider = ScriptedTestProvider({
        "RIFT_GENERATE": [make_rift_generate_response(make_diagnosis(), candidates)],
        "RIFT_SELECT": [make_rift_select_response(selections)],
    })

    req = PerspectiveRequest(source=source, objective="Test objective", mode="rift")
    result = run_rift(req, session_store=store, provider=provider, trace_root=trace_root)

    assert result.outcome == "NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS"
    assert len(result.kept) == 0
    assert result.rendered == ""

    session = store.load(result.session_id)
    assert len(session.perspectives) == 0
    assert len(session.passes[0].selections) == 1
    assert session.passes[0].selections[0].disposition == "BORDERLINE"


def test_rift_merge_target_handling(tmp_path: Path) -> None:
    """MERGE disposition with valid candidate merge target is persisted in PassRecord."""
    source = load_fixture("r1")
    store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    candidates = [
        make_candidate("C1", mechanism="Primary mechanism", central_problem="Problem"),
        make_candidate("C2", mechanism="Overlapping mechanism", central_problem="Problem"),
    ]
    selections = [
        make_selection("C1", disposition="KEEP"),
        make_selection(
            "C2",
            disposition="MERGE",
            merge_target={"kind": "candidate", "target_id": "C1"},
            structurally_distinct=False,
            reason="Merges into C1.",
        ),
    ]

    provider = ScriptedTestProvider({
        "RIFT_GENERATE": [make_rift_generate_response(make_diagnosis(), candidates)],
        "RIFT_SELECT": [make_rift_select_response(selections)],
    })

    req = PerspectiveRequest(source=source, objective="Test objective", mode="rift")
    result = run_rift(req, session_store=store, provider=provider, trace_root=trace_root)

    assert len(result.kept) == 1
    assert result.kept[0].identity.p_id == "P1"

    session = store.load(result.session_id)
    assert len(session.perspectives) == 1
    assert session.passes[0].selections[1].disposition == "MERGE"
    assert session.passes[0].selections[1].merge_target.target_id == "C1"


def test_rift_inadmissible_keep_fails_validation(tmp_path: Path) -> None:
    """Selection record marking inadmissible candidate as KEEP fails validation."""
    source = load_fixture("r1")
    store = SessionStore(tmp_path / "sessions")
    trace_root = tmp_path / "traces"

    candidates = [make_candidate("C1", mechanism="Mechanism", central_problem="Problem")]
    selections = [
        make_selection(
            "C1",
            disposition="KEEP",
            admissible=False,  # Contradiction: KEEP with admissible=False
            reason="Invalid KEEP",
        )
    ]

    provider = ScriptedTestProvider({
        "RIFT_GENERATE": [make_rift_generate_response(make_diagnosis(), candidates)],
        "RIFT_SELECT": [make_rift_select_response(selections)],
    })

    req = PerspectiveRequest(source=source, objective="Test objective", mode="rift")
    with pytest.raises(ValueError, match="INADMISSIBLE_KEEP"):
        run_rift(req, session_store=store, provider=provider, trace_root=trace_root)


# ─────────────────────────────────────────────────────────────────────────────
# CLI Integration
# ─────────────────────────────────────────────────────────────────────────────


def test_rift_cli_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI run command with --mode rift dispatches to RIFT and exits 0."""
    monkeypatch.chdir(tmp_path)

    source_file = tmp_path / "source.md"
    source_file.write_text(load_fixture("r2"), encoding="utf-8")

    candidates = [
        make_candidate(
            "C1",
            mechanism="Commit-velocity decay timers",
            central_problem="Documentation staleness",
        )
    ]
    selections = [make_selection("C1", disposition="KEEP")]

    responses = {
        "RIFT_GENERATE": [make_rift_generate_response(make_diagnosis(), candidates)],
        "RIFT_SELECT": [make_rift_select_response(selections)],
    }
    factory = make_scripted_factory(responses)

    exit_code = main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Solve documentation decay",
            "--mode",
            "rift",
            "--session",
            "cli-rift-session",
            "--trace-root",
            str(tmp_path / "traces"),
        ],
        provider_factory=factory,
    )

    assert exit_code == 0

    session_file = tmp_path / "prism-sessions" / "perspective-core" / "cli-rift-session" / "session.json"
    assert session_file.exists()
    session_data = json.loads(session_file.read_text(encoding="utf-8"))
    assert len(session_data["perspectives"]) == 1
    assert "P1" in session_data["perspectives"]
    assert session_data["passes"][0]["mode"] == "rift"


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Assets Inspection
# ─────────────────────────────────────────────────────────────────────────────


def test_rift_prompt_assets_integrity() -> None:
    """Verify RIFT prompt assets exist and contain mandatory clauses."""
    gen_path = prompt_path("rift_generate.md")
    sel_path = prompt_path("rift_select.md")
    rep_gen_path = prompt_path("rift_repair_generate.md")
    rep_sel_path = prompt_path("rift_repair_select.md")

    assert gen_path.exists()
    assert sel_path.exists()
    assert rep_gen_path.exists()
    assert rep_sel_path.exists()

    gen_text = gen_path.read_text(encoding="utf-8")
    sel_text = sel_path.read_text(encoding="utf-8")

    # Generate prompt clauses
    assert "Conceptual Distance" in gen_text
    assert "return path" in gen_text.lower()
    assert "Binding Constraints" in gen_text
    assert "free-lane" in gen_text.lower()

    # Selection prompt clauses
    assert "Donor-Vocabulary Ablation" in sel_text
    assert "decorative strangeness" in sel_text.lower() or "decorative metaphor" in sel_text.lower()
    assert "return path" in sel_text.lower()
    assert "KEEP requires" in sel_text
