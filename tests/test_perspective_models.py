"""Tests for Perspective Core v0 models.

Covers:
- ConstraintLedger ID-based supersession
- Full PassRecord round-trip serialization
- Validation helpers
- MergeTarget integrity
"""

import pytest

from prism.perspective_core import (
    ConstraintEntry,
    ConstraintLedger,
    DeepRunRef,
    Diagnosis,
    Epistemics,
    MergeTarget,
    PassRecord,
    PerspectiveCandidate,
    PerspectiveIdentity,
    PerspectiveSession,
    PerspectiveState,
    ReturnPath,
    SelectionRecord,
    SemanticCore,
    ValidationIssue,
    compute_source_hash,
    validate_candidates,
    validate_selections,
)


# ─────────────────────────────────────────────────────────────────────────────
# ConstraintLedger supersession (§6.1, requirement 2)
# ─────────────────────────────────────────────────────────────────────────────


def test_constraint_ledger_add_new_constraint():
    """Adding a new constraint appends it as active."""
    ledger = ConstraintLedger()
    ledger.add(constraint_id="c1", value="Must be clear", kind="hard")

    assert len(ledger.entries) == 1
    assert ledger.entries[0].constraint_id == "c1"
    assert ledger.entries[0].status == "active"
    assert ledger.entries[0].value == "Must be clear"


def test_constraint_ledger_supersession_by_id():
    """Adding a constraint with same ID supersedes the previous one."""
    ledger = ConstraintLedger()
    ledger.add(constraint_id="c1", value="Must be clear", kind="hard")
    ledger.add(constraint_id="c1", value="Must be very clear", kind="hard")

    assert len(ledger.entries) == 2
    assert ledger.entries[0].status == "superseded"
    assert ledger.entries[1].status == "active"
    assert ledger.entries[1].value == "Must be very clear"


def test_constraint_ledger_different_ids_same_value_coexist():
    """Different constraint IDs with same value can coexist."""
    ledger = ConstraintLedger()
    ledger.add(constraint_id="c1", value="Be clear", kind="hard")
    ledger.add(constraint_id="c2", value="Be clear", kind="preference")

    assert len(ledger.entries) == 2
    assert ledger.entries[0].status == "active"
    assert ledger.entries[1].status == "active"

def test_constraint_ledger_active_entries():
    """active_entries() returns only non-superseded constraints."""
    ledger = ConstraintLedger()
    ledger.add(constraint_id="c1", value="First", kind="hard")
    ledger.add(constraint_id="c2", value="Second", kind="hard")
    ledger.add(constraint_id="c1", value="First updated", kind="hard")

    active = ledger.active_entries()
    assert len(active) == 2
    assert {e.constraint_id for e in active} == {"c1", "c2"}
    # c2 (active) comes before c1_updated (active) in insertion order; c1_v1 is superseded
    active_by_id = {e.constraint_id: e.value for e in active}
    assert active_by_id["c1"] == "First updated"
    assert active_by_id["c2"] == "Second"


def test_constraint_ledger_serialization():
    """ConstraintLedger round-trips through dict."""
    ledger = ConstraintLedger()
    ledger.add(constraint_id="c1", value="Value 1", kind="hard", provenance_turn="T1")
    ledger.add(constraint_id="c2", value="Value 2", kind="preference")
    ledger.add(constraint_id="c1", value="Value 1 updated", kind="hard")

    data = ledger.to_dict()
    restored = ConstraintLedger.from_dict(data)

    assert len(restored.entries) == 3
    assert restored.entries[0].status == "superseded"
    assert restored.entries[2].status == "active"


# ─────────────────────────────────────────────────────────────────────────────
# PassRecord full round-trip (§6.9, requirement 1)
# ─────────────────────────────────────────────────────────────────────────────


