"""Tests for Beerlight Runtime — contracts, inspect, models, and invariant checks.

Deterministic tests only. No LLM calls.
"""
import json
from pathlib import Path

from prism.runtime.contracts import (
    RunRequest,
    RunResponse,
    ExitCode,
)
from prism.runtime.models import (
    Candidate,
    Card,
    JudgeJudgment,
    JudgeResult,
    TraceMetadata,
    PrivacyLevel,
    TraceLevel,
    RunMode,
    ContextMode,
    TrajectoryEntry,
    InspectResult,
)


# --- RunRequest validation ---

def test_run_request_validation_valid():
    """Valid request passes validation."""
    req = RunRequest(input_path="test.md", task="find angles")
    errors = req.validate()
    assert errors == []


def test_run_request_validation_requires_input_path():
    """Missing input_path is an error."""
    req = RunRequest(input_path="", task="test")
    errors = req.validate()
    assert any("input_path" in e for e in errors)


def test_run_request_validation_requires_task():
    """Missing task is an error."""
    req = RunRequest(input_path="test.md", task="")
    errors = req.validate()
    assert any("task" in e for e in errors)


def test_run_request_validation_invalid_mode():
    """Invalid mode is rejected."""
    req = RunRequest(input_path="t.md", task="t", mode="invalid")
    errors = req.validate()
    assert any("mode" in e for e in errors)


def test_run_request_validation_invalid_context_mode():
    """Invalid context_mode is rejected."""
    req = RunRequest(input_path="t.md", task="t", context_mode="bad")
    errors = req.validate()
    assert any("context_mode" in e for e in errors)


def test_run_request_from_dict():
    """RunRequest can be constructed from a dict."""
    data = {
        "input_path": "test.md",
        "task": "find angles",
        "mode": "360",
        "trajectory_path": None,
        "context_mode": "full",
        "trace_level": "full",
        "output_dir": "runs",
    }
    req = RunRequest.from_dict(data)
    assert req.input_path == "test.md"
    assert req.task == "find angles"
    assert req.mode == "360"
    assert req.trajectory_path is None
    assert req.context_mode == "full"
    assert req.trace_level == "full"
    assert req.output_dir == "runs"


# --- RunResponse ---

def test_run_response_to_dict():
    """RunResponse serializes correctly."""
    resp = RunResponse(
        status="ok",
        run_id="abc123",
        cards=[{"title": "Test"}],
        trace_dir="/tmp/trace",
        warnings=["w1"],
    )
    d = resp.to_dict()
    assert d["status"] == "ok"
    assert d["run_id"] == "abc123"
    assert d["cards"] == [{"title": "Test"}]
    assert d["trace_dir"] == "/tmp/trace"
    assert d["warnings"] == ["w1"]
    assert d["error"] is None


def test_run_response_to_json():
    """RunResponse to_json() produces valid JSON."""
    resp = RunResponse(status="ok", run_id="x")
    js = resp.to_json()
    parsed = json.loads(js)
    assert parsed["status"] == "ok"


def test_run_response_error():
    """Error responses include error field."""
    resp = RunResponse(status="error", error="something went wrong")
    assert resp.status == "error"
    assert resp.error == "something went wrong"


# --- Exit codes ---

def test_exit_codes_are_distinct():
    """Exit codes are all different."""
    values = [e.value for e in ExitCode]
    assert len(values) == len(set(values))


def test_exit_code_ok_is_zero():
    """OK exit code is 0."""
    assert ExitCode.OK == 0


def test_exit_code_invalid_request():
    """Invalid request exit code > 0."""
    assert ExitCode.INVALID_REQUEST > 0
    assert ExitCode.GENERATOR_FAILED > 0


# --- Model deserialization ---

def test_candidate_from_dict():
    """Candidate.from_dict constructs correctly."""
    data = {
        "id": "c1",
        "title": "Test Candidate",
        "core_shift": "shift desc",
        "source_basis": ["line 1", "line 2"],
        "practical_return": "return desc",
        "boundary": "boundary desc",
        "operator": "renaming",
    }
    c = Candidate.from_dict(data)
    assert c.id == "c1"
    assert c.title == "Test Candidate"
    assert c.source_basis == ["line 1", "line 2"]
    assert c.operator == "renaming"


def test_candidate_from_dict_optional_operator():
    """Operator is optional in candidate data."""
    data = {
        "id": "c2",
        "title": "T",
        "core_shift": "s",
        "source_basis": [],
        "practical_return": "r",
        "boundary": "b",
    }
    c = Candidate.from_dict(data)
    assert c.operator is None


def test_card_from_dict():
    """Card.from_dict constructs correctly."""
    data = {
        "title": "Card Title",
        "shift": "The shift",
        "basis": "The basis",
        "action": "The action",
        "boundary": "The boundary",
    }
    c = Card.from_dict(data)
    assert c.title == "Card Title"
    assert c.shift == "The shift"
    assert c.basis == "The basis"
    assert c.action == "The action"
    assert c.boundary == "The boundary"


