"""Tests for Perspective Core v0 Deep (Wave 2B).

Covers D1–D11 scripted fixtures:
- D1: lock echo mismatch detected and passed to review
- D2: legitimate refinement → MODEL_READY
- D3: load-bearing objection → RETURN_TO_EXPLORE
- D4: peripheral objection → MODEL_READY
- D5: NEED_EVIDENCE terminal state
- D6: premature MODEL_READY rejected by review → RETURN_TO_EXPLORE
- D7: RETURN_TO_EXPLORE from review
- D8: evidence debt survives rebuild
- D9: non-causal perspective leaves optional_analysis absent
- D10: source hash mismatch fails before provider call
- D11: unknown P-ID fails cleanly

Uses stage-indexed provider; verifies all queues exhausted and max semantic calls.
"""

import json
from collections import deque
from pathlib import Path

import pytest

from prism.perspective_core import (
    ConstraintLedger,
    DeepDevelopment,
    DeepRebuildResult,
    DeepReview,
    DeepRunResult,
    Epistemics,
    PerspectiveIdentity,
    PerspectiveSession,
    PerspectiveState,
    ProviderResult,
    SemanticCore,
    SessionStore,
    compute_source_hash,
)
from prism.perspective_core.deep import (
    _build_develop_prompt,
    _build_rebuild_prompt,
    _build_review_prompt,
    _extract_json,
    _normalize_semantic_core,
    run_deep,
)


# ─────────────────────────────────────────────────────────────────────────────
# Stage-indexed test provider
# ─────────────────────────────────────────────────────────────────────────────


class DeepStageProvider:
    """Stage-indexed scripted provider for Deep tests.

    Routes by stage queue; validates stage match; does NOT validate
    invocation_id (deep.py generates dynamic IDs internally).
    Tracks call count and supports queue-exhaustion assertion.
    """

    def __init__(self, responses_by_stage: dict[str, list[ProviderResult]]):
        self._queues: dict[str, deque[ProviderResult]] = {
            stage: deque(responses) for stage, responses in responses_by_stage.items()
        }
        self._call_count = 0

    def complete(
        self, prompt: str, *, stage: str, invocation_id: str
    ) -> ProviderResult:
        if stage not in self._queues:
            from prism.perspective_core.provider import TransportError

            raise TransportError(f"Unknown stage: {stage}")
        queue = self._queues[stage]
        if not queue:
            from prism.perspective_core.provider import TransportError

            raise TransportError(f"Exhausted stage queue: {stage}")
        result = queue.popleft()
        if result.stage != stage:
            from prism.perspective_core.provider import TransportError

            raise TransportError(
                f"Stage mismatch: expected {result.stage}, got {stage}"
            )
        self._call_count += 1
        return result

    def assert_all_consumed(self) -> None:
        for stage, queue in self._queues.items():
            if queue:
                raise AssertionError(
                    f"Unused responses in {stage}: {len(queue)} remaining"
                )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

SOURCE = "Source material for Deep tests. A text about decision-making under uncertainty."


def _make_identity_core() -> SemanticCore:
    return SemanticCore(
        central_problem="How mental models shape decision-making",
        mechanism="Cognitive framing through temporal discounting",
        load_bearing_claim="Temporal discounting is the primary driver of suboptimal decisions",
        central_object="Mental model",
        unit_of_analysis="Individual decision-maker",
        system_boundary="Personal cognitive architecture",
        agency_model="Bounded rationality",
        temporal_logic="Sequential with feedback loops",
        key_constraint="Working memory capacity",
        downstream_consequences=["Systematic bias in long-term planning"],
    )


def _echo_dict(core: SemanticCore) -> dict:
    """Exact dict representation of identity core for echo matching."""
    return core.to_dict()


def _echo_dict_modified(core: SemanticCore, **overrides: str) -> dict:
    """Echo dict with specific fields changed (for mismatch tests)."""
    d = core.to_dict()
    d.update(overrides)
    return d


def _make_dev_json(
    p_id: str, echo: dict, *, optional_analysis=None, extra_evidence_missing=None
) -> str:
    dev = {
        "p_id": p_id,
        "semantic_lock_echo": echo,
        "developed_model": "Refined model of cognitive framing",
        "what_became_more_precise": ["Mechanism of temporal discounting"],
        "assumptions": ["Stable cognitive architecture"],
        "supporting_basis": ["Empirical studies on framing effects"],
        "evidence_missing": extra_evidence_missing or ["Longitudinal data on framing interventions"],
        "unknowns": ["Cross-cultural variation"],
        "strongest_countermodel": "Situational factors dominate cognitive framing",
        "break_conditions": ["If working memory is not the binding constraint"],
        "downstream_implications": ["Decision aids should target framing"],
        "optional_analysis": optional_analysis,
    }
    return json.dumps(dev)


