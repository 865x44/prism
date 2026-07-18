"""Beerlight Runtime v1 — productized runtime wrapping the validated slice.

Public API:
    import beerlight.runtime
    result = beerlight.runtime.run(document=..., task=..., mode="normal")

CLI entrypoint:
    python -m beerlight.runtime run <input_file> --task "<task>"
    python -m beerlight.runtime run-json request.json
    python -m beerlight.runtime inspect <run_id>
    python -m beerlight.runtime session create <input_file>
    python -m beerlight.runtime trajectory show <session_path>
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
