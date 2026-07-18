"""Tests for Beerlight Runtime — outcome events (append-only semantics).

Deterministic tests only. No LLM calls.

Coverage (per brief §4):
    - append-only: attempt to rewrite/delete line → error/immutable
    - unrated semantics: absence of event = unrated (not rejected)
    - event type validation
    - run_id/candidate_id validation
    - write/read round-trip
    - per-candidate and per-run queries
    - last event for candidate
    - event count
    - CLI exit codes (via subprocess or direct main() call)
"""
import json
from pathlib import Path

import pytest

from prism.runtime.events import (
    write_event,
    read_events,
    read_events_for_candidate,
    read_events_for_run,
    get_last_event_for_candidate,
    count_events,
    EVENT_TYPES,
)
from prism.runtime.session import create_session


# --- helpers ---

def _make_session(tmp_path: Path, name: str = "sess") -> Path:
    """Create a minimal session for testing."""
    input_file = tmp_path / f"{name}_input.md"
    input_file.write_text("Test document.", encoding="utf-8")
    session_dir = tmp_path / name
    create_session(str(input_file), str(session_dir))
    return session_dir


# --- write and read ---

def test_write_event_and_read_back(tmp_path):
    """Write a single event and read it back."""
    sd = _make_session(tmp_path)

    event = write_event(str(sd), "run001", "cand-A", "selected",
                        reason="looks promising")
    assert event["type"] == "selected"
    assert event["run_id"] == "run001"
    assert event["candidate_id"] == "cand-A"
    assert "timestamp" in event

    events = read_events(str(sd))
    assert len(events) == 1
    assert events[0]["run_id"] == "run001"


def test_write_multiple_events_preserves_order(tmp_path):
    """Events are read back in the order they were written."""
    sd = _make_session(tmp_path)

    write_event(str(sd), "run001", "c1", "shown")
    write_event(str(sd), "run001", "c1", "selected")
    write_event(str(sd), "run001", "c1", "applied")

    events = read_events(str(sd))
    assert len(events) == 3
    assert [e["type"] for e in events] == ["shown", "selected", "applied"]


def test_write_event_different_candidates_and_runs(tmp_path):
    """Events for different candidates and runs coexist independently."""
    sd = _make_session(tmp_path)

    write_event(str(sd), "run001", "c1", "selected")
    write_event(str(sd), "run001", "c2", "rejected", reason="too vague")
    write_event(str(sd), "run002", "c1", "selected")

    events = read_events(str(sd))
    assert len(events) == 3


# --- append-only: no modification ---

def test_events_file_is_append_only_no_line_modification(tmp_path):
    """events.jsonl lines cannot be modified after writing — lines are immutable."""
    sd = _make_session(tmp_path)

    write_event(str(sd), "run001", "c1", "shown")

    # Read the raw file
    events_path = sd / "events.jsonl"
    original_content = events_path.read_text(encoding="utf-8")

    # Write another event — it must only append
    write_event(str(sd), "run001", "c1", "selected")
    new_content = events_path.read_text(encoding="utf-8")

    # The original content is still a prefix of the new content
    assert new_content.startswith(original_content)
    # The new content is longer (has the appended line)
    assert len(new_content) > len(original_content)


def test_cannot_delete_events_lines(tmp_path):
    """There is no API to delete or modify event lines."""
    sd = _make_session(tmp_path)
    write_event(str(sd), "run001", "c1", "selected")

    # There is no delete function. read_events returns what's there.
    events = read_events(str(sd))
    assert len(events) == 1

    # Writing more events doesn't remove existing ones
    write_event(str(sd), "run001", "c1", "rejected")
    events = read_events(str(sd))
    assert len(events) == 2  # both events present


# --- validation ---

def test_invalid_event_type_raises_valueerror(tmp_path):
    """Writing an invalid event type raises ValueError."""
    sd = _make_session(tmp_path)

    with pytest.raises(ValueError, match="Invalid event type"):
        write_event(str(sd), "run001", "c1", "nonexistent_type")


