"""Tests for Prism Runtime — outcomes derived from events.

Deterministic tests only. No LLM calls.

Coverage (per brief §4):
    - selected/applied/retained separation (distinct states)
    - unrated semantics via derived outcomes
    - session/run/candidate linking validity
    - handoff excludes raw traces by default
    - handoff preview + path normalization
    - calibration filtering on fixtures (judge.json with fake data)
    - outcomes CLI exit codes
    - outcomes table formatting
    - outcomes JSON export
"""
import json
from pathlib import Path

import pytest

from prism.runtime.events import write_event
from prism.runtime.outcomes import (
    derive_outcomes,
    format_outcomes_table,
    build_outcomes_json,
    SessionOutcomes,
)
from prism.runtime.session import create_session
from prism.runtime.inspect import calibration_report


# --- helpers ---

def _make_session(tmp_path: Path, name: str = "sess") -> Path:
    """Create a minimal session for testing."""
    input_file = tmp_path / f"{name}_input.md"
    input_file.write_text("Test document.", encoding="utf-8")
    session_dir = tmp_path / name
    create_session(str(input_file), str(session_dir))
    return session_dir


def _make_fake_run(session_dir: Path, run_id: str, candidate_ids: list[str]) -> None:
    """Create a fake run directory with candidates.json so outcomes
    can discover unrated candidates."""
    runs_dir = session_dir / "runs" / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)

    candidates = []
    for i, cid in enumerate(candidate_ids):
        candidates.append({
            "id": cid,
            "title": f"Card {cid}",
            "core_shift": f"shift {i}",
            "source_basis": [f"line {i}"],
            "practical_return": f"return {i}",
            "boundary": f"boundary {i}",
        })

    (runs_dir / "candidates.json").write_text(
        json.dumps(candidates, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Also create a minimal judge.json for calibration tests
    judgments = []
    for i, cid in enumerate(candidate_ids):
        action = "keep" if i < 2 else "drop"
        novelty = "real" if i < 2 else "false"
        fidelity = "grounded" if i < 2 else "distorted"
        judgments.append({
            "candidate_id": cid,
            "action": action,
            "novelty": novelty,
            "fidelity": fidelity,
            "failure_tags": [],
            "reason": f"judge reason for {cid}",
        })

    (runs_dir / "judge.json").write_text(
        json.dumps({
            "overall_decision": "useful_output",
            "cards": [{"title": f"Card {candidate_ids[0]}"}],
            "judgments": judgments,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Also a minimal output.md for inspect's shown-card parsing
    (runs_dir / "output.md").write_text(
        f"## Card {candidate_ids[0]}\n\nRun: {run_id}\nTrace: {runs_dir}\n",
        encoding="utf-8",
    )


# --- selected/applied/retained distinction ---

def test_selected_applied_retained_are_distinct(tmp_path):
    """selected, applied, and retained are distinct statuses in outcomes."""
    sd = _make_session(tmp_path)

    write_event(str(sd), "run001", "c1", "selected")
    write_event(str(sd), "run001", "c1", "applied")
    write_event(str(sd), "run001", "c1", "retained")

    write_event(str(sd), "run001", "c2", "selected")
    # c2 selected but NOT applied

    outcomes = derive_outcomes(str(sd))

    # c1: last status is retained (through chain)
    c1_outcomes = [o for o in outcomes.rated if o.candidate_id == "c1"]
    assert len(c1_outcomes) == 1
    assert c1_outcomes[0].status == "retained"
    assert c1_outcomes[0].status_chain == ["selected", "applied", "retained"]

    # c2: last status is selected (not applied)
    c2_outcomes = [o for o in outcomes.rated if o.candidate_id == "c2"]
    assert len(c2_outcomes) == 1
    assert c2_outcomes[0].status == "selected"
    assert c2_outcomes[0].status_chain == ["selected"]

    # Counts
    # c1: status=retained → counted under retained
    # c2: status=selected → counted under selected
    assert outcomes.selected_count == 1  # c2 is still selected
    assert outcomes.applied_count == 0   # c1 moved from applied to retained
    assert outcomes.retained_count == 1  # c1
    assert outcomes.reverted_count == 0


def test_selected_applied_reverted_chain(tmp_path):
    """selected→applied→reverted: outcome shows reverted."""
    sd = _make_session(tmp_path)

    write_event(str(sd), "run001", "c1", "selected")
    write_event(str(sd), "run001", "c1", "applied")
    write_event(str(sd), "run001", "c1", "reverted", reason="bad fit")

    outcomes = derive_outcomes(str(sd))

    c1 = [o for o in outcomes.rated if o.candidate_id == "c1"][0]
    assert c1.status == "reverted"
    assert c1.status_chain == ["selected", "applied", "reverted"]
    assert outcomes.reverted_count == 1


def test_selected_applied_chain_unfinished(tmp_path):
    """selected→applied without retained/reverted means status=applied."""
    sd = _make_session(tmp_path)

    write_event(str(sd), "run001", "c1", "selected")
    write_event(str(sd), "run001", "c1", "applied")

    outcomes = derive_outcomes(str(sd))

    c1 = [o for o in outcomes.rated if o.candidate_id == "c1"][0]
    assert c1.status == "applied"
    assert outcomes.applied_count == 1


# --- unrated semantics in outcomes ---

def test_unrated_candidates_appear_in_outcomes(tmp_path):
    """Candidates that exist in runs but have no events appear as unrated."""
    sd = _make_session(tmp_path)

    # Create a fake run with 3 candidates
    _make_fake_run(sd, "run001", ["c1", "c2", "c3"])

    # Only mark c1 as selected
    write_event(str(sd), "run001", "c1", "selected")

    outcomes = derive_outcomes(str(sd))

    assert len(outcomes.rated) == 1  # c1
    assert len(outcomes.unrated) == 2  # c2, c3
    assert outcomes.total_candidates == 3

    unrated_ids = [o.candidate_id for o in outcomes.unrated]
    assert "c2" in unrated_ids
    assert "c3" in unrated_ids


def test_unrated_is_not_counted_as_rejected(tmp_path):
    """Unrated candidates are NOT counted as rejected."""
    sd = _make_session(tmp_path)

    _make_fake_run(sd, "run001", ["c1", "c2", "c3"])

    write_event(str(sd), "run001", "c1", "selected")
    write_event(str(sd), "run001", "c2", "rejected")
    # c3 has no events → unrated

    outcomes = derive_outcomes(str(sd))

    assert outcomes.selected_count == 1
    assert outcomes.rejected_count == 1
    assert outcomes.unrated  # c3
    # rejected_count should be 1, NOT 2 (unrated ≠ rejected)
    assert outcomes.rejected_count == 1


# --- multiple runs ---

def test_outcomes_across_multiple_runs(tmp_path):
    """Outcomes correctly separate candidates from different runs."""
    sd = _make_session(tmp_path)

    _make_fake_run(sd, "run001", ["c1", "c2"])
    _make_fake_run(sd, "run002", ["c3", "c4"])

    write_event(str(sd), "run001", "c1", "selected")
    write_event(str(sd), "run002", "c3", "rejected")

    outcomes = derive_outcomes(str(sd))

    # rated: c1 (selected), c3 (rejected)
    assert len(outcomes.rated) == 2

    # unrated: c2, c4
    assert len(outcomes.unrated) == 2

    # Verify run_id on outcomes
    c1 = [o for o in outcomes.rated if o.candidate_id == "c1"][0]
    assert c1.run_id == "run001"

    c3 = [o for o in outcomes.rated if o.candidate_id == "c3"][0]
    assert c3.run_id == "run002"


# --- format_outcomes_table ---

def test_format_outcomes_table_includes_all_sections(tmp_path):
    """The formatted table shows rated, unrated, and summary."""
    sd = _make_session(tmp_path)

    _make_fake_run(sd, "run001", ["c1", "c2"])
    write_event(str(sd), "run001", "c1", "selected", reason="good")

    outcomes = derive_outcomes(str(sd))
    table = format_outcomes_table(outcomes)

    assert "RUN" in table
    assert "CANDIDATE" in table
    assert "STATUS" in table
    assert "selected" in table
    assert "c1" in table
    # c2 is unrated
    assert "c2" in table
    assert "unrated" in table
    assert "Total:" in table


def test_format_outcomes_table_shows_chain_summary(tmp_path):
    """Summary shows both status-based and event-based counts (R3 dual representation)."""
    sd = _make_session(tmp_path)

    _make_fake_run(sd, "run001", ["c1", "c2", "c3", "c4"])
    write_event(str(sd), "run001", "c1", "selected")
    write_event(str(sd), "run001", "c2", "selected")
    write_event(str(sd), "run001", "c2", "applied")
    write_event(str(sd), "run001", "c3", "rejected")

    outcomes = derive_outcomes(str(sd))
    table = format_outcomes_table(outcomes)

    # R3: dual representation — status counts and event counts
    assert "Status counts" in table
    assert "Event counts" in table

    # Status counts (last-event-wins): c1=selected, c2=applied, c3=rejected
    assert "selected=1" in table  # c1 is still selected
    assert "applied=1" in table   # c2 last status is applied
    assert "rejected=1" in table  # c3

    # Event counts (uncollapsed): c1 (selected), c2 (selected+applied), c3 (rejected)
    assert "Event counts" in table


# --- outcomes JSON export ---

def test_build_outcomes_json(tmp_path):
    """build_outcomes_json produces valid JSON for export (R3 field names)."""
    sd = _make_session(tmp_path)

    _make_fake_run(sd, "run001", ["c1", "c2"])
    write_event(str(sd), "run001", "c1", "selected")
    write_event(str(sd), "run001", "c1", "applied")

    outcomes = derive_outcomes(str(sd))
    data = build_outcomes_json(outcomes)

    # R3: renamed fields
    assert data["total_candidates"] == 2
    assert data["rated_candidates"] == 1
    assert data["unrated_candidates"] == 1
    assert data["session_id"] != ""  # R3: session_id populated from session.json
    assert data["selected_count"] == 0  # c1 was selected then applied → last=applied
    assert data["applied_count"] == 1
    assert len(data["rated"]) == 1
    assert len(data["unrated"]) == 1
    assert data["selection_to_application_ratio"] == "0/1"


# --- handoff export ---

def test_handoff_cli_export(tmp_path):
    """Handoff CLI creates a bundle with expected files."""
    from prism.runtime.cli import main

    sd = _make_session(tmp_path)
    _make_fake_run(sd, "run001", ["c1"])
    write_event(str(sd), "run001", "c1", "selected")

    output_dir = tmp_path / "handoff_bundle"

    # Non-interactive with --yes
    rc = main([
        "handoff", str(sd),
        "--output", str(output_dir),
        "--yes",
    ])
    assert rc == 0

    # Verify bundle contents
    assert (output_dir / "current.md").exists()
    assert (output_dir / "trajectory.md").exists()
    assert (output_dir / "session.json").exists()
    assert (output_dir / "outcomes.json").exists()
    assert (output_dir / "handoff.json").exists()

    # R2 repair: raw traces NOT included by default (traces/ not runs/)
    assert not (output_dir / "traces").exists()
    assert not (output_dir / "runs").exists()


def test_handoff_excludes_raw_traces_by_default(tmp_path):
    """By default, handoff export does NOT include raw traces."""
    from prism.runtime.cli import main

    sd = _make_session(tmp_path)
    _make_fake_run(sd, "run001", ["c1"])

    output_dir = tmp_path / "bundle_no_traces"

    rc = main([
        "handoff", str(sd),
        "--output", str(output_dir),
        "--yes",
    ])
    assert rc == 0

    # R2 repair: no traces/ directory
    assert not (output_dir / "traces").exists()
    assert not any(output_dir.rglob("raw-*.txt"))


def test_handoff_include_traces_opt_in(tmp_path):
    """--include-traces flag adds raw traces to the bundle (R2: traces/ dir)."""
    from prism.runtime.cli import main

    sd = _make_session(tmp_path)
    _make_fake_run(sd, "run001", ["c1"])

    output_dir = tmp_path / "bundle_with_traces"

    rc = main([
        "handoff", str(sd),
        "--output", str(output_dir),
        "--yes",
        "--include-traces",
    ])
    assert rc == 0

    # R2 repair: traces go to traces/ not runs/
    assert (output_dir / "traces").exists()
    # Verify there is content in traces/
    traces_contents = list((output_dir / "traces").rglob("*"))
    # At minimum we should have the run directory with trace files
    assert len(traces_contents) > 0


def test_handoff_normalizes_absolute_paths_to_relative(tmp_path):
    """Handoff bundle uses relative paths, not absolute."""
    from prism.runtime.cli import main

    sd = _make_session(tmp_path)
    _make_fake_run(sd, "run001", ["c1"])

    # Read session.json which has absolute path for source_file
    session_json = json.loads((sd / "session.json").read_text(encoding="utf-8"))

    output_dir = tmp_path / "bundle_rel"
    rc = main([
        "handoff", str(sd),
        "--output", str(output_dir),
        "--yes",
    ])
    assert rc == 0

    # Verify handoff.json exists and has file list
    handoff_meta = json.loads(
        (output_dir / "handoff.json").read_text(encoding="utf-8")
    )
    assert "files" in handoff_meta
    # All file paths should be relative (no leading /)
    for f in handoff_meta["files"]:
        assert not f.startswith("/"), f"Path not relative: {f}"


def test_handoff_preview_before_write(tmp_path, monkeypatch, capsys):
    """Handoff prints a preview before writing the bundle."""
    from prism.runtime.cli import main

    sd = _make_session(tmp_path)
    output_dir = tmp_path / "bundle_preview"

    # Mock input() to simulate "n" (cancel)
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")

    rc = main([
        "handoff", str(sd),
        "--output", str(output_dir),
    ])
    assert rc == 0  # Cancelled, not errored

    captured = capsys.readouterr()
    assert "Handoff bundle preview:" in captured.out
    assert "Export cancelled" in captured.out


def test_handoff_invalid_session_returns_error(tmp_path):
    """Handoff with invalid session returns error code."""
    from prism.runtime.cli import main

    output_dir = tmp_path / "bundle_err"
    rc = main([
        "handoff", str(tmp_path / "not_a_session"),
        "--output", str(output_dir),
        "--yes",
    ])
    assert rc == 1


# --- calibration filtering ---

def test_calibration_finds_strong_dropped(tmp_path):
    """calibration_report finds candidates dropped despite novelty=real+fidelity=grounded."""
    sd = _make_session(tmp_path)

    # Create a run with judge data that includes a "strong dropped" candidate
    runs_dir = sd / "runs" / "run001"
    runs_dir.mkdir(parents=True, exist_ok=True)

    judge_data = {
        "overall_decision": "useful_output",
        "cards": [
            {"title": "Card c1", "shift": "s1", "basis": "b1",
             "action": "a1", "boundary": "b1"},
        ],
        "judgments": [
            {
                "candidate_id": "c1",
                "action": "keep",
                "novelty": "real",
                "fidelity": "grounded",
                "failure_tags": [],
                "reason": "good angle",
            },
            {
                "candidate_id": "c2",
                "action": "drop",       # dropped!
                "novelty": "real",      # but genuinely novel
                "fidelity": "grounded",  # and well-grounded
                "failure_tags": [],
                "reason": "too abstract despite being real",
            },
            {
                "candidate_id": "c3",
                "action": "drop",
                "novelty": "false",     # legitimately dropped
                "fidelity": "distorted",
                "failure_tags": ["banal"],
                "reason": "nothing new",
            },
        ],
    }
    (runs_dir / "judge.json").write_text(
        json.dumps(judge_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report = calibration_report(str(runs_dir))

    assert "Strong Dropped" in report
    # c2 should be flagged (drop + real + grounded)
    assert "c2" in report
    assert "too abstract" in report
    # c3 should NOT be flagged (drop + false + distorted is normal)
    # c1 should NOT be flagged (keep)


def test_calibration_no_strong_dropped(tmp_path):
    """When no strong-dropped candidates exist, calibration reports honestly."""
    runs_dir = tmp_path / "clean_run"
    runs_dir.mkdir(parents=True, exist_ok=True)

    judge_data = {
        "overall_decision": "useful_output",
        "cards": [],
        "judgments": [
            {
                "candidate_id": "c1",
                "action": "keep",
                "novelty": "real",
                "fidelity": "grounded",
                "failure_tags": [],
                "reason": "good",
            },
            {
                "candidate_id": "c2",
                "action": "drop",
                "novelty": "false",
                "fidelity": "distorted",
                "failure_tags": ["banal"],
                "reason": "boring",
            },
        ],
    }
    (runs_dir / "judge.json").write_text(
        json.dumps(judge_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report = calibration_report(str(runs_dir))
    assert "No strong dropped candidates found" in report


def test_calibration_handles_missing_judge_json(tmp_path):
    """calibration_report handles missing judge.json gracefully."""
    runs_dir = tmp_path / "empty_run"
    runs_dir.mkdir(parents=True, exist_ok=True)

    report = calibration_report(str(runs_dir))
    assert "No judge.json found" in report


def test_calibration_handles_empty_judgments(tmp_path):
    """calibration_report handles judge with no judgments."""
    runs_dir = tmp_path / "empty_judgments"
    runs_dir.mkdir(parents=True, exist_ok=True)

    (runs_dir / "judge.json").write_text(
        json.dumps({"overall_decision": "no_useful_output", "cards": [], "judgments": []}),
        encoding="utf-8",
    )

    report = calibration_report(str(runs_dir))
    assert "No judgments found" in report


# --- rate only from explicit events ---

def test_outcomes_never_derive_from_model_text(tmp_path):
    """Outcomes are derived ONLY from events.jsonl, never by parsing model output.

    This is a key invariant: status is never inferred from model text,
    only from explicit event writes via CLI/API.
    """
    sd = _make_session(tmp_path)

    # Even if a run has judge data saying "keep", outcomes don't read it
    _make_fake_run(sd, "run001", ["c1", "c2"])

    # No events written
    outcomes = derive_outcomes(str(sd))
    assert len(outcomes.rated) == 0
    # All candidates are unrated
    assert len(outcomes.unrated) == 2

    # Now write explicit events
    write_event(str(sd), "run001", "c1", "selected")
    outcomes = derive_outcomes(str(sd))
    assert len(outcomes.rated) == 1
    assert outcomes.rated[0].status == "selected"


# --- edge cases ---

def test_empty_session_derives_empty_outcomes(tmp_path):
    """Session with no runs and no events yields empty outcomes."""
    sd = _make_session(tmp_path)
    outcomes = derive_outcomes(str(sd))
    assert outcomes.total_candidates == 0
    assert len(outcomes.rated) == 0
    assert len(outcomes.unrated) == 0


def test_session_with_runs_no_candidates_json(tmp_path):
    """Session with run dirs but no candidates.json is handled gracefully."""
    sd = _make_session(tmp_path)
    (sd / "runs" / "orphan").mkdir(parents=True, exist_ok=True)
    # No candidates.json in the orphan dir

    outcomes = derive_outcomes(str(sd))
    assert outcomes.total_candidates == 0