def test_pass_record_full_round_trip():
    """PassRecord preserves full candidates and selections through serialization."""
    semantic_core = SemanticCore(
        central_problem="Test problem",
        mechanism="Test mechanism",
        load_bearing_claim="Test claim",
        downstream_consequences=["consequence 1"],
    )

    candidate = PerspectiveCandidate(
        candidate_id="cand_1",
        semantic_core=semantic_core,
        preserved=["preserved 1"],
        default_frame="default frame",
        blind_spot="blind spot",
        operator_ids=["op1"],
        shift="shift description",
        perspective="perspective text",
        new_consequences=["new consequence"],
        return_path=ReturnPath(
            dimension_changed="dimension",
            consequence_chain=["chain link"],
            why_it_matters="why",
        ),
        epistemics=Epistemics(
            supported=["supported"],
            inferred=["inferred"],
            speculative=["speculative"],
            unknown=["unknown"],
            break_condition=["break"],
        ),
    )

    selection = SelectionRecord(
        candidate_id="cand_1",
        admissible=True,
        constraint_failures=[],
        structurally_distinct=True,
        novelty_dimensions=["dimension"],
        nearest_candidate_id=None,
        nearest_existing_p_id=None,
        standalone_quality="strong",
        marginal_contribution="high",
        disposition="KEEP",
        merge_target=None,
        reason="Strong candidate",
    )

    pass_record = PassRecord(
        pass_id="pass_1",
        mode="normal",
        created_at="2026-08-23T10:00:00Z",
        diagnosis=Diagnosis(
            central_problem="Test problem",
            search_profile="normal",
            priority_dimensions=["dim1"],
        ),
        candidates=[candidate],
        selections=[selection],
        kept_p_ids=["P1"],
        provider_invocation_ids=["inv_1", "inv_2"],
        trace_ref="traces/run_1",
    )

    # Serialize and deserialize
    data = pass_record.to_dict()
    restored = PassRecord.from_dict(data)

    # Verify full preservation
    assert restored.pass_id == pass_record.pass_id
    assert restored.mode == pass_record.mode
    assert len(restored.candidates) == 1
    assert restored.candidates[0].candidate_id == "cand_1"
    assert restored.candidates[0].semantic_core.central_problem == "Test problem"
    assert len(restored.selections) == 1
    assert restored.selections[0].disposition == "KEEP"
    assert restored.kept_p_ids == ["P1"]
    assert restored.provider_invocation_ids == ["inv_1", "inv_2"]


def test_pass_record_with_merge_selection():
    """PassRecord preserves MERGE selections with targets."""
    selection = SelectionRecord(
        candidate_id="cand_2",
        admissible=True,
        constraint_failures=[],
        structurally_distinct=False,
        novelty_dimensions=[],
        nearest_candidate_id="cand_1",
        nearest_existing_p_id=None,
        standalone_quality="borderline",
        marginal_contribution="low",
        disposition="MERGE",
        merge_target=MergeTarget(kind="candidate", target_id="cand_1"),
        reason="Similar to cand_1",
    )

    data = selection.to_dict()
    restored = SelectionRecord.from_dict(data)

    assert restored.disposition == "MERGE"
    assert restored.merge_target is not None
    assert restored.merge_target.kind == "candidate"
    assert restored.merge_target.target_id == "cand_1"


# ─────────────────────────────────────────────────────────────────────────────
# Validation helpers (§6.5, requirement 5)
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_candidates_unique_ids():
    """validate_candidates detects duplicate candidate IDs."""
    core = SemanticCore(
        central_problem="Test",
        mechanism="Test",
        load_bearing_claim="Test",
    )

    candidate1 = PerspectiveCandidate(
        candidate_id="cand_1",
        semantic_core=core,
        preserved=[],
        default_frame="frame",
        blind_spot="spot",
        operator_ids=[],
        shift="shift",
        perspective="persp",
        new_consequences=[],
        return_path=ReturnPath("dim", ["chain"], "why"),
        epistemics=Epistemics([], [], [], [], []),
    )

    # Duplicate ID
    candidate2 = PerspectiveCandidate(
        candidate_id="cand_1",
        semantic_core=core,
        preserved=[],
        default_frame="frame",
        blind_spot="spot",
        operator_ids=[],
        shift="shift",
        perspective="persp",
        new_consequences=[],
        return_path=ReturnPath("dim", ["chain"], "why"),
        epistemics=Epistemics([], [], [], [], []),
    )

    issues = validate_candidates([candidate1, candidate2])
    assert "cand_1" in issues
    assert any(i.code == "DUPLICATE_CANDIDATE_ID" for i in issues["cand_1"])


