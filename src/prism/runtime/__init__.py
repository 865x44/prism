"""Prism Runtime v1 — productized runtime wrapping the validated slice.

Public API:
    import prism.runtime
    result = prism.runtime.run(document=..., task=..., mode="normal")

CLI entrypoint:
    python -m prism.runtime run <input_file> --task "<task>"
    python -m prism.runtime run-json request.json
    python -m prism.runtime inspect <run_id>
    python -m prism.runtime session create <input_file>
    python -m prism.runtime trajectory show <session_path>
"""

from .service import run
from .contracts import RunRequest, RunResponse, ExitCode
from .models import (
    Candidate,
    Card,
    PrivacyLevel,
    TraceLevel,
    RunMode,
    ContextMode,
)

__all__ = [
    "run",
    "RunRequest",
    "RunResponse",
    "ExitCode",
    "Candidate",
    "Card",
    "PrivacyLevel",
    "TraceLevel",
    "RunMode",
    "ContextMode",
]
