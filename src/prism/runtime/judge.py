"""Judge wrapper for Prism Runtime.

Thin wrapper over the validated slice judge.
Builds judge prompts, calls LLM, and validates output.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .provider import (
    TransportError,
    call_llm,
    get_judge_model,
)
from .validation import (
    validate_judge,
    build_judge_repair_prompt,
)
from .models import JudgeResult

# Reuse slice prompt loading
from prism.slice.prompts import load_prompt


def build_judge_prompt(
    source: str,
    task: str,
    candidates_json: str,
    trajectory: str | None,
) -> str:
    """Build the judge prompt using validated slice template."""
    template = load_prompt("judge-v1.md")
    result = template.replace("{source}", source)
    result = result.replace("{task}", task)
    result = result.replace(
        "{trajectory}",
        trajectory or "(траектория отсутствует)",
    )
    result = result.replace("{candidates}", candidates_json)
    return result


def judge_with_repair(
    prompt: str,
    trace_dir: Path,
    expected_ids: list[str],
) -> tuple[JudgeResult | None, str, str, str | None]:
    """Run judge with one repair retry on validation failure.

    Returns:
        (JudgeResult|None, status, raw_response, repair_prompt|None)
        status: "ok" or "error"
    """
    model = get_judge_model()
    repair_prompt_used = None

    try:
        raw = call_llm(prompt, model)
    except TransportError as e:
        raw = str(e)
        (trace_dir / "raw-judge.txt").write_text(raw, encoding="utf-8")
        return None, "error", raw, None

    data, error = validate_judge(raw, expected_ids)
    if error is None and data is not None:
        return JudgeResult.from_dict(data), "ok", raw, None

    # One repair retry
    repair_prompt = build_judge_repair_prompt(raw, error or "unknown error")
    repair_prompt_used = repair_prompt

    try:
        raw2 = call_llm(repair_prompt, model)
    except TransportError as e:
        raw2 = str(e)
        (trace_dir / "raw-judge.txt").write_text(
            f"--- original ---\n{raw}\n\n"
            f"--- repair (transport error) ---\n{raw2}",
            encoding="utf-8",
        )
        return None, "error", raw2, repair_prompt_used

    data, error = validate_judge(raw2, expected_ids)
    if error is None and data is not None:
        return JudgeResult.from_dict(data), "ok", raw2, repair_prompt_used

    # Second failure
    (trace_dir / "raw-judge.txt").write_text(
        f"--- original ---\n{raw}\n\n"
        f"--- repair ---\n{raw2}\n\n"
        f"--- error ---\n{error}",
        encoding="utf-8",
    )
    return None, "error", raw2, repair_prompt_used


def judge_abstention(candidates: list[dict]) -> JudgeResult:
    """Create a judge result for generator abstention (zero candidates).

    No LLM call is made — this records the abstention source explicitly.
    """
    return JudgeResult(
        overall_decision="no_useful_output",
        cards=[],
        judgments=[],
        abstention_source="generator",
    )