def test_validate_selections_missing_selection():
    """validate_selections detects missing selection for candidate."""
    core = SemanticCore("Test", "Test", "Test")
    candidate = PerspectiveCandidate(
        candidate_id="cand_1",
        semantic_core=core,
        preserved=[],
        default_frame="frame",
        blind_spot="spot",
        operator_ids=[],
        shift="shift",
        perspective="persp",
        new_consequences=[],
        return_path=ReturnPath("dim", ["chain"], "why"),
        epistemics=Epistemics([], [], [], [], []),
    )

    issues = validate_selections([candidate], [])
    assert "cand_1" in issues
    assert any(i.code == "MISSING_SELECTION" for i in issues["cand_1"])


def test_validate_selections_merge_target_validation():
    """validate_selections validates MERGE target existence and non-self."""
    core = SemanticCore("Test", "Test", "Test")
    candidate = PerspectiveCandidate(
        candidate_id="cand_1",
        semantic_core=core,
        preserved=[],
        default_frame="frame",
        blind_spot="spot",
        operator_ids=[],
        shift="shift",
        perspective="persp",
        new_consequences=[],
        return_path=ReturnPath("dim", ["chain"], "why"),
        epistemics=Epistemics([], [], [], [], []),
    )

    # Self-merge
    selection = SelectionRecord(
        candidate_id="cand_1",
        admissible=True,
        constraint_failures=[],
        structurally_distinct=True,
        novelty_dimensions=[],
        nearest_candidate_id=None,
        nearest_existing_p_id=None,
        standalone_quality="strong",
        marginal_contribution="high",
        disposition="MERGE",
        merge_target=MergeTarget(kind="candidate", target_id="cand_1"),
        reason="Self merge",
    )

    issues = validate_selections([candidate], [selection])
    assert "cand_1" in issues
    assert any(i.code == "MERGE_SELF" for i in issues["cand_1"])


def test_validate_selections_merge_to_perspective():
    """validate_selections validates MERGE to existing P-ID."""
    core = SemanticCore("Test", "Test", "Test")
    candidate = PerspectiveCandidate(
        candidate_id="cand_1",
        semantic_core=core,
        preserved=[],
        default_frame="frame",
        blind_spot="spot",
        operator_ids=[],
        shift="shift",
        perspective="persp",
        new_consequences=[],
        return_path=ReturnPath("dim", ["chain"], "why"),
        epistemics=Epistemics([], [], [], [], []),
    )

    # Merge to non-existent P-ID
    selection = SelectionRecord(
        candidate_id="cand_1",
        admissible=True,
        constraint_failures=[],
        structurally_distinct=True,
        novelty_dimensions=[],
        nearest_candidate_id=None,
        nearest_existing_p_id="P99",
        standalone_quality="strong",
        marginal_contribution="high",
        disposition="MERGE",
        merge_target=MergeTarget(kind="perspective", target_id="P99"),
        reason="Merge to P99",
    )

    issues = validate_selections([candidate], [selection], existing_p_ids={"P1", "P2"})
    assert "cand_1" in issues
    assert any(i.code == "INVALID_MERGE_TARGET" for i in issues["cand_1"])


