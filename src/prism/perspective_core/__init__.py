"""Perspective Core v0 — shared package.

Public exports: models, provider protocol, session store, trace writer,
and frozen dispatch functions.
"""

from __future__ import annotations

from .models import (
    ConstraintEntry,
    ConstraintLedger,
    DeepDevelopment,
    DeepRebuildResult,
    DeepReview,
    DeepRunRef,
    DeepRunResult,
    Diagnosis,
    Epistemics,
    ExploreRunResult,
    MergeTarget,
    PassRecord,
    PerspectiveCandidate,
    PerspectiveIdentity,
    PerspectiveRequest,
    PerspectiveSession,
    PerspectiveState,
    ProviderResult,
    ReturnPath,
    SelectionRecord,
    SemanticCore,
    ValidationIssue,
    compute_source_hash,
    validate_candidates,
    validate_selections,
)
from .provider import (
    LLMProvider,
    QwenCliProvider,
    ScriptedProvider,
    STAGES,
    TransportError,
    get_repair_parent,
    is_repair_stage,
    make_default_provider,
    make_scripted_provider,
)
from .session import SessionStore
from .trace import TraceWriter

__all__ = [
    # Models
    "ConstraintEntry",
    "ConstraintLedger",
    "DeepDevelopment",
    "DeepRebuildResult",
    "DeepReview",
    "DeepRunRef",
    "DeepRunResult",
    "Diagnosis",
    "Epistemics",
    "ExploreRunResult",
    "MergeTarget",
    "PassRecord",
    "PerspectiveCandidate",
    "PerspectiveIdentity",
    "PerspectiveRequest",
    "PerspectiveSession",
    "PerspectiveState",
    "ProviderResult",
    "ReturnPath",
    "SelectionRecord",
    "SemanticCore",
    "ValidationIssue",
    "compute_source_hash",
    "validate_candidates",
    "validate_selections",
    # Provider
    "LLMProvider",
    "QwenCliProvider",
    "ScriptedProvider",
    "STAGES",
    "TransportError",
    "get_repair_parent",
    "is_repair_stage",
    "make_default_provider",
    "make_scripted_provider",
    # Session
    "SessionStore",
    # Trace
    "TraceWriter",
]