def _make_review_json(
    *,
    identity_preserved=True,
    identity_drift=None,
    load_bearing_claim="Temporal discounting drives decisions",
    strongest_objection="No objection",
    objection_target="None",
    objection_is_load_bearing=False,
    counterevidence=None,
    evidence_debt=None,
    rebuild_required=False,
    rebuild_instructions=None,
    terminal_state="MODEL_READY",
    rationale="Model is sound",
) -> str:
    review = {
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
    return json.dumps(review)


def _make_rebuild_json(
    p_id: str,
    echo: dict,
    *,
    evidence_missing=None,
    evidence_debt=None,
    terminal_state="MODEL_READY",
    rationale="Rebuild addressed issues",
    rebuild_required=False,
) -> str:
    rebuild = {
        "development": {
            "p_id": p_id,
            "semantic_lock_echo": echo,
            "developed_model": "Rebuilt model with addressed issues",
            "what_became_more_precise": ["Addressed review feedback"],
            "assumptions": ["Stable cognitive architecture"],
            "supporting_basis": ["Additional evidence incorporated"],
            "evidence_missing": evidence_missing or [],
            "unknowns": ["Remaining uncertainties"],
            "strongest_countermodel": "Updated countermodel",
            "break_conditions": ["Updated break conditions"],
            "downstream_implications": ["Updated implications"],
            "optional_analysis": None,
        },
        "final_review": {
            "identity_preserved": True,
            "identity_drift": [],
            "load_bearing_claim": "Rebuilt model addresses prior objections",
            "strongest_objection": "No remaining load-bearing objection",
            "objection_target": "None",
            "objection_is_load_bearing": False,
            "counterevidence": [],
            "evidence_debt": evidence_debt or [],
            "rebuild_required": rebuild_required,
            "rebuild_instructions": [],
            "terminal_state": terminal_state,
            "rationale": rationale,
        },
    }
    return json.dumps(rebuild)


def _make_result(
    stage: str, raw_text: str, invocation_id: str = "test-inv"
) -> ProviderResult:
    return ProviderResult(
        invocation_id=invocation_id,
        stage=stage,
        raw_text=raw_text,
        model="scripted",
        transport="test",
        duration_ms=0,
        exit_code=0,
    )


def _setup_session(tmp_path: Path, identity_core: SemanticCore) -> tuple:
    """Create a session with one perspective and return (store, session, sid, pid, core)."""
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    store = SessionStore(base_dir=session_dir)
    sid = "test-session-deep"
    pid = "P1"

    session = store.create(session_id=sid, source=SOURCE, objective="Test objective")

    identity = PerspectiveIdentity(
        p_id=pid, candidate_id="cand_1", identity_core=identity_core
    )
    state = PerspectiveState(
        identity=identity,
        current_version=1,
        epistemics=Epistemics(
            supported=["Initial observation"],
            inferred=["Preliminary inference"],
            speculative=[],
            unknown=[],
            break_condition=[],
        ),
        deep_refs=[],
        terminal_state=None,
    )
    session.perspectives[pid] = state
    store.save(session)

    return store, session, sid, pid, identity_core


def _run(
    store, sid, pid, provider, tmp_path, expected_calls=2
) -> DeepRunResult:
    """Run deep and assert provider consumption."""
    trace_root = tmp_path / "traces"
    trace_root.mkdir(exist_ok=True)

    result = run_deep(
        session_id=sid,
        p_id=pid,
        session_store=store,
        provider=provider,
        trace_root=trace_root,
    )

    assert provider._call_count == expected_calls
    provider.assert_all_consumed()
    return result


# ─────────────────────────────────────────────────────────────────────────────
# D1: Semantic lock echo mismatch
# ─────────────────────────────────────────────────────────────────────────────


class TestD1LockEchoMismatch:
    """Development echoes a modified identity core; mismatch is detected."""

    def test_mismatch_detected_and_passed_to_review(self, tmp_path):
        core = _make_identity_core()
        store, session, sid, pid, _ = _setup_session(tmp_path, core)

        modified_echo = _echo_dict_modified(
            core, central_problem="DIFFERENT problem statement"
        )
        dev_json = _make_dev_json(pid, modified_echo)
        review_json = _make_review_json(
            identity_preserved=False,
            identity_drift=["central_problem changed"],
            terminal_state="RETURN_TO_EXPLORE",
            rationale="Identity echo mismatch",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)

        assert result.terminal_state == "RETURN_TO_EXPLORE"
        assert result.development.semantic_lock_echo.central_problem == "DIFFERENT problem statement"
        assert result.rebuilt_development is None
        assert result.review.identity_preserved is False
        assert result.p_id == pid

        # Session updated
        updated = store.load(sid)
        assert len(updated.deep_runs) == 1
        assert updated.deep_runs[0].terminal_state == "RETURN_TO_EXPLORE"
        assert updated.perspectives[pid].current_version == 2
        assert updated.perspectives[pid].terminal_state == "RETURN_TO_EXPLORE"

    def test_original_identity_core_unchanged_in_session(self, tmp_path):
        """Identity core in session is never mutated by Deep."""
        core = _make_identity_core()
        original_central = core.central_problem
        store, session, sid, pid, _ = _setup_session(tmp_path, core)

        modified_echo = _echo_dict_modified(core, central_problem="WRONG")
        dev_json = _make_dev_json(pid, modified_echo)
        review_json = _make_review_json(
            identity_preserved=False,
            terminal_state="RETURN_TO_EXPLORE",
            rationale="Mismatch",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        _run(store, sid, pid, provider, tmp_path)

        updated = store.load(sid)
        stored_core = updated.perspectives[pid].identity.identity_core
        assert stored_core.central_problem == original_central


# ─────────────────────────────────────────────────────────────────────────────
# D2: Legitimate refinement → MODEL_READY
# ─────────────────────────────────────────────────────────────────────────────


class TestD2LegitimateRefinement:
    """Development echoes exact identity core; review accepts → MODEL_READY."""

    def test_model_ready_two_calls(self, tmp_path):
        core = _make_identity_core()
        store, session, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json(
            terminal_state="MODEL_READY",
            rationale="Model is sound and well-developed",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)

        assert result.terminal_state == "MODEL_READY"
        assert result.review.terminal_state == "MODEL_READY"
        assert result.review.identity_preserved is True
        assert result.rebuilt_development is None
        assert result.review.rebuild_required is False

        # Session
        updated = store.load(sid)
        assert len(updated.deep_runs) == 1
        ref = updated.deep_runs[0]
        assert ref.p_id == pid
        assert ref.terminal_state == "MODEL_READY"
        assert updated.perspectives[pid].current_version == 2

    def test_development_preserves_p_id(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json()

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)
        assert result.development.p_id == pid

    def test_evidence_debt_empty_on_clean_model(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json(
            evidence_debt=[],
            terminal_state="MODEL_READY",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)
        assert result.review.evidence_debt == []


# ─────────────────────────────────────────────────────────────────────────────
# D3: Load-bearing objection → RETURN_TO_EXPLORE
# ─────────────────────────────────────────────────────────────────────────────


class TestD3LoadBearingObjection:
    """Review finds a load-bearing objection → RETURN_TO_EXPLORE."""

    def test_return_to_explore_on_load_bearing(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json(
            load_bearing_claim="Temporal discounting drives decisions",
            strongest_objection="The mechanism cannot explain cross-domain variation",
            objection_target="Core mechanism of temporal discounting",
            objection_is_load_bearing=True,
            rebuild_required=False,
            terminal_state="RETURN_TO_EXPLORE",
            rationale="Load-bearing objection cannot be resolved by rebuild",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)

        assert result.terminal_state == "RETURN_TO_EXPLORE"
        assert result.review.objection_is_load_bearing is True
        assert result.review.rebuild_required is False
        assert result.rebuilt_development is None

        updated = store.load(sid)
        assert updated.perspectives[pid].terminal_state == "RETURN_TO_EXPLORE"


# ─────────────────────────────────────────────────────────────────────────────
# D4: Peripheral objection → MODEL_READY
# ─────────────────────────────────────────────────────────────────────────────


class TestD4PeripheralObjection:
    """Review has a non-load-bearing objection → MODEL_READY."""

    def test_model_ready_with_peripheral_objection(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json(
            strongest_objection="Minor edge case in boundary conditions",
            objection_target="Boundary conditions",
            objection_is_load_bearing=False,
            terminal_state="MODEL_READY",
            rationale="Peripheral objection does not undermine core model",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)

        assert result.terminal_state == "MODEL_READY"
        assert result.review.objection_is_load_bearing is False
        assert result.review.strongest_objection == "Minor edge case in boundary conditions"


# ─────────────────────────────────────────────────────────────────────────────
# D5: NEED_EVIDENCE
# ─────────────────────────────────────────────────────────────────────────────


class TestD5NeedEvidence:
    """Review assigns NEED_EVIDENCE terminal state."""

    def test_need_evidence_terminal_state(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo, extra_evidence_missing=["Critical RCT data", "Longitudinal cohort results"])
        review_json = _make_review_json(
            evidence_debt=["Critical RCT data", "Longitudinal cohort results"],
            terminal_state="NEED_EVIDENCE",
            rationale="Critical evidence gaps prevent definitive assessment",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)

        assert result.terminal_state == "NEED_EVIDENCE"
        assert result.review.terminal_state == "NEED_EVIDENCE"
        assert len(result.review.evidence_debt) == 2
        assert "Critical RCT data" in result.review.evidence_debt

        updated = store.load(sid)
        assert updated.perspectives[pid].terminal_state == "NEED_EVIDENCE"


# ─────────────────────────────────────────────────────────────────────────────
# D6: Premature MODEL_READY rejected by review → RETURN_TO_EXPLORE
# ─────────────────────────────────────────────────────────────────────────────


class TestD6PrematureModelReady:
    """Development is flawed; review rejects with RETURN_TO_EXPLORE."""

    def test_review_overrides_to_return_to_explore(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json(
            identity_preserved=False,
            identity_drift=["Developed model diverges from core framing"],
            strongest_objection="Model lost the central mechanism",
            objection_is_load_bearing=True,
            rebuild_required=False,
            terminal_state="RETURN_TO_EXPLORE",
            rationale="Fundamental divergence requires fresh exploration",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)

        assert result.terminal_state == "RETURN_TO_EXPLORE"
        assert result.review.identity_preserved is False
        assert result.review.objection_is_load_bearing is True
        assert result.rebuilt_development is None

        updated = store.load(sid)
        assert updated.perspectives[pid].terminal_state == "RETURN_TO_EXPLORE"


# ─────────────────────────────────────────────────────────────────────────────
# D7: RETURN_TO_EXPLORE from review
# ─────────────────────────────────────────────────────────────────────────────


class TestD7ReturnToExplore:
    """Review explicitly assigns RETURN_TO_EXPLORE."""

    def test_explicit_return_to_explore(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json(
            terminal_state="RETURN_TO_EXPLORE",
            strongest_objection="Perspective may need fundamental reframing",
            objection_is_load_bearing=True,
            rationale="The perspective needs to be reconsidered from explore phase",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)

        assert result.terminal_state == "RETURN_TO_EXPLORE"
        assert result.review.rebuild_required is False


# ─────────────────────────────────────────────────────────────────────────────
# D8: Evidence debt survives rebuild
# ─────────────────────────────────────────────────────────────────────────────


class TestD8EvidenceDebtSurvivesRebuild:
    """Evidence debt from original development carries through rebuild."""

    def test_evidence_debt_preserved_after_rebuild(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(
            pid,
            echo,
            extra_evidence_missing=["Longitudinal data", "Cross-cultural studies"],
        )
        review_json = _make_review_json(
            evidence_debt=["Longitudinal data"],
            rebuild_required=True,
            rebuild_instructions=["Address missing longitudinal data"],
            terminal_state="NEED_EVIDENCE",
            rationale="Needs rebuild to address evidence gaps",
        )
        rebuild_json = _make_rebuild_json(
            pid,
            echo,
            evidence_missing=["Longitudinal data", "Cross-cultural studies"],
            evidence_debt=["Longitudinal data", "Cross-cultural studies"],
            terminal_state="NEED_EVIDENCE",
            rationale="Evidence gaps remain after rebuild",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
                "DEEP_REBUILD": [_make_result("DEEP_REBUILD", rebuild_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path, expected_calls=3)

        # Rebuild occurred
        assert result.rebuilt_development is not None
        assert result.rebuilt_development.p_id == pid

        # Evidence debt survived
        assert "Longitudinal data" in result.review.evidence_debt
        assert "Cross-cultural studies" in result.review.evidence_debt
        assert result.terminal_state == "NEED_EVIDENCE"

        # Original development preserved separately
        assert result.development.p_id == pid
        assert result.development is not result.rebuilt_development

        # Session
        updated = store.load(sid)
        assert updated.perspectives[pid].terminal_state == "NEED_EVIDENCE"

    def test_rebuild_model_ready_clears_debt(self, tmp_path):
        """Rebuild resolves all evidence debt → MODEL_READY."""
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo, extra_evidence_missing=["Some data"])
        review_json = _make_review_json(
            evidence_debt=["Some data"],
            rebuild_required=True,
            rebuild_instructions=["Incorporate missing data"],
            terminal_state="NEED_EVIDENCE",
        )
        rebuild_json = _make_rebuild_json(
            pid,
            echo,
            evidence_missing=[],
            evidence_debt=[],
            terminal_state="MODEL_READY",
            rationale="All evidence gaps resolved",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
                "DEEP_REBUILD": [_make_result("DEEP_REBUILD", rebuild_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path, expected_calls=3)
        assert result.terminal_state == "MODEL_READY"
        assert result.review.evidence_debt == []


# ─────────────────────────────────────────────────────────────────────────────
# D9: Non-causal perspective leaves optional analysis absent
# ─────────────────────────────────────────────────────────────────────────────


class TestD9NonCausalPerspective:
    """Non-causal perspective: optional_analysis stays null."""

    def test_optional_analysis_null(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo, optional_analysis=None)
        review_json = _make_review_json(
            terminal_state="MODEL_READY",
            rationale="Sound model without causal structure",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)

        assert result.development.optional_analysis is None
        assert result.rebuilt_development is None
        assert result.terminal_state == "MODEL_READY"

    def test_optional_analysis_null_through_rebuild(self, tmp_path):
        """Optional analysis stays null even through rebuild path."""
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo, optional_analysis=None)
        review_json = _make_review_json(
            rebuild_required=True,
            rebuild_instructions=["Clarify boundary conditions"],
            terminal_state="NEED_EVIDENCE",
        )
        rebuild_json = _make_rebuild_json(
            pid, echo, terminal_state="MODEL_READY"
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
                "DEEP_REBUILD": [_make_result("DEEP_REBUILD", rebuild_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path, expected_calls=3)

        assert result.development.optional_analysis is None
        assert result.rebuilt_development.optional_analysis is None
        assert result.terminal_state == "MODEL_READY"


# ─────────────────────────────────────────────────────────────────────────────
# D10: Source hash mismatch fails before provider call
# ─────────────────────────────────────────────────────────────────────────────


class TestD10SourceHashMismatch:
    """Source hash mismatch raises before any provider call."""

    def test_source_hash_mismatch_fails_closed(self, tmp_path):
        core = _make_identity_core()
        store, session, sid, pid, _ = _setup_session(tmp_path, core)

        # Tamper with source.md after session creation
        source_file = tmp_path / "sessions" / sid / "source.md"
        source_file.write_text("TAMPERED source content", encoding="utf-8")

        provider = DeepStageProvider({})

        with pytest.raises(RuntimeError, match="Source hash mismatch"):
            run_deep(
                session_id=sid,
                p_id=pid,
                session_store=store,
                provider=provider,
                trace_root=tmp_path / "traces",
            )

        assert provider._call_count == 0

    def test_no_session_mutation_on_source_mismatch(self, tmp_path):
        """Session is not mutated when source hash mismatches."""
        core = _make_identity_core()
        store, session, sid, pid, _ = _setup_session(tmp_path, core)

        original_version = session.perspectives[pid].current_version
        original_deep_runs = len(session.deep_runs)

        source_file = tmp_path / "sessions" / sid / "source.md"
        source_file.write_text("TAMPERED", encoding="utf-8")

        provider = DeepStageProvider({})

        with pytest.raises(RuntimeError):
            run_deep(
                session_id=sid,
                p_id=pid,
                session_store=store,
                provider=provider,
                trace_root=tmp_path / "traces",
            )

        # Verify no mutation
        updated = store.load(sid)
        assert updated.perspectives[pid].current_version == original_version
        assert len(updated.deep_runs) == original_deep_runs


# ─────────────────────────────────────────────────────────────────────────────
# D11: Unknown P-ID fails cleanly
# ─────────────────────────────────────────────────────────────────────────────


class TestD11UnknownPId:
    """Unknown P-ID raises ValueError before provider call."""

    def test_unknown_p_id_raises(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, _, _ = _setup_session(tmp_path, core)

        provider = DeepStageProvider({})

        with pytest.raises(ValueError, match="Unknown P-ID"):
            run_deep(
                session_id=sid,
                p_id="P99",
                session_store=store,
                provider=provider,
                trace_root=tmp_path / "traces",
            )

        assert provider._call_count == 0

    def test_no_session_mutation_on_unknown_p_id(self, tmp_path):
        core = _make_identity_core()
        store, session, sid, _, _ = _setup_session(tmp_path, core)

        original_version = session.perspectives["P1"].current_version

        provider = DeepStageProvider({})
        with pytest.raises(ValueError):
            run_deep(
                session_id=sid,
                p_id="P_NONEXISTENT",
                session_store=store,
                provider=provider,
                trace_root=tmp_path / "traces",
            )

        updated = store.load(sid)
        assert updated.perspectives["P1"].current_version == original_version
        assert len(updated.deep_runs) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Rebuild semantics
# ─────────────────────────────────────────────────────────────────────────────


class TestRebuildSemantics:
    """Additional rebuild-specific tests."""

    def test_second_rebuild_request_becomes_return_to_explore(self, tmp_path):
        """If rebuild's final_review requests another rebuild → RETURN_TO_EXPLORE."""
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json(
            rebuild_required=True,
            rebuild_instructions=["Fix issue A"],
            terminal_state="NEED_EVIDENCE",
        )
        # Rebuild's final_review also requests rebuild → invalid
        rebuild_json = _make_rebuild_json(
            pid,
            echo,
            terminal_state="NEED_EVIDENCE",
            rationale="Still needs work",
            rebuild_required=True,
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
                "DEEP_REBUILD": [_make_result("DEEP_REBUILD", rebuild_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path, expected_calls=3)

        assert result.terminal_state == "RETURN_TO_EXPLORE"
        assert result.review.rebuild_required is False
        assert "Second rebuild request is invalid" in result.review.rationale
        assert result.rebuilt_development is not None

    def test_rebuild_lock_echo_mismatch_becomes_return_to_explore(self, tmp_path):
        """If rebuilt development has lock echo mismatch → RETURN_TO_EXPLORE."""
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json(
            rebuild_required=True,
            rebuild_instructions=["Fix something"],
            terminal_state="NEED_EVIDENCE",
        )
        # Rebuilt development has wrong echo
        modified_echo = _echo_dict_modified(core, mechanism="WRONG mechanism")
        rebuild_json = _make_rebuild_json(
            pid,
            modified_echo,
            terminal_state="MODEL_READY",
            rationale="Rebuilt and ready",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
                "DEEP_REBUILD": [_make_result("DEEP_REBUILD", rebuild_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path, expected_calls=3)

        assert result.terminal_state == "RETURN_TO_EXPLORE"
        assert result.review.identity_preserved is False
        assert "mismatch persists after rebuild" in result.review.rationale

    def test_rebuild_preserves_original_development(self, tmp_path):
        """Original development is preserved alongside rebuilt development."""
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json(
            rebuild_required=True,
            rebuild_instructions=["Improve model"],
            terminal_state="NEED_EVIDENCE",
        )
        rebuild_json = _make_rebuild_json(
            pid,
            echo,
            terminal_state="MODEL_READY",
            rationale="Fixed",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
                "DEEP_REBUILD": [_make_result("DEEP_REBUILD", rebuild_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path, expected_calls=3)

        # Both developments present
        assert result.development is not None
        assert result.rebuilt_development is not None
        # Original has original text
        assert result.development.developed_model == "Refined model of cognitive framing"
        # Rebuilt has rebuilt text
        assert result.rebuilt_development.developed_model == "Rebuilt model with addressed issues"

    def test_rebuild_success_model_ready(self, tmp_path):
        """Successful rebuild → MODEL_READY."""
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json(
            rebuild_required=True,
            rebuild_instructions=["Tighten assumptions"],
            terminal_state="NEED_EVIDENCE",
        )
        rebuild_json = _make_rebuild_json(
            pid,
            echo,
            terminal_state="MODEL_READY",
            rationale="All issues resolved",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
                "DEEP_REBUILD": [_make_result("DEEP_REBUILD", rebuild_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path, expected_calls=3)

        assert result.terminal_state == "MODEL_READY"
        assert result.review.terminal_state == "MODEL_READY"
        assert result.review.rebuild_required is False

        updated = store.load(sid)
        assert updated.perspectives[pid].current_version == 2
        assert updated.perspectives[pid].terminal_state == "MODEL_READY"


# ─────────────────────────────────────────────────────────────────────────────
# Persistence semantics
# ─────────────────────────────────────────────────────────────────────────────


class TestPersistenceSemantics:
    """Verify session persistence and trace artifacts."""

    def test_deep_run_ref_appended(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json()

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)

        updated = store.load(sid)
        assert len(updated.deep_runs) == 1
        ref = updated.deep_runs[0]
        assert ref.p_id == pid
        assert ref.terminal_state == "MODEL_READY"
        assert ref.deep_id == result.deep_id
        assert ref.trace_ref == result.run_id
        assert updated.perspectives[pid].deep_refs == [result.deep_id]
    def test_version_increments_exactly_once(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json()

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        _run(store, sid, pid, provider, tmp_path)

        updated = store.load(sid)
        assert updated.perspectives[pid].current_version == 2

    def test_terminal_state_visible_in_state(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json(
            terminal_state="NEED_EVIDENCE",
            rationale="Evidence gaps",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)

        updated = store.load(sid)
        assert updated.perspectives[pid].terminal_state == "NEED_EVIDENCE"
        assert result.terminal_state == "NEED_EVIDENCE"

    def test_trace_artifacts_written(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json()

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)

        trace_dir = tmp_path / "traces" / result.run_id
        assert trace_dir.exists()
        assert (trace_dir / "deep_request.json").exists()
        assert (trace_dir / "development.json").exists()
        assert (trace_dir / "review.json").exists()
        assert (trace_dir / "result.json").exists()
        assert (trace_dir / "provider-invocations.json").exists()

        # Two provider invocations recorded
        invocations = json.loads(
            (trace_dir / "provider-invocations.json").read_text()
        )
        assert len(invocations) == 2
        stages = [inv["stage"] for inv in invocations]
        assert stages == ["DEEP_DEVELOP", "DEEP_REVIEW"]

    def test_trace_artifacts_include_rebuild(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json(
            rebuild_required=True,
            rebuild_instructions=["Fix"],
            terminal_state="NEED_EVIDENCE",
        )
        rebuild_json = _make_rebuild_json(pid, echo)

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
                "DEEP_REBUILD": [_make_result("DEEP_REBUILD", rebuild_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path, expected_calls=3)

        trace_dir = tmp_path / "traces" / result.run_id
        assert (trace_dir / "development.json").exists()
        assert (trace_dir / "review.json").exists()
        assert (trace_dir / "rebuild.json").exists()
        assert (trace_dir / "rebuilt_development.json").exists()
        rebuild_data = json.loads((trace_dir / "rebuild.json").read_text())
        assert "development" in rebuild_data
        assert "final_review" in rebuild_data
        invocations = json.loads(
            (trace_dir / "provider-invocations.json").read_text()
        )
        assert len(invocations) == 3
        stages = [inv["stage"] for inv in invocations]
        assert stages == ["DEEP_DEVELOP", "DEEP_REVIEW", "DEEP_REBUILD"]


# ─────────────────────────────────────────────────────────────────────────────
# Helper function tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHelpers:
    """Test internal helper functions."""

    def test_normalize_semantic_core_deterministic(self):
        core = _make_identity_core()
        n1 = _normalize_semantic_core(core)
        n2 = _normalize_semantic_core(core)
        assert n1 == n2

    def test_normalize_semantic_core_order_independent(self):
        """Two equivalent cores produce same normalization regardless of construction order."""
        c1 = SemanticCore(
            central_problem="A",
            mechanism="B",
            load_bearing_claim="C",
        )
        c2 = SemanticCore(
            load_bearing_claim="C",
            mechanism="B",
            central_problem="A",
        )
        assert _normalize_semantic_core(c1) == _normalize_semantic_core(c2)

    def test_normalize_semantic_core_different_values(self):
        c1 = SemanticCore(
            central_problem="A",
            mechanism="B",
            load_bearing_claim="C",
        )
        c2 = SemanticCore(
            central_problem="DIFFERENT",
            mechanism="B",
            load_bearing_claim="C",
        )
        assert _normalize_semantic_core(c1) != _normalize_semantic_core(c2)

    def test_extract_json_direct(self):
        data = {"key": "value", "num": 42}
        result = _extract_json(json.dumps(data))
        assert result == data

    def test_extract_json_code_fence(self):
        data = {"key": "value"}
        text = f"Here is the result:\n```json\n{json.dumps(data)}\n```\nDone."
        result = _extract_json(text)
        assert result == data

    def test_extract_json_embedded(self):
        data = {"key": "value"}
        text = f"Preamble text {json.dumps(data)} trailing text"
        result = _extract_json(text)
        assert result == data

    def test_extract_json_no_json_raises(self):
        with pytest.raises(ValueError, match="No JSON object found"):
            _extract_json("no json here")


# ─────────────────────────────────────────────────────────────────────────────
# DeepRunResult round-trip
# ─────────────────────────────────────────────────────────────────────────────


class TestDeepRunResultRoundTrip:
    def test_to_dict_from_dict(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json()

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)

        data = result.to_dict()
        assert data["p_id"] == pid
        assert data["terminal_state"] == "MODEL_READY"
        assert data["rebuilt_development"] is None
        assert "development" in data
        assert "review" in data

    def test_to_dict_with_rebuild(self, tmp_path):
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        echo = _echo_dict(core)
        dev_json = _make_dev_json(pid, echo)
        review_json = _make_review_json(
            rebuild_required=True,
            rebuild_instructions=["Fix"],
            terminal_state="NEED_EVIDENCE",
        )
        rebuild_json = _make_rebuild_json(pid, echo)

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
                "DEEP_REBUILD": [_make_result("DEEP_REBUILD", rebuild_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path, expected_calls=3)

        data = result.to_dict()
        assert data["rebuilt_development"] is not None
        assert data["rebuilt_development"]["p_id"] == pid


# ─────────────────────────────────────────────────────────────────────────────
# Atomic session behavior
# ─────────────────────────────────────────────────────────────────────────────



class TestAtomicSessionBehavior:
    """Verify session is saved only after successful completion."""

    def test_provider_failure_does_not_mutate_session(self, tmp_path):
        """If provider fails mid-run, session should not be mutated."""
        core = _make_identity_core()
        store, session, sid, pid, _ = _setup_session(tmp_path, core)

        from prism.perspective_core.provider import TransportError

        class FailingProvider:
            def __init__(self):
                self._call_count = 0

            def complete(self, prompt, *, stage, invocation_id):
                self._call_count += 1
                if stage == "DEEP_REVIEW":
                    raise TransportError("Simulated failure")
                echo = _echo_dict(core)
                return _make_result(
                    stage,
                    _make_dev_json(pid, echo),
                    invocation_id=invocation_id,
                )

        provider = FailingProvider()

        with pytest.raises(TransportError):
            run_deep(
                session_id=sid,
                p_id=pid,
                session_store=store,
                provider=provider,
                trace_root=tmp_path / "traces",
            )

        # Session should not have new deep runs
        updated = store.load(sid)
        assert len(updated.deep_runs) == 0
        assert updated.perspectives[pid].current_version == 1


# ─────────────────────────────────────────────────────────────────────────────
# Code-enforced lock echo gate (§10.3 enforcement)
# ─────────────────────────────────────────────────────────────────────────────


class TestCodeEnforcedLockEchoGate:
    """Verify §10.3 code-enforced gate: mismatch without rebuild → RETURN_TO_EXPLORE."""

    def test_mismatch_with_review_model_ready_forces_return_to_explore(self, tmp_path):
        """Review returns MODEL_READY despite mismatch → code forces RETURN_TO_EXPLORE."""
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        # Development echoes a MODIFIED identity core
        modified_echo = _echo_dict_modified(core, central_problem="WRONG problem")
        dev_json = _make_dev_json(pid, modified_echo)

        # Review incorrectly returns MODEL_READY without requesting rebuild
        review_json = _make_review_json(
            identity_preserved=True,
            terminal_state="MODEL_READY",
            rationale="Reviewer says everything is fine",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)

        # Code gate must override review's MODEL_READY → RETURN_TO_EXPLORE
        assert result.terminal_state == "RETURN_TO_EXPLORE"
        assert result.review.terminal_state == "RETURN_TO_EXPLORE"
        assert result.review.identity_preserved is False
        assert result.rebuilt_development is None
        assert "Code gate" in result.review.rationale

        # Session reflects the forced terminal
        updated = store.load(sid)
        assert updated.perspectives[pid].terminal_state == "RETURN_TO_EXPLORE"

    def test_mismatch_with_need_evidence_forces_return_to_explore(self, tmp_path):
        """Review returns NEED_EVIDENCE despite mismatch → code forces RETURN_TO_EXPLORE."""
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        modified_echo = _echo_dict_modified(core, mechanism="WRONG mechanism")
        dev_json = _make_dev_json(pid, modified_echo)

        # Review returns NEED_EVIDENCE without requesting rebuild
        review_json = _make_review_json(
            evidence_debt=["Missing RCT data"],
            terminal_state="NEED_EVIDENCE",
            rationale="Evidence gaps remain",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path)

        # Code gate overrides NEED_EVIDENCE → RETURN_TO_EXPLORE
        assert result.terminal_state == "RETURN_TO_EXPLORE"
        assert result.rebuilt_development is None
        assert "Code gate" in result.review.rationale

    def test_mismatch_with_rebuild_request_proceeds_to_rebuild(self, tmp_path):
        """Review requests rebuild despite mismatch → code allows rebuild path."""
        core = _make_identity_core()
        store, _, sid, pid, _ = _setup_session(tmp_path, core)

        modified_echo = _echo_dict_modified(core, central_problem="WRONG")
        dev_json = _make_dev_json(pid, modified_echo)

        # Review requests rebuild (code gate allows this)
        review_json = _make_review_json(
            identity_preserved=False,
            rebuild_required=True,
            rebuild_instructions=["Fix the identity echo"],
            terminal_state="NEED_EVIDENCE",
            rationale="Lock echo mismatch detected",
        )

        # Rebuild restores the correct echo
        correct_echo = _echo_dict(core)
        rebuild_json = _make_rebuild_json(
            pid,
            correct_echo,
            terminal_state="MODEL_READY",
            rationale="Identity restored",
        )

        provider = DeepStageProvider(
            {
                "DEEP_DEVELOP": [_make_result("DEEP_DEVELOP", dev_json)],
                "DEEP_REVIEW": [_make_result("DEEP_REVIEW", review_json)],
                "DEEP_REBUILD": [_make_result("DEEP_REBUILD", rebuild_json)],
            }
        )

        result = _run(store, sid, pid, provider, tmp_path, expected_calls=3)

        # Rebuild path was taken (not blocked by code gate)
        assert result.rebuilt_development is not None
        assert result.terminal_state == "MODEL_READY"


# ─────────────────────────────────────────────────────────────────────────────
# Prompt asset loading verification
# ─────────────────────────────────────────────────────────────────────────────


class TestPromptAssetLoading:
    """Verify Deep prompt builders load from .md assets, not inline duplicates."""

    def test_develop_prompt_includes_distinctive_asset_instruction(self, tmp_path):
        """DEEP_DEVELOP prompt includes distinctive text from deep_develop.md."""
        core = _make_identity_core()
        identity_core_json = json.dumps(core.to_dict(), indent=2)
        constraints_json = json.dumps({"entries": []})
        state_json = json.dumps({"version": 1})

        prompt = _build_develop_prompt(
            source="test source",
            objective="test objective",
            identity_core_json=identity_core_json,
            constraints_json=constraints_json,
            state_json=state_json,
            p_id="P1",
        )

        # Distinctive text from deep_develop.md (lines 39-41)
        assert "deterministic normalized equality check" in prompt
        # Distinctive text from deep_develop.md (line 42)
        assert "Do not fabricate causal structure" in prompt

    def test_review_prompt_includes_distinctive_asset_instruction(self, tmp_path):
        """DEEP_REVIEW prompt includes distinctive text from deep_review.md."""
        core = _make_identity_core()
        identity_core_json = json.dumps(core.to_dict(), indent=2)
        development_json = json.dumps({"developed_model": "test"})

        prompt = _build_review_prompt(
            source="test source",
            objective="test objective",
            identity_core_json=identity_core_json,
            development_json=development_json,
            identity_echo_mismatch=False,
            p_id="P1",
        )

        # Distinctive text from deep_review.md (lines 38-40)
        assert "Evidence debt is acknowledged but" in prompt
        # Distinctive text from deep_review.md (lines 50-52)
        assert "objection_is_load_bearing: true" in prompt

    def test_review_prompt_includes_mismatch_warning(self, tmp_path):
        """DEEP_REVIEW prompt includes mismatch warning when flag is True."""
        core = _make_identity_core()
        identity_core_json = json.dumps(core.to_dict(), indent=2)
        development_json = json.dumps({"developed_model": "test"})

        prompt = _build_review_prompt(
            source="test source",
            objective="test objective",
            identity_core_json=identity_core_json,
            development_json=development_json,
            identity_echo_mismatch=True,
            p_id="P1",
        )

        assert "Identity Echo Mismatch Detected" in prompt
        assert "identity_preserved" in prompt

    def test_rebuild_prompt_includes_distinctive_asset_instruction(self, tmp_path):
        """DEEP_REBUILD prompt includes distinctive text from deep_rebuild.md."""
        core = _make_identity_core()
        identity_core_json = json.dumps(core.to_dict(), indent=2)
        development_json = json.dumps({"developed_model": "test"})
        review_json = json.dumps({"rebuild_instructions": ["fix X"]})
        constraints_json = json.dumps({"entries": []})

        prompt = _build_rebuild_prompt(
            source="test source",
            objective="test objective",
            identity_core_json=identity_core_json,
            development_json=development_json,
            review_json=review_json,
            constraints_json=constraints_json,
            p_id="P1",
        )

        # Distinctive text from deep_rebuild.md (lines 8-9)
        assert "There is no fourth call" in prompt
        # Distinctive text from deep_rebuild.md (line 60)
        assert "no recursive rebuild" in prompt
