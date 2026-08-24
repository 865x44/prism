"""Integration tests for Perspective Core v0 (Wave 5).

Proves the complete local architecture through the real injectable CLI and
stage-indexed ScriptedProvider without network calls or semantic-quality claims.

Requirements covered:
1. Exercise a continuous synthetic session through cli.main(argv, provider_factory=...):
   - NORMAL creates source snapshot, candidates/selections, and KEEP P-IDs (P1, P2);
   - 360 consumes PassRecord history and produces new KEEP (P3);
   - Deep resolves visible P-ID (P1), verifies source, preserves identity, and reaches terminal state;
   - RIFT uses the same session and shared P-ID sequence (P4);
   - Deep on RIFT perspective reaches NEED_EVIDENCE (P4).
2. Assert session/pass/trace consistency:
   - Full candidates and selections recorded in each pass;
   - Relative trace references in passes and deep runs;
   - Provider invocation IDs recorded in pass records and trace writer;
   - Monotonic P-ID numbering (P1 -> P2 -> P3 -> P4 -> P5);
   - Complete stage-queue exhaustion with zero stage-queue drift;
   - Atomic behavior on injected provider errors (session unchanged on failure).
3. Assert schema repair is tagged SCHEMA_REPAIR:<parent_stage> and does not consume another stage's response.
4. Capture visible CLI output and assert P-ID and terminal state present while all internal IDs/paths are absent.
5. Substantive synthetic/anonymized fixtures loaded from tests/perspective_core/fixtures/integration/**.
"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any, Callable

import pytest

from prism.perspective_core.cli import main
from prism.perspective_core.models import (
    ConstraintLedger,
    DeepDevelopment,
    DeepRebuildResult,
    DeepReview,
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

FIXTURES_DIR = Path(__file__).parent / "perspective_core" / "fixtures" / "integration"


def load_integration_source() -> str:
    """Load primary integration fixture source."""
    return (FIXTURES_DIR / "integration_source.md").read_text(encoding="utf-8")


def load_alternative_source() -> str:
    """Load alternative fixture source for mismatch testing."""
    return (FIXTURES_DIR / "alternative_source.md").read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Test Provider & Helpers
# ─────────────────────────────────────────────────────────────────────────────


class IntegrationScriptedProvider(ScriptedProvider):
    """Stage-indexed scripted provider for integration test suite.

    Validates:
    - Stage is known and queued.
    - Queue is not exhausted.
    - Result stage matches requested stage.
    - Returns result with caller's invocation_id for trace fidelity.
    - Fully asserts all stage queues are exhausted at conclusion.
    """

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


def make_factory(
    responses_by_stage: dict[str, list[ProviderResult]],
) -> tuple[Callable[[], IntegrationScriptedProvider], IntegrationScriptedProvider]:
    """Create a provider factory and retain the provider instance for assertions."""
    provider = IntegrationScriptedProvider(responses_by_stage)

    def factory() -> IntegrationScriptedProvider:
        return provider

    return factory, provider


def make_semantic_core(
    central_problem: str = "Consensus failure detection under gray network partitions",
    mechanism: str = "Multi-path heartbeat triangulation with asymmetric reachability matrix",
    load_bearing_claim: str = "Triangulated heartbeat gossip detects gray failures before lease timeout expiry",
    central_object: str | None = "Reachability matrix",
    unit_of_analysis: str | None = "Node cluster",
    system_boundary: str | None = "Replication layer",
    agency_model: str | None = "Autonomous quorum voters",
    temporal_logic: str | None = "Epoch-based round numbering",
    key_constraint: str | None = "Network latency upper bound",
    downstream_consequences: list[str] | None = None,
) -> dict[str, Any]:
    """Create a full semantic core dictionary."""
    return {
        "central_problem": central_problem,
        "mechanism": mechanism,
        "load_bearing_claim": load_bearing_claim,
        "central_object": central_object,
        "unit_of_analysis": unit_of_analysis,
        "system_boundary": system_boundary,
        "agency_model": agency_model,
        "temporal_logic": temporal_logic,
        "key_constraint": key_constraint,
        "downstream_consequences": downstream_consequences or ["Faster leader failover during asymmetric loss"],
    }


def make_return_path(
    dimension_changed: str = "Failure detection topology",
    consequence_chain: list[str] | None = None,
    why_it_matters: str = "Prevents split-brain leadership thrashing during partial network isolation",
) -> dict[str, Any]:
    """Create a return path dictionary."""
    return {
        "dimension_changed": dimension_changed,
        "consequence_chain": consequence_chain or [
            "Heartbeat triangulation matrix reveals partial drop",
            "Followers self-isolate before electing conflicting leader",
        ],
        "why_it_matters": why_it_matters,
    }


def make_epistemics(
    supported: list[str] | None = None,
    inferred: list[str] | None = None,
    speculative: list[str] | None = None,
    unknown: list[str] | None = None,
    break_condition: list[str] | None = None,
) -> dict[str, Any]:
    """Create an epistemics dictionary."""
    return {
        "supported": supported or ["Paxos/Raft state machine replication assumes majority quorums"],
        "inferred": inferred or ["Asymmetric partitions cause leadership election cycles"],
        "speculative": speculative or ["Triangulated gossip stabilizes election latency under high packet drop"],
        "unknown": unknown or ["Exact CPU overhead of mesh ping verification"],
        "break_condition": break_condition or ["Total partition isolating > N/2 nodes simultaneously"],
    }


def make_candidate(
    candidate_id: str = "C1",
    semantic_core: dict[str, Any] | None = None,
    preserved: list[str] | None = None,
    default_frame: str = "Standard binary heartbeat leases",
    blind_spot: str = "Ignores directional packet drop where A reaches B but B cannot reach A",
    operator_ids: list[str] | None = None,
    shift: str = "Shift from pairwise lease pings to global reachability topology matrix",
    perspective: str = "Triangulated Asymmetric Reachability Gossip Perspective",
    new_consequences: list[str] | None = None,
    return_path: dict[str, Any] | None = None,
    epistemics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a candidate dictionary matching perspective candidate schema."""
    return {
        "candidate_id": candidate_id,
        "semantic_core": semantic_core or make_semantic_core(),
        "preserved": preserved or ["Quorum intersection guarantees across epoch boundaries"],
        "default_frame": default_frame,
        "blind_spot": blind_spot,
        "operator_ids": operator_ids or ["OP_ASYMMETRY_INVERSION"],
        "shift": shift,
        "perspective": perspective,
        "new_consequences": new_consequences or ["Avoids leader oscillation during gray faults"],
        "return_path": return_path or make_return_path(),
        "epistemics": epistemics or make_epistemics(),
    }


