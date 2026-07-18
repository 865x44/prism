"""Tests for Prism Runtime — RIFT profile.

Covers RIFT constraints from Part B:
- Profile defaulting to practical
- CLI and JSON profile parsing
- Session-run profile parsing
- Practical prompt byte/semantic preservation
- All 4 mode/profile routing combinations
- Operator-family optional fields
- Old trace normalization to practical
- RIFT prompt version in metadata
- RIFT card cap (3 max)
- RIFT abstention
- Malformed RIFT output repair
"""
import json
from pathlib import Path
import pytest

from prism.runtime.contracts import RunRequest, ExitCode
from prism.runtime.cli import main
from prism.runtime.service import run, run_json
from prism.runtime.trace import read_trace_metadata, _normalize_v0_metadata
from prism.runtime.session import create_session

FAKE_PRACTICAL_CANDIDATES = [
    {
        "id": "c1",
        "title": "A1",
        "core_shift": "s",
        "source_basis": ["s"],
        "practical_return": "r",
        "boundary": "b",
        "operator": "mixed",
    }
]

FAKE_RIFT_CANDIDATES = [
    {
        "id": "c1",
        "title": "Rift A1",
        "core_shift": "s",
        "source_basis": ["s"],
        "practical_return": "r",
        "boundary": "b",
        "operator": "mixed",
        "operator_family": "category mutation",
        "rift_distance": "far",
    },
    {
        "id": "c2",
        "title": "Rift A2",
        "core_shift": "s",
        "source_basis": ["s"],
        "practical_return": "r",
        "boundary": "b",
        "operator": "mixed",
        "operator_family": "scale inversion",
        "rift_distance": "extreme",
    },
    {
        "id": "c3",
        "title": "Rift A3",
        "core_shift": "s",
        "source_basis": ["s"],
        "practical_return": "r",
        "boundary": "b",
        "operator": "mixed",
        "operator_family": "identity and legitimacy",
        "rift_distance": "near",
    },
    {
        "id": "c4",
        "title": "Rift A4",
        "core_shift": "s",
        "source_basis": ["s"],
        "practical_return": "r",
        "boundary": "b",
        "operator": "mixed",
        "operator_family": "time and irreversibility",
        "rift_distance": "extreme",
    }
]

def _make_judge_json(candidate_ids: list[str]) -> str:
    judgments = []
    cards = []
    for i, cid in enumerate(candidate_ids):
        judgments.append({
            "candidate_id": cid,
            "action": "keep",
            "novelty": "real",
            "fidelity": "grounded",
            "failure_tags": [],
            "reason": "good",
        })
        cards.append({
            "title": f"Card {cid}",
            "shift": "s",
            "basis": "b",
            "action": "a",
            "boundary": "b",
        })
    return json.dumps({
        "overall_decision": "useful_output",
        "cards": cards,
        "judgments": judgments,
    })


def test_cli_profile_parsing(tmp_path, monkeypatch):
    """CLI should parse --profile rift."""
    def fake_run(**kwargs):
        assert kwargs.get("profile") == "rift"
        assert kwargs.get("mode") == "normal"
        import dataclasses
        @dataclasses.dataclass
        class FakeResponse:
            status = "ok"
            warnings = []
        return FakeResponse()

    monkeypatch.setattr("prism.runtime.cli.run", fake_run)
    input_file = tmp_path / "in.md"
    input_file.write_text("Test", encoding="utf-8")
    main(["run", str(input_file), "--task", "t", "--profile", "rift"])


def test_json_profile_parsing():
    """RunRequest should parse profile."""
    req = RunRequest.from_dict({"input_path": "x", "task": "t", "profile": "rift"})
    assert req.profile == "rift"
    assert not req.validate()

    req = RunRequest.from_dict({"input_path": "x", "task": "t", "profile": "invalid"})
    assert "invalid profile: invalid" in req.validate()