def test_validate_selections_valid_merge():
    """validate_selections accepts valid MERGE targets."""
    core = SemanticCore("Test", "Test", "Test")
    candidate1 = PerspectiveCandidate(
        candidate_id="cand_1",
        semantic_core=core,
        preserved=[],
        default_frame="frame",
        blind_spot="spot",
        operator_ids=[],
        shift="shift",
        perspective="persp",
        new_consequences=[],
        return_path=ReturnPath("dim", ["chain"], "why"),
        epistemics=Epistemics([], [], [], [], []),
    )
    candidate2 = PerspectiveCandidate(
        candidate_id="cand_2",
        semantic_core=core,
        preserved=[],
        default_frame="frame",
        blind_spot="spot",
        operator_ids=[],
        shift="shift",
        perspective="persp",
        new_consequences=[],
        return_path=ReturnPath("dim", ["chain"], "why"),
        epistemics=Epistemics([], [], [], [], []),
    )

    selection1 = SelectionRecord(
        candidate_id="cand_1",
        admissible=True,
        constraint_failures=[],
        structurally_distinct=True,
        novelty_dimensions=[],
        nearest_candidate_id=None,
        nearest_existing_p_id=None,
        standalone_quality="strong",
        marginal_contribution="high",
        disposition="KEEP",
        merge_target=None,
        reason="Keep",
    )

    selection2 = SelectionRecord(
        candidate_id="cand_2",
        admissible=True,
        constraint_failures=[],
        structurally_distinct=True,
        novelty_dimensions=[],
        nearest_candidate_id="cand_1",
        nearest_existing_p_id=None,
        standalone_quality="strong",
        marginal_contribution="low",
        disposition="MERGE",
        merge_target=MergeTarget(kind="candidate", target_id="cand_1"),
        reason="Merge to cand_1",
    )

    issues = validate_selections([candidate1, candidate2], [selection1, selection2])
    assert "cand_1" not in issues
    assert "cand_2" not in issues

def test_validate_selections_rejects_inadmissible_keep():
    """validate_selections rejects KEEP when candidate is marked not admissible."""
    core = SemanticCore("Test", "Test", "Test")
    candidate = PerspectiveCandidate(
        candidate_id="cand_1",
        semantic_core=core,
        preserved=[],
        default_frame="frame",
        blind_spot="spot",
        operator_ids=[],
        shift="shift",
        perspective="persp",
        new_consequences=[],
        return_path=ReturnPath("dim", ["chain"], "why"),
        epistemics=Epistemics([], [], [], [], []),
    )
    selection = SelectionRecord(
        candidate_id="cand_1",
        admissible=False,
        constraint_failures=[],
        structurally_distinct=True,
        novelty_dimensions=[],
        nearest_candidate_id=None,
        nearest_existing_p_id=None,
        standalone_quality="strong",
        marginal_contribution="high",
        disposition="KEEP",
        merge_target=None,
        reason="Inadmissible but marked KEEP",
    )
    issues = validate_selections([candidate], [selection])
    assert "cand_1" in issues
    assert any(i.code == "INADMISSIBLE_KEEP" for i in issues["cand_1"])


def test_validate_selections_rejects_keep_with_constraint_failures():
    """validate_selections rejects KEEP when candidate has constraint failures."""
    core = SemanticCore("Test", "Test", "Test")
    candidate = PerspectiveCandidate(
        candidate_id="cand_1",
        semantic_core=core,
        preserved=[],
        default_frame="frame",
        blind_spot="spot",
        operator_ids=[],
        shift="shift",
        perspective="persp",
        new_consequences=[],
        return_path=ReturnPath("dim", ["chain"], "why"),
        epistemics=Epistemics([], [], [], [], []),
    )
    selection = SelectionRecord(
        candidate_id="cand_1",
        admissible=True,
        constraint_failures=["violates no-unregulated-systems constraint"],
        structurally_distinct=True,
        novelty_dimensions=[],
        nearest_candidate_id=None,
        nearest_existing_p_id=None,
        standalone_quality="strong",
        marginal_contribution="high",
        disposition="KEEP",
        merge_target=None,
        reason="Has constraint failures but marked KEEP",
    )
    issues = validate_selections([candidate], [selection])
    assert "cand_1" in issues
    assert any(i.code == "KEEP_WITH_CONSTRAINT_FAILURES" for i in issues["cand_1"])


