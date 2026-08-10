"""Small provider seam used by later subject runners.

There is no transport implementation here.  The default stub fails closed so
tests and deterministic validation cannot accidentally make a real call.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SubjectResponse:
    """Visible subject output plus optional structured protocol data."""

    visible_output: str
    structured_output: dict[str, Any] | None = None


class SubjectProvider(Protocol):
    def execute(self, fixture: dict[str, Any]) -> SubjectResponse:
        """Execute a fixture only in a future explicitly authorized run."""


class ProviderCallsDisabled(RuntimeError):
    """Signals an intentionally prohibited provider call, never subject failure."""


class DisabledProvider:
    """Fail-closed default used until a separately authorized provider runner exists."""

    def execute(self, fixture: dict[str, Any]) -> SubjectResponse:
        raise ProviderCallsDisabled(
            "Beerlight DEMO_RC provider calls are disabled in the WS3 harness"
        )
