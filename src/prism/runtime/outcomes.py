"""Session outcomes — derived representation from events.

Reads events.jsonl and computes per-candidate state without duplicating
any state outside the append-only event log. Outcomes are always derived
from the events — there is no separate outcome store.

Per-candidate semantics (brief §3.2):
    - Last event type determines current status.
    - Chain: selected → applied → retained / reverted.
    - Distinction: selected ≠ applied ≠ retained.
    - Candidates with events = rated; without events = unrated.
    - Unrated is NOT rejected — it means no action was taken.

CLI output:
    Table: run, candidate, title, last status, timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .events import read_events, EVENT_TYPES

# Status chain order (for sorting/distinction)
STATUS_ORDER = {
    "selected": 1,
    "applied": 2,
    "retained": 3,
    "reverted": 4,
    "rejected": 5,
    "saved": 6,
    "expanded": 7,
    "revised": 8,
    "shown": 9,
    "unrated": 10,
}


@dataclass
class CandidateOutcome:
    """Derived outcome for a single candidate from events."""
    candidate_id: str
    run_id: str = ""
    title: str = ""
    status: str = "unrated"
    status_chain: list[str] = field(default_factory=list)
    last_updated: str = ""


@dataclass
class SessionOutcomes:
    """All outcomes for a session, derived from events.

    Per-candidate status: last-event-wins (current state).
    Per-type event counts: uncollapsed — counts every candidate that ever had
        an event of that type (regardless of later events).

    R3 repair: both representations are tracked and displayed separately.
    """
    session_id: str = ""
    # Status-based counts (last-event-wins — current state per candidate)
    total_candidates: int = 0
    rated: list[CandidateOutcome] = field(default_factory=list)
    unrated: list[CandidateOutcome] = field(default_factory=list)
    selected_count: int = 0
    applied_count: int = 0
    retained_count: int = 0
    reverted_count: int = 0
    rejected_count: int = 0
    # Event-based counts (not collapsed — every event type that ever occurred)
    event_selected_count: int = 0
    event_applied_count: int = 0
    event_retained_count: int = 0
    event_reverted_count: int = 0
    event_rejected_count: int = 0
    # R3 repair: rated and unrated counts with clear field names
    rated_candidates: int = 0
    unrated_candidates: int = 0
    # Metrics
    selection_to_application_ratio: str = "0/0"


def derive_outcomes(
    session_dir: str,
    *,
    candidate_titles: dict[str, str] | None = None,
) -> SessionOutcomes:
    """Derive all outcomes from events.jsonl.

    Args:
        session_dir: Path to the session directory.
        candidate_titles: Optional mapping of candidate_id → title for display.
                          If not provided, titles are resolved from candidates.json
                          in run trace directories.

    Returns:
        SessionOutcomes with per-candidate status derived from event history
        and R3 dual-count (current status + event counts).
    """
    events = read_events(session_dir)

    # R3 repair: auto-resolve titles from candidates.json in run traces
    if candidate_titles is None:
        candidate_titles = _resolve_candidate_titles(session_dir, events)

    # Read session_id from session.json
    try:
        from .session import get_session_metadata
        session_meta = get_session_metadata(session_dir)
        session_id = session_meta.get("session_id", "")
    except Exception:
        session_id = ""

    # Group events by (run_id, candidate_id)
    # Since events are append-only and ordered, last event wins for status
    candidate_events: dict[tuple[str, str], list[dict]] = {}
    for ev in events:
        key = (ev.get("run_id", ""), ev.get("candidate_id", ""))
        candidate_events.setdefault(key, []).append(ev)

    # Build outcomes
    outcomes = SessionOutcomes(session_id=session_id)

    for (run_id, candidate_id), ev_list in sorted(candidate_events.items()):
        last_ev = ev_list[-1]
        status = last_ev.get("type", "unrated")
        title = candidate_titles.get(candidate_id, "")
        chain = [e.get("type", "?") for e in ev_list]

        outcome = CandidateOutcome(
            candidate_id=candidate_id,
            run_id=run_id,
            title=title,
            status=status,
            status_chain=chain,
            last_updated=last_ev.get("timestamp", ""),
        )
        outcomes.rated.append(outcome)

        # === Status-based counts (last-event-wins) ===
        if status == "selected":
            outcomes.selected_count += 1
        elif status == "applied":
            outcomes.applied_count += 1
        elif status == "retained":
            outcomes.retained_count += 1
        elif status == "reverted":
            outcomes.reverted_count += 1
        elif status == "rejected":
            outcomes.rejected_count += 1

        # === Event-based counts (uncollapsed — every event type ever seen) ===
        event_types_seen = {e.get("type") for e in ev_list}
        if "selected" in event_types_seen:
            outcomes.event_selected_count += 1
        if "applied" in event_types_seen:
            outcomes.event_applied_count += 1
        if "retained" in event_types_seen:
            outcomes.event_retained_count += 1
        if "reverted" in event_types_seen:
            outcomes.event_reverted_count += 1
        if "rejected" in event_types_seen:
            outcomes.event_rejected_count += 1

    # Discover unrated candidates from session runs
    unrated_ids = _discover_unrated(session_dir, candidate_events, candidate_titles)
    for cid, run_id, title in unrated_ids:
        outcomes.unrated.append(CandidateOutcome(
            candidate_id=cid,
            run_id=run_id,
            title=title,
            status="unrated",
        ))

    outcomes.total_candidates = len(outcomes.rated) + len(outcomes.unrated)
    outcomes.rated_candidates = len(outcomes.rated)
    outcomes.unrated_candidates = len(outcomes.unrated)

    # selection_to_application_ratio (based on status counts)
    if outcomes.selected_count > 0 or outcomes.applied_count > 0:
        outcomes.selection_to_application_ratio = (
            f"{outcomes.selected_count}/{outcomes.applied_count}"
        )

    return outcomes


def _resolve_candidate_titles(
    session_dir: str,
    events: list[dict],
) -> dict[str, str]:
    """Resolve candidate titles from candidates.json in run trace directories.

    For each run_id that appears in events, reads candidates.json
    and maps candidate_id → title.  Falls back to legacy beerlight-runs/
    if the session-local run directory is missing.

    R3 repair: ensures titles are populated in outcomes export.
    """
    import json as _json
    from pathlib import Path as _Path
    from .session import resolve_run_path as _resolve_run_path

    titles: dict[str, str] = {}
    run_ids_seen = {ev.get("run_id", "") for ev in events if ev.get("run_id")}

    for run_id in sorted(run_ids_seen):
        # Try resolving through session.json (R1 layout)
        run_path = _resolve_run_path(session_dir, run_id)

        if run_path:
            cand_file = _Path(run_path) / "candidates.json"
        else:
            # Fallback: try session-local runs/ directory
            cand_file = _Path(session_dir) / "runs" / run_id / "candidates.json"
            if not cand_file.exists():
                continue

        if not cand_file.exists():
            continue

        try:
            candidates = _json.loads(cand_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        for c in candidates:
            cid = c.get("id", "")
            ctitle = c.get("title", "")
            if cid and cid not in titles:
                titles[cid] = ctitle
            elif cid and not titles.get(cid) and ctitle:
                titles[cid] = ctitle

    return titles


def _discover_unrated(
    session_dir: str,
    rated_keys: dict[tuple[str, str], list],
    candidate_titles: dict[str, str],
) -> list[tuple[str, str, str]]:
    """Find candidates that exist in runs but have zero events (unrated).

    Returns list of (candidate_id, run_id, title).
    R1: reads from session/runs/ (new layout) and falls back to
    beerlight-runs/<run_id>/ (legacy flat layout).
    """
    import json as _json
    from pathlib import Path as _Path

    unrated: list[tuple[str, str, str]] = []
    runs_dir = _Path(session_dir) / "runs"

    # Collect run directories from both R1 layout and legacy
    run_dirs: list[tuple[str, _Path]] = []

    if runs_dir.exists():
        for run_dir in sorted(runs_dir.iterdir()):
            if run_dir.is_dir():
                run_dirs.append((run_dir.name, run_dir))

    # Also check legacy beerlight-runs/ for runs not found in session/runs/
    # (only if runs are recorded in session.json but not under session/runs/)
    legacy_runs = _Path("beerlight-runs")
    if legacy_runs.exists():
        # Check session.json for legacy runs without session-local traces
        try:
            from .session import get_session_metadata
            meta = get_session_metadata(session_dir)
            for r in meta.get("runs", []):
                rid = r.get("run_id") if isinstance(r, dict) else r
                if isinstance(rid, str) and rid:
                    # Skip if already found in session/runs/
                    if any(d[0] == rid for d in run_dirs):
                        continue
                    legacy_dir = legacy_runs / rid
                    if legacy_dir.exists() and legacy_dir.is_dir():
                        run_dirs.append((rid, legacy_dir))
        except Exception:
            pass

    for run_id, cand_dir in run_dirs:
        # Read candidates.json to find candidate IDs
        cand_file = cand_dir / "candidates.json"
        if not cand_file.exists():
            continue

        try:
            candidates = _json.loads(cand_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        for c in candidates:
            cid = c.get("id", "")
            if not cid:
                continue
            key = (run_id, cid)
            if key not in rated_keys:
                title = candidate_titles.get(cid, c.get("title", ""))
                unrated.append((cid, run_id, title))

    return unrated


def format_outcomes_table(outcomes: SessionOutcomes) -> str:
    """Format outcomes as a human-readable table.

    Brief §3.2: table with columns: run, candidate, title, last status, time.
    Distinguishes selected / applied / retained / reverted.
    """
    lines: list[str] = []
    lines.append(f"{'RUN':<14} {'CANDIDATE':<14} {'TITLE':<30} {'STATUS':<12} {'TIME'}")
    lines.append("-" * 90)

    # Sort: rated first by status chain, then unrated
    all_outcomes = sorted(
        outcomes.rated,
        key=lambda o: STATUS_ORDER.get(o.status, 99),
    ) + sorted(outcomes.unrated, key=lambda o: o.run_id)

    for oc in all_outcomes:
        run = oc.run_id[:12] if len(oc.run_id) > 12 else oc.run_id
        cid = oc.candidate_id[:12] if len(oc.candidate_id) > 12 else oc.candidate_id
        title = oc.title[:28] if len(oc.title) > 28 else oc.title
        status = oc.status
        time_str = oc.last_updated[:19] if oc.last_updated else "—"

        lines.append(
            f"{run:<14} {cid:<14} {title:<30} {status:<12} {time_str}"
        )

    # Summary section — R3 repair: dual representation
    lines.append("")
    lines.append(f"Total: {outcomes.total_candidates} candidates "
                 f"({outcomes.rated_candidates} rated, {outcomes.unrated_candidates} unrated)")
    lines.append("")

    # Status-based counts (last-event-wins — current state per candidate)
    lines.append("Status counts (by current state, last-event-wins):")
    lines.append(
        f"  selected={outcomes.selected_count}, "
        f"applied={outcomes.applied_count}, "
        f"retained={outcomes.retained_count}, "
        f"reverted={outcomes.reverted_count}, "
        f"rejected={outcomes.rejected_count}"
    )

    # Event-based counts (uncollapsed — every event type ever seen)
    lines.append("Event counts (by event history, uncollapsed):")
    lines.append(
        f"  selected={outcomes.event_selected_count}, "
        f"applied={outcomes.event_applied_count}, "
        f"retained={outcomes.event_retained_count}, "
        f"reverted={outcomes.event_reverted_count}, "
        f"rejected={outcomes.event_rejected_count}"
    )

    return "\n".join(lines)


def build_outcomes_json(outcomes: SessionOutcomes) -> dict:
    """Build JSON representation of outcomes for export (e.g. handoff).

    R3 repair: session_id from session.json, renamed total_candidates → rated_candidates
    + unrated_candidates, titles resolved from candidates.json.
    """
    return {
        "session_id": outcomes.session_id,
        "rated_candidates": outcomes.rated_candidates,
        "unrated_candidates": outcomes.unrated_candidates,
        "total_candidates": outcomes.total_candidates,
        "selected_count": outcomes.selected_count,
        "applied_count": outcomes.applied_count,
        "retained_count": outcomes.retained_count,
        "reverted_count": outcomes.reverted_count,
        "rejected_count": outcomes.rejected_count,
        "selection_to_application_ratio": outcomes.selection_to_application_ratio,
        "rated": [
            {
                "candidate_id": oc.candidate_id,
                "run_id": oc.run_id,
                "title": oc.title,
                "status": oc.status,
                "status_chain": oc.status_chain,
                "last_updated": oc.last_updated,
            }
            for oc in outcomes.rated
        ],
        "unrated": [
            {
                "candidate_id": oc.candidate_id,
                "run_id": oc.run_id,
                "title": oc.title,
            }
            for oc in outcomes.unrated
        ],
    }