def test_validate_selections_rejects_inadmissible_keep_with_constraint_failures():
    """validate_selections reports both issues when KEEP is inadmissible and has constraint failures."""
    core = SemanticCore("Test", "Test", "Test")
    candidate = PerspectiveCandidate(
        candidate_id="cand_1",
        semantic_core=core,
        preserved=[],
        default_frame="frame",
        blind_spot="spot",
        operator_ids=[],
        shift="shift",
        perspective="persp",
        new_consequences=[],
        return_path=ReturnPath("dim", ["chain"], "why"),
        epistemics=Epistemics([], [], [], [], []),
    )
    selection = SelectionRecord(
        candidate_id="cand_1",
        admissible=False,
        constraint_failures=["violates hard constraint"],
        structurally_distinct=True,
        novelty_dimensions=[],
        nearest_candidate_id=None,
        nearest_existing_p_id=None,
        standalone_quality="strong",
        marginal_contribution="high",
        disposition="KEEP",
        merge_target=None,
        reason="Inadmissible with failures but marked KEEP",
    )
    issues = validate_selections([candidate], [selection])
    assert "cand_1" in issues
    codes = {i.code for i in issues["cand_1"]}
    assert "INADMISSIBLE_KEEP" in codes
    assert "KEEP_WITH_CONSTRAINT_FAILURES" in codes


def test_validate_selections_rejects_non_merge_with_merge_target():
    """validate_selections rejects non-MERGE dispositions carrying a merge_target."""
    core = SemanticCore("Test", "Test", "Test")
    candidate1 = PerspectiveCandidate(
        candidate_id="cand_1",
        semantic_core=core,
        preserved=[],
        default_frame="frame",
        blind_spot="spot",
        operator_ids=[],
        shift="shift",
        perspective="persp",
        new_consequences=[],
        return_path=ReturnPath("dim", ["chain"], "why"),
        epistemics=Epistemics([], [], [], [], []),
    )
    candidate2 = PerspectiveCandidate(
        candidate_id="cand_2",
        semantic_core=core,
        preserved=[],
        default_frame="frame",
        blind_spot="spot",
        operator_ids=[],
        shift="shift",
        perspective="persp",
        new_consequences=[],
        return_path=ReturnPath("dim", ["chain"], "why"),
        epistemics=Epistemics([], [], [], [], []),
    )
    candidate3 = PerspectiveCandidate(
        candidate_id="cand_3",
        semantic_core=core,
        preserved=[],
        default_frame="frame",
        blind_spot="spot",
        operator_ids=[],
        shift="shift",
        perspective="persp",
        new_consequences=[],
        return_path=ReturnPath("dim", ["chain"], "why"),
        epistemics=Epistemics([], [], [], [], []),
    )

    # KEEP with merge_target
    sel_keep = SelectionRecord(
        candidate_id="cand_1",
        admissible=True,
        constraint_failures=[],
        structurally_distinct=True,
        novelty_dimensions=[],
        nearest_candidate_id=None,
        nearest_existing_p_id=None,
        standalone_quality="strong",
        marginal_contribution="high",
        disposition="KEEP",
        merge_target=MergeTarget(kind="candidate", target_id="cand_2"),
        reason="KEEP carrying merge_target",
    )
    # BORDERLINE with merge_target
    sel_borderline = SelectionRecord(
        candidate_id="cand_2",
        admissible=True,
        constraint_failures=[],
        structurally_distinct=True,
        novelty_dimensions=[],
        nearest_candidate_id=None,
        nearest_existing_p_id=None,
        standalone_quality="borderline",
        marginal_contribution="low",
        disposition="BORDERLINE",
        merge_target=MergeTarget(kind="candidate", target_id="cand_1"),
        reason="BORDERLINE carrying merge_target",
    )
    # DROP with merge_target
    sel_drop = SelectionRecord(
        candidate_id="cand_3",
        admissible=False,
        constraint_failures=["c1"],
        structurally_distinct=False,
        novelty_dimensions=[],
        nearest_candidate_id=None,
        nearest_existing_p_id=None,
        standalone_quality="weak",
        marginal_contribution="none",
        disposition="DROP",
        merge_target=MergeTarget(kind="candidate", target_id="cand_1"),
        reason="DROP carrying merge_target",
    )

    issues = validate_selections(
        [candidate1, candidate2, candidate3],
        [sel_keep, sel_borderline, sel_drop],
    )
    assert any(i.code == "UNEXPECTED_MERGE_TARGET" for i in issues["cand_1"])
    assert any(i.code == "UNEXPECTED_MERGE_TARGET" for i in issues["cand_2"])
    assert any(i.code == "UNEXPECTED_MERGE_TARGET" for i in issues["cand_3"])


