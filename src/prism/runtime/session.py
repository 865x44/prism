"""Session layer for Beerlight Runtime.

Session layout:
    session/
    ├── original.md       (immutable, written once on creation)
    ├── current.md         (mutable, updated by user or harness)
    ├── trajectory.md      (accumulated trajectory)
    ├── session.json       (session metadata)
    ├── events.jsonl       (empty append-only surface in Wave 1)
    └── runs/
        └── <run_id>/

Operations:
    create session
    run current document
    update current document
    read trajectory
    apply trajectory update
    list session runs

Rules:
    - original.md is immutable
    - current.md may be updated
    - session writes are atomic or safely recoverable
    - interrupted runs must not corrupt the session
    - events.jsonl exists as empty append-only surface (Wave 2 semantics)
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SESSION_JSON = "session.json"
EVENTS_JSONL = "events.jsonl"
ORIGINAL_MD = "original.md"
CURRENT_MD = "current.md"
TRAJECTORY_MD = "trajectory.md"
RUNS_DIR = "runs"

# Default maximum cards shown to user (preserved invariant)
MAX_CARDS = 3


def create_session(input_path: str, session_dir: str) -> dict:
    """Create a new session from an input file.

    Args:
        input_path: Path to the original document.
        session_dir: Directory for the session.

    Returns:
        Session metadata dict.

    Rules:
        - original.md is written once and never modified.
        - current.md is initialized as a copy of the original.
        - session.json records creation time and source.
        - events.jsonl is created empty.
        - runs/ directory is created.
    """
    session_path = Path(session_dir)
    session_path.mkdir(parents=True, exist_ok=True)

    # Read the original document
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    original_text = input_file.read_text(encoding="utf-8")

    # Write immutable original.md
    _atomic_write(session_path / ORIGINAL_MD, original_text)

    # Write current.md (initially same as original)
    _atomic_write(session_path / CURRENT_MD, original_text)

    # Create runs directory
    (session_path / RUNS_DIR).mkdir(parents=True, exist_ok=True)

    # Write trajectory template (R3: §5.4 6-section template)
    if not (session_path / TRAJECTORY_MD).exists():
        from .trajectory import TRAJECTORY_TEMPLATE
        _atomic_write(
            session_path / TRAJECTORY_MD,
            TRAJECTORY_TEMPLATE.format(
                task="(not set yet)",
                explored="(none yet)",
                selected="(none yet)",
                rejected="(none yet)",
                changes="(none yet)",
                questions="(none yet)",
            ),
        )

    # Initialize empty events.jsonl (Wave 2 fills this)
    (session_path / EVENTS_JSONL).write_text("", encoding="utf-8")

    # Write session metadata
    session_id = uuid.uuid4().hex[:12]
    metadata = {
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(input_file.resolve()),
        "document_hash": _hash_text(original_text),
        "runs": [],
    }
    _atomic_write(
        session_path / SESSION_JSON,
        json.dumps(metadata, indent=2, ensure_ascii=False),
    )

    return metadata


def get_session_metadata(session_dir: str) -> dict:
    """Read session metadata."""
    session_path = Path(session_dir)
    meta_path = session_path / SESSION_JSON
    if not meta_path.exists():
        raise FileNotFoundError(f"No session found at {session_dir}")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def read_current(session_dir: str) -> str:
    """Read the current document from a session."""
    current_path = Path(session_dir) / CURRENT_MD
    if not current_path.exists():
        raise FileNotFoundError(
            f"current.md not found in {session_dir} — is this a valid session?"
        )
    return current_path.read_text(encoding="utf-8")


def read_original(session_dir: str) -> str:
    """Read the immutable original document."""
    original_path = Path(session_dir) / ORIGINAL_MD
    if not original_path.exists():
        raise FileNotFoundError(
            f"original.md not found in {session_dir}"
        )
    return original_path.read_text(encoding="utf-8")


def update_current(session_dir: str, new_text: str) -> None:
    """Update the current document (user or harness edit).

    current.md is atomically replaced.
    """
    current_path = Path(session_dir) / CURRENT_MD
    _atomic_write(current_path, new_text)


def read_trajectory(session_dir: str) -> str:
    """Read the accumulated trajectory from a session."""
    traj_path = Path(session_dir) / TRAJECTORY_MD
    if not traj_path.exists():
        return ""
    return traj_path.read_text(encoding="utf-8")


def apply_trajectory_update(session_dir: str, update_text: str) -> None:
    """Parse a run-block update and merge into the trajectory template sections.

    R3 semantics:
        - Исследовано → Directions already explored
        - Показано → Directions already explored (NOT selected — invariant: proposed ≠ confirmed)
        - Вопросы → Open questions

    Existing trajectory.md files with legacy raw append format are NOT migrated
    (new logic applies to new entries, as per R3 requirement).
    """
    from .trajectory import read_trajectory_file, write_trajectory_file

    traj_path = Path(session_dir) / TRAJECTORY_MD

    # Parse the update block to extract sections
    explored_items = _parse_run_section(update_text, "Исследовано:")
    shown_items = _parse_run_section(update_text, "Показано пользователю:")
    question_items = _parse_run_section(update_text, "Новые открытые вопросы:")

    # Read current trajectory
    traj = read_trajectory_file(str(traj_path))

    # Merge into template sections
    # Explored + shown both go to "Directions already explored"
    # Shown items are prefixed to indicate they were proposed (not confirmed selected)
    for item in explored_items:
        if item not in traj.explored:
            traj.explored.append(item)
    for item in shown_items:
        prefixed = f"[показано] {item}"
        if prefixed not in traj.explored:
            traj.explored.append(prefixed)

    # Questions go to "Open questions"
    for item in question_items:
        if item not in traj.open_questions:
            traj.open_questions.append(item)

    # "Directions selected and developed" stays untouched (invariant)

    # Write back
    write_trajectory_file(traj, str(traj_path))


def list_session_runs(session_dir: str) -> list[str]:
    """List run IDs in a session."""
    runs_path = Path(session_dir) / RUNS_DIR
    if not runs_path.exists():
        return []
    return sorted(
        d.name for d in runs_path.iterdir() if d.is_dir()
    )


def register_run(session_dir: str, run_id: str, rel_path: str = "") -> None:
    """Register a run in the session metadata.

    Args:
        session_dir: Session directory.
        run_id: Run identifier.
        rel_path: Relative path from session_dir to the trace (e.g. 'runs/<run_id>').
                  Empty string means path is not under session_dir (legacy).
    """
    meta_path = Path(session_dir) / SESSION_JSON
    if not meta_path.exists():
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    # Build entry (dict with run_id + path, for R1 semantics)
    entry: dict = {"run_id": run_id}
    if rel_path:
        entry["path"] = rel_path

    # Check if already registered (backward-compat: handle both string and dict formats)
    existing_ids = set()
    for r in meta.get("runs", []):
        if isinstance(r, dict):
            existing_ids.add(r.get("run_id", ""))
        else:
            existing_ids.add(r)

    if run_id not in existing_ids:
        meta.setdefault("runs", []).append(entry)

    _atomic_write(
        meta_path,
        json.dumps(meta, indent=2, ensure_ascii=False),
    )


def is_valid_session(session_dir: str) -> bool:
    """Check if a directory contains a valid session."""
    session_path = Path(session_dir)
    return (
        (session_path / ORIGINAL_MD).exists() and
        (session_path / SESSION_JSON).exists()
    )


# --- helpers ---

def _parse_run_section(update_text: str, section_header: str) -> list[str]:
    """Parse a run-block section (e.g. 'Исследовано:') and return bullet items.

    Args:
        update_text: The full run-block markdown.
        section_header: Section header to look for (e.g. 'Исследовано:').

    Returns:
        List of item strings (without '- ' prefix).
    """
    items: list[str] = []
    lines = update_text.split("\n")
    in_section = False
    for line in lines:
        if line.strip().startswith(section_header):
            in_section = True
            continue
        if in_section:
            stripped = line.strip()
            if stripped.startswith("- "):
                items.append(stripped[2:])
            elif stripped == "":
                continue
            elif stripped.startswith("##") or stripped.endswith(":"):
                # Next section or run header
                in_section = False
    return items


def _atomic_write(path: Path, content: str) -> None:
    """Write to a temp file then rename — atomic on same filesystem."""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def resolve_run_path(session_dir: str, run_id: str) -> str | None:
    """Resolve the trace directory for a run from session.json.

    Checks session.json entries (dict with 'path' field, or legacy string),
    then falls back to the flat beerlight-runs/<run_id>/ directory for
    legacy sessions whose traces predate the R1 session/runs/ layout.

    Args:
        session_dir: Session directory.
        run_id: Run identifier to look up.

    Returns:
        Absolute or relative path to the trace directory, or None if not found.
    """
    session_path = Path(session_dir)
    meta_path = session_path / SESSION_JSON
    if not meta_path.exists():
        return _legacy_trace_fallback(run_id)

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return _legacy_trace_fallback(run_id)

    runs = meta.get("runs", [])

    for r in runs:
        if isinstance(r, dict):
            if r.get("run_id") == run_id:
                path = r.get("path", "")
                if path:
                    candidate = session_path / path
                    if candidate.exists():
                        return str(candidate)
                    # Path recorded but directory missing — try legacy fallback
                    return _legacy_trace_fallback(run_id)
        elif isinstance(r, str) and r == run_id:
            # Legacy string-only run entry: try new layout first
            candidate = session_path / "runs" / run_id
            if candidate.exists():
                return str(candidate)
            return _legacy_trace_fallback(run_id)

    # Run ID not found in session.json — try legacy fallback
    return _legacy_trace_fallback(run_id)


def _legacy_trace_fallback(run_id: str) -> str | None:
    """Fall back to the flat beerlight-runs/<run_id>/ directory (pre-R1)."""
    legacy = Path("beerlight-runs") / run_id
    if legacy.exists():
        return str(legacy)
    return None


def _hash_text(text: str) -> str:
    """Stable SHA-256 hash of text content."""
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
