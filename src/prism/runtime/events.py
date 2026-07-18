"""Outcome events — append-only semantics for Beerlight Runtime.

Every user action that changes a candidate's state is recorded as an event
in session/events.jsonl. Events are append-only and immutable — no edits
or deletions of lines are allowed.

Event types (from brief §3.1):
    shown selected expanded saved rejected applied revised retained
    reverted unrated

Schema (one JSON object per line):
    {"timestamp": "...", "session_id": "...", "run_id": "...",
     "candidate_id": "...", "type": "...", "reason": "...", "metadata": {}}

Rules:
    - Absence of any event for a candidate = unrated (not rejected).
    - Append-only: no modifications to existing lines.
    - Validation: type must be a known event type; run_id and candidate_id
      are required.
    - events.jsonl is the single source of truth; outcomes are derived from it.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .session import EVENTS_JSONL

# Valid event types
EVENT_TYPES = frozenset({
    "shown",
    "selected",
    "expanded",
    "saved",
    "rejected",
    "applied",
    "revised",
    "retained",
    "reverted",
    "unrated",
})


def _events_path(session_dir: str) -> Path:
    """Resolve the events.jsonl path for a session directory."""
    return Path(session_dir) / EVENTS_JSONL


def write_event(
    session_dir: str,
    run_id: str,
    candidate_id: str,
    event_type: str,
    *,
    reason: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict:
    """Append a single event to session/events.jsonl.

    Args:
        session_dir: Path to the session directory.
        run_id: The run that generated this candidate.
        candidate_id: The candidate this event applies to.
        event_type: One of the valid event types.
        reason: Optional human-readable reason.
        metadata: Optional extra metadata dict.

    Returns:
        The written event as a dict.

    Raises:
        ValueError: If event_type is invalid or run_id/candidate_id are empty.
        FileNotFoundError: If the session does not exist.
    """
    # Validate
    if event_type not in EVENT_TYPES:
        raise ValueError(
            f"Invalid event type: {event_type!r}. "
            f"Must be one of: {sorted(EVENT_TYPES)}"
        )
    if not run_id:
        raise ValueError("run_id is required")
    if not candidate_id:
        raise ValueError("candidate_id is required")

    events_path = _events_path(session_dir)
    if not events_path.parent.exists():
        raise FileNotFoundError(
            f"Session directory not found: {session_dir}"
        )

    # Build event
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": _get_session_id(session_dir),
        "run_id": run_id,
        "candidate_id": candidate_id,
        "type": event_type,
        "reason": reason,
        "metadata": metadata or {},
    }

    # Append atomically
    line = json.dumps(event, ensure_ascii=False) + "\n"
    _append_line(events_path, line)

    return event


def read_events(session_dir: str) -> list[dict]:
    """Read all events from session/events.jsonl.

    Args:
        session_dir: Path to the session directory.

    Returns:
        List of event dicts in order they were written.

    Raises:
        FileNotFoundError: If the session does not exist.
    """
    events_path = _events_path(session_dir)
    if not events_path.exists():
        return []

    events: list[dict] = []
    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # Skip corrupted lines (should not happen with atomic writes)
                continue
    return events


def read_events_for_candidate(session_dir: str, candidate_id: str) -> list[dict]:
    """Read all events for a specific candidate (preserving order)."""
    return [e for e in read_events(session_dir)
            if e.get("candidate_id") == candidate_id]


def read_events_for_run(session_dir: str, run_id: str) -> list[dict]:
    """Read all events for a specific run (preserving order)."""
    return [e for e in read_events(session_dir)
            if e.get("run_id") == run_id]


def get_last_event_for_candidate(
    session_dir: str, candidate_id: str
) -> dict | None:
    """Get the most recent event for a candidate, or None if unrated."""
    events = read_events_for_candidate(session_dir, candidate_id)
    if not events:
        return None
    return events[-1]


def count_events(session_dir: str) -> int:
    """Count total number of events in the session."""
    events_path = _events_path(session_dir)
    if not events_path.exists():
        return 0
    count = 0
    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


# --- internal helpers ---

def _append_line(path: Path, line: str) -> None:
    """Append a line to a file atomically (open-append-close with fsync).

    For truly concurrent writes you'd want file locking, but for a
    single-process CLI this is safe.
    """
    # Ensure the file exists
    if not path.exists():
        path.write_text("", encoding="utf-8")

    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def _get_session_id(session_dir: str) -> str:
    """Read session_id from session.json, or return a fallback."""
    try:
        from .session import get_session_metadata
        return get_session_metadata(session_dir).get("session_id", "")
    except Exception:
        return ""
