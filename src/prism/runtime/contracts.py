"""JSON request/response contracts for Prism Runtime.

External Contract v0:
    Input: JSON request file with document, task, mode, etc.
    Output: JSON response with status, cards, trace_dir, errors.

Deterministic exit codes for machine-readable integration.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class ExitCode(enum.IntEnum):
    """Deterministic exit codes for the run-json command."""
    OK = 0
    INVALID_REQUEST = 1
    INPUT_NOT_FOUND = 2
    GENERATOR_FAILED = 3
    JUDGE_FAILED = 4
    TRACE_WRITE_FAILED = 5
    INTERNAL_ERROR = 6
    DEGRADED = 7


@dataclass
class RunRequest:
    """Machine-readable request for a Prism run.

    JSON schema:
        {
          "input_path": "...",
          "task": "...",
          "mode": "normal",
          "trajectory_path": null,
          "context_mode": "trajectory",
          "trace_level": "compact",
          "output_dir": null
        }
    """
    input_path: str
    task: str
    mode: str = "normal"       # normal or 360
    trajectory_path: str | None = None
    context_mode: str = "trajectory"  # trajectory or full
    trace_level: str = "compact"      # compact or full
    output_dir: str | None = None

    def validate(self) -> list[str]:
        """Return list of validation errors; empty = valid."""
        errors: list[str] = []
        if not self.input_path:
            errors.append("input_path is required")
        if not self.task:
            errors.append("task is required")
        if self.mode not in ("normal", "360"):
            errors.append(f"invalid mode: {self.mode}")
        if self.context_mode not in ("trajectory", "full"):
            errors.append(f"invalid context_mode: {self.context_mode}")
        if self.trace_level not in ("compact", "full"):
            errors.append(f"invalid trace_level: {self.trace_level}")
        return errors

    @staticmethod
    def from_dict(data: dict) -> RunRequest:
        return RunRequest(
            input_path=data.get("input_path", ""),
            task=data.get("task", ""),
            mode=data.get("mode", "normal"),
            trajectory_path=data.get("trajectory_path"),
            context_mode=data.get("context_mode", "trajectory"),
            trace_level=data.get("trace_level", "compact"),
            output_dir=data.get("output_dir"),
        )


@dataclass
class RunResponse:
    """Machine-readable response from a Prism run.

    JSON schema:
        {
          "status": "ok",
          "run_id": "...",
          "cards": [],
          "trace_dir": "...",
          "trajectory_update_path": "...",
          "warnings": [],
          "error": null
        }
    """
    status: str = "ok"          # ok, no_useful_output, degraded, error
    run_id: str = ""
    cards: list[dict] = field(default_factory=list)
    trace_dir: str = ""
    trajectory_update_path: str | None = None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "run_id": self.run_id,
            "cards": self.cards,
            "trace_dir": self.trace_dir,
            "trajectory_update_path": self.trajectory_update_path,
            "warnings": self.warnings,
            "error": self.error,
        }

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
