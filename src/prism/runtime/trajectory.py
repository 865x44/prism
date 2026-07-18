"""Trajectory as a first-class artifact for Prism Runtime.

Trajectory is both prompt compression and a durable decision-development record.

Template:
    # Prism trajectory
    ## Original task
    ...
    ## Directions already explored
    ...
    ## Directions selected and developed
    ...
    ## Directions rejected or parked
    ...
    ## Changes made to the text
    ...
    ## Open questions
    ...

Operations:
    read — read the trajectory file
    edit — update trajectory content
    export — export trajectory to a standalone file
    apply proposed update — merge proposed update into the trajectory
    extract for another harness — get machine-readable trajectory data

Rules:
    - Human-readable
    - Target 1–5k tokens
    - No ontology, no embeddings
    - No automatic invention of user decisions
    - Each run may create a proposed update
    - Proposed update is not confirmed history until explicitly applied or edited
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import TrajectoryEntry

TRAJECTORY_TEMPLATE = """# Prism trajectory

## Original task
{task}

## Directions already explored
{explored}

## Directions selected and developed
{selected}

## Directions rejected or parked
{rejected}

## Changes made to the text
{changes}

## Open questions
{questions}
"""


@dataclass
class Trajectory:
    """First-class trajectory artifact.

    Separate from the raw trajectory.md file — this is the structured
    in-memory representation that can be read, edited, and exported.
    """
    task: str = ""
    explored: list[str] = field(default_factory=list)
    selected: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    changes: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    # Proposed updates not yet confirmed
    proposed: TrajectoryEntry | None = None

    def to_markdown(self) -> str:
        return TRAJECTORY_TEMPLATE.format(
            task=self.task or "(no task recorded)",
            explored=self._bullet_list(self.explored),
            selected=self._bullet_list(self.selected),
            rejected=self._bullet_list(self.rejected),
            changes=self._bullet_list(self.changes),
            questions=self._bullet_list(self.open_questions),
        )

    def to_dict(self) -> dict:
        return {
            "task": self.task,
            "explored": self.explored,
            "selected": self.selected,
            "rejected": self.rejected,
            "changes": self.changes,
            "open_questions": self.open_questions,
        }

    @staticmethod
    def from_dict(data: dict) -> Trajectory:
        return Trajectory(
            task=data.get("task", ""),
            explored=data.get("explored", []),
            selected=data.get("selected", []),
            rejected=data.get("rejected", []),
            changes=data.get("changes", []),
            open_questions=data.get("open_questions", []),
        )

    @staticmethod
    def _bullet_list(items: list[str]) -> str:
        if not items:
            return "(none yet)"
        return "\n".join(f"- {item}" for item in items)

    # --- operations ---

    def add_explored(self, directions: list[str]) -> None:
        """Add newly explored directions (deduplicated)."""
        for d in directions:
            if d not in self.explored:
                self.explored.append(d)

    def select_direction(self, direction: str) -> None:
        """Mark a direction as selected/developed."""
        if direction not in self.selected:
            self.selected.append(direction)

    def reject_direction(self, direction: str) -> None:
        """Mark a direction as rejected/parked."""
        if direction not in self.rejected:
            self.rejected.append(direction)

    def record_change(self, change: str) -> None:
        """Record a change made to the text."""
        self.changes.append(change)

    def add_question(self, question: str) -> None:
        """Add an open question."""
        if question not in self.open_questions:
            self.open_questions.append(question)

    def apply_proposed(self) -> None:
        """Apply the proposed update, merging it into the trajectory.

        After this call, the proposed update is consumed and cleared.
        """
        if self.proposed is None:
            return
        self.add_explored(self.proposed.explored)
        self.selected.extend(self.proposed.shown)
        self.open_questions.extend(self.proposed.open_questions)
        self.proposed = None


def read_trajectory_file(path: str) -> Trajectory:
    """Read a trajectory.md file into a structured Trajectory.

    This is a best-effort parser for the markdown template.
    For precise storage, use to_dict/to_markdown cycle.
    """
    p = Path(path)
    if not p.exists():
        return Trajectory()

    text = p.read_text(encoding="utf-8")
    traj = Trajectory()
    traj.task = _extract_section(text, "Original task")
    traj.explored = _extract_items(text, "Directions already explored")
    traj.selected = _extract_items(text, "Directions selected and developed")
    traj.rejected = _extract_items(text, "Directions rejected or parked")
    traj.changes = _extract_items(text, "Changes made to the text")
    traj.open_questions = _extract_items(text, "Open questions")
    return traj


def write_trajectory_file(traj: Trajectory, path: str) -> None:
    """Write a Trajectory to a file."""
    Path(path).write_text(traj.to_markdown(), encoding="utf-8")


def export_trajectory(traj: Trajectory, output_path: str) -> None:
    """Export trajectory to a standalone markdown file."""
    write_trajectory_file(traj, output_path)


# --- help text for trajectory markdown ---

TRAJECTORY_HELP = """Trajectory format:
- **Original task** — the task you're working on
- **Directions already explored** — what the system has already suggested/investigated  
- **Directions selected and developed** — what you chose to pursue
- **Directions rejected or parked** — what you decided against
- **Changes made to the text** — concrete edits based on directions
- **Open questions** — what's still unresolved

Keep it under ~5000 tokens. Update after each meaningful decision.
"""


def _extract_section(text: str, heading: str) -> str:
    """Extract text under a ## heading."""
    import re
    pattern = rf"## {re.escape(heading)}\s*\n(.*?)(?=\n## |\Z)"
    m = re.search(pattern, text, re.DOTALL)
    if m:
        content = m.group(1).strip()
        if content == "(none yet)":
            return ""
        return content
    return ""


def _extract_items(text: str, heading: str) -> list[str]:
    """Extract bullet items under a ## heading."""
    section = _extract_section(text, heading)
    if not section:
        return []
    items = []
    for line in section.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:])
    return items
