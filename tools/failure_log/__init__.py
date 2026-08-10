"""Isolated Failure Log System Core v0."""

from .schema import (
    ALLOWED_KINDS,
    ALLOWED_SEVERITIES,
    REQUIRED_FIELDS,
    ConflictError,
    FailureLogError,
    StorageError,
    ValidationError,
    normalize,
    serialize_event,
    split_jsonl_records,
    validate,
)
from .store import append_event

__all__ = [
    "ALLOWED_KINDS",
    "ALLOWED_SEVERITIES",
    "ConflictError",
    "FailureLogError",
    "REQUIRED_FIELDS",
    "StorageError",
    "ValidationError",
    "append_event",
    "normalize",
    "serialize_event",
    "split_jsonl_records",
    "validate",
]