def test_judge_judgment_from_dict():
    """JudgeJudgment.from_dict constructs correctly."""
    data = {
        "candidate_id": "c1",
        "action": "keep",
        "novelty": "real",
        "fidelity": "grounded",
        "failure_tags": [],
        "reason": "good idea",
    }
    j = JudgeJudgment.from_dict(data)
    assert j.candidate_id == "c1"
    assert j.action == "keep"
    assert j.novelty == "real"
    assert j.reason == "good idea"


def test_judge_result_from_dict():
    """JudgeResult.from_dict constructs fully."""
    data = {
        "overall_decision": "useful_output",
        "cards": [
            {"title": "C1", "shift": "s", "basis": "b",
             "action": "a", "boundary": "g"},
        ],
        "judgments": [
            {"candidate_id": "c1", "action": "keep", "novelty": "real",
             "fidelity": "grounded", "failure_tags": [], "reason": "good"},
        ],
        "abstention_source": "judge",
        "trajectory_update": {"explored": ["X"]},
    }
    jr = JudgeResult.from_dict(data)
    assert jr.overall_decision == "useful_output"
    assert len(jr.cards) == 1
    assert len(jr.judgments) == 1
    assert jr.abstention_source == "judge"
    assert jr.trajectory_update == {"explored": ["X"]}


# --- Privacy and trace levels ---

def test_privacy_level_enum():
    """PrivacyLevel has correct values."""
    assert PrivacyLevel.PRIVATE == "private"
    assert PrivacyLevel.PROJECT == "project"
    assert PrivacyLevel.SHAREABLE == "shareable"


def test_trace_level_enum():
    """TraceLevel has correct values."""
    assert TraceLevel.COMPACT == "compact"
    assert TraceLevel.FULL == "full"


def test_run_mode_enum():
    """RunMode has correct values."""
    assert RunMode.NORMAL == "normal"
    assert RunMode.MODE_360 == "360"


def test_context_mode_enum():
    """ContextMode has correct values."""
    assert ContextMode.TRAJECTORY == "trajectory"
    assert ContextMode.FULL == "full"


# --- TrajectoryEntry ---

def test_trajectory_entry_to_markdown():
    """TrajectoryEntry.to_markdown produces correct output."""
    entry = TrajectoryEntry(
        run_id="run1",
        explored=["A", "B"],
        shown=["C"],
        open_questions=["Q"],
    )
    md = entry.to_markdown()
    assert "## Run run1" in md
    assert "- A" in md
    assert "- B" in md
    assert "- C" in md
    assert "- Q" in md


def test_trajectory_entry_from_dict():
    """TrajectoryEntry.from_dict constructs correctly."""
    data = {
        "explored": ["E1"],
        "shown": ["S1"],
        "open_questions": ["O1"],
    }
    entry = TrajectoryEntry.from_dict(data, run_id="r99")
    assert entry.run_id == "r99"
    assert entry.explored == ["E1"]


# --- TraceMetadata ---

def test_trace_metadata_to_dict():
    """TraceMetadata.to_dict() includes all required fields."""
    meta = TraceMetadata(
        run_id="r1",
        mode="normal",
        input_hash="abc123",
        privacy=PrivacyLevel.SHAREABLE,
        trace_level="full",
    )
    d = meta.to_dict()
    assert d["trace_schema_version"] == "1"
    assert d["run_id"] == "r1"
    assert d["privacy"] == "shareable"
    assert d["trace_level"] == "full"


def test_trace_metadata_abstention_source_included_when_set():
    """abstention_source is included in dict when set."""
    meta = TraceMetadata(abstention_source="generator")
    d = meta.to_dict()
    assert d["abstention_source"] == "generator"

    meta2 = TraceMetadata()
    d2 = meta2.to_dict()
    assert "abstention_source" not in d2


# --- InspectResult ---

def test_inspect_result_defaults():
    """InspectResult has sensible defaults."""
    r = InspectResult(run_id="test")
    assert r.run_id == "test"
    assert r.candidates == []
    assert r.errors == []


# --- Card cap invariant (re-verifies slice invariant in runtime context) ---

def test_card_cap_preserved():
    """MAX_CARDS = 3 is the invariant (re-verified from runtime)."""
    from prism.runtime.service import MAX_CARDS
    assert MAX_CARDS == 3


# --- R1: Inspect semantics (shown / kept-hidden / dropped) ---

