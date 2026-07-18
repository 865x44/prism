"""Trace schema v1 and legacy v0 reader for Beerlight Runtime.

Trace schema v1:
    - Explicit trace_schema_version: "1"
    - Compact (default) and full trace levels
    - Privacy metadata (private|project|shareable)
    - Normalized paths (no absolute paths in committed artifacts)

Legacy v0:
    - Read-only compatibility
    - No trace_schema_version field
    - Normalized on read via internal representation

Unknown versions: explicit error.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import (
    TraceMetadata,
    PrivacyLevel,
    TraceLevel,
    Candidate,
    Card,
    JudgeJudgment,
    JudgeResult,
)


# --- legacy v0 normalization ---

def _normalize_v0_metadata(meta: dict) -> TraceMetadata:
    """Convert a legacy v0 metadata dict into a TraceMetadata."""
    return TraceMetadata(
        trace_schema_version="0",  # legacy
        run_id=meta.get("run_id", ""),
        mode=meta.get("mode", "normal"),
        generator_prompt_version=meta.get("generator_prompt_version", ""),
        judge_prompt_version=meta.get("judge_prompt_version", ""),
        generator_model=meta.get("generator_model", ""),
        judge_model=meta.get("judge_model", ""),
        judge_family_fallback=meta.get("judge_family_fallback", True),
        created_at=meta.get("created_at", ""),
        status=meta.get("status", ""),
        privacy=PrivacyLevel.PRIVATE,
        trace_level="compact",
        abstention_source=meta.get("abstention_source"),
    )


# --- trace writing (v1) ---

def write_trace_v1(
    trace_dir: Path,
    *,
    metadata: TraceMetadata,
    request: dict,
    candidates: list[dict],
    judge: dict,
    cards: list[dict],
    input_text: str,
    trajectory: str | None = None,
    # full-trace extras
    raw_generator: str | None = None,
    raw_judge: str | None = None,
    gen_prompt: str | None = None,
    judge_prompt: str | None = None,
    repair_prompt: str | None = None,
) -> None:
    """Write a v1 trace to `trace_dir`.

    Always writes: metadata.json, request.json, input.md,
                   candidates.json, judge.json, output.md.
    When trace_level=full: additionally raw-generator.txt, raw-judge.txt,
                           prompts-gen.txt, prompts-judge.txt.
    """
    trace_dir.mkdir(parents=True, exist_ok=True)

    # metadata.json (v1 with trace_schema_version)
    (trace_dir / "metadata.json").write_text(
        json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # request.json
    (trace_dir / "request.json").write_text(
        json.dumps(request, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # input.md
    (trace_dir / "input.md").write_text(input_text, encoding="utf-8")

    # candidates.json
    (trace_dir / "candidates.json").write_text(
        json.dumps(candidates, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # judge.json (full decisions)
    (trace_dir / "judge.json").write_text(
        json.dumps(judge, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # output.md (user-facing)
    from .service import _format_cards as _fmt
    output_md = _fmt(cards)
    output_md += f"\nRun: {metadata.run_id}\n"
    output_md += f"Trace: {trace_dir}\n"
    (trace_dir / "output.md").write_text(output_md, encoding="utf-8")

    # trajectory update if present
    if trajectory:
        (trace_dir / "trajectory-input.md").write_text(trajectory, encoding="utf-8")

    # full-trace extras
    if metadata.trace_level == "full":
        if raw_generator is not None:
            (trace_dir / "raw-generator.txt").write_text(
                raw_generator, encoding="utf-8",
            )
        if raw_judge is not None:
            (trace_dir / "raw-judge.txt").write_text(
                raw_judge, encoding="utf-8",
            )
        if gen_prompt is not None:
            (trace_dir / "prompt-generator.txt").write_text(
                gen_prompt, encoding="utf-8",
            )
        if judge_prompt is not None:
            (trace_dir / "prompt-judge.txt").write_text(
                judge_prompt, encoding="utf-8",
            )
        if repair_prompt is not None:
            (trace_dir / "prompt-repair.txt").write_text(
                repair_prompt, encoding="utf-8",
            )


# --- trace reading ---

def read_trace_metadata(trace_dir: Path) -> TraceMetadata:
    """Read trace metadata, handling v0 and v1 formats.

    Raises ValueError for unknown schema versions.
    """
    meta_path = trace_dir / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"metadata.json not found in {trace_dir}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    version = meta.get("trace_schema_version")

    if version is None:
        # Legacy v0
        return _normalize_v0_metadata(meta)
    elif version == "1":
        return TraceMetadata(
            trace_schema_version="1",
            run_id=meta.get("run_id", ""),
            mode=meta.get("mode", "normal"),
            generator_prompt_version=meta.get("generator_prompt_version", ""),
            judge_prompt_version=meta.get("judge_prompt_version", ""),
            generator_model=meta.get("generator_model", ""),
            judge_model=meta.get("judge_model", ""),
            judge_family_fallback=meta.get("judge_family_fallback", True),
            created_at=meta.get("created_at", ""),
            status=meta.get("status", ""),
            privacy=PrivacyLevel(meta.get("privacy", "private")),
            trace_level=meta.get("trace_level", "compact"),
            token_usage_estimate=meta.get("token_usage_estimate", 0),
            duration_sec=meta.get("duration_sec", 0.0),
            input_hash=meta.get("input_hash", ""),
            warnings=meta.get("warnings", []),
            abstention_source=meta.get("abstention_source"),
        )
    else:
        raise ValueError(
            f"Unknown trace_schema_version: {version!r}. "
            f"This version of Beerlight only reads v0 and v1 traces."
        )


def read_trace_judge(trace_dir: Path) -> JudgeResult:
    """Read judge.json from a trace directory."""
    judge_path = trace_dir / "judge.json"
    if not judge_path.exists():
        return JudgeResult(
            overall_decision="no_useful_output",
            cards=[],
            judgments=[],
        )
    data = json.loads(judge_path.read_text(encoding="utf-8"))
    return JudgeResult.from_dict(data)


def read_trace_candidates(trace_dir: Path) -> list[dict]:
    """Read candidates.json from a trace directory."""
    cand_path = trace_dir / "candidates.json"
    if not cand_path.exists():
        return []
    return json.loads(cand_path.read_text(encoding="utf-8"))


def compute_input_hash(text: str) -> str:
    """Compute a stable SHA-256 hash of the input text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
