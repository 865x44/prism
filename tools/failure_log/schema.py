"""Event schema and validation for the Failure Log System Core."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

REQUIRED_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "timestamp",
        "kind",
        "source",
        "summary",
        "evidence",
        "severity",
        "recurrence_key",
    }
)

ALLOWED_KINDS: frozenset[str] = frozenset({"failure", "papercut"})
ALLOWED_SEVERITIES: frozenset[str] = frozenset({"minor", "major", "blocker"})

# Strict RFC 3339 profile:
#   YYYY-MM-DDTHH:MM:SS with optional fractional seconds,
#   followed by Z or a numeric offset HH:MM.
_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?"
    r"(?:Z|[+-]\d{2}:\d{2})$"
)


class FailureLogError(Exception):
    """Base class for domain errors raised by the Failure Log Core."""


class ValidationError(FailureLogError):
    """Raised when an event fails schema validation."""


class ConflictError(FailureLogError):
    """Raised when a record conflicts with an existing id."""


class StorageError(FailureLogError):
    """Raised when existing storage is unreadable, malformed or invalid."""


def split_jsonl_records(text: str) -> list[str]:
    """Split JSONL text on literal LF only.

    Unicode line and paragraph separators (U+0085, U+2028, U+2029) that occur
    inside JSON string values are preserved. A normal terminal LF does not
    create an extra empty record, but internal empty LF-delimited records are
    retained so validation can report them.
    """
    if text == "":
        return []
    records = text.split("\n")
    if records and records[-1] == "":
        records.pop()
    return records


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def validate_input_shape(event: Any) -> list[str]:
    """Validate the raw input shape before normalization.

    Checks that *event* is a mapping, that every key is a string, and that no
    unknown fields are present. Missing required fields are intentionally left
    to :func:`validate` so that valid-field values are normalized first.
    """
    errors: list[str] = []

    if not isinstance(event, dict):
        errors.append("event must be a mapping")
        return errors

    for key in event.keys():
        if not isinstance(key, str):
            errors.append(f"field name must be a string, got {type(key).__name__}")

    unknown = event.keys() - REQUIRED_FIELDS
    if unknown:
        errors.append(f"unknown fields: {', '.join(sorted(str(k) for k in unknown))}")

    return errors


def _parse_rfc3339(value: str) -> datetime:
    """Parse a strict RFC 3339 timestamp and require a timezone.

    The accepted shape is ``YYYY-MM-DDTHH:MM:SS(.frac)?(Z|[+-]HH:MM)``.
    Rejected forms include space instead of ``T``, compact dates/times,
    ISO week dates, offsets with seconds, timestamps without seconds, and
    timestamps without timezone.

    Raises ValueError for shape mismatches, missing timezone, or impossible
    calendar values.
    """
    if not _TIMESTAMP_RE.match(value):
        raise ValueError(
            "timestamp must match RFC 3339 "
            "YYYY-MM-DDTHH:MM:SS(.frac)?(Z|[+-]HH:MM)"
        )
    parse_value = value[:-1] + "+00:00" if value.endswith("Z") else value
    dt = datetime.fromisoformat(parse_value)
    if dt.tzinfo is None:
        raise ValueError("timestamp is missing timezone offset or Z")
    return dt


def _ensure_utf8_encodable(record: dict[str, Any]) -> str | None:
    """Return an error message if the canonical serialization is not UTF-8 encodable."""
    try:
        serialize_event(record).encode("utf-8")
    except UnicodeEncodeError as exc:
        return f"event cannot be encoded as UTF-8: {exc}"
    return None


def validate(event: dict[str, Any]) -> list[str]:
    """Return a list of validation errors for *event*.

    An empty list means the event conforms to the core schema.
    """
    errors: list[str] = []

    if not isinstance(event, dict):
        errors.append("event must be a JSON object")
        return errors

    for key in event.keys():
        if not isinstance(key, str):
            errors.append(f"field name must be a string, got {type(key).__name__}")

    string_keys = {k for k in event.keys() if isinstance(k, str)}
    unknown = string_keys - REQUIRED_FIELDS
    if unknown:
        errors.append(f"unknown fields: {', '.join(sorted(unknown))}")

    missing = REQUIRED_FIELDS - string_keys
    if missing:
        errors.append(f"missing required fields: {', '.join(sorted(missing))}")

    if not _is_non_empty_string(event.get("id")):
        errors.append("id must be a non-empty string")

    timestamp = event.get("timestamp")
    if not _is_non_empty_string(timestamp):
        errors.append("timestamp must be a non-empty string")
    else:
        try:
            _parse_rfc3339(timestamp)
        except ValueError as exc:
            errors.append(f"timestamp must be a valid RFC 3339 datetime: {exc}")

    kind = event.get("kind")
    if kind not in ALLOWED_KINDS:
        errors.append(f"kind must be one of: {', '.join(sorted(ALLOWED_KINDS))}")

    if not _is_non_empty_string(event.get("source")):
        errors.append("source must be a non-empty string")

    if not _is_non_empty_string(event.get("summary")):
        errors.append("summary must be a non-empty string")

    evidence = event.get("evidence")
    if not _is_non_empty_string(evidence):
        errors.append("evidence must be a non-empty string")

    severity = event.get("severity")
    if severity not in ALLOWED_SEVERITIES:
        errors.append(f"severity must be one of: {', '.join(sorted(ALLOWED_SEVERITIES))}")

    if not _is_non_empty_string(event.get("recurrence_key")):
        errors.append("recurrence_key must be a non-empty string")

    if not errors:
        utf8_error = _ensure_utf8_encodable(event)
        if utf8_error:
            errors.append(utf8_error)

    return errors


def normalize(event: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized copy of *event* with trimmed string values."""
    normalized: dict[str, Any] = {}
    for key in REQUIRED_FIELDS:
        value = event.get(key)
        if isinstance(value, str):
            value = value.strip()
        normalized[key] = value
    return normalized


def serialize_event(event: dict[str, Any]) -> str:
    """Return a deterministic, canonical JSON representation of *event*."""
    return json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def now_timestamp() -> str:
    """Return the current UTC time as an RFC 3339 timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
