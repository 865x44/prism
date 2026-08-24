"""Core dispatch for Perspective Core v0.

Implements execution contract frozen dispatch signatures.
Dispatches to stable entry modules (explore, deep, rift).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .models import ExploreRunResult, DeepRunResult, PerspectiveRequest

if TYPE_CHECKING:
    from .provider import LLMProvider
    from .session import SessionStore


# ─────────────────────────────────────────────────────────────────────────────
# Dispatch to entry modules
# ─────────────────────────────────────────────────────────────────────────────


def dispatch_explore(
    request: PerspectiveRequest,
    *,
    session_store: "SessionStore",
    provider: "LLMProvider",
    trace_root: Path,
) -> ExploreRunResult:
    """Dispatch to explore.run_explore.

    Frozen signature from execution contract.
    """
    from . import explore

    return explore.run_explore(
        request,
        session_store=session_store,
        provider=provider,
        trace_root=trace_root,
    )


def dispatch_deep(
    *,
    session_id: str,
    p_id: str,
    session_store: "SessionStore",
    provider: "LLMProvider",
    trace_root: Path,
) -> DeepRunResult:
    """Dispatch to deep.run_deep.

    Frozen signature from execution contract.
    """
    from . import deep

    return deep.run_deep(
        session_id=session_id,
        p_id=p_id,
        session_store=session_store,
        provider=provider,
        trace_root=trace_root,
    )


def dispatch_rift(
    request: PerspectiveRequest,
    *,
    session_store: "SessionStore",
    provider: "LLMProvider",
    trace_root: Path,
) -> ExploreRunResult:
    """Dispatch to rift.run_rift.

    Frozen signature from execution contract.
    """
    from . import rift

    return rift.run_rift(
        request,
        session_store=session_store,
        provider=provider,
        trace_root=trace_root,
    )
