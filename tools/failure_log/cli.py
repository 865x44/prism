"""Command-line interface for the Failure Log System Core."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Sequence

from .schema import (
    ALLOWED_KINDS,
    ALLOWED_SEVERITIES,
    ConflictError,
    StorageError,
    ValidationError,
    normalize,
    now_timestamp,
    serialize_event,
    split_jsonl_records,
    validate,
)
from .store import append_event

EXIT_OK = 0
EXIT_DOMAIN = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3


def _build_event(args: argparse.Namespace) -> dict[str, Any]:
    event_id = args.id
    if event_id is None:
        event_id = str(uuid.uuid4())

    timestamp = args.timestamp
    if timestamp is None:
        timestamp = now_timestamp()

    return {
        "id": event_id,
        "timestamp": timestamp,
        "kind": args.kind,
        "source": args.source,
        "summary": args.summary,
        "evidence": args.evidence,
        "severity": args.severity,
        "recurrence_key": args.recurrence_key,
    }


def _cmd_record(args: argparse.Namespace) -> int:
    event = _build_event(args)
    errors = validate(event)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return EXIT_DOMAIN

    normalized = normalize(event)

    if args.dry_run:
        print(serialize_event(normalized).rstrip("\n"))
        return EXIT_OK

    try:
        _, committed = append_event(Path(args.output), normalized)
    except (ValidationError, ConflictError, StorageError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_DOMAIN
    except OSError as exc:
        print(f"ERROR: cannot write to {args.output}: {exc}", file=sys.stderr)
        return EXIT_INTERNAL
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"ERROR: unexpected failure: {exc}", file=sys.stderr)
        return EXIT_INTERNAL

    print(serialize_event(committed).rstrip("\n"))
    return EXIT_OK


def _cmd_doctor(args: argparse.Namespace) -> int:
    path = Path(args.output)
    if not path.exists():
        print(f"ERROR: file does not exist: {path}", file=sys.stderr)
        return EXIT_INTERNAL

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        print(f"ERROR: cannot decode {path} as UTF-8: {exc}", file=sys.stderr)
        return EXIT_INTERNAL
    except OSError as exc:
        print(f"ERROR: cannot read {path}: {exc}", file=sys.stderr)
        return EXIT_INTERNAL

    findings: list[str] = []
    seen_ids: dict[str, int] = {}

    for lineno, raw in enumerate(split_jsonl_records(text), start=1):
        if raw == "":
            findings.append(f"line {lineno}: empty line")
            continue

        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            findings.append(f"line {lineno}: malformed JSON ({exc})")
            continue

        errors = validate(record)
        if errors:
            for err in errors:
                findings.append(f"line {lineno}: {err}")
            continue

        normalized_record = normalize(record)
        record_id = normalized_record["id"]
        if record_id in seen_ids:
            findings.append(
                f"line {lineno}: duplicate event id '{record_id}' "
                f"(first seen on line {seen_ids[record_id]})"
            )
        else:
            seen_ids[record_id] = lineno

    if findings:
        print(f"DOCTOR: {len(findings)} issue(s) found in {path}", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return EXIT_DOMAIN

    print(f"DOCTOR: {path} is healthy ({len(split_jsonl_records(text))} record(s))")
    return EXIT_OK


def _add_output_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Path to the JSONL log file. Must be explicit; no default is provided.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="failure-log-record",
        description="Isolated Failure Log System Core v0",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record", help="append a failure or papercut event")
    _add_output_arg(record)
    record.add_argument("--id", help="event id (generated if omitted)")
    record.add_argument(
        "--timestamp",
        help=(
            "RFC 3339 timestamp with timezone, e.g. "
            "2026-07-16T20:00:00Z or 2026-07-16T20:00:00+05:00 "
            "(current UTC time if omitted)"
        ),
    )
    record.add_argument(
        "--kind",
        required=True,
        choices=sorted(ALLOWED_KINDS),
        help="event kind",
    )
    record.add_argument("--source", required=True, help="event source")
    record.add_argument("--summary", required=True, help="concise summary")
    record.add_argument("--evidence", required=True, help="evidence or evidence reference")
    record.add_argument(
        "--severity",
        required=True,
        choices=sorted(ALLOWED_SEVERITIES),
        help="severity",
    )
    record.add_argument("--recurrence-key", required=True, help="recurrence grouping key")
    record.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and print the normalized event without writing",
    )

    doctor = subparsers.add_parser("doctor", help="validate an existing log without modifying it")
    _add_output_arg(doctor)

    args = parser.parse_args(argv)

    if args.command == "record":
        return _cmd_record(args)
    if args.command == "doctor":
        return _cmd_doctor(args)

    parser.print_help(sys.stderr)
    return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