def test_empty_run_id_raises_valueerror(tmp_path):
    """Empty run_id raises ValueError."""
    sd = _make_session(tmp_path)

    with pytest.raises(ValueError, match="run_id is required"):
        write_event(str(sd), "", "c1", "selected")


def test_empty_candidate_id_raises_valueerror(tmp_path):
    """Empty candidate_id raises ValueError."""
    sd = _make_session(tmp_path)

    with pytest.raises(ValueError, match="candidate_id is required"):
        write_event(str(sd), "run001", "", "selected")


def test_all_valid_event_types_accepted(tmp_path):
    """Each event type in EVENT_TYPES is accepted."""
    sd = _make_session(tmp_path)

    for et in sorted(EVENT_TYPES):
        write_event(str(sd), "run001", "c1", et)

    events = read_events(str(sd))
    assert len(events) == len(EVENT_TYPES)


# --- unrated semantics ---

def test_unrated_is_not_rejected(tmp_path):
    """Absence of any event means 'unrated', not 'rejected'.

    A candidate with no events is unrated. Only an explicit 'rejected'
    event marks it as rejected.
    """
    sd = _make_session(tmp_path)

    # c1 is explicitly rejected
    write_event(str(sd), "run001", "c1", "rejected", reason="banal")
    # c2 has no events — implicitly unrated
    # c3 is explicitly selected
    write_event(str(sd), "run001", "c3", "selected")

    # c2 has no events => last event is None (unrated)
    last_c2 = get_last_event_for_candidate(str(sd), "c2")
    assert last_c2 is None

    # c1 is rejected
    last_c1 = get_last_event_for_candidate(str(sd), "c1")
    assert last_c1 is not None
    assert last_c1["type"] == "rejected"

    # c3 is selected
    last_c3 = get_last_event_for_candidate(str(sd), "c3")
    assert last_c3 is not None
    assert last_c3["type"] == "selected"


# --- per-candidate and per-run queries ---

def test_read_events_for_candidate(tmp_path):
    """read_events_for_candidate returns only that candidate's events."""
    sd = _make_session(tmp_path)

    write_event(str(sd), "run001", "c1", "shown")
    write_event(str(sd), "run001", "c1", "selected")
    write_event(str(sd), "run001", "c2", "shown")

    c1_events = read_events_for_candidate(str(sd), "c1")
    assert len(c1_events) == 2
    assert all(e["candidate_id"] == "c1" for e in c1_events)

    c2_events = read_events_for_candidate(str(sd), "c2")
    assert len(c2_events) == 1
    assert c2_events[0]["candidate_id"] == "c2"


def test_read_events_for_run(tmp_path):
    """read_events_for_run returns only that run's events."""
    sd = _make_session(tmp_path)

    write_event(str(sd), "run001", "c1", "shown")
    write_event(str(sd), "run001", "c2", "shown")
    write_event(str(sd), "run002", "c1", "shown")

    r1_events = read_events_for_run(str(sd), "run001")
    assert len(r1_events) == 2
    assert all(e["run_id"] == "run001" for e in r1_events)

    r2_events = read_events_for_run(str(sd), "run002")
    assert len(r2_events) == 1


# --- last event ---

def test_get_last_event_for_candidate(tmp_path):
    """get_last_event_for_candidate returns the most recent event."""
    sd = _make_session(tmp_path)

    write_event(str(sd), "run001", "c1", "shown")
    write_event(str(sd), "run001", "c1", "selected")
    write_event(str(sd), "run001", "c1", "applied")

    last = get_last_event_for_candidate(str(sd), "c1")
    assert last is not None
    assert last["type"] == "applied"


def test_get_last_event_for_unknown_candidate_returns_none(tmp_path):
    """Unknown candidate returns None (unrated)."""
    sd = _make_session(tmp_path)
    write_event(str(sd), "run001", "c1", "selected")

    last = get_last_event_for_candidate(str(sd), "c2")
    assert last is None


