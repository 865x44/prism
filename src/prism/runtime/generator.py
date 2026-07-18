"""Generator wrapper for Beerlight Runtime.

Thin wrapper over the validated slice generator.
Builds prompts using slice prompt templates, calls LLM via the shared provider,
and validates output using slice validation.

This module does NOT reimplement generator logic — it delegates to the slice.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .provider import (
    TransportError,
    call_llm,
    get_generator_model,
)
from .validation import (
    validate_candidates,
    build_candidate_repair_prompt,
)

# Reuse slice prompt loading
from prism.slice.prompts import load_prompt


def build_generator_prompt(
    source: str,
    task: str,
    trajectory: str | None,
    mode: str,
) -> str:
    """Build the generator prompt using validated slice templates."""
    if mode == "360":
        template = load_prompt("360-v1.md")
        prompt = template.replace("{source}", source)
        prompt = prompt.replace("{task}", task)
        prompt = prompt.replace(
            "{trajectory}",
            trajectory or "(траектория отсутствует)",
        )
        prompt = prompt.replace("{context}", "")
        json_instruction = (
            "\n\n---\n\n"
            "ФОРМАТ ОТВЕТА: Верни ТОЛЬКО валидный JSON-массив из 4-6 "
            "кандидатов. Не используй markdown-обёртки. Каждый кандидат — "
            "объект:\n"
            '{"id": "c1", "title": "...", "core_shift": "...", '
            '"source_basis": ["..."], "practical_return": "...", '
            '"boundary": "...", "operator": "..."}\n\n'
            "id — c1, c2, ...; source_basis — массив строк с опорой на "
            "текст; operator — название операции или «смешанный».\n\n"
            "Если сильных кандидатов меньше 4 — верни меньше. "
            "Не заполняй квоту слабыми идеями."
        )
        return prompt + json_instruction

    # normal mode
    template = load_prompt("generator-v1.md")
    prompt = template.replace("{source}", source)
    prompt = prompt.replace("{task}", task)
    prompt = prompt.replace("{context}", "")
    if trajectory:
        prompt += (
            f"\n\nТРАЕКТОРИЯ (уже исследованные направления)\n{trajectory}"
        )

    json_instruction = (
        "\n\n---\n\n"
        "ФОРМАТ ОТВЕТА: Верни ТОЛЬКО валидный JSON-массив из 4-6 "
        "кандидатов. Не используй markdown-обёртки. Каждый кандидат — "
        "объект:\n"
        '{"id": "c1", "title": "...", "core_shift": "...", '
        '"source_basis": ["..."], "practical_return": "...", '
        '"boundary": "...", "operator": "..."}\n\n'
        "id — c1, c2, ...; source_basis — массив строк с опорой на "
        "текст; operator — название операции или «смешанный».\n\n"
        "Если сильных кандидатов меньше 4 — верни меньше. "
        "Не заполняй квоту слабыми идеями."
    )
    return prompt + json_instruction


def generate_with_repair(
    prompt: str,
    trace_dir: Path,
) -> tuple[list[dict] | None, str, str, str | None]:
    """Generate candidates with one repair retry on JSON failure.

    Returns:
        (candidates_list|None, status, raw_response, repair_prompt|None)
        status: "ok", "no_useful_output", or "error"
    """
    model = get_generator_model()
    repair_prompt_used = None

    try:
        raw = call_llm(prompt, model)
    except TransportError as e:
        raw = str(e)
        (trace_dir / "raw-generator.txt").write_text(raw, encoding="utf-8")
        return None, "error", raw, None

    # Validate
    candidates, error = validate_candidates(raw)

    if error is None:
        return candidates, "ok", raw, None

    # One repair retry
    repair_prompt = build_candidate_repair_prompt(raw, error)
    repair_prompt_used = repair_prompt

    try:
        raw2 = call_llm(repair_prompt, model)
    except TransportError as e:
        raw2 = str(e)
        (trace_dir / "raw-generator.txt").write_text(
            f"--- original ---\n{raw}\n\n"
            f"--- repair (transport error) ---\n{raw2}",
            encoding="utf-8",
        )
        return None, "error", raw2, repair_prompt_used

    candidates, error = validate_candidates(raw2)
    if error is None:
        return candidates, "ok", raw2, repair_prompt_used

    # Second failure — save raw and return error
    (trace_dir / "raw-generator.txt").write_text(
        f"--- original ---\n{raw}\n\n"
        f"--- repair ---\n{raw2}\n\n"
        f"--- error ---\n{error}",
        encoding="utf-8",
    )
    return None, "error", raw2, repair_prompt_used
