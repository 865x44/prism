from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from prism.beerlight_demo_rc.evaluator_runner import _invoke, load_challenge_packets, run_smoke


def test_visible_challenge_parser_is_complete_and_excludes_draft_gold_from_packets():
    root = Path(__file__).resolve().parents[2]
    packets = load_challenge_packets(
        root / "docs/beerlight_agent_docs/current/EVALUATOR_CHALLENGE_V1_PROVISIONAL.md"
    )
    assert [item["case_id"] for item in packets] == [f"C{number:02d}" for number in range(1, 17)]
    assert packets[8]["criterion_id"] == "TRAJECTORY_NOVELTY"
    for item in packets:
        serialized = str(item["packet"].as_dict())
        assert "DRAFT_GOLD_PENDING_HUMAN" not in serialized
        assert item["draft_gold"] in {"MET", "VIOLATED", "UNCLEAR"}


def test_timeout_is_sanitized_as_failed_attempt(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], output="partial", stderr="sk-secret-value-123456")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = _invoke("opencode", "openai/gpt-5.4-mini", "prompt", timeout_seconds=45)
    assert result["exit_code"] is None
    assert result["timed_out"] is True
    assert result["stdout"] == "partial"
    assert "REDACTED_SECRET_SHAPED_VALUE" in result["stderr"]


def test_maximum_must_cover_all_32_planned_calls(tmp_path):
    root = Path(__file__).resolve().parents[2]
    with pytest.raises(ValueError, match="required 32 planned calls"):
        run_smoke(
            challenge_path=root / "docs/beerlight_agent_docs/current/EVALUATOR_CHALLENGE_V1_PROVISIONAL.md",
            evaluator_config_path=root / "prism-runs/beerlight-demo-rc-p0-20260810-01/phase0/evaluator-config.json",
            run_root=tmp_path / "must-not-exist",
            opencode_bin="not-called",
            max_logical_calls=31,
        )
    assert not (tmp_path / "must-not-exist").exists()