def test_validate_selections_merge_without_target():
    """validate_selections rejects MERGE disposition lacking merge_target."""
    core = SemanticCore("Test", "Test", "Test")
    candidate = PerspectiveCandidate(
        candidate_id="cand_1",
        semantic_core=core,
        preserved=[],
        default_frame="frame",
        blind_spot="spot",
        operator_ids=[],
        shift="shift",
        perspective="persp",
        new_consequences=[],
        return_path=ReturnPath("dim", ["chain"], "why"),
        epistemics=Epistemics([], [], [], [], []),
    )
    selection = SelectionRecord(
        candidate_id="cand_1",
        admissible=True,
        constraint_failures=[],
        structurally_distinct=False,
        novelty_dimensions=[],
        nearest_candidate_id=None,
        nearest_existing_p_id=None,
        standalone_quality="strong",
        marginal_contribution="low",
        disposition="MERGE",
        merge_target=None,
        reason="Merge missing target",
    )
    issues = validate_selections([candidate], [selection])
    assert "cand_1" in issues
    assert any(i.code == "MERGE_WITHOUT_TARGET" for i in issues["cand_1"])


def test_validate_selections_valid_controls():
    """validate_selections accepts valid combinations of KEEP, BORDERLINE, MERGE, and DROP."""
    core = SemanticCore("Test", "Test", "Test")
    candidates = [
        PerspectiveCandidate(
            candidate_id=f"cand_{i}",
            semantic_core=core,
            preserved=[],
            default_frame="frame",
            blind_spot="spot",
            operator_ids=[],
            shift="shift",
            perspective="persp",
            new_consequences=[],
            return_path=ReturnPath("dim", ["chain"], "why"),
            epistemics=Epistemics([], [], [], [], []),
        )
        for i in range(1, 6)
    ]

    selections = [
        # Valid KEEP
        SelectionRecord(
            candidate_id="cand_1",
            admissible=True,
            constraint_failures=[],
            structurally_distinct=True,
            novelty_dimensions=["dim1"],
            nearest_candidate_id=None,
            nearest_existing_p_id=None,
            standalone_quality="strong",
            marginal_contribution="high",
            disposition="KEEP",
            merge_target=None,
            reason="Strong admissible keep",
        ),
        # Valid BORDERLINE (admissible)
        SelectionRecord(
            candidate_id="cand_2",
            admissible=True,
            constraint_failures=[],
            structurally_distinct=True,
            novelty_dimensions=[],
            nearest_candidate_id=None,
            nearest_existing_p_id=None,
            standalone_quality="borderline",
            marginal_contribution="low",
            disposition="BORDERLINE",
            merge_target=None,
            reason="Borderline quality",
        ),
        # Valid BORDERLINE (inadmissible with constraint failure)
        SelectionRecord(
            candidate_id="cand_3",
            admissible=False,
            constraint_failures=["c1"],
            structurally_distinct=False,
            novelty_dimensions=[],
            nearest_candidate_id=None,
            nearest_existing_p_id=None,
            standalone_quality="borderline",
            marginal_contribution="low",
            disposition="BORDERLINE",
            merge_target=None,
            reason="Borderline with failure",
        ),
        # Valid DROP (inadmissible with constraint failure)
        SelectionRecord(
            candidate_id="cand_4",
            admissible=False,
            constraint_failures=["c1"],
            structurally_distinct=False,
            novelty_dimensions=[],
            nearest_candidate_id=None,
            nearest_existing_p_id=None,
            standalone_quality="weak",
            marginal_contribution="none",
            disposition="DROP",
            merge_target=None,
            reason="Hard failure drop",
        ),
        # Valid MERGE to existing perspective P1
        SelectionRecord(
            candidate_id="cand_5",
            admissible=True,
            constraint_failures=[],
            structurally_distinct=False,
            novelty_dimensions=[],
            nearest_candidate_id=None,
            nearest_existing_p_id="P1",
            standalone_quality="strong",
            marginal_contribution="low",
            disposition="MERGE",
            merge_target=MergeTarget(kind="perspective", target_id="P1"),
            reason="Valid perspective merge",
        ),
    ]

    issues = validate_selections(candidates, selections, existing_p_ids={"P1", "P2"})
    assert issues == {}

