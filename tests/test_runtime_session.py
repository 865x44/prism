"""Tests for Prism Runtime — session layer.

Deterministic tests only. No LLM calls.
"""
import json
from pathlib import Path

from prism.runtime.session import (
    create_session,
    read_current,
    read_original,
    update_current,
    read_trajectory,
    apply_trajectory_update,
    list_session_runs,
    register_run,
    is_valid_session,
    get_session_metadata,
    ORIGINAL_MD,
    CURRENT_MD,
    EVENTS_JSONL,
)


def test_create_session_writes_original_md_immutable(tmp_path):
    """original.md is written once and matches the input file exactly."""
    input_file = tmp_path / "draft.md"
    input_file.write_text("Original content.", encoding="utf-8")

    session_dir = tmp_path / "sess"
    meta = create_session(str(input_file), str(session_dir))

    original_path = session_dir / ORIGINAL_MD
    assert original_path.exists()
    assert original_path.read_text(encoding="utf-8") == "Original content."

    # Verify original is immutable — overwriting input shouldn't change original
    input_file.write_text("Changed content.", encoding="utf-8")
    assert original_path.read_text(encoding="utf-8") == "Original content."


def test_create_session_initializes_current_md(tmp_path):
    """current.md starts as a copy of the original."""
    input_file = tmp_path / "draft.md"
    input_file.write_text("Initial text.", encoding="utf-8")

    session_dir = tmp_path / "sess"
    create_session(str(input_file), str(session_dir))

    current_path = session_dir / CURRENT_MD
    assert current_path.read_text(encoding="utf-8") == "Initial text."


def test_create_session_creates_empty_events_jsonl(tmp_path):
    """events.jsonl exists but is empty (Wave 1 surface only)."""
    input_file = tmp_path / "draft.md"
    input_file.write_text("Text.", encoding="utf-8")

    session_dir = tmp_path / "sess"
    create_session(str(input_file), str(session_dir))

    events_path = session_dir / EVENTS_JSONL
    assert events_path.exists()
    assert events_path.read_text(encoding="utf-8") == ""


def test_update_current_replaces_file(tmp_path):
    """update_current atomically replaces current.md content."""
    input_file = tmp_path / "draft.md"
    input_file.write_text("Old text.", encoding="utf-8")

    session_dir = tmp_path / "sess"
    create_session(str(input_file), str(session_dir))

    update_current(str(session_dir), "New text after edit.")
    assert read_current(str(session_dir)) == "New text after edit."


def test_read_original_returns_immutable_copy(tmp_path):
    """read_original always returns the original content."""
    input_file = tmp_path / "draft.md"
    input_file.write_text("Original only.", encoding="utf-8")

    session_dir = tmp_path / "sess"
    create_session(str(input_file), str(session_dir))

    update_current(str(session_dir), "Modified.")
    assert read_original(str(session_dir)) == "Original only."


def test_trajectory_read_write_cycle(tmp_path):
    """Trajectory starts with template and updates merge into sections."""
    input_file = tmp_path / "draft.md"
    input_file.write_text("Text.", encoding="utf-8")

    session_dir = tmp_path / "sess"
    create_session(str(input_file), str(session_dir))

    # Initially has template (not empty)
    traj = read_trajectory(str(session_dir))
    assert "## Original task" in traj
    assert "(not set yet)" in traj
    assert "## Directions already explored" in traj
    assert "## Directions selected and developed" in traj
    assert "## Open questions" in traj

    # Apply updates — items go into template sections
    apply_trajectory_update(str(session_dir),
                            "## Run abc\nИсследовано:\n- X\nПоказано пользователю:\n- Y\nНовые открытые вопросы:\n- Q1")
    apply_trajectory_update(str(session_dir),
                            "## Run def\nИсследовано:\n- Z\n")

    traj = read_trajectory(str(session_dir))
    assert "- X" in traj
    assert "[показано] Y" in traj  # shown items go to already explored, not selected
    assert "- Z" in traj
    assert "- Q1" in traj
    # Invariant: selected-and-developed NOT auto-filled
    assert "## Directions selected and developed" in traj
    # After the section header, it should still be "(none yet)" since we don't auto-fill
    assert "(none yet)" in traj


def test_register_run_adds_to_session_metadata(tmp_path):
    """register_run records run IDs as dict entries in session.json (R1 format)."""
    input_file = tmp_path / "draft.md"
    input_file.write_text("Text.", encoding="utf-8")

    session_dir = tmp_path / "sess"
    create_session(str(input_file), str(session_dir))

    register_run(str(session_dir), "run001")
    register_run(str(session_dir), "run002")
    # Duplicate should be deduplicated
    register_run(str(session_dir), "run001")

    meta = get_session_metadata(str(session_dir))
    run_ids = [r.get("run_id") if isinstance(r, dict) else r for r in meta["runs"]]
    assert "run001" in run_ids
    assert "run002" in run_ids
    assert run_ids.count("run001") == 1