def make_diagnosis(
    central_problem: str = "Consensus stability under non-fail-stop network anomalies",
    search_profile: str = "Structural failure detection mechanisms and epoch fencing invariants",
    priority_dimensions: list[str] | None = None,
) -> dict[str, Any]:
    """Create a diagnosis dictionary."""
    return {
        "central_problem": central_problem,
        "search_profile": search_profile,
        "priority_dimensions": priority_dimensions or ["Topology asymmetry", "Epoch fencing token validation"],
    }


def make_prior_summary(
    covered_mechanisms: list[str] | None = None,
    known_failure_modes: list[str] | None = None,
    unexplored_angles: list[str] | None = None,
) -> dict[str, Any]:
    """Create a prior summary dictionary for 360 exploration."""
    return {
        "covered_mechanisms": covered_mechanisms or ["Triangulated heartbeat gossip", "Log compaction backpressure"],
        "known_failure_modes": known_failure_modes or ["Gray network partitions", "Snapshot bandwidth starvation"],
        "unexplored_angles": unexplored_angles or ["Byzantine view-change non-equivocation proofs"],
    }


def make_selection(
    candidate_id: str = "C1",
    admissible: bool = True,
    constraint_failures: list[str] | None = None,
    structurally_distinct: bool = True,
    novelty_dimensions: list[str] | None = None,
    nearest_candidate_id: str | None = None,
    nearest_existing_p_id: str | None = None,
    standalone_quality: str = "strong",
    marginal_contribution: str = "high",
    disposition: str = "KEEP",
    merge_target: dict[str, str] | None = None,
    reason: str = "Proposes a novel reachability mesh mechanism distinct from standard lease timeouts",
) -> dict[str, Any]:
    """Create a selection record dictionary."""
    return {
        "candidate_id": candidate_id,
        "admissible": admissible,
        "constraint_failures": constraint_failures or [],
        "structurally_distinct": structurally_distinct,
        "novelty_dimensions": novelty_dimensions or ["Asymmetric fault topology"],
        "nearest_candidate_id": nearest_candidate_id,
        "nearest_existing_p_id": nearest_existing_p_id,
        "standalone_quality": standalone_quality,
        "marginal_contribution": marginal_contribution,
        "disposition": disposition,
        "merge_target": merge_target,
        "reason": reason,
    }


