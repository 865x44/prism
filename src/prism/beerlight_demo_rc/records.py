"""Write-once material run records and visible-artifact safety checks."""
from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


RUN_RECORD_SCHEMA_VERSION = "beerlight-demo-rc-run-record-v1"
_RUN_ID = re.compile(r"^beerlight-demo-rc-[a-z0-9-]+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PHASES = {"P0", "P1", "P2", "P3", "P4", "P5"}
_CLASSIFICATIONS = {
    "SUBJECT_FAILURE",
    "BORDERLINE",
    "EVAL_ERROR",
    "SPEC_AMBIGUITY",
    "INFRASTRUCTURE_ERROR",
}


class RunRecordValidationError(ValueError):
    """Raised when material run evidence cannot be recorded safely."""


def safe_artifact_path(path: str) -> PurePosixPath:
    """Accept only repository-relative, traversal-free artifact paths."""
    candidate = PurePosixPath(path)
    if not isinstance(path, str) or not path or candidate.is_absolute() or ".." in candidate.parts:
        raise RunRecordValidationError(f"unsafe artifact path: {path!r}")
    if str(candidate) in {".", ""}:
        raise RunRecordValidationError(f"unsafe artifact path: {path!r}")
    return candidate


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256.fullmatch(value))


def validate_run_record(record: Any) -> dict[str, Any]:
    """Validate REV 2 material-run fields without inferring semantic success."""
    if not isinstance(record, dict):
        raise RunRecordValidationError("run record must be an object")
    required = {
        "schema_version",
        "run_id",
        "phase",
        "started_at",
        "git_head",
        "subject_config_identity",
        "subject_config_sha256",
        "evaluator_config_identity",
        "evaluator_config_sha256",
        "fixture_schema_version",
        "predicate_version",
        "input_sha256_manifest",
        "raw_visible_outputs",
        "deterministic_results",
        "semantic_diagnostic_results",
        "classification",
        "cost",
        "notes",
    }
    missing = sorted(required - record.keys())
    errors: list[str] = [f"missing required fields: {', '.join(missing)}"] if missing else []
    if record.get("schema_version") != RUN_RECORD_SCHEMA_VERSION:
        errors.append(f"schema_version must be {RUN_RECORD_SCHEMA_VERSION!r}")
    if not isinstance(record.get("run_id"), str) or not _RUN_ID.fullmatch(record["run_id"]):
        errors.append("run_id is invalid")
    if record.get("phase") not in _PHASES:
        errors.append("phase is invalid")
    if not isinstance(record.get("started_at"), str) or not record["started_at"]:
        errors.append("started_at is required")
    if not isinstance(record.get("git_head"), str) or not re.fullmatch(r"[0-9a-f]{40}", record["git_head"]):
        errors.append("git_head must be a 40-character SHA")
    for key in ("subject_config_sha256", "evaluator_config_sha256"):
        if not _is_sha(record.get(key)):
            errors.append(f"{key} must be a SHA-256")
    for key in ("subject_config_identity", "evaluator_config_identity", "fixture_schema_version", "predicate_version", "input_sha256_manifest"):
        if not isinstance(record.get(key), str) or not record[key]:
            errors.append(f"{key} must be a non-empty string")
    raw_outputs = record.get("raw_visible_outputs")
    if not isinstance(raw_outputs, list) or not raw_outputs:
        errors.append("raw_visible_outputs must be a non-empty list")
    elif any(not isinstance(item, str) for item in raw_outputs):
        errors.append("raw_visible_outputs must contain strings")
    else:
        for item in raw_outputs:
            try:
                safe_artifact_path(item)
            except RunRecordValidationError as exc:
                errors.append(str(exc))
    deterministic = record.get("deterministic_results")
    if not isinstance(deterministic, list):
        errors.append("deterministic_results must be a list")
    elif any(not isinstance(item, dict) or item.get("layer") != "DETERMINISTIC_CHECK" or item.get("status") not in {"PASS", "FAIL", "ERROR"} for item in deterministic):
        errors.append("deterministic results need DETERMINISTIC_CHECK and PASS/FAIL/ERROR")
    semantic = record.get("semantic_diagnostic_results")
    if not isinstance(semantic, list):
        errors.append("semantic_diagnostic_results must be a list")
    elif any(not isinstance(item, dict) or item.get("layer") != "SEMANTIC_JUDGMENT" or item.get("status") not in {"MET", "VIOLATED", "UNCLEAR", "EVAL_ERROR"} for item in semantic):
        errors.append("semantic diagnostics need SEMANTIC_JUDGMENT and a valid status")
    classifications = record.get("classification")
    if not isinstance(classifications, list) or any(item not in _CLASSIFICATIONS for item in classifications):
        errors.append("classification contains an invalid result class")
    if any(item.get("status") == "EVAL_ERROR" for item in semantic or []) and "EVAL_ERROR" not in classifications:
        errors.append("EVAL_ERROR diagnostic must be classified as EVAL_ERROR")
    if "SUBJECT_FAILURE" in (classifications or []) and any(
        item.get("status") == "EVAL_ERROR" for item in semantic or []
    ) and not any(item.get("status") == "FAIL" for item in deterministic or []) and not any(
        item.get("status") == "VIOLATED" for item in semantic or []
    ):
        errors.append("EVAL_ERROR alone cannot become SUBJECT_FAILURE")
    if not isinstance(record.get("cost"), dict) or not isinstance(record.get("notes"), list):
        errors.append("cost must be an object and notes must be a list")
    if errors:
        raise RunRecordValidationError("; ".join(errors))
    return record


def write_visible_output(run_root: str | Path, relative_path: str, text: str) -> Path:
    """Write one visible output under the run root, never outside it."""
    root = Path(run_root).resolve()
    target = root / safe_artifact_path(relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(text)
    return target


def write_run_record(run_root: str | Path, record: dict[str, Any], *, filename: str = "run-record.json") -> Path:
    """Validate and write a material record exactly once below its run root."""
    validate_run_record(record)
    root = Path(run_root).resolve()
    target = root / safe_artifact_path(filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return target
