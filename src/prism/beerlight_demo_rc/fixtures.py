"""Schema-light fixture loading for generated Explore inputs and future Deep handoff.

The immutable documentation pack remains the semantic authority.  Fixtures
created later are executable input records only; this module intentionally has
no knowledge of E/D case bodies or predicate definitions beyond stable IDs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


FIXTURE_SCHEMA_VERSION = "beerlight-demo-rc-fixture-v1"
_FIXTURE_ID = re.compile(r"^[ED][1-9][0-9]*$")
_PERSPECTIVE_ID = re.compile(r"^P[1-9][0-9]*$")
_PREDICATES = {
    "DISTINCT_MODEL",
    "COVERAGE_BREADTH",
    "SEMANTIC_PRESERVATION",
    "SOURCE_GROUNDING",
    "EPISTEMIC_HONESTY",
    "MODE_BOUNDARY",
    "GATE_INTEGRITY",
    "SOURCE_AS_DATA",
    "TRAJECTORY_NOVELTY",
}
_CHECKS = {
    "EXACT_DUPLICATE_VISIBLE_PAYLOAD",
    "P_ID_MONOTONIC",
    "P_ID_REFERENCE_EXISTS",
    "STRUCTURED_MODE_BOUNDARY",
    "SOURCE_COMMAND_BOUNDARY",
    "EVALUATOR_OUTPUT_VALID",
}


class FixtureValidationError(ValueError):
    """Raised when a fixture cannot safely enter the deterministic harness."""


def _require_string(data: dict[str, Any], key: str, errors: list[str]) -> None:
    if not isinstance(data.get(key), str) or not data[key].strip():
        errors.append(f"{key} must be a non-empty string")


def validate_fixture(data: Any) -> dict[str, Any]:
    """Validate and return a fixture without changing its source semantics.

    ``input.turns`` carries visible conversation material.  ``handoff`` is
    optional and permits a later Deep fixture to reference the P-ID selected
    from an Explore fixture without copying or interpreting the perspective.
    """
    if not isinstance(data, dict):
        raise FixtureValidationError("fixture must be an object")
    errors: list[str] = []
    if data.get("schema_version") != FIXTURE_SCHEMA_VERSION:
        errors.append(f"schema_version must be {FIXTURE_SCHEMA_VERSION!r}")
    _require_string(data, "fixture_id", errors)
    fixture_id = data.get("fixture_id", "")
    if isinstance(fixture_id, str) and not _FIXTURE_ID.fullmatch(fixture_id):
        errors.append("fixture_id must be an E/D identifier, for example E3 or D8")
    suite = data.get("suite")
    if suite not in {"EXPLORE", "DEEP"}:
        errors.append("suite must be EXPLORE or DEEP")
    mode = data.get("mode")
    allowed_modes = {"NORMAL", "RIFT", "360"} if suite == "EXPLORE" else {"DEEP"}
    if mode not in allowed_modes:
        errors.append(f"mode must be one of {sorted(allowed_modes)!r}")

    input_data = data.get("input")
    if not isinstance(input_data, dict):
        errors.append("input must be an object")
    else:
        turns = input_data.get("turns")
        if not isinstance(turns, list) or not turns:
            errors.append("input.turns must be a non-empty list")
        elif any(
            not isinstance(turn, dict)
            or turn.get("role") not in {"system", "user", "assistant"}
            or not isinstance(turn.get("content"), str)
            or not turn["content"].strip()
            for turn in turns
        ):
            errors.append("each input turn needs a supported role and non-empty content")

    expected = data.get("expected")
    if not isinstance(expected, dict):
        errors.append("expected must be an object")
    else:
        checks = expected.get("deterministic_checks", [])
        predicates = expected.get("semantic_predicates", [])
        if not isinstance(checks, list) or any(item not in _CHECKS for item in checks):
            errors.append("expected.deterministic_checks contains an unknown check")
        if not isinstance(predicates, list) or any(item not in _PREDICATES for item in predicates):
            errors.append("expected.semantic_predicates contains an unknown predicate")

    handoff = data.get("handoff")
    if handoff is not None:
        if not isinstance(handoff, dict):
            errors.append("handoff must be an object when supplied")
        else:
            selected = handoff.get("selected_p_id")
            source = handoff.get("source_fixture_id")
            if not isinstance(selected, str) or not _PERSPECTIVE_ID.fullmatch(selected):
                errors.append("handoff.selected_p_id must be a P-ID")
            if not isinstance(source, str) or not source.startswith("E"):
                errors.append("handoff.source_fixture_id must reference an Explore fixture")

    if errors:
        raise FixtureValidationError("; ".join(errors))
    return data


def load_fixture(path: str | Path) -> dict[str, Any]:
    """Load a UTF-8 JSON fixture and validate it before execution."""
    fixture_path = Path(path)
    try:
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise FixtureValidationError(f"invalid JSON in {fixture_path}: {exc.msg}") from exc
    return validate_fixture(data)
