"""Append-only storage for failure/papercut events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import (
    ConflictError,
    StorageError,
    ValidationError,
    normalize,
    serialize_event,
    split_jsonl_records,
    validate,
    validate_input_shape,
)


def _load_storage(path: Path) -> tuple[list[dict[str, Any]], str]:
    """Read and validate every record in *path*.

    Returns the parsed, normalized records and the raw file text. Each record
    is normalized before its id is used for cross-record uniqueness checks so
    that ``"x"`` and ``" x "`` collide.

    Raises StorageError on malformed JSON, invalid records, duplicate event
    ids, or UTF-8 unencodable canonical records. OSError while reading the
    file is allowed to propagate so callers can treat it as an unexpected I/O
    problem.
    """
    text = path.read_text(encoding="utf-8")

    records: list[dict[str, Any]] = []
    seen_ids: dict[str, int] = {}

    for lineno, raw in enumerate(split_jsonl_records(text), start=1):
        if raw == "":
            raise StorageError(f"line {lineno}: empty line")
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StorageError(f"line {lineno}: malformed JSON ({exc})")

        errors = validate(record)
        if errors:
            raise StorageError(f"line {lineno}: " + "; ".join(errors))

        normalized_record = normalize(record)
        record_id = normalized_record["id"]
        if record_id in seen_ids:
            raise StorageError(
                f"line {lineno}: duplicate event id '{record_id}' "
                f"(first seen on line {seen_ids[record_id]})"
            )
        seen_ids[record_id] = lineno
        records.append(normalized_record)

    return records, text


def append_event(path: Path, event: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Append a single event to *path*.

    Validates the raw input shape first, then normalizes and validates the
    event. If the file exists and is non-empty, the entire existing storage is
    validated and cross-record id uniqueness is checked using normalized ids.

    - If the same normalized id already exists with an identical normalized
      event, this call is an idempotent no-op and returns
      ``(False, existing_record)``.
    - If the same normalized id exists with a different payload, a
      :class:`ConflictError` is raised.

    Returns ``(True, committed_record)`` when a new record is actually written.

    The parent directory is created if it does not exist. A missing terminal
    newline in the existing file is handled by writing a separator newline
    before the new record.
    """
    path = Path(path)

    shape_errors = validate_input_shape(event)
    if shape_errors:
        raise ValidationError("; ".join(shape_errors))

    normalized = normalize(event)

    errors = validate(normalized)
    if errors:
        raise ValidationError("; ".join(errors))

    serialized_new = serialize_event(normalized)
    try:
        serialized_new.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValidationError(f"event cannot be encoded as UTF-8: {exc}")

    existing_text = ""

    if path.exists() and path.stat().st_size > 0:
        existing, existing_text = _load_storage(path)
        for existing_normalized in existing:
            if existing_normalized["id"] == normalized["id"]:
                if serialize_event(existing_normalized) == serialized_new:
                    return False, existing_normalized
                raise ConflictError(
                    f"id '{normalized['id']}' already exists with a different payload"
                )

    path.parent.mkdir(parents=True, exist_ok=True)
    separator = "\n" if existing_text and not existing_text.endswith("\n") else ""
    payload = separator + serialized_new

    with path.open("a", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()

    return True, normalized