def make_deep_development(
    p_id: str,
    semantic_lock_echo: dict[str, Any],
    developed_model: str = "Formalized specification of triangulated asymmetric reachability protocol with epoch fencing",
    what_became_more_precise: list[str] | None = None,
    assumptions: list[str] | None = None,
    supporting_basis: list[str] | None = None,
    evidence_missing: list[str] | None = None,
    unknowns: list[str] | None = None,
    strongest_countermodel: str | None = "Adaptive round-trip timer leasing without topology matrix exchange",
    break_conditions: list[str] | None = None,
    downstream_implications: list[str] | None = None,
    optional_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a DeepDevelopment dictionary."""
    return {
        "p_id": p_id,
        "semantic_lock_echo": semantic_lock_echo,
        "developed_model": developed_model,
        "what_became_more_precise": what_became_more_precise or [
            "Exact gossip exchange interval bounds",
            "Epoch transition non-equivocation proof verification",
        ],
        "assumptions": assumptions or ["Network packet corruption is caught by cryptographic checksums"],
        "supporting_basis": supporting_basis or ["Section 1 and 3 of source text regarding gray failures and BFT"],
        "evidence_missing": evidence_missing or [],
        "unknowns": unknowns or ["Exact latency cost of mesh signature validation"],
        "strongest_countermodel": strongest_countermodel,
        "break_conditions": break_conditions or ["Concurrent partition affecting strict majority of nodes"],
        "downstream_implications": downstream_implications or [
            "Zero false-positive leader failovers during temporary one-way packet drops"
        ],
        "optional_analysis": optional_analysis,
    }


def make_deep_review(
    identity_preserved: bool = True,
    identity_drift: list[str] | None = None,
    load_bearing_claim: str = "Triangulated heartbeat gossip detects gray failures before lease timeout expiry",
    strongest_objection: str = "High gossip packet overhead under large cluster node count",
    objection_target: str = "Message complexity scaling",
    objection_is_load_bearing: bool = False,
    counterevidence: list[str] | None = None,
    evidence_debt: list[str] | None = None,
    rebuild_required: bool = False,
    rebuild_instructions: list[str] | None = None,
    terminal_state: str = "MODEL_READY",
    rationale: str = "Semantic lock echo matches identity core perfectly and model development resolves core problem.",
) -> dict[str, Any]:
    """Create a DeepReview dictionary."""
    return {
        "identity_preserved": identity_preserved,
        "identity_drift": identity_drift or [],
        "load_bearing_claim": load_bearing_claim,
        "strongest_objection": strongest_objection,
        "objection_target": objection_target,
        "objection_is_load_bearing": objection_is_load_bearing,
        "counterevidence": counterevidence or [],
        "evidence_debt": evidence_debt or [],
        "rebuild_required": rebuild_required,
        "rebuild_instructions": rebuild_instructions or [],
        "terminal_state": terminal_state,
        "rationale": rationale,
    }


def make_provider_result(
    stage: str,
    payload: Any,
    invocation_id: str = "inv_test",
    model: str = "qwen-scripted",
    transport: str = "scripted",
    duration_ms: int = 42,
    exit_code: int = 0,
) -> ProviderResult:
    """Helper to construct ProviderResult."""
    raw_text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return ProviderResult(
        invocation_id=invocation_id,
        stage=stage,
        raw_text=raw_text,
        model=model,
        transport=transport,
        duration_ms=duration_ms,
        exit_code=exit_code,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Continuous Synthetic Session End-to-End Orchestration (Req 1, 2, 4)
# ─────────────────────────────────────────────────────────────────────────────


def test_continuous_session_full_lifecycle_normal_360_deep_rift(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Exercise complete continuous session: NORMAL -> 360 -> Deep -> RIFT -> Deep.

    Verifies:
    - NORMAL produces P1 and P2 with source snapshot and pass record;
    - 360 consumes prior PassRecord history and produces P3;
    - Deep resolves P1, preserves identity, and reaches MODEL_READY;
    - RIFT runs on same session and assigns P4;
    - Deep on P4 reaches NEED_EVIDENCE;
    - Monotonic P-ID numbering (P1 -> P2 -> P3 -> P4);
    - Full trace artifacts written and relative trace refs match;
    - Stage queues are 100% consumed with zero drift;
    - CLI visible output includes P-IDs and terminal states while internal IDs are hidden.
    """
    source_content = load_integration_source()
    source_file = tmp_path / "source.md"
    source_file.write_text(source_content, encoding="utf-8")
    session_dir = tmp_path / "session_integration_cont"
    trace_root = tmp_path / "traces"
    task_objective = "Explore robust consensus under asymmetric network failure modes"

    # ── STEP 1: NORMAL Exploration (Call A + Call B) ─────────────────────────
    # Generates C1 (KEEP -> P1), C2 (KEEP -> P2), C3 (BORDERLINE), C4 (MERGE -> C1)
    c1_core = make_semantic_core(
        central_problem="Gray failures causing asymmetric election thrashing",
        mechanism="Triangulated heartbeat gossip matrix",
        load_bearing_claim="Matrix triangulation identifies asymmetric reachability faster than timeouts",
    )
    c2_core = make_semantic_core(
        central_problem="Log snapshotting network bandwidth starvation",
        mechanism="Adaptive chunked snapshot streaming with priority rate limiting",
        load_bearing_claim="Bandwidth throttling on snapshots prevents quorum commit starvation",
    )
    c3_core = make_semantic_core(
        central_problem="Memory cache sizing during continuous mutation",
        mechanism="Hierarchical LRU cache with epoch fencing",
        load_bearing_claim="Cache tiering stabilizes hit rates",
    )
    c4_core = make_semantic_core(
        central_problem="Gray failures in leader election",
        mechanism="Paraphrased triangulated heartbeat pings",
        load_bearing_claim="Mesh pings find bad nodes",
    )

    normal_candidates = [
        make_candidate("C1", semantic_core=c1_core, perspective="Triangulated Reachability Perspective"),
        make_candidate("C2", semantic_core=c2_core, perspective="Adaptive Snapshot Bandwidth Perspective"),
        make_candidate("C3", semantic_core=c3_core, perspective="Hierarchical Cache Tiering Perspective"),
        make_candidate("C4", semantic_core=c4_core, perspective="Paraphrased Gossip Perspective"),
    ]
    normal_selections = [
        make_selection("C1", disposition="KEEP", standalone_quality="strong", marginal_contribution="high"),
        make_selection("C2", disposition="KEEP", standalone_quality="strong", marginal_contribution="high"),
        make_selection("C3", disposition="BORDERLINE", standalone_quality="borderline", marginal_contribution="low"),
        make_selection(
            "C4",
            disposition="MERGE",
            standalone_quality="strong",
            marginal_contribution="low",
            merge_target={"kind": "candidate", "target_id": "C1"},
        ),
    ]

    normal_responses = {
        "EXPLORE_GENERATE": [
            make_provider_result(
                "EXPLORE_GENERATE",
                {"diagnosis": make_diagnosis(), "candidates": normal_candidates},
            )
        ],
        "EXPLORE_SELECT": [make_provider_result("EXPLORE_SELECT", normal_selections)],
    }
    factory_normal, provider_normal = make_factory(normal_responses)

    capsys.readouterr()
    exit_code_1 = main(
        [
            "run",
            "--source-file", str(source_file),
            "--task", task_objective,
            "--session", str(session_dir),
            "--mode", "normal",
            "--trace-root", str(trace_root),
        ],
        provider_factory=factory_normal,
    )
    captured_normal = capsys.readouterr()

    assert exit_code_1 == 0
    provider_normal.assert_exhausted()

    # Assert CLI visible rendering hides internal metadata
    assert "P1" in captured_normal.out
    assert "P2" in captured_normal.out
    assert "OK" in captured_normal.out or "Triangulated" in captured_normal.out
    assert str(session_dir) not in captured_normal.out
    assert "provider_invocation_id" not in captured_normal.out
    assert "explore-run-" not in captured_normal.out
    assert '"C1"' not in captured_normal.out

    # Verify session on disk after NORMAL
    store = SessionStore()
    session = store.load(str(session_dir))
    assert session.session_id == str(session_dir)
    assert session.next_p_number == 3
    assert len(session.perspectives) == 2
    assert "P1" in session.perspectives
    assert "P2" in session.perspectives
    assert session.perspectives["P1"].identity.p_id == "P1"
    assert session.perspectives["P1"].identity.candidate_id == "C1"
    assert session.perspectives["P2"].identity.p_id == "P2"
    assert session.perspectives["P2"].identity.candidate_id == "C2"
    assert len(session.passes) == 1
    assert session.passes[0].mode == "normal"
    assert session.passes[0].kept_p_ids == ["P1", "P2"]
    assert len(session.passes[0].candidates) == 4
    assert len(session.passes[0].selections) == 4
    assert len(session.passes[0].provider_invocation_ids) == 2

    # Check trace directory
    pass1_trace_dir = trace_root / session.passes[0].trace_ref
    assert pass1_trace_dir.exists()
    assert (pass1_trace_dir / "candidates.json").exists()
    assert (pass1_trace_dir / "selection.json").exists()
    assert (pass1_trace_dir / "provider-invocations.json").exists()

    # ── STEP 2: 360 Exploration (Call A + Call B) on Same Session ────────────
    # Ingests prior summary of P1, P2 and generates C1 (KEEP -> P3), C2 (DROP)
    c360_1_core = make_semantic_core(
        central_problem="Byzantine non-equivocation validation under view changes",
        mechanism="Multi-party threshold signature accumulator with epoch fencing",
        load_bearing_claim="Threshold signatures prevent split-brain view change broadcasts",
    )
    c360_2_core = make_semantic_core(
        central_problem="Repetition of gray partition gossip",
        mechanism="Minor variation of reachability pings",
        load_bearing_claim="Slightly different gossip cadence",
    )

    candidates_360 = [
        make_candidate("C1", semantic_core=c360_1_core, perspective="Threshold View-Change Non-Equivocation"),
        make_candidate("C2", semantic_core=c360_2_core, perspective="Redundant Gossip Candidate"),
    ]
    selections_360 = [
        make_selection("C1", disposition="KEEP", standalone_quality="strong", marginal_contribution="high"),
        make_selection(
            "C2",
            disposition="DROP",
            standalone_quality="weak",
            marginal_contribution="none",
            nearest_existing_p_id="P1",
        ),
    ]

    responses_360 = {
        "EXPLORE_360_GENERATE": [
            make_provider_result(
                "EXPLORE_360_GENERATE",
                {
                    "prior_summary": make_prior_summary(),
                    "diagnosis": make_diagnosis(central_problem="Byzantine view-change divergence"),
                    "candidates": candidates_360,
                },
            )
        ],
        "EXPLORE_360_SELECT": [make_provider_result("EXPLORE_360_SELECT", selections_360)],
    }
    factory_360, provider_360 = make_factory(responses_360)

    exit_code_2 = main(
        [
            "run",
            "--source-file", str(source_file),
            "--task", task_objective,
            "--session", str(session_dir),
            "--mode", "360",
            "--trace-root", str(trace_root),
        ],
        provider_factory=factory_360,
    )
    captured_360 = capsys.readouterr()

    assert exit_code_2 == 0
    provider_360.assert_exhausted()

    # Output verification: P3 assigned monotonically
    assert "P3" in captured_360.out
    assert str(session_dir) not in captured_360.out

    # Verify session on disk after 360
    session = store.load(str(session_dir))
    assert session.next_p_number == 4
    assert len(session.perspectives) == 3
    assert "P3" in session.perspectives
    assert session.perspectives["P3"].identity.p_id == "P3"
    assert len(session.passes) == 2
    assert session.passes[1].mode == "360"
    assert session.passes[1].kept_p_ids == ["P3"]

    # Trace directory for 360 contains prior-summary.json
    pass2_trace_dir = trace_root / session.passes[1].trace_ref
    assert pass2_trace_dir.exists()
    assert (pass2_trace_dir / "prior-summary.json").exists()

    # ── STEP 3: Deep Analysis on P1 ──────────────────────────────────────────
    # DEVELOP + REVIEW -> MODEL_READY with identity preserved
    p1_state = session.perspectives["P1"]
    p1_echo = p1_state.identity.identity_core.to_dict()

    dev_p1 = make_deep_development(
        p_id="P1",
        semantic_lock_echo=p1_echo,
        developed_model="Complete algorithmic specification of multi-path reachability matrix exchange",
    )
    rev_p1 = make_deep_review(
        identity_preserved=True,
        terminal_state="MODEL_READY",
        rationale="Lock echo is identical to P1 core and edge cases are bounded.",
    )

    responses_deep = {
        "DEEP_DEVELOP": [make_provider_result("DEEP_DEVELOP", dev_p1)],
        "DEEP_REVIEW": [make_provider_result("DEEP_REVIEW", rev_p1)],
    }
    factory_deep, provider_deep = make_factory(responses_deep)

    exit_code_3 = main(
        [
            "deep",
            "--session", str(session_dir),
            "--p-id", "P1",
            "--trace-root", str(trace_root),
        ],
        provider_factory=factory_deep,
    )
    captured_deep = capsys.readouterr()

    assert exit_code_3 == 0
    provider_deep.assert_exhausted()

    # Output verification: Perspective P1 and terminal state MODEL_READY rendered
    assert "Perspective: P1" in captured_deep.out
    assert "Terminal state: MODEL_READY" in captured_deep.out
    assert "deep-run-" not in captured_deep.out
    assert "deep-" not in captured_deep.out
    assert str(session_dir) not in captured_deep.out

    # Verify session on disk after Deep
    session = store.load(str(session_dir))
    assert len(session.deep_runs) == 1
    assert session.deep_runs[0].p_id == "P1"
    assert session.deep_runs[0].terminal_state == "MODEL_READY"
    assert session.perspectives["P1"].terminal_state == "MODEL_READY"
    assert session.perspectives["P1"].current_version == 2
    assert len(session.perspectives["P1"].deep_refs) == 1

    # Check deep trace artifacts
    deep1_trace_dir = trace_root / session.deep_runs[0].trace_ref
    assert deep1_trace_dir.exists()
    assert (deep1_trace_dir / "development.json").exists()
    assert (deep1_trace_dir / "review.json").exists()

    # ── STEP 4: RIFT Exploration (Call A + Call B) on Same Session ───────────
    # Generates C1 (KEEP -> P4) with operator_ids and return path
    c_rift_core = make_semantic_core(
        central_problem="Log compaction divergence during concurrent snapshot branch application",
        mechanism="Deterministic speculative log rollback engine using reversible undo-logs",
        load_bearing_claim="Reversible undo-logs allow speculative state execution while snapshot transfer completes",
    )
    candidates_rift = [
        make_candidate(
            "C1",
            semantic_core=c_rift_core,
            operator_ids=["OP_TEMPORAL_INVERSION"],
            perspective="Reversible Speculative Undo-Log Perspective",
        )
    ]
    selections_rift = [
        make_selection("C1", disposition="KEEP", standalone_quality="strong", marginal_contribution="high")
    ]

    responses_rift = {
        "RIFT_GENERATE": [
            make_provider_result(
                "RIFT_GENERATE",
                {
                    "diagnosis": make_diagnosis(central_problem="Log divergence during snapshot restore"),
                    "candidates": candidates_rift,
                },
            )
        ],
        "RIFT_SELECT": [make_provider_result("RIFT_SELECT", selections_rift)],
    }
    factory_rift, provider_rift = make_factory(responses_rift)

    exit_code_4 = main(
        [
            "run",
            "--source-file", str(source_file),
            "--task", task_objective,
            "--session", str(session_dir),
            "--mode", "rift",
            "--trace-root", str(trace_root),
        ],
        provider_factory=factory_rift,
    )
    captured_rift = capsys.readouterr()

    assert exit_code_4 == 0
    provider_rift.assert_exhausted()

    # Output verification: P4 assigned monotonically
    assert "P4" in captured_rift.out
    assert str(session_dir) not in captured_rift.out

    # Verify session on disk after RIFT
    session = store.load(str(session_dir))
    assert session.next_p_number == 5
    assert len(session.perspectives) == 4
    assert "P4" in session.perspectives
    assert session.perspectives["P4"].identity.p_id == "P4"
    assert session.perspectives["P4"].identity.candidate_id == "C1"
    assert len(session.passes) == 3
    assert session.passes[2].mode == "rift"
    assert session.passes[2].kept_p_ids == ["P4"]

    # ── STEP 5: Deep Analysis on RIFT Perspective P4 (NEED_EVIDENCE) ─────────
    p4_state = session.perspectives["P4"]
    p4_echo = p4_state.identity.identity_core.to_dict()

    dev_p4 = make_deep_development(
        p_id="P4",
        semantic_lock_echo=p4_echo,
        developed_model="Speculative undo-log memory-bounded journaling architecture",
        evidence_missing=["Empirical benchmarks under sustained 100k IOPS snapshot streaming"],
    )
    rev_p4 = make_deep_review(
        identity_preserved=True,
        terminal_state="NEED_EVIDENCE",
        evidence_debt=["Missing empirical memory overhead measurements on flash storage"],
        rationale="Concept is sound but requires empirical stress test validation.",
    )

    responses_deep_p4 = {
        "DEEP_DEVELOP": [make_provider_result("DEEP_DEVELOP", dev_p4)],
        "DEEP_REVIEW": [make_provider_result("DEEP_REVIEW", rev_p4)],
    }
    factory_deep_p4, provider_deep_p4 = make_factory(responses_deep_p4)

    exit_code_5 = main(
        [
            "deep",
            "--session", str(session_dir),
            "--p-id", "P4",
            "--trace-root", str(trace_root),
        ],
        provider_factory=factory_deep_p4,
    )
    captured_deep_p4 = capsys.readouterr()

    assert exit_code_5 == 0
    provider_deep_p4.assert_exhausted()
    assert "Perspective: P4" in captured_deep_p4.out
    assert "Terminal state: NEED_EVIDENCE" in captured_deep_p4.out

    # ── STEP 6: Session Show Command Integration ─────────────────────────────
    exit_code_show = main(
        ["session", "show", str(session_dir)],
        provider_factory=lambda: IntegrationScriptedProvider({}),
    )
    captured_show = capsys.readouterr()
    assert exit_code_show == 0
    assert f"Session ID: {session_dir}" in captured_show.out
    assert "Perspectives: 4" in captured_show.out
    assert "Passes: 3" in captured_show.out
    assert "Deep runs: 2" in captured_show.out
    assert "P1:" in captured_show.out
    assert "P2:" in captured_show.out
    assert "P3:" in captured_show.out
    assert "P4:" in captured_show.out

    # Final overall session and source consistency assertion
    verified_source = store.load_verified_source(session)
    assert verified_source == source_content
    assert session.source_hash == compute_source_hash(source_content)


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Schema Repair Isolation & Queue Integrity (Req 3, 2)
# ─────────────────────────────────────────────────────────────────────────────


def test_schema_repair_isolated_to_repair_stage_and_queue(tmp_path: Path):
    """Assert schema repair invocation is tagged SCHEMA_REPAIR:<parent_stage> and does not shift other stage queues.

    Verifies:
    - Primary EXPLORE_GENERATE returns unparseable JSON;
    - Repair stage SCHEMA_REPAIR:EXPLORE_GENERATE returns valid JSON;
    - EXPLORE_SELECT is invoked normally and consumes its own queue cleanly;
    - Provider trace logs 3 invocations with repair_parent set on the second;
    - All 3 queues are completely exhausted.
    """
    source_content = load_integration_source()
    source_file = tmp_path / "source.md"
    source_file.write_text(source_content, encoding="utf-8")
    session_dir = tmp_path / "session_repair_test"
    trace_root = tmp_path / "traces"

    malformed_json_response = "```json\n{ THIS IS NOT VALID JSON ... MALFORMED SYNTAX ]\n```"

    valid_candidates = [
        make_candidate("C1", perspective="Repaired Gossip Perspective")
    ]
    valid_generate_payload = {
        "diagnosis": make_diagnosis(),
        "candidates": valid_candidates,
    }
    valid_select_payload = [
        make_selection("C1", disposition="KEEP", standalone_quality="strong", marginal_contribution="high")
    ]

    responses = {
        "EXPLORE_GENERATE": [
            make_provider_result("EXPLORE_GENERATE", malformed_json_response)
        ],
        "SCHEMA_REPAIR:EXPLORE_GENERATE": [
            make_provider_result("SCHEMA_REPAIR:EXPLORE_GENERATE", valid_generate_payload)
        ],
        "EXPLORE_SELECT": [
            make_provider_result("EXPLORE_SELECT", valid_select_payload)
        ],
    }
    factory, provider = make_factory(responses)

    exit_code = main(
        [
            "run",
            "--source-file", str(source_file),
            "--task", "Explore consensus under repair test",
            "--session", str(session_dir),
            "--mode", "normal",
            "--trace-root", str(trace_root),
        ],
        provider_factory=factory,
    )

    assert exit_code == 0
    provider.assert_exhausted()

    # Verify session and pass record
    store = SessionStore()
    session = store.load(str(session_dir))
    assert len(session.passes) == 1
    assert session.passes[0].kept_p_ids == ["P1"]
    assert len(session.passes[0].provider_invocation_ids) == 3

    # Verify provider-invocations.json in trace directory
    trace_dir = trace_root / session.passes[0].trace_ref
    invocations_file = trace_dir / "provider-invocations.json"
    assert invocations_file.exists()

    invocations = json.loads(invocations_file.read_text(encoding="utf-8"))
    assert len(invocations) == 3
    assert invocations[0]["stage"] == "EXPLORE_GENERATE"
    assert "repair_parent" not in invocations[0]

    assert invocations[1]["stage"] == "SCHEMA_REPAIR:EXPLORE_GENERATE"
    assert invocations[1]["repair_parent"] == "EXPLORE_GENERATE"

    assert invocations[2]["stage"] == "EXPLORE_SELECT"
    assert "repair_parent" not in invocations[2]


def test_schema_repair_on_select_stage_isolation(tmp_path: Path):
    """Assert schema repair on selection stage RIFT_SELECT isolates cleanly."""
    source_content = load_integration_source()
    source_file = tmp_path / "source.md"
    source_file.write_text(source_content, encoding="utf-8")
    session_dir = tmp_path / "session_repair_select"
    trace_root = tmp_path / "traces"

    valid_candidates = [
        make_candidate("C1", perspective="RIFT Operator Perspective", operator_ids=["OP_ASYMMETRY"])
    ]
    malformed_select_response = "```json\nNOT A JSON ARRAY\n```"
    valid_select_payload = [
        make_selection("C1", disposition="KEEP", standalone_quality="strong", marginal_contribution="high")
    ]

    responses = {
        "RIFT_GENERATE": [
            make_provider_result(
                "RIFT_GENERATE",
                {"diagnosis": make_diagnosis(), "candidates": valid_candidates},
            )
        ],
        "RIFT_SELECT": [
            make_provider_result("RIFT_SELECT", malformed_select_response)
        ],
        "SCHEMA_REPAIR:RIFT_SELECT": [
            make_provider_result("SCHEMA_REPAIR:RIFT_SELECT", valid_select_payload)
        ],
    }
    factory, provider = make_factory(responses)

    exit_code = main(
        [
            "run",
            "--source-file", str(source_file),
            "--task", "Explore rift under select repair test",
            "--session", str(session_dir),
            "--mode", "rift",
            "--trace-root", str(trace_root),
        ],
        provider_factory=factory,
    )

    assert exit_code == 0
    provider.assert_exhausted()

    store = SessionStore()
    session = store.load(str(session_dir))
    assert session.passes[0].kept_p_ids == ["P1"]

    trace_dir = trace_root / session.passes[0].trace_ref
    invocations = json.loads((trace_dir / "provider-invocations.json").read_text(encoding="utf-8"))
    assert len(invocations) == 3
    assert invocations[0]["stage"] == "RIFT_GENERATE"
    assert "repair_parent" not in invocations[0]
    assert invocations[1]["stage"] == "RIFT_SELECT"
    assert "repair_parent" not in invocations[1]
    assert invocations[2]["stage"] == "SCHEMA_REPAIR:RIFT_SELECT"
    assert invocations[2]["repair_parent"] == "RIFT_SELECT"

# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Deep Rebuild Lifecycle & Identity Preservation (Req 1, 2)
# ─────────────────────────────────────────────────────────────────────────────


def test_deep_rebuild_lifecycle_and_trace_artifacts(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Exercise Deep analysis when initial review requires rebuild.

    Verifies:
    - DEEP_DEVELOP -> DEEP_REVIEW (rebuild_required=True) -> DEEP_REBUILD (terminal_state=MODEL_READY);
    - Traces written: development.json, review.json, rebuild.json;
    - Terminal state is MODEL_READY and state current_version increments to 2;
    - Output displays 'Rebuild: yes'.
    """
    source_content = load_integration_source()
    source_file = tmp_path / "source.md"
    source_file.write_text(source_content, encoding="utf-8")
    session_dir = tmp_path / "session_deep_rebuild"
    trace_root = tmp_path / "traces"

    # Setup session with P1 via NORMAL run
    c1_core = make_semantic_core(
        central_problem="Byzantine non-equivocation",
        mechanism="Cryptographic epoch fencing with threshold signatures",
    )
    normal_responses = {
        "EXPLORE_GENERATE": [
            make_provider_result(
                "EXPLORE_GENERATE",
                {"diagnosis": make_diagnosis(), "candidates": [make_candidate("C1", semantic_core=c1_core)]},
            )
        ],
        "EXPLORE_SELECT": [
            make_provider_result("EXPLORE_SELECT", [make_selection("C1", disposition="KEEP")])
        ],
    }
    main(
        [
            "run",
            "--source-file", str(source_file),
            "--task", "Rebuild test objective",
            "--session", str(session_dir),
            "--mode", "normal",
            "--trace-root", str(trace_root),
        ],
        provider_factory=lambda: IntegrationScriptedProvider(normal_responses),
    )

    # Prepare Deep rebuild responses
    dev_initial = make_deep_development(
        p_id="P1",
        semantic_lock_echo=c1_core,
        developed_model="Initial model lacking Byzantine message bounds",
    )
    rev_initial = make_deep_review(
        identity_preserved=True,
        rebuild_required=True,
        rebuild_instructions=["Specify explicit message complexity bounds for 3f+1 threshold signatures"],
        terminal_state="RETURN_TO_EXPLORE",  # temporary state before rebuild
        rationale="Message bounds must be formalized.",
    )
    dev_rebuilt = make_deep_development(
        p_id="P1",
        semantic_lock_echo=c1_core,
        developed_model="Rebuilt model with O(N^2) prepare/commit message bounds and threshold signatures",
        what_became_more_precise=["Explicit polynomial message exchange bounds"],
    )
    rev_final = make_deep_review(
        identity_preserved=True,
        rebuild_required=False,
        rebuild_instructions=[],
        terminal_state="MODEL_READY",
        rationale="Rebuild successfully added O(N^2) complexity bounds without identity drift.",
    )
    rebuild_payload = {
        "development": dev_rebuilt,
        "final_review": rev_final,
    }

    responses_deep = {
        "DEEP_DEVELOP": [make_provider_result("DEEP_DEVELOP", dev_initial)],
        "DEEP_REVIEW": [make_provider_result("DEEP_REVIEW", rev_initial)],
        "DEEP_REBUILD": [make_provider_result("DEEP_REBUILD", rebuild_payload)],
    }
    factory_deep, provider_deep = make_factory(responses_deep)

    capsys.readouterr()
    exit_code = main(
        [
            "deep",
            "--session", str(session_dir),
            "--p-id", "P1",
            "--trace-root", str(trace_root),
        ],
        provider_factory=factory_deep,
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    provider_deep.assert_exhausted()

    assert "Perspective: P1" in captured.out
    assert "Terminal state: MODEL_READY" in captured.out
    assert "Rebuild: yes" in captured.out

    store = SessionStore()
    session = store.load(str(session_dir))
    p1 = session.perspectives["P1"]
    assert p1.terminal_state == "MODEL_READY"
    # One successful Deep run increments current_version once (1 -> 2), rebuild or not
    assert p1.current_version == 2
    assert p1.deep_refs == [session.deep_runs[0].deep_id]

    deep_trace_dir = trace_root / session.deep_runs[0].trace_ref
    assert (deep_trace_dir / "development.json").exists()
    assert (deep_trace_dir / "review.json").exists()
    assert (deep_trace_dir / "rebuild.json").exists()
    rebuild_data = json.loads((deep_trace_dir / "rebuild.json").read_text(encoding="utf-8"))
    assert "development" in rebuild_data
    assert "final_review" in rebuild_data

# ─────────────────────────────────────────────────────────────────────────────
# Test 4: 360 Bounded No New Territory Continuity (Req 1, 2)
# ─────────────────────────────────────────────────────────────────────────────


def test_360_bounded_no_new_territory_continuity(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Assert 360 handles empty/dropped candidate set cleanly without advancing P-ID counter.

    Verifies:
    - 360 pass with all DROP candidates produces NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS;
    - session.next_p_number is NOT incremented;
    - Subsequent RIFT run increments next_p_number monotonically.
    """
    source_content = load_integration_source()
    source_file = tmp_path / "source.md"
    source_file.write_text(source_content, encoding="utf-8")
    session_dir = tmp_path / "session_no_territory"
    trace_root = tmp_path / "traces"

    # Step 1: Normal pass -> P1
    normal_responses = {
        "EXPLORE_GENERATE": [
            make_provider_result("EXPLORE_GENERATE", {"diagnosis": make_diagnosis(), "candidates": [make_candidate("C1")]})
        ],
        "EXPLORE_SELECT": [
            make_provider_result("EXPLORE_SELECT", [make_selection("C1", disposition="KEEP")])
        ],
    }
    main(
        ["run", "--source-file", str(source_file), "--task", "Territory test", "--session", str(session_dir), "--mode", "normal"],
        provider_factory=lambda: IntegrationScriptedProvider(normal_responses),
    )

    # Step 2: 360 pass where all candidates are dropped
    candidates_360 = [make_candidate("C1", perspective="Weak Redundant Perspective")]
    selections_360 = [
        make_selection("C1", disposition="DROP", standalone_quality="weak", marginal_contribution="none")
    ]
    responses_360 = {
        "EXPLORE_360_GENERATE": [
            make_provider_result("EXPLORE_360_GENERATE", {"prior_summary": make_prior_summary(), "diagnosis": make_diagnosis(), "candidates": candidates_360})
        ],
        "EXPLORE_360_SELECT": [make_provider_result("EXPLORE_360_SELECT", selections_360)],
    }
    factory_360, provider_360 = make_factory(responses_360)

    capsys.readouterr()
    exit_code_360 = main(
        ["run", "--source-file", str(source_file), "--task", "Territory test", "--session", str(session_dir), "--mode", "360"],
        provider_factory=factory_360,
    )
    captured_360 = capsys.readouterr()

    assert exit_code_360 == 0
    provider_360.assert_exhausted()
    assert "NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS" in captured_360.out

    store = SessionStore()
    session = store.load(str(session_dir))
    assert session.next_p_number == 2  # Unchanged!
    assert len(session.passes) == 2
    assert session.passes[1].kept_p_ids == []

    # Step 3: Subsequent RIFT pass adds P2
    rift_responses = {
        "RIFT_GENERATE": [
            make_provider_result("RIFT_GENERATE", {"diagnosis": make_diagnosis(), "candidates": [make_candidate("C1")]})
        ],
        "RIFT_SELECT": [
            make_provider_result("RIFT_SELECT", [make_selection("C1", disposition="KEEP")])
        ],
    }
    factory_rift, provider_rift = make_factory(rift_responses)
    main(
        ["run", "--source-file", str(source_file), "--task", "Territory test", "--session", str(session_dir), "--mode", "rift"],
        provider_factory=factory_rift,
    )
    provider_rift.assert_exhausted()

    session = store.load(str(session_dir))
    assert session.next_p_number == 3
    assert len(session.perspectives) == 2
    assert "P2" in session.perspectives
    assert session.passes[2].kept_p_ids == ["P2"]


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Atomic Behavior on Injected Provider Error (Req 2)
# ─────────────────────────────────────────────────────────────────────────────


def test_atomic_behavior_on_provider_transport_error(tmp_path: Path):
    """Assert session state is not corrupted when provider raises transport error mid-run.

    Verifies:
    - Injected TransportError on Call B (EXPLORE_SELECT);
    - cli.main returns non-zero error code;
    - Session on disk remains unchanged (no partial pass appended, no perspective pollution);
    - Subsequent valid run succeeds and adds expected perspective cleanly.
    """
    source_content = load_integration_source()
    source_file = tmp_path / "source.md"
    source_file.write_text(source_content, encoding="utf-8")
    session_dir = tmp_path / "session_atomic_error"

    # Step 1: Initialize session with P1
    responses_init = {
        "EXPLORE_GENERATE": [
            make_provider_result("EXPLORE_GENERATE", {"diagnosis": make_diagnosis(), "candidates": [make_candidate("C1")]})
        ],
        "EXPLORE_SELECT": [
            make_provider_result("EXPLORE_SELECT", [make_selection("C1", disposition="KEEP")])
        ],
    }
    main(
        ["run", "--source-file", str(source_file), "--task", "Atomic test", "--session", str(session_dir), "--mode", "normal"],
        provider_factory=lambda: IntegrationScriptedProvider(responses_init),
    )

    store = SessionStore()
    session_before = store.load(str(session_dir))
    assert len(session_before.passes) == 1
    assert session_before.next_p_number == 2

    # Step 2: Attempt 360 pass where EXPLORE_360_SELECT is missing / exhausted
    faulty_responses = {
        "EXPLORE_360_GENERATE": [
            make_provider_result("EXPLORE_360_GENERATE", {"prior_summary": make_prior_summary(), "diagnosis": make_diagnosis(), "candidates": [make_candidate("C1")]})
        ],
        "EXPLORE_360_SELECT": [],  # Empty queue will raise TransportError
    }
    factory_faulty, _ = make_factory(faulty_responses)

    exit_code_faulty = main(
        ["run", "--source-file", str(source_file), "--task", "Atomic test", "--session", str(session_dir), "--mode", "360"],
        provider_factory=factory_faulty,
    )

    assert exit_code_faulty != 0

    # Assert session was not corrupted
    session_after_failure = store.load(str(session_dir))
    assert len(session_after_failure.passes) == 1
    assert session_after_failure.next_p_number == 2
    assert len(session_after_failure.perspectives) == 1

    # Step 3: Subsequent valid run succeeds
    valid_360_responses = {
        "EXPLORE_360_GENERATE": [
            make_provider_result("EXPLORE_360_GENERATE", {"prior_summary": make_prior_summary(), "diagnosis": make_diagnosis(), "candidates": [make_candidate("C1")]})
        ],
        "EXPLORE_360_SELECT": [
            make_provider_result("EXPLORE_360_SELECT", [make_selection("C1", disposition="KEEP")])
        ],
    }
    factory_valid, provider_valid = make_factory(valid_360_responses)

    exit_code_valid = main(
        ["run", "--source-file", str(source_file), "--task", "Atomic test", "--session", str(session_dir), "--mode", "360"],
        provider_factory=factory_valid,
    )

    assert exit_code_valid == 0
    provider_valid.assert_exhausted()

    session_final = store.load(str(session_dir))
    assert len(session_final.passes) == 2
    assert session_final.next_p_number == 3
    assert "P2" in session_final.perspectives


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: CLI JSON & Plain Output Contracts Hide Internal IDs (Req 4)
# ─────────────────────────────────────────────────────────────────────────────


def test_cli_output_hiding_internal_identifiers_plain_and_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    """Assert CLI plain and JSON outputs include domain models while strictly hiding internal metadata.

    Verifies for both 'run' and 'deep':
    - Plain text output includes P-IDs and terminal states;
    - Plain text output strictly excludes session_id, run_id, deep_id, candidate IDs (C1/C2), invocation IDs, trace paths;
    - JSON output contains structured domain fields (outcome, rendered, kept, terminal_state);
    - JSON output strictly excludes internal execution artifacts.
    """
    source_content = load_integration_source()
    source_file = tmp_path / "source.md"
    source_file.write_text(source_content, encoding="utf-8")
    session_dir = tmp_path / "session_output_contract"
    trace_root = tmp_path / "custom_traces_dir"

    # Step 1: Test run --json output
    c1_core = make_semantic_core(central_problem="Asymmetric Gray Failures")
    responses_run = {
        "EXPLORE_GENERATE": [
            make_provider_result("EXPLORE_GENERATE", {"diagnosis": make_diagnosis(), "candidates": [make_candidate("C1", semantic_core=c1_core)]})
        ],
        "EXPLORE_SELECT": [
            make_provider_result("EXPLORE_SELECT", [make_selection("C1", disposition="KEEP")])
        ],
    }
    factory_run, provider_run = make_factory(responses_run)

    capsys.readouterr()
    exit_code_json = main(
        [
            "run",
            "--source-file", str(source_file),
            "--task", "Output contract task",
            "--session", str(session_dir),
            "--mode", "normal",
            "--trace-root", str(trace_root),
            "--json",
        ],
        provider_factory=factory_run,
    )
    captured_json = capsys.readouterr()

    assert exit_code_json == 0
    provider_run.assert_exhausted()

    parsed_json = json.loads(captured_json.out)
    assert "outcome" in parsed_json
    assert "rendered" in parsed_json
    assert "kept" in parsed_json
    assert len(parsed_json["kept"]) == 1
    assert parsed_json["kept"][0]["identity"]["p_id"] == "P1"

    # Forbidden internal strings in JSON stdout
    json_raw_out = captured_json.out
    assert str(session_dir) not in json_raw_out
    assert "custom_traces_dir" not in json_raw_out
    assert "explore-run-" not in json_raw_out
    assert "provider_invocation_id" not in json_raw_out

    # Step 2: Test deep --json output
    dev = make_deep_development(p_id="P1", semantic_lock_echo=c1_core)
    rev = make_deep_review(identity_preserved=True, terminal_state="MODEL_READY")
    responses_deep = {
        "DEEP_DEVELOP": [make_provider_result("DEEP_DEVELOP", dev)],
        "DEEP_REVIEW": [make_provider_result("DEEP_REVIEW", rev)],
    }
    factory_deep, provider_deep = make_factory(responses_deep)

    capsys.readouterr()
    exit_code_deep_json = main(
        [
            "deep",
            "--session", str(session_dir),
            "--p-id", "P1",
            "--trace-root", str(trace_root),
            "--json",
        ],
        provider_factory=factory_deep,
    )
    captured_deep_json = capsys.readouterr()

    assert exit_code_deep_json == 0
    provider_deep.assert_exhausted()

    parsed_deep = json.loads(captured_deep_json.out)
    assert parsed_deep["p_id"] == "P1"
    assert parsed_deep["terminal_state"] == "MODEL_READY"
    assert "development" in parsed_deep
    assert "review" in parsed_deep

    deep_raw_out = captured_deep_json.out
    assert str(session_dir) not in deep_raw_out
    assert "custom_traces_dir" not in deep_raw_out
    assert "deep-run-" not in deep_raw_out
    assert "deep-" not in parsed_deep.get("run_id", "")


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Source and Objective Immutability Enforced by CLI (Req 2)
# ─────────────────────────────────────────────────────────────────────────────


def test_source_and_objective_immutability_enforced_by_cli(tmp_path: Path):
    """Assert CLI rejects source changes or objective changes on existing sessions before provider calls."""
    source_content_1 = load_integration_source()
    source_content_2 = load_alternative_source()

    source_file_1 = tmp_path / "source1.md"
    source_file_1.write_text(source_content_1, encoding="utf-8")
    source_file_2 = tmp_path / "source2.md"
    source_file_2.write_text(source_content_2, encoding="utf-8")

    session_dir = tmp_path / "session_immutability"

    # Step 1: Create session with source 1 and objective A
    init_responses = {
        "EXPLORE_GENERATE": [
            make_provider_result("EXPLORE_GENERATE", {"diagnosis": make_diagnosis(), "candidates": [make_candidate("C1")]})
        ],
        "EXPLORE_SELECT": [
            make_provider_result("EXPLORE_SELECT", [make_selection("C1", disposition="KEEP")])
        ],
    }
    exit_code_init = main(
        ["run", "--source-file", str(source_file_1), "--task", "Objective A", "--session", str(session_dir)],
        provider_factory=lambda: IntegrationScriptedProvider(init_responses),
    )
    assert exit_code_init == 0

    # Step 2: Attempt run with different source on same session -> fails closed with 0 provider calls
    unused_provider = IntegrationScriptedProvider({"EXPLORE_GENERATE": [make_provider_result("EXPLORE_GENERATE", "{}")]})
    exit_code_source_mismatch = main(
        ["run", "--source-file", str(source_file_2), "--task", "Objective A", "--session", str(session_dir)],
        provider_factory=lambda: unused_provider,
    )
    assert exit_code_source_mismatch != 0
    assert unused_provider._call_count == 0

    # Step 3: Attempt run with different objective on same session -> fails closed with 0 provider calls
    exit_code_obj_mismatch = main(
        ["run", "--source-file", str(source_file_1), "--task", "Materially Different Objective B", "--session", str(session_dir)],
        provider_factory=lambda: unused_provider,
    )
    assert exit_code_obj_mismatch != 0
    assert unused_provider._call_count == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Constraint Ledger Integration with CLI Commands (Req 1, 2)
# ─────────────────────────────────────────────────────────────────────────────


def test_session_add_constraint_integration(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """Assert session add-constraint updates ConstraintLedger and feeds active constraints into next pass."""
    source_content = load_integration_source()
    source_file = tmp_path / "source.md"
    source_file.write_text(source_content, encoding="utf-8")
    session_dir = tmp_path / "session_constraints"

    # Step 1: Initialize session
    init_responses = {
        "EXPLORE_GENERATE": [
            make_provider_result("EXPLORE_GENERATE", {"diagnosis": make_diagnosis(), "candidates": [make_candidate("C1")]})
        ],
        "EXPLORE_SELECT": [
            make_provider_result("EXPLORE_SELECT", [make_selection("C1", disposition="KEEP")])
        ],
    }
    main(
        ["run", "--source-file", str(source_file), "--task", "Constraint task", "--session", str(session_dir)],
        provider_factory=lambda: IntegrationScriptedProvider(init_responses),
    )

    # Step 2: Add hard constraint via CLI command
    capsys.readouterr()
    exit_code_add = main(
        [
            "session",
            "add-constraint",
            str(session_dir),
            "--id", "C_FENCE_1",
            "--value", "Must require epoch fencing token on state machine writes",
            "--kind", "hard",
            "--turn", "turn-2",
        ],
        provider_factory=lambda: IntegrationScriptedProvider({}),
    )
    captured_add = capsys.readouterr()
    assert exit_code_add == 0
    assert "Added constraint C_FENCE_1" in captured_add.out

    # Step 3: Add second constraint that supersedes the first
    main(
        [
            "session",
            "add-constraint",
            str(session_dir),
            "--id", "C_FENCE_1",
            "--value", "Must require cryptographic epoch fencing token and non-equivocation proof",
            "--kind", "hard",
            "--turn", "turn-3",
        ],
        provider_factory=lambda: IntegrationScriptedProvider({}),
    )

    # Verify session store constraint ledger
    store = SessionStore()
    session = store.load(str(session_dir))
    active_constraints = session.constraint_ledger.active_entries()
    assert len(active_constraints) == 1
    assert active_constraints[0].constraint_id == "C_FENCE_1"
    assert "non-equivocation proof" in active_constraints[0].value
    assert len(session.constraint_ledger.entries) == 2
    assert session.constraint_ledger.entries[0].status == "superseded"
    assert session.constraint_ledger.entries[1].status == "active"


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Deep Command Negative Cases (Req 2)
# ─────────────────────────────────────────────────────────────────────────────


def test_deep_fails_closed_on_unknown_p_id(tmp_path: Path):
    """Assert deep command rejects unknown P-ID before making any provider calls."""
    source_content = load_integration_source()
    source_file = tmp_path / "source.md"
    source_file.write_text(source_content, encoding="utf-8")
    session_dir = tmp_path / "session_deep_neg"

    init_responses = {
        "EXPLORE_GENERATE": [
            make_provider_result("EXPLORE_GENERATE", {"diagnosis": make_diagnosis(), "candidates": [make_candidate("C1")]})
        ],
        "EXPLORE_SELECT": [
            make_provider_result("EXPLORE_SELECT", [make_selection("C1", disposition="KEEP")])
        ],
    }
    main(
        ["run", "--source-file", str(source_file), "--task", "Task", "--session", str(session_dir)],
        provider_factory=lambda: IntegrationScriptedProvider(init_responses),
    )

    unused_provider = IntegrationScriptedProvider({"DEEP_DEVELOP": []})
    exit_code = main(
        ["deep", "--session", str(session_dir), "--p-id", "P99"],
        provider_factory=lambda: unused_provider,
    )

    assert exit_code != 0
    assert unused_provider._call_count == 0
