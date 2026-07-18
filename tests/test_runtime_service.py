"""Tests for Beerlight Runtime — service layer with fake transport.

Deterministic tests. No LLM calls — uses fake call_llm via monkeypatch.

Tests cover:
    - Normal run (generator + judge success)
    - Generator abstention (zero candidates)
    - Judge abstention
    - Card cap at MAX_CARDS
    - Abstention source classification
    - Degraded judge (judge fails after repair)
    - Graceful degradation (trace write failure)
    - One repair retry (generator and judge)
    - JSON API exit codes
    - Trajectory persistence in session
"""
import json
from pathlib import Path

import pytest

from prism.runtime.service import (
    run,
    run_json,
    run_json_file,
    _format_cards,
    _format_trajectory_update_block,
)
from prism.runtime.contracts import RunRequest, RunResponse, ExitCode

# --- Fake candidate and judge data ---

FAKE_CANDIDATES = [
    {
        "id": "c1",
        "title": "Angle One",
        "core_shift": "shift1",
        "source_basis": ["line 1"],
        "practical_return": "return1",
        "boundary": "boundary1",
        "operator": "renaming",
    },
    {
        "id": "c2",
        "title": "Angle Two",
        "core_shift": "shift2",
        "source_basis": ["line 2"],
        "practical_return": "return2",
        "boundary": "boundary2",
        "operator": "mixed",
    },
    {
        "id": "c3",
        "title": "Angle Three",
        "core_shift": "shift3",
        "source_basis": ["line 3"],
        "practical_return": "return3",
        "boundary": "boundary3",
        "operator": "rewrite",
    },
    {
        "id": "c4",
        "title": "Angle Four",
        "core_shift": "shift4",
        "source_basis": ["line 4"],
        "practical_return": "return4",
        "boundary": "boundary4",
        "operator": "mixed",
    },
]


def _make_judge_json(candidate_ids: list[str],
                     overall: str = "useful_output",
                     cards_count: int | None = None) -> str:
    """Build a valid judge JSON response for given candidates.

    cards_count controls how many cards the judge returns (default: all keep actions).
    Set to None to include cards for all keep actions,
    set to a number to cap the returned cards.
    """
    judgments = []
    cards = []
    for i, cid in enumerate(candidate_ids):
        judgments.append({
            "candidate_id": cid,
            "action": "keep" if i < 3 else "drop",
            "novelty": "real",
            "fidelity": "grounded",
            "failure_tags": [],
            "reason": f"good angle {i}",
        })
        # Always include a card for the first 3 keep actions (judge keeps first 3)
        # For card-cap tests, include cards for ALL candidates (judge returns many)
        limit = cards_count if cards_count is not None else 3
        if i < limit:
            cards.append({
                "title": f"Card {cid}",
                "shift": f"shift {cid}",
                "basis": f"basis {cid}",
                "action": f"action {cid}",
                "boundary": f"boundary {cid}",
            })

    return json.dumps({
        "overall_decision": overall,
        "cards": cards,
        "judgments": judgments,
        "trajectory_update": {
            "explored": ["all angles"],
            "shown": [f"Card {candidate_ids[0]}"] if candidate_ids else [],
            "open_questions": ["what next?"],
        },
    })


# --- normal run ---

