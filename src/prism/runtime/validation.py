"""Validation layer for Beerlight Runtime.

Reuses the validated slice validation logic (extract_json, validate_candidates,
validate_judge) plus adds runtime-level validations.

This is a thin wrapper — the core JSON extraction and schema validation
stays in the slice module.
"""
from __future__ import annotations

from typing import Any

# Re-export slice validation for convenience
from prism.slice.validate import (  # noqa: F401
    extract_json,
    validate_candidates,
    validate_judge,
    build_candidate_repair_prompt,
    build_judge_repair_prompt,
    CANDIDATE_SCHEMA,
    JUDGE_SCHEMA,
)

from .contracts import RunRequest


def validate_request(req: RunRequest) -> list[str]:
    """Validate a RunRequest. Returns list of errors."""
    return req.validate()


def validate_run_args(
    document: str | None,
    task: str | None,
    mode: str,
) -> list[str]:
    """Validate the arguments to beerlight.run()."""
    errors: list[str] = []
    if not document:
        errors.append("document is required")
    if not task:
        errors.append("task is required")
    if mode not in ("normal", "360"):
        errors.append(f"invalid mode: {mode}")
    return errors


def is_legacy_v0_trace(metadata: dict) -> bool:
    """Check if trace metadata is from legacy v0 slice.

    v0 traces lack the `trace_schema_version` field.
    """
    return "trace_schema_version" not in metadata


def is_v1_trace(metadata: dict) -> bool:
    """Check if trace metadata is v1."""
    return metadata.get("trace_schema_version") == "1"
