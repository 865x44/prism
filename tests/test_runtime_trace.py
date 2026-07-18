"""Tests for Prism Runtime — trace schema v1 and legacy v0 reading.

Deterministic tests only. No LLM calls.
"""
import json
from pathlib import Path

from prism.runtime.trace import (
    read_trace_metadata,
    read_trace_judge,
    read_trace_candidates,
    write_trace_v1,
    compute_input_hash,
)
from prism.runtime.models import (
    TraceMetadata,
    PrivacyLevel,
    JudgeResult,
)
from prism.runtime.validation import (
    is_legacy_v0_trace,
    is_v1_trace,
)


# --- legacy v0 trace reading ---

def test_read_legacy_v0_metadata_from_real_trace():
    """Read metadata from a legacy v0 trace in beerlight-runs/smoke/."""
    smoke_dir = Path("beerlight-runs/smoke/draft")
    if not smoke_dir.exists():
        import pytest
        pytest.skip("No legacy smoke traces available")

    # Find a v0 trace
    traces = [d for d in smoke_dir.iterdir() if d.is_dir()]
    if not traces:
        import pytest
        pytest.skip("No trace subdirectories found")

    trace_dir = traces[0]
    meta = read_trace_metadata(trace_dir)

    assert meta.trace_schema_version == "0"  # legacy
    assert meta.run_id
    assert meta.mode in ("normal", "360")
    assert meta.status in ("ok", "no_useful_output", "error")


def test_read_legacy_v0_trace_detection():
    """is_legacy_v0_trace detects v0 (no trace_schema_version)."""
    meta_v0 = {"run_id": "abc", "mode": "normal", "status": "ok"}
    assert is_legacy_v0_trace(meta_v0)
    assert not is_v1_trace(meta_v0)


def test_read_v1_trace_detection():
    """is_v1_trace detects v1 traces."""
    meta_v1 = {
        "trace_schema_version": "1",
        "run_id": "abc",
        "mode": "normal",
        "status": "ok",
    }
    assert is_v1_trace(meta_v1)
    assert not is_legacy_v0_trace(meta_v1)


def test_read_unknown_schema_version_rejected():
    """Unknown trace_schema_version raises ValueError."""
    meta = {
        "trace_schema_version": "99",
        "run_id": "abc",
        "mode": "normal",
        "status": "ok",
        "generator_prompt_version": "v1",
        "judge_prompt_version": "v1",
        "generator_model": "x",
        "judge_model": "x",
        "judge_family_fallback": True,
        "created_at": "",
        "privacy": "private",
        "trace_level": "compact",
    }
    trace_dir = Path("/tmp/test_unknown_v99")
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / "metadata.json").write_text(
        json.dumps(meta), encoding="utf-8"
    )
    try:
        read_trace_metadata(trace_dir)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "99" in str(e)


# --- v1 trace writing ---

def test_write_trace_v1_compact(tmp_path):
    """write_trace_v1 creates compact trace with all required files."""
    trace_dir = tmp_path / "run001"
    meta = TraceMetadata(
        trace_schema_version="1",
        run_id="run001",
        mode="normal",
        generator_prompt_version="generator-v1",
        judge_prompt_version="judge-v1",
        generator_model="test-model",
        judge_model="test-model",
        input_hash=compute_input_hash("test input"),
    )

    write_trace_v1(
        trace_dir,
        metadata=meta,
        request={"input_path": "test.md", "task": "test"},
        candidates=[{"id": "c1", "title": "Test"}],
        judge={"overall_decision": "useful_output", "cards": [],
               "judgments": []},
        cards=[],
        input_text="test input",
    )

    # Required files
    assert (trace_dir / "metadata.json").exists()
    assert (trace_dir / "request.json").exists()
    assert (trace_dir / "input.md").exists()
    assert (trace_dir / "candidates.json").exists()
    assert (trace_dir / "judge.json").exists()
    assert (trace_dir / "output.md").exists()

    # No full-trace extras in compact mode
    assert not (trace_dir / "raw-generator.txt").exists()
    assert not (trace_dir / "raw-judge.txt").exists()
    assert not (trace_dir / "prompt-generator.txt").exists()

    # Verify metadata has v1 schema
    meta_file = json.loads(
        (trace_dir / "metadata.json").read_text(encoding="utf-8")
    )
    assert meta_file["trace_schema_version"] == "1"
    assert meta_file["privacy"] == "private"


