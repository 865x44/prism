"""Tests for Beerlight Runtime — trajectory as a first-class artifact.

Deterministic tests only. No LLM calls.
"""
from pathlib import Path

from prism.runtime.trajectory import (
    Trajectory,
    TrajectoryEntry,
    read_trajectory_file,
    write_trajectory_file,
    export_trajectory,
    TRAJECTORY_TEMPLATE,
)


def test_trajectory_to_markdown_includes_all_sections():
    """Trajectory.to_markdown() produces valid template output."""
    traj = Trajectory(
        task="найти развороты",
        explored=["Direction A", "Direction B"],
        selected=["Chosen X"],
        rejected=["Rejected Y"],
        changes=["Rewrote intro"],
        open_questions=["What about Z?"],
    )
    md = traj.to_markdown()

    assert "## Original task" in md
    assert "найти развороты" in md
    assert "Direction A" in md
    assert "Chosen X" in md
    assert "Rejected Y" in md
    assert "Rewrote intro" in md
    assert "What about Z?" in md


def test_trajectory_empty_sections_show_placeholder():
    """Empty sections display '(none yet)' placeholder."""
    traj = Trajectory()
    md = traj.to_markdown()

    assert "(none yet)" in md


def test_trajectory_roundtrip_markdown(tmp_path):
    """Trajectory → markdown → parse → equals original."""
    traj = Trajectory(
        task="Test task",
        explored=["Alpha", "Beta"],
        selected=["Gamma"],
        rejected=["Delta"],
        changes=["Edit 1"],
        open_questions=["Q1", "Q2"],
    )
    path = tmp_path / "trajectory.md"
    write_trajectory_file(traj, str(path))

    restored = read_trajectory_file(str(path))
    assert restored.task == "Test task"
    assert "Alpha" in restored.explored
    assert "Beta" in restored.explored
    assert "Gamma" in restored.selected
    assert "Delta" in restored.rejected
    assert "Edit 1" in restored.changes
    assert restored.open_questions == ["Q1", "Q2"]


def test_trajectory_add_explored_deduplicates():
    """add_explored deduplicates entries."""
    traj = Trajectory()
    traj.add_explored(["A", "B"])
    traj.add_explored(["A", "C"])
    assert traj.explored == ["A", "B", "C"]


def test_trajectory_proposed_vs_confirmed():
    """Proposed update is separate from confirmed trajectory."""
    traj = Trajectory(
        task="test",
        explored=["Already there"],
    )
    traj.proposed = TrajectoryEntry(
        run_id="run1",
        explored=["New direction"],
        shown=["Card 1"],
        open_questions=["Q?"],
    )

    # Before apply: proposed is separate
    assert traj.proposed is not None
    assert "New direction" not in traj.explored
    assert "Card 1" not in traj.selected
    assert "Q?" not in traj.open_questions

    # After apply: proposed is merged and cleared
    traj.apply_proposed()
    assert traj.proposed is None
    assert "New direction" in traj.explored
    assert "Card 1" in traj.selected
    assert "Q?" in traj.open_questions


def test_trajectory_apply_proposed_noop_when_none():
    """apply_proposed does nothing when there's no proposed update."""
    traj = Trajectory(task="test")
    traj.apply_proposed()  # Should not raise
    assert traj.proposed is None


def test_trajectory_to_dict_and_back():
    """Trajectory → dict → Trajectory.from_dict is round-trip safe."""
    traj = Trajectory(
        task="T",
        explored=["e1"],
        selected=["s1"],
        rejected=["r1"],
        changes=["c1"],
        open_questions=["q1"],
    )
    d = traj.to_dict()
    traj2 = Trajectory.from_dict(d)
    assert traj2.task == "T"
    assert traj2.explored == ["e1"]
    assert traj2.selected == ["s1"]
    assert traj2.rejected == ["r1"]
    assert traj2.changes == ["c1"]
    assert traj2.open_questions == ["q1"]


def test_export_trajectory_writes_file(tmp_path):
    """export_trajectory writes a standalone markdown file."""
    traj = Trajectory(task="Export test")
    out = tmp_path / "exported.md"
    export_trajectory(traj, str(out))
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Export test" in content


def test_trajectory_template_has_all_sections():
    """The TRAJECTORY_TEMPLATE constant has all required sections."""
    assert "## Original task" in TRAJECTORY_TEMPLATE
    assert "## Directions already explored" in TRAJECTORY_TEMPLATE
    assert "## Directions selected and developed" in TRAJECTORY_TEMPLATE
    assert "## Directions rejected or parked" in TRAJECTORY_TEMPLATE
    assert "## Changes made to the text" in TRAJECTORY_TEMPLATE
    assert "## Open questions" in TRAJECTORY_TEMPLATE


def test_trajectory_select_and_reject():
    """select_direction and reject_direction work as expected."""
    traj = Trajectory()
    traj.select_direction("Dir A")
    traj.select_direction("Dir A")  # dedup
    traj.reject_direction("Dir Z")

    assert traj.selected == ["Dir A"]
    assert traj.rejected == ["Dir Z"]


def test_trajectory_record_change_and_question():
    """record_change and add_question append."""
    traj = Trajectory()
    traj.record_change("Fixed paragraph 3")
    traj.add_question("Is paragraph 3 strong enough?")
    traj.add_question("Is paragraph 3 strong enough?")  # dedup

    assert traj.changes == ["Fixed paragraph 3"]
    assert traj.open_questions == ["Is paragraph 3 strong enough?"]