# ─────────────────────────────────────────────────────────────────────────────
# Source hash computation
# ─────────────────────────────────────────────────────────────────────────────


def test_compute_source_hash_deterministic():
    """compute_source_hash produces consistent SHA-256."""
    source = "Test source material"
    hash1 = compute_source_hash(source)
    hash2 = compute_source_hash(source)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex length


def test_compute_source_hash_different_inputs():
    """compute_source_hash produces different hashes for different inputs."""
    hash1 = compute_source_hash("Source A")
    hash2 = compute_source_hash("Source B")

    assert hash1 != hash2


# ─────────────────────────────────────────────────────────────────────────────
# Model validation
# ─────────────────────────────────────────────────────────────────────────────


def test_merge_target_invalid_kind():
    """MergeTarget.from_dict rejects invalid kind."""
    with pytest.raises(ValueError, match="Invalid MergeTarget kind"):
        MergeTarget.from_dict({"kind": "invalid", "target_id": "x"})


def test_selection_record_invalid_disposition():
    """SelectionRecord.from_dict rejects invalid disposition."""
    with pytest.raises(ValueError, match="Invalid disposition"):
        SelectionRecord.from_dict({
            "candidate_id": "c1",
            "admissible": True,
            "constraint_failures": [],
            "structurally_distinct": True,
            "novelty_dimensions": [],
            "nearest_candidate_id": None,
            "nearest_existing_p_id": None,
            "standalone_quality": "strong",
            "marginal_contribution": "high",
            "disposition": "INVALID",
            "merge_target": None,
            "reason": "test",
        })


def test_perspective_session_round_trip():
    """PerspectiveSession round-trips through dict."""
    session = PerspectiveSession(
        session_id="test_session",
        source_hash="abc123",
        objective="Test objective",
        constraint_ledger=ConstraintLedger(),
        next_p_number=5,
        perspectives={},
        passes=[],
        deep_runs=[],
    )

    data = session.to_dict()
    restored = PerspectiveSession.from_dict(data)

    assert restored.session_id == "test_session"
    assert restored.source_hash == "abc123"
    assert restored.objective == "Test objective"
    assert restored.next_p_number == 5


def test_deep_run_ref_validation():
    """DeepRunRef validates terminal_state enum."""
    with pytest.raises(ValueError, match="Invalid terminal_state"):
        DeepRunRef.from_dict({
            "deep_id": "d1",
            "p_id": "P1",
            "terminal_state": "INVALID",
            "trace_ref": "traces/d1",
        })
