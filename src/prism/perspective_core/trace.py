"""Trace writer for Perspective Core v0.

Implements execution contract trace API.
Records provider invocations and structured outputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .models import ProviderResult


# ─────────────────────────────────────────────────────────────────────────────
# Trace writer
# ─────────────────────────────────────────────────────────────────────────────


class TraceWriter:
    """Manages trace directory and provider invocation logging.

    Trace structure:
        <trace_root>/<run_id>/
        ├── provider-invocations.json
        ├── candidates.json
        ├── selection.json
        ├── development.json
        └── ...
    """

    def __init__(self, trace_root: Path):
        """Initialize trace writer.

        Args:
            trace_root: Base directory for traces
        """
        self._trace_root = trace_root
        self._current_run_dir: Path | None = None
        self._current_session_id: str | None = None

    def start_run(self, *, run_id: str, session_id: str) -> Path:
        """Start a new trace run.

        Args:
            run_id: Unique run identifier
            session_id: Session identifier

        Returns:
            Path to run directory
        """
        self._current_run_dir = self._trace_root / run_id
        self._current_run_dir.mkdir(parents=True, exist_ok=True)
        self._current_session_id = session_id

        # Initialize provider-invocations.json
        invocations_file = self._current_run_dir / "provider-invocations.json"
        if not invocations_file.exists():
            invocations_file.write_text("[]", encoding="utf-8")

        return self._current_run_dir

    def write_json(self, relative_name: str, value: Mapping[str, Any]) -> None:
        """Write structured JSON to trace directory.

        Args:
            relative_name: Filename relative to current run directory
            value: JSON-serializable data

        Raises:
            RuntimeError: If no active run
        """
        if self._current_run_dir is None:
            raise RuntimeError("No active trace run")

        file_path = self._current_run_dir / relative_name
        file_path.write_text(
            json.dumps(value, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def record_provider_result(
        self,
        result: ProviderResult,
        *,
        repair_parent: str | None = None,
    ) -> None:
        """Record provider invocation metadata.

        Appends to provider-invocations.json.

        Args:
            result: Provider result to record
            repair_parent: Parent stage if this is a repair call

        Raises:
            RuntimeError: If no active run
        """
        if self._current_run_dir is None:
            raise RuntimeError("No active trace run")

        invocations_file = self._current_run_dir / "provider-invocations.json"

        # Load existing invocations
        with open(invocations_file, encoding="utf-8") as f:
            invocations = json.load(f)

        # Append new invocation
        invocation = {
            "invocation_id": result.invocation_id,
            "stage": result.stage,
            "model": result.model,
            "transport": result.transport,
            "duration_ms": result.duration_ms,
            "exit_code": result.exit_code,
        }

        if repair_parent is not None:
            invocation["repair_parent"] = repair_parent

        invocations.append(invocation)

        # Write back
        invocations_file.write_text(
            json.dumps(invocations, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @property
    def current_run_dir(self) -> Path | None:
        """Get current run directory."""
        return self._current_run_dir

    @property
    def current_session_id(self) -> str | None:
        """Get current session ID."""
        return self._current_session_id