def test_inspect_distinguishes_shown_kept_hidden_dropped(tmp_path):
    """Synthetic trace: judge kept 5, shown 3 in output.md → inspect shows 3/2/dropped."""
    from prism.runtime.inspect import inspect_run, format_inspect_output

    trace_dir = tmp_path / "run_test"
    trace_dir.mkdir()

    # Write metadata.json (v1)
    import json
    meta = {
        "trace_schema_version": "1",
        "run_id": "test001",
        "mode": "normal",
        "generator_prompt_version": "generator-v1",
        "judge_prompt_version": "judge-v1",
        "generator_model": "fake",
        "judge_model": "fake",
        "judge_family_fallback": True,
        "created_at": "2026-01-01T00:00:00Z",
        "status": "ok",
        "privacy": "private",
        "trace_level": "compact",
        "token_usage_estimate": 0,
        "token_usage_breakdown": {},
        "duration_sec": 1.0,
        "retry_count": 0,
        "input_hash": "abc123",
        "warnings": [],
    }
    (trace_dir / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")

    # Write candidates.json (5 candidates)
    candidates = [
        {"id": "c1", "title": "Angle Alpha", "core_shift": "x", "source_basis": [],
         "practical_return": "x", "boundary": "x"},
        {"id": "c2", "title": "Angle Beta", "core_shift": "x", "source_basis": [],
         "practical_return": "x", "boundary": "x"},
        {"id": "c3", "title": "Angle Gamma", "core_shift": "x", "source_basis": [],
         "practical_return": "x", "boundary": "x"},
        {"id": "c4", "title": "Angle Delta", "core_shift": "x", "source_basis": [],
         "practical_return": "x", "boundary": "x"},
        {"id": "c5", "title": "Angle Epsilon", "core_shift": "x", "source_basis": [],
         "practical_return": "x", "boundary": "x"},
    ]
    (trace_dir / "candidates.json").write_text(json.dumps(candidates), encoding="utf-8")

    # Write judge.json: judge keeps 4 (c1,c2,c3,c4), drops c5
    judge = {
        "overall_decision": "useful_output",
        "cards": [
            {"title": "Card c1", "shift": "s", "basis": "b", "action": "a", "boundary": "g"},
            {"title": "Card c2", "shift": "s", "basis": "b", "action": "a", "boundary": "g"},
            {"title": "Card c3", "shift": "s", "basis": "b", "action": "a", "boundary": "g"},
            {"title": "Card c4", "shift": "s", "basis": "b", "action": "a", "boundary": "g"},
        ],
        "judgments": [
            {"candidate_id": "c1", "action": "keep", "novelty": "real",
             "fidelity": "grounded", "failure_tags": [], "reason": "good"},
            {"candidate_id": "c2", "action": "keep", "novelty": "real",
             "fidelity": "grounded", "failure_tags": [], "reason": "good"},
            {"candidate_id": "c3", "action": "keep", "novelty": "real",
             "fidelity": "grounded", "failure_tags": [], "reason": "good"},
            {"candidate_id": "c4", "action": "keep", "novelty": "real",
             "fidelity": "grounded", "failure_tags": [], "reason": "good"},
            {"candidate_id": "c5", "action": "drop", "novelty": "false",
             "fidelity": "mixed", "failure_tags": ["banal"], "reason": "weak"},
        ],
    }
    (trace_dir / "judge.json").write_text(json.dumps(judge), encoding="utf-8")

    # Write output.md: only 3 cards shown (capped at MAX_CARDS=3)
    output_md = "## Card c1\n\n**Сдвиг**\ns\n\n...\n\n## Card c2\n\n...\n\n## Card c3\n\n...\n\nRun: test001\nTrace: /tmp/test001\n"
    (trace_dir / "output.md").write_text(output_md, encoding="utf-8")

    # Inspect
    result = inspect_run(str(trace_dir))
    output = format_inspect_output(result)

    # Shown to user: 3 (from output.md)
    assert len(result.shown_cards) == 3, f"Expected 3 shown, got {result.shown_cards}"
    assert "Shown to user (3)" in output

    # Kept by judge, hidden by cap: 1 (card c4 kept but beyond cap of 3)
    assert len(result.kept_hidden) == 1, f"Expected 1 kept-hidden, got {result.kept_hidden}"
    assert "Kept by judge, hidden by cap (1)" in output

    # Dropped: c5 is dropped by judgment
    assert len(result.dropped_candidates) == 1
    assert result.dropped_candidates[0]["candidate_id"] == "c5"
    assert "Dropped" in output


def test_inspect_no_judge_yet(tmp_path):
    """Inspect works even when there's no judge.json (empty result)."""
    from prism.runtime.inspect import inspect_run

    trace_dir = tmp_path / "run_empty"
    trace_dir.mkdir()

    meta = {
        "trace_schema_version": "1",
        "run_id": "empty001",
        "mode": "normal",
        "generator_prompt_version": "v1",
        "judge_prompt_version": "v1",
        "generator_model": "x",
        "judge_model": "x",
        "judge_family_fallback": True,
        "created_at": "",
        "status": "error",
        "privacy": "private",
        "trace_level": "compact",
        "token_usage_estimate": 0,
        "token_usage_breakdown": {},
        "duration_sec": 0,
        "retry_count": 0,
        "input_hash": "",
        "warnings": [],
    }
    import json
    (trace_dir / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")

    result = inspect_run(str(trace_dir))
    assert result.shown_cards == []
    assert result.kept_hidden == []


def test_inspect_shown_cards_set_on_result():
    """InspectResult has shown_cards and kept_hidden fields."""
    r = InspectResult(run_id="test")
    assert hasattr(r, "shown_cards")
    assert hasattr(r, "kept_hidden")
    assert r.shown_cards == []
    assert r.kept_hidden == []