def test_write_trace_v1_full(tmp_path):
    """write_trace_v1 with trace_level=full includes raw responses and prompts."""
    trace_dir = tmp_path / "run_full"
    meta = TraceMetadata(
        trace_schema_version="1",
        run_id="run_full",
        mode="normal",
        generator_prompt_version="generator-v1",
        judge_prompt_version="judge-v1",
        generator_model="test-model",
        judge_model="test-model",
        trace_level="full",
        input_hash=compute_input_hash("test"),
    )

    write_trace_v1(
        trace_dir,
        metadata=meta,
        request={"input_path": "test.md", "task": "test"},
        candidates=[{"id": "c1", "title": "T"}],
        judge={"overall_decision": "useful_output", "cards": [],
               "judgments": []},
        cards=[],
        input_text="test",
        raw_generator="RAW GEN OUTPUT",
        raw_judge="RAW JUDGE OUTPUT",
        gen_prompt="GEN PROMPT",
        judge_prompt="JUDGE PROMPT",
        repair_prompt="REPAIR PROMPT",
    )

    # Full-trace extras present
    assert (trace_dir / "raw-generator.txt").exists()
    assert (trace_dir / "raw-judge.txt").exists()
    assert (trace_dir / "prompt-generator.txt").exists()
    assert (trace_dir / "prompt-judge.txt").exists()
    assert (trace_dir / "prompt-repair.txt").exists()


def test_compact_vs_full_difference(tmp_path):
    """Compact trace excludes raw model responses and prompts."""
    # Compact
    compact_dir = tmp_path / "compact"
    meta = TraceMetadata(
        trace_schema_version="1",
        run_id="cmp",
        mode="normal",
        generator_prompt_version="generator-v1",
        judge_prompt_version="judge-v1",
        generator_model="test",
        judge_model="test",
        trace_level="compact",
        input_hash=compute_input_hash("test"),
    )
    write_trace_v1(
        compact_dir, metadata=meta,
        request={}, candidates=[], judge={}, cards=[], input_text="t",
        raw_generator="secret", raw_judge="secret",
        gen_prompt="prompt", judge_prompt="prompt",
    )
    assert not (compact_dir / "raw-generator.txt").exists()
    assert not (compact_dir / "prompt-generator.txt").exists()

    # Full
    full_dir = tmp_path / "full"
    meta.trace_level = "full"
    meta.run_id = "full"
    write_trace_v1(
        full_dir, metadata=meta,
        request={}, candidates=[], judge={}, cards=[], input_text="t",
        raw_generator="secret", raw_judge="secret",
        gen_prompt="prompt", judge_prompt="prompt",
    )
    assert (full_dir / "raw-generator.txt").exists()
    assert (full_dir / "prompt-generator.txt").exists()


def test_read_trace_judge_missing_file_returns_empty():
    """Missing judge.json returns a default empty JudgeResult."""
    d = Path("/tmp/test_no_judge_trace")
    d.mkdir(parents=True, exist_ok=True)
    # Ensure no judge.json
    jp = d / "judge.json"
    if jp.exists():
        jp.unlink()

    result = read_trace_judge(d)
    assert result.overall_decision == "no_useful_output"
    assert result.cards == []


def test_read_trace_candidates_missing_returns_empty():
    """Missing candidates.json returns empty list."""
    d = Path("/tmp/test_no_cand")
    d.mkdir(parents=True, exist_ok=True)
    cp = d / "candidates.json"
    if cp.exists():
        cp.unlink()

    result = read_trace_candidates(d)
    assert result == []


def test_compute_input_hash_stable():
    """Same input produces the same hash."""
    h1 = compute_input_hash("hello world")
    h2 = compute_input_hash("hello world")
    h3 = compute_input_hash("hello world!")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 16


def test_trace_metadata_privacy_default_private():
    """Default privacy level is PRIVATE."""
    meta = TraceMetadata()
    assert meta.privacy == PrivacyLevel.PRIVATE
    assert meta.to_dict()["privacy"] == "private"
    assert meta.trace_schema_version == "1"