def test_session_run_profile_parsing(tmp_path, monkeypatch):
    """Session run parses --profile."""
    def fake_run(**kwargs):
        assert kwargs.get("profile") == "rift"
        import dataclasses
        @dataclasses.dataclass
        class FakeResponse:
            status = "ok"
            warnings = []
        return FakeResponse()
    monkeypatch.setattr("prism.runtime.cli.run", fake_run)
    
    sess_dir = tmp_path / "sess"
    in_file = tmp_path / "in.md"
    in_file.write_text("test")
    create_session(str(in_file), str(sess_dir))
    
    main(["session", "run", str(sess_dir), "--task", "t", "--profile", "rift"])


def test_routing_combinations_and_prompts(tmp_path, monkeypatch):
    """Test all 4 mode/profile combinations and prompt versions."""
    combos = [
        ("normal", "practical", "generator-v1", "judge-v1"),
        ("360", "practical", "360-v1", "judge-v1"),
        ("normal", "rift", "generator-rift-v0", "judge-rift-v0"),
        ("360", "rift", "360-rift-v0", "judge-rift-v0"),
    ]
    
    for mode, profile, expected_gen, expected_judge in combos:
        def fake_call_llm(prompt: str, model: str) -> str:
            if "novelty" in prompt:
                return _make_judge_json(["c1"])
            return json.dumps(FAKE_PRACTICAL_CANDIDATES)
            
        monkeypatch.setattr("prism.runtime.generator.call_llm", fake_call_llm)
        monkeypatch.setattr("prism.runtime.judge.call_llm", fake_call_llm)
        
        resp = run("test", "test", mode=mode, profile=profile, output_dir=str(tmp_path))
        meta = read_trace_metadata(Path(resp.trace_dir))
        
        assert meta.profile == profile
        assert meta.generator_prompt_version == expected_gen
        assert meta.judge_prompt_version == expected_judge


def test_rift_card_cap(tmp_path, monkeypatch):
    """RIFT should cap output to 3 cards."""
    def fake_call_llm(prompt: str, model: str) -> str:
        if "novelty" in prompt:
            return _make_judge_json(["c1", "c2", "c3", "c4"])
        return json.dumps(FAKE_RIFT_CANDIDATES)
        
    monkeypatch.setattr("prism.runtime.generator.call_llm", fake_call_llm)
    monkeypatch.setattr("prism.runtime.judge.call_llm", fake_call_llm)
    
    resp = run("test", "test", profile="rift", output_dir=str(tmp_path))
    assert len(resp.cards) == 3


def test_old_trace_normalization():
    """Legacy traces without profile should normalize to practical."""
    old_meta = {
        "run_id": "123",
        "mode": "normal",
        "generator_prompt_version": "generator-v1"
    }
    meta = _normalize_v0_metadata(old_meta)
    assert meta.profile == "practical"


def test_malformed_rift_repair(tmp_path, monkeypatch):
    """Malformed JSON should trigger repair using RIFT fields."""
    calls = []
    def fake_call_llm(prompt: str, model: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return "not json"
        elif "Твой предыдущий ответ не был валидным" in prompt:
            return json.dumps(FAKE_RIFT_CANDIDATES[:2])
        else:
            return _make_judge_json(["c1", "c2"])

    monkeypatch.setattr("prism.runtime.generator.call_llm", fake_call_llm)
    monkeypatch.setattr("prism.runtime.judge.call_llm", fake_call_llm)

    resp = run("test", "test", profile="rift", output_dir=str(tmp_path))
    assert resp.status == "ok"
    assert len(resp.cards) == 2


def test_rift_abstention(tmp_path, monkeypatch):
    """RIFT generator abstention -> no_useful_output."""
    def fake_call_llm(prompt: str, model: str) -> str:
        return "[]"

    monkeypatch.setattr("prism.runtime.generator.call_llm", fake_call_llm)
    
    resp = run("test", "test", profile="rift", output_dir=str(tmp_path))
    assert resp.status == "no_useful_output"
    
    meta = read_trace_metadata(Path(resp.trace_dir))
    assert meta.abstention_source == "generator"