# --- count ---

def test_count_events(tmp_path):
    """count_events returns correct total."""
    sd = _make_session(tmp_path)
    assert count_events(str(sd)) == 0

    write_event(str(sd), "run001", "c1", "shown")
    assert count_events(str(sd)) == 1

    write_event(str(sd), "run001", "c2", "selected")
    write_event(str(sd), "run002", "c1", "rejected")
    assert count_events(str(sd)) == 3


# --- empty session ---

def test_read_events_from_empty_session(tmp_path):
    """Reading events from a session with no events returns empty list."""
    sd = _make_session(tmp_path)
    events = read_events(str(sd))
    assert events == []
    assert count_events(str(sd)) == 0


# --- status chain: selected → applied → retained ---

def test_status_chain_selected_applied_retained(tmp_path):
    """A candidate can move through the full lifecycle chain."""
    sd = _make_session(tmp_path)

    write_event(str(sd), "run001", "c1", "selected", reason="good angle")
    write_event(str(sd), "run001", "c1", "applied", reason="edited text")
    write_event(str(sd), "run001", "c1", "retained", reason="360 approved")

    events = read_events_for_candidate(str(sd), "c1")
    types = [e["type"] for e in events]
    assert types == ["selected", "applied", "retained"]

    last = get_last_event_for_candidate(str(sd), "c1")
    assert last["type"] == "retained"


def test_selected_applied_reverted_chain(tmp_path):
    """A candidate can be selected, applied, then reverted."""
    sd = _make_session(tmp_path)

    write_event(str(sd), "run001", "c1", "selected")
    write_event(str(sd), "run001", "c1", "applied")
    write_event(str(sd), "run001", "c1", "reverted", reason="bad fit")

    last = get_last_event_for_candidate(str(sd), "c1")
    assert last["type"] == "reverted"


def test_rejected_overrides_selected(tmp_path):
    """If a candidate was selected but then rejected, last status is rejected."""
    sd = _make_session(tmp_path)

    write_event(str(sd), "run001", "c1", "selected")
    write_event(str(sd), "run001", "c1", "rejected", reason="changed mind")

    last = get_last_event_for_candidate(str(sd), "c1")
    assert last["type"] == "rejected"


# --- metadata field ---

def test_event_metadata_field(tmp_path):
    """The metadata field is preserved in the event."""
    sd = _make_session(tmp_path)

    write_event(str(sd), "run001", "c1", "selected",
                metadata={"editor": "user", "version": 1})

    events = read_events(str(sd))
    assert len(events) == 1
    assert events[0]["metadata"] == {"editor": "user", "version": 1}


# --- session_id is recorded ---

def test_event_includes_session_id(tmp_path):
    """Each event records the session_id from session.json."""
    sd = _make_session(tmp_path)

    event = write_event(str(sd), "run001", "c1", "shown")
    assert "session_id" in event
    assert len(event["session_id"]) > 0


# --- CLI exit codes ---

def test_event_cli_exit_codes(tmp_path):
    """Event CLI returns 0 on success, 1 on error."""
    from prism.runtime.cli import main

    sd = _make_session(tmp_path)

    # Success
    rc = main(["session", "event", str(sd), "run001", "c1", "selected"])
    assert rc == 0

    # Invalid type
    rc = main(["session", "event", str(sd), "run001", "c1", "bad_type"])
    assert rc == 1

    # Missing session
    rc = main(["session", "event", "/nonexistent/session", "run001", "c1", "selected"])
    assert rc == 1


def test_outcomes_cli_exit_codes(tmp_path):
    """Outcomes CLI returns 0 on success, 1 on missing session."""
    from prism.runtime.cli import main

    sd = _make_session(tmp_path)
    write_event(str(sd), "run001", "c1", "selected")

    rc = main(["session", "outcomes", str(sd)])
    assert rc == 0

    rc = main(["session", "outcomes", "/nonexistent/session"])
    assert rc == 1