def test_list_session_runs(tmp_path):
    """list_session_runs returns directories in runs/."""
    input_file = tmp_path / "draft.md"
    input_file.write_text("Text.", encoding="utf-8")

    session_dir = tmp_path / "sess"
    create_session(str(input_file), str(session_dir))

    # Create run directories
    (session_dir / "runs" / "aaa").mkdir()
    (session_dir / "runs" / "bbb").mkdir()

    runs = list_session_runs(str(session_dir))
    assert len(runs) == 2
    assert "aaa" in runs
    assert "bbb" in runs


def test_is_valid_session(tmp_path):
    """is_valid_session checks for required files."""
    # Not a valid session
    d = tmp_path / "not_a_session"
    d.mkdir()
    assert not is_valid_session(str(d))

    # Create a real session
    input_file = tmp_path / "draft.md"
    input_file.write_text("Text.", encoding="utf-8")
    session_dir = tmp_path / "sess"
    create_session(str(input_file), str(session_dir))
    assert is_valid_session(str(session_dir))


def test_session_atomic_write(tmp_path):
    """Atomic write doesn't leave tmp files behind."""
    input_file = tmp_path / "draft.md"
    input_file.write_text("Text.", encoding="utf-8")

    session_dir = tmp_path / "sess"
    create_session(str(input_file), str(session_dir))

    # No .tmp files should remain
    tmp_files = list(session_dir.glob("*.tmp"))
    assert len(tmp_files) == 0, f"Found leftover tmp files: {tmp_files}"


# --- R3: Trajectory template init + run-block mapping ---

def test_session_create_writes_trajectory_template(tmp_path):
    """session create populates trajectory.md with the 6-section template."""
    input_file = tmp_path / "draft.md"
    input_file.write_text("Text.", encoding="utf-8")

    session_dir = tmp_path / "sess"
    create_session(str(input_file), str(session_dir))

    traj = read_trajectory(str(session_dir))
    assert "## Original task" in traj
    assert "## Directions already explored" in traj
    assert "## Directions selected and developed" in traj
    assert "## Directions rejected or parked" in traj
    assert "## Changes made to the text" in traj
    assert "## Open questions" in traj
    # All 6 sections present
    assert traj.count("## ") >= 6


def test_apply_trajectory_update_does_not_fill_selected(tmp_path):
    """After applying update, 'Directions selected and developed' stays (none yet)."""
    input_file = tmp_path / "draft.md"
    input_file.write_text("Text.", encoding="utf-8")

    session_dir = tmp_path / "sess"
    create_session(str(input_file), str(session_dir))

    # Apply update with explored and shown items
    apply_trajectory_update(
        str(session_dir),
        "## Run test\nИсследовано:\n- Direction X\nПоказано пользователю:\n- Card Y\nНовые открытые вопросы:\n- Q?",
    )

    traj = read_trajectory(str(session_dir))

    # Explored items go to "already explored"
    assert "Direction X" in traj

    # Shown items go to "already explored" with prefix, NOT to selected
    assert "[показано] Card Y" in traj

    # "Directions selected and developed" still shows (none yet)
    # Find the section
    assert "## Directions selected and developed" in traj
    selected_start = traj.find("## Directions selected and developed")
    chunk = traj[selected_start:]
    # After the header, it should contain (none yet)
    assert "(none yet)" in chunk[:200]

    # Open questions are populated
    assert "Q?" in traj


def test_apply_trajectory_update_invariant_proposed_not_confirmed(tmp_path):
    """Invariant: proposed directions never auto-fill 'selected and developed'."""
    input_file = tmp_path / "draft.md"
    input_file.write_text("Text.", encoding="utf-8")

    session_dir = tmp_path / "sess"
    create_session(str(input_file), str(session_dir))

    # Apply multiple updates
    apply_trajectory_update(str(session_dir),
                            "## Run r1\nПоказано пользователю:\n- Card A\n- Card B")
    apply_trajectory_update(str(session_dir),
                            "## Run r2\nПоказано пользователю:\n- Card C")

    traj = read_trajectory(str(session_dir))

    # Cards should NOT appear under "selected and developed"
    selected_section_start = traj.find("## Directions selected and developed")
    # Find next section header
    next_header = traj.find("## ", selected_section_start + 10)
    if next_header == -1:
        next_header = len(traj)
    selected_section = traj[selected_section_start:next_header]

    # "Card A" and "Card B" must NOT appear in the selected-and-developed section
    assert "Card A" not in selected_section, (
        "Card A leaked into 'selected and developed' section"
    )
    assert "Card B" not in selected_section

    # They should appear in "already explored" section with [показано] prefix
    explored_start = traj.find("## Directions already explored")
    explored_section = traj[explored_start:explored_start + 500]
    assert "[показано] Card A" in explored_section
    assert "[показано] Card B" in explored_section
    assert "[показано] Card C" in explored_section
