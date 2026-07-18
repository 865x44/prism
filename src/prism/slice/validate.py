"""JSON extraction and schema validation for Prism slice.

Handles:
- Extraction of JSON from LLM output (fenced blocks, raw spans)
- Schema validation against expected shapes
- One bounded repair retry via LLM on parse failure
"""
from __future__ import annotations

import json
import re
from typing import Any

# --------------- candidate schema ---------------

CANDIDATE_SCHEMA: dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["id", "title", "core_shift", "source_basis",
                     "practical_return", "boundary"],
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "core_shift": {"type": "string"},
            "source_basis": {"type": "array", "items": {"type": "string"}},
            "practical_return": {"type": "string"},
            "boundary": {"type": "string"},
            "operator": {"type": "string"},
        },
    },
}

# --------------- judge schema ---------------

JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["overall_decision", "cards", "judgments"],
    "properties": {
        "overall_decision": {"type": "string"},
        "cards": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "shift", "basis", "action", "boundary"],
                "properties": {
                    "title": {"type": "string"},
                    "shift": {"type": "string"},
                    "basis": {"type": "string"},
                    "action": {"type": "string"},
                    "boundary": {"type": "string"},
                },
            },
        },
        "judgments": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["candidate_id", "action", "novelty",
                             "fidelity", "failure_tags", "reason"],
                "properties": {
                    "candidate_id": {"type": "string"},
                    "action": {"type": "string"},
                    "novelty": {"type": "string"},
                    "fidelity": {"type": "string"},
                    "failure_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "reason": {"type": "string"},
                },
            },
        },
        "trajectory_update": {
            "type": "object",
            "properties": {
                "explored": {"type": "array", "items": {"type": "string"}},
                "shown": {"type": "array", "items": {"type": "string"}},
                "open_questions": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
    },
}


def _type_matches(instance: Any, schema: dict) -> bool:
    """Simple structural type check (not full JSON Schema)."""
    t = schema.get("type")
    if t == "string":
        return isinstance(instance, str)
    if t == "array":
        if not isinstance(instance, list):
            return False
        items_schema = schema.get("items")
        if items_schema:
            return all(_type_matches(item, items_schema) for item in instance)
        return True
    if t == "object":
        if not isinstance(instance, dict):
            return False
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                return False
        for key, val in instance.items():
            prop_schema = schema.get("properties", {}).get(key)
            if prop_schema:
                if not _type_matches(val, prop_schema):
                    return False
        return True
    return True  # unknown type → accept


def extract_json(text: str) -> str | None:
    """Extract JSON from LLM output that may contain markdown wrappers.

    Tries:
    1. Parse the whole text as JSON directly.
    2. Extract from ```json ... ``` fenced block.
    3. Extract from ``` ... ``` fenced block.
    4. Find span from first '{' or '[' to last '}' or ']'.
    """
    text = text.strip()

    # 1. Direct parse (will be tried by caller)

    # 2. Fenced json block
    m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        return m.group(1).strip()

    # 3. Any fenced block
    m = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        return m.group(1).strip()

    # 4. Span from outermost bracket to matching outermost bracket
    first_sq = text.find("[")
    first_cu = text.find("{")
    last_sq = text.rfind("]")
    last_cu = text.rfind("}")

    first = -1
    if first_sq != -1 and first_cu != -1:
        first = min(first_sq, first_cu)
    elif first_sq != -1:
        first = first_sq
    elif first_cu != -1:
        first = first_cu

    last = -1
    if last_sq != -1 and last_cu != -1:
        last = max(last_sq, last_cu)
    elif last_sq != -1:
        last = last_sq
    elif last_cu != -1:
        last = last_cu

    if first != -1 and last > first:
        return text[first:last + 1]

    return None


def validate_candidates(raw_text: str) -> tuple[list[dict] | None, str | None]:
    """Extract and validate candidate JSON.

    Returns (parsed_list, error_string).
    If error_string is not None, parsed_list is None.
    """
    extracted = extract_json(raw_text)
    if extracted is None:
        # Try parsing whole text as-is
        extracted = raw_text

    try:
        data = json.loads(extracted)
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"

    if not isinstance(data, list):
        return None, "Expected a JSON array of candidates, got: " + type(data).__name__

    if not data:
        # Empty candidate list is valid (no useful ideas)
        return [], None

    if not _type_matches(data, CANDIDATE_SCHEMA):
        return None, "Candidates do not match expected schema"

    return data, None


def validate_judge(
    raw_text: str,
    expected_ids: list[str] | None = None,
) -> tuple[dict | None, str | None]:
    """Extract and validate judge JSON.

    Args:
        raw_text: Raw judge response.
        expected_ids: Candidate ids the judge had to decide on.
            When non-empty, judgments must cover every id — even
            (especially) when overall_decision is no_useful_output.
            Empty list (generator abstention) allows empty judgments.

    Returns (parsed_dict, error_string).
    """
    extracted = extract_json(raw_text)
    if extracted is None:
        extracted = raw_text

    try:
        data = json.loads(extracted)
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"

    if not isinstance(data, dict):
        return None, "Expected a JSON object, got: " + type(data).__name__

    if not _type_matches(data, JUDGE_SCHEMA):
        return None, "Judge output does not match expected schema"

    if expected_ids:
        judged = {
            j.get("candidate_id")
            for j in data.get("judgments", [])
            if isinstance(j, dict)
        }
        missing = [cid for cid in expected_ids if cid not in judged]
        if missing:
            return None, (
                "judgments must cover every candidate even when "
                "overall_decision is no_useful_output; "
                f"missing: {', '.join(missing)}"
            )

    return data, None


def build_candidate_repair_prompt(raw_response: str, error: str) -> str:
    """Build a repair prompt asking the LLM to return valid candidate JSON."""
    return (
        "Твой предыдущий ответ не был валидным JSON по требуемой схеме.\n\n"
        f"Ошибка: {error}\n\n"
        "Верни ТОЛЬКО валидный JSON-массив кандидатов. "
        "Каждый кандидат — объект с полями: "
        "id (строка), title (строка), core_shift (строка), "
        "source_basis (массив строк), practical_return (строка), "
        "boundary (строка), operator (строка, опционально).\n\n"
        "Не используй markdown-обёртки. Только JSON."
    )


def build_judge_repair_prompt(raw_response: str, error: str) -> str:
    """Build a repair prompt asking the LLM to return valid judge JSON."""
    return (
        "Твой предыдущий ответ не был валидным JSON по требуемой схеме.\n\n"
        f"Ошибка: {error}\n\n"
        "Верни ТОЛЬКО валидный JSON-объект с полями: "
        "overall_decision (строка), cards (массив карточек), "
        "judgments (массив оценок), trajectory_update (объект, опционально).\n\n"
        "Не используй markdown-обёртки. Только JSON."
    )