def test_run_normal_flow(tmp_path, monkeypatch):
    """A normal run with fake transport produces cards and traces."""
    calls: list[str] = []

    def fake_call_llm(prompt: str, model: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return json.dumps(FAKE_CANDIDATES)
        else:
            return _make_judge_json(["c1", "c2", "c3", "c4"])

    monkeypatch.setattr(
        "prism.runtime.generator.call_llm", fake_call_llm
    )
    monkeypatch.setattr(
        "prism.runtime.judge.call_llm", fake_call_llm
    )

    resp = run(
        document="Test document content.",
        task="find angles",
        mode="normal",
        output_dir=str(tmp_path / "runs"),
    )

    assert resp.status == "ok"
    assert len(resp.cards) == 3  # MAX_CARDS
    assert resp.run_id
    assert resp.trace_dir
    assert len(calls) == 2  # one generator, one judge


def test_run_normal_single_card_not_full_quota(tmp_path, monkeypatch):
    """Generator returns fewer than 3 strong candidates."""
    calls: list[str] = []

    def fake_call_llm(prompt: str, model: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return json.dumps(FAKE_CANDIDATES[:2])
        else:
            return _make_judge_json(["c1", "c2"])

    monkeypatch.setattr(
        "prism.runtime.generator.call_llm", fake_call_llm
    )
    monkeypatch.setattr(
        "prism.runtime.judge.call_llm", fake_call_llm
    )

    resp = run(
        document="Test.",
        task="find",
        output_dir=str(tmp_path / "runs"),
    )

    assert resp.status == "ok"
    assert len(resp.cards) <= 3
    assert len(resp.cards) == 2  # only 2 candidates generated


# --- generator abstention ---

def test_run_generator_abstention(tmp_path, monkeypatch):
    """Generator returns zero candidates → abstention_source = generator."""
    calls: list[str] = []

    def fake_call_llm(prompt: str, model: str) -> str:
        calls.append(prompt)
        return "[]"

    monkeypatch.setattr(
        "prism.runtime.generator.call_llm", fake_call_llm
    )
    monkeypatch.setattr(
        "prism.runtime.judge.call_llm", fake_call_llm
    )

    resp = run(
        document="Inert text.",
        task="find angles",
        output_dir=str(tmp_path / "runs"),
    )

    assert resp.status == "no_useful_output"
    assert len(resp.cards) == 0
    # Only generator called, not judge
    assert len(calls) == 1

    # Verify trace has abstention_source
    trace_dir = Path(resp.trace_dir)
    judge = json.loads((trace_dir / "judge.json").read_text(encoding="utf-8"))
    assert judge["abstention_source"] == "generator"
    meta = json.loads(
        (trace_dir / "metadata.json").read_text(encoding="utf-8")
    )
    assert meta["abstention_source"] == "generator"


# --- judge abstention ---

def test_run_judge_abstention(tmp_path, monkeypatch):
    """Judge declares no_useful_output."""
    calls: list[str] = []

    def fake_call_llm(prompt: str, model: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return json.dumps(FAKE_CANDIDATES[:2])
        else:
            return json.dumps({
                "overall_decision": "no_useful_output",
                "cards": [],
                "judgments": [
                    {"candidate_id": "c1", "action": "drop",
                     "novelty": "false", "fidelity": "grounded",
                     "failure_tags": ["banal"], "reason": "nothing new"},
                    {"candidate_id": "c2", "action": "drop",
                     "novelty": "false", "fidelity": "grounded",
                     "failure_tags": ["banal"], "reason": "nothing new"},
                ],
            })

    monkeypatch.setattr(
        "prism.runtime.generator.call_llm", fake_call_llm
    )
    monkeypatch.setattr(
        "prism.runtime.judge.call_llm", fake_call_llm
    )

    resp = run(
        document="Boring text.",
        task="find",
        output_dir=str(tmp_path / "runs"),
    )

    assert resp.status == "no_useful_output"
    assert len(resp.cards) == 0


# --- card cap ---

def test_run_card_cap_at_three(tmp_path, monkeypatch):
    """User sees at most 3 cards even when judge returns more."""
    calls: list[str] = []

    def fake_call_llm(prompt: str, model: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            # 6 candidates
            return json.dumps(FAKE_CANDIDATES + [
                {"id": f"c{i}", "title": f"More {i}",
                 "core_shift": "s", "source_basis": [],
                 "practical_return": "r", "boundary": "b"}
                for i in range(5, 7)
            ])
        else:
            return _make_judge_json([f"c{i}" for i in range(1, 7)], cards_count=6)

    monkeypatch.setattr(
        "prism.runtime.generator.call_llm", fake_call_llm
    )
    monkeypatch.setattr(
        "prism.runtime.judge.call_llm", fake_call_llm
    )

    resp = run(
        document="Rich text.",
        task="find",
        output_dir=str(tmp_path / "runs"),
    )

    assert resp.status == "ok"
    assert len(resp.cards) == 3  # capped at 3 visible

    # But judge.json has all 6 cards (uncapped judge output)
    trace_dir = Path(resp.trace_dir)
    judge = json.loads((trace_dir / "judge.json").read_text(encoding="utf-8"))
    assert len(judge["cards"]) == 6


# --- one repair retry for generator ---

def test_run_generator_repair_retry(tmp_path, monkeypatch):
    """Generator first produces invalid JSON, second succeeds."""
    calls: list[str] = []

    def fake_call_llm(prompt: str, model: str) -> str:
        calls.append(prompt)
        if "Твой предыдущий ответ не был валидным" in prompt:
            # This is the repair prompt
            return json.dumps(FAKE_CANDIDATES[:2])
        elif len(calls) == 1:
            return "not valid json at all }}}}"
        else:
            return _make_judge_json(["c1", "c2"])

    monkeypatch.setattr(
        "prism.runtime.generator.call_llm", fake_call_llm
    )
    monkeypatch.setattr(
        "prism.runtime.judge.call_llm", fake_call_llm
    )

    resp = run(
        document="Test.",
        task="find",
        output_dir=str(tmp_path / "runs"),
    )

    assert resp.status == "ok"
    assert len(calls) >= 3  # gen (fail) + repair (ok) + judge
    assert len(resp.cards) == 2


# --- graceful degradation: judge fails ---

def test_run_judge_failure_returns_error(tmp_path, monkeypatch):
    """When judge fails after repair, result is error."""
    def fake_call_llm(prompt: str, model: str) -> str:
        if "Твой предыдущий ответ не был валидным" in prompt:
            return "still invalid }}}}"
        if "КАНДИДАТЫ" in prompt:
            return "not valid judge json }}}}"
        return json.dumps(FAKE_CANDIDATES[:2])

    monkeypatch.setattr(
        "prism.runtime.generator.call_llm", fake_call_llm
    )
    monkeypatch.setattr(
        "prism.runtime.judge.call_llm", fake_call_llm
    )

    resp = run(
        document="Test.",
        task="find",
        output_dir=str(tmp_path / "runs"),
    )

    assert resp.status == "error"
    assert resp.error is not None


# --- JSON API ---

def test_run_json_valid_request(tmp_path, monkeypatch):
    """run_json with valid RunRequest works."""
    calls: list[str] = []

    def fake_call_llm(prompt: str, model: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return json.dumps(FAKE_CANDIDATES[:2])
        else:
            return _make_judge_json(["c1", "c2"])

    monkeypatch.setattr(
        "prism.runtime.generator.call_llm", fake_call_llm
    )
    monkeypatch.setattr(
        "prism.runtime.judge.call_llm", fake_call_llm
    )

    input_file = tmp_path / "input.md"
    input_file.write_text("Test document.", encoding="utf-8")

    req = RunRequest(
        input_path=str(input_file),
        task="find angles",
        output_dir=str(tmp_path / "runs"),
    )
    resp = run_json(req)
    assert resp.status == "ok"
    assert len(resp.cards) == 2


def test_run_json_missing_input_file(tmp_path):
    """run_json with missing file returns error."""
    req = RunRequest(
        input_path="/nonexistent/file.md",
        task="test",
    )
    resp = run_json(req)
    assert resp.status == "error"


def test_run_json_invalid_request():
    """run_json with invalid request returns error."""
    req = RunRequest(input_path="", task="")
    resp = run_json(req)
    assert resp.status == "error"


def test_run_json_file_exit_codes(tmp_path, monkeypatch):
    """run_json_file returns correct ExitCode."""
    def fake_call_llm(prompt: str, model: str) -> str:
        if "Твой предыдущий ответ" in prompt:
            return json.dumps(FAKE_CANDIDATES[:2])
        if "КАНДИДАТЫ" in prompt:
            return _make_judge_json(["c1", "c2"])
        return json.dumps(FAKE_CANDIDATES[:2])

    monkeypatch.setattr(
        "prism.runtime.generator.call_llm", fake_call_llm
    )
    monkeypatch.setattr(
        "prism.runtime.judge.call_llm", fake_call_llm
    )

    input_file = tmp_path / "input.md"
    input_file.write_text("Test.", encoding="utf-8")

    req_file = tmp_path / "request.json"
    req_file.write_text(json.dumps({
        "input_path": str(input_file),
        "task": "find angles",
        "output_dir": str(tmp_path / "runs"),
    }), encoding="utf-8")

    resp, exit_code = run_json_file(str(req_file))
    assert exit_code == ExitCode.OK
    assert resp.status == "ok"


def test_run_json_file_not_found():
    """run_json_file with missing file returns INPUT_NOT_FOUND."""
    resp, exit_code = run_json_file("/nonexistent/request.json")
    assert exit_code == ExitCode.INPUT_NOT_FOUND


def test_run_json_file_invalid_json(tmp_path):
    """run_json_file with bad JSON returns INVALID_REQUEST."""
    req_file = tmp_path / "bad.json"
    req_file.write_text("not json", encoding="utf-8")

    resp, exit_code = run_json_file(str(req_file))
    assert exit_code == ExitCode.INVALID_REQUEST


# --- trajectory persistence ---

def test_run_with_session_persists_trajectory(tmp_path, monkeypatch):
    """When session_dir is provided, trajectory updates merge into template sections."""
    from prism.runtime.session import create_session, read_trajectory

    calls: list[str] = []

    def fake_call_llm(prompt: str, model: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return json.dumps(FAKE_CANDIDATES[:2])
        else:
            return _make_judge_json(["c1", "c2"])

    monkeypatch.setattr(
        "prism.runtime.generator.call_llm", fake_call_llm
    )
    monkeypatch.setattr(
        "prism.runtime.judge.call_llm", fake_call_llm
    )

    input_file = tmp_path / "draft.md"
    input_file.write_text("Session doc.", encoding="utf-8")

    session_dir = tmp_path / "sess"
    create_session(str(input_file), str(session_dir))

    resp = run(
        document="Session doc.",
        task="find",
        session_dir=str(session_dir),
        output_dir=str(tmp_path / "runs"),
    )

    assert resp.status == "ok"
    traj = read_trajectory(str(session_dir))
    # Template sections present
    assert "## Original task" in traj
    assert "## Directions already explored" in traj
    # Explored items from judge trajectory_update are merged
    assert "all angles" in traj
    # shown cards go to already explored as [показано], not to selected
    assert "[показано] Card c1" in traj
    assert "## Directions selected and developed" in traj
    # Selected section must NOT be auto-filled (invariant)
    assert "(none yet)" in traj


# --- format helpers ---

def test_format_cards():
    """_format_cards produces expected markdown."""
    cards = [{
        "title": "Test Card",
        "shift": "A shift",
        "basis": "A basis",
        "action": "An action",
        "boundary": "A boundary",
    }]
    result = _format_cards(cards)
    assert "## Test Card" in result
    assert "A shift" in result


def test_format_cards_empty():
    """Empty cards produce empty string."""
    assert _format_cards([]) == ""


def test_format_trajectory_update_block():
    """Trajectory update block includes all data."""
    block = _format_trajectory_update_block(
        "run123",
        {"explored": ["X"], "shown": ["Y"], "open_questions": ["Z"]},
        [],
    )
    assert "## Run run123" in block
    assert "- X" in block
    assert "- Y" in block
    assert "- Z" in block


# --- R2: Metadata recording (token usage, duration, retries) ---

def test_metadata_token_usage_and_retries(tmp_path, monkeypatch):
    """After a run with fake transport, metadata fields > 0 and correct."""
    import json as _json
    from pathlib import Path

    calls: list[str] = []

    def fake_call_llm(prompt: str, model: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return _json.dumps(FAKE_CANDIDATES[:2])
        else:
            return _make_judge_json(["c1", "c2"])

    monkeypatch.setattr(
        "prism.runtime.generator.call_llm", fake_call_llm
    )
    monkeypatch.setattr(
        "prism.runtime.judge.call_llm", fake_call_llm
    )

    resp = run(
        document="Test document for metadata test.",
        task="find angles",
        mode="normal",
        output_dir=str(tmp_path / "runs"),
    )

    assert resp.status == "ok"

    # Read metadata.json
    meta_path = Path(resp.trace_dir) / "metadata.json"
    meta = _json.loads(meta_path.read_text(encoding="utf-8"))

    # duration_sec >= 0 (may be 0.0 with fake transport that returns instantly)
    assert meta["duration_sec"] >= 0, f"duration_sec should be >= 0, got {meta['duration_sec']}"

    # retry_count
    assert "retry_count" in meta
    assert meta["retry_count"] >= 0

    # token_usage_estimate > 0
    assert meta["token_usage_estimate"] > 0, (
        f"token_usage_estimate should be > 0, got {meta['token_usage_estimate']}"
    )

    # token_usage_breakdown has generator and judge
    breakdown = meta.get("token_usage_breakdown", {})
    assert "generator" in breakdown, f"breakdown missing generator: {breakdown}"
    assert "judge" in breakdown, f"breakdown missing judge: {breakdown}"
    assert breakdown["generator"] > 0
    assert breakdown["judge"] > 0


def test_metadata_retry_count_with_generator_repair(tmp_path, monkeypatch):
    """Generator repair increments retry_count."""
    import json as _json
    from pathlib import Path

    calls: list[str] = []

    def fake_call_llm(prompt: str, model: str) -> str:
        calls.append(prompt)
        if "Твой предыдущий ответ не был валидным" in prompt:
            return _json.dumps(FAKE_CANDIDATES[:2])
        elif len(calls) == 1:
            return "not valid json }}}}"
        else:
            return _make_judge_json(["c1", "c2"])

    monkeypatch.setattr(
        "prism.runtime.generator.call_llm", fake_call_llm
    )
    monkeypatch.setattr(
        "prism.runtime.judge.call_llm", fake_call_llm
    )

    resp = run(
        document="Test.",
        task="find",
        output_dir=str(tmp_path / "runs"),
    )

    assert resp.status == "ok"

    meta_path = Path(resp.trace_dir) / "metadata.json"
    meta = _json.loads(meta_path.read_text(encoding="utf-8"))

    # Generator needed a repair → retry_count >= 1
    assert meta["retry_count"] >= 1, (
        f"Expected retry_count >= 1 due to generator repair, got {meta['retry_count']}"
    )


def test_metadata_duration_sec_is_float(tmp_path, monkeypatch):
    """duration_sec is a positive float."""
    import json as _json
    from pathlib import Path

    calls: list[str] = []

    def fake_call_llm(prompt: str, model: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return _json.dumps(FAKE_CANDIDATES[:1])
        else:
            return _make_judge_json(["c1"])

    monkeypatch.setattr(
        "prism.runtime.generator.call_llm", fake_call_llm
    )
    monkeypatch.setattr(
        "prism.runtime.judge.call_llm", fake_call_llm
    )

    resp = run(
        document="Quick test.",
        task="find",
        output_dir=str(tmp_path / "runs"),
    )

    meta_path = Path(resp.trace_dir) / "metadata.json"
    meta = _json.loads(meta_path.read_text(encoding="utf-8"))

    assert isinstance(meta["duration_sec"], (int, float))
    assert meta["duration_sec"] >= 0
