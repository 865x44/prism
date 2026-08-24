"""Selection logic for Perspective Core v0.

Implements Call B selection validation and KEEP-only registration.
Structural/integrity validation only; Call B owns semantic admissibility.
"""

from __future__ import annotations

import json
from typing import Any

from .models import (
    MergeTarget,
    PerspectiveCandidate,
    PerspectiveIdentity,
    PerspectiveState,
    SelectionRecord,
    Epistemics,
    SemanticCore,
)


# ─────────────────────────────────────────────────────────────────────────────
# Selection JSON parsing and validation
# ─────────────────────────────────────────────────────────────────────────────


def parse_selections_json(raw_text: str) -> list[dict[str, Any]]:
    """Parse and validate selection JSON from provider response.

    Args:
        raw_text: Raw JSON text from provider

    Returns:
        List of selection dictionaries

    Raises:
        ValueError: If JSON is malformed or structure is invalid
    """
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    if not isinstance(data, list):
        raise ValueError("Selection response must be a JSON array")

    return data


def validate_selection_structure(
    selections: list[dict[str, Any]],
    candidate_ids: set[str],
    existing_p_ids: set[str] | None = None,
) -> list[str]:
    """Validate selection structure against candidates.

    Args:
        selections: List of selection dictionaries
        candidate_ids: Set of valid candidate IDs
        existing_p_ids: Set of existing P-IDs for perspective merge targets

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    existing_p_ids = existing_p_ids or set()

    # Check exactly one selection per candidate
    selected_ids = [s.get("candidate_id") for s in selections]
    for cid in candidate_ids:
        count = selected_ids.count(cid)
        if count == 0:
            errors.append(f"Missing selection for candidate {cid}")
        elif count > 1:
            errors.append(f"Multiple selections for candidate {cid}")

    # Check for unknown candidates
    for sel in selections:
        cid = sel.get("candidate_id")
        if cid not in candidate_ids:
            errors.append(f"Selection references unknown candidate {cid}")

    # Validate each selection
    for sel in selections:
        cid = sel.get("candidate_id")

        # Validate disposition
        disposition = sel.get("disposition")
        if disposition not in ("KEEP", "BORDERLINE", "MERGE", "DROP"):
            errors.append(f"Invalid disposition for {cid}: {disposition}")

        # Validate standalone_quality
        quality = sel.get("standalone_quality")
        if quality not in ("strong", "borderline", "weak"):
            errors.append(f"Invalid standalone_quality for {cid}: {quality}")

        # Validate marginal_contribution
        marginal = sel.get("marginal_contribution")
        if marginal not in ("high", "medium", "low", "none"):
            errors.append(f"Invalid marginal_contribution for {cid}: {marginal}")

        # Validate MERGE target
        if disposition == "MERGE":
            merge_target = sel.get("merge_target")
            if merge_target is None:
                errors.append(f"MERGE disposition requires merge_target for {cid}")
            else:
                kind = merge_target.get("kind")
                target_id = merge_target.get("target_id")

                if kind == "candidate":
                    if target_id not in candidate_ids:
                        errors.append(
                            f"Merge target candidate {target_id} not found for {cid}"
                        )
                    if target_id == cid:
                        errors.append(f"Candidate {cid} cannot merge with itself")
                elif kind == "perspective":
                    if target_id not in existing_p_ids:
                        errors.append(
                            f"Merge target P-ID {target_id} not found for {cid}"
                        )
                else:
                    errors.append(f"Invalid merge target kind for {cid}: {kind}")

    return errors


def selection_record_from_dict(data: dict[str, Any]) -> SelectionRecord:
    """Convert selection dictionary to SelectionRecord.

    Args:
        data: Selection dictionary

    Returns:
        SelectionRecord instance
    """
    merge_target_data = data.get("merge_target")
    merge_target = None
    if merge_target_data:
        merge_target = MergeTarget(
            kind=merge_target_data["kind"],
            target_id=merge_target_data["target_id"],
        )

    return SelectionRecord(
        candidate_id=data["candidate_id"],
        admissible=data["admissible"],
        constraint_failures=data.get("constraint_failures", []),
        structurally_distinct=data.get("structurally_distinct", True),
        novelty_dimensions=data.get("novelty_dimensions", []),
        nearest_candidate_id=data.get("nearest_candidate_id"),
        nearest_existing_p_id=data.get("nearest_existing_p_id"),
        standalone_quality=data["standalone_quality"],
        marginal_contribution=data["marginal_contribution"],
        disposition=data["disposition"],
        merge_target=merge_target,
        reason=data["reason"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# KEEP registration and rendering
# ─────────────────────────────────────────────────────────────────────────────


def register_kept_perspectives(
    candidates: list[PerspectiveCandidate],
    selections: list[SelectionRecord],
    next_p_number: int,
) -> tuple[list[PerspectiveState], list[str]]:
    """Register KEEP selections as PerspectiveState with P-IDs.

    Args:
        candidates: List of candidates
        selections: List of selections (must be validated)
        next_p_number: Next available P-number

    Returns:
        Tuple of (list of PerspectiveState, list of kept P-IDs)
    """
    # Build candidate lookup
    candidate_map = {c.candidate_id: c for c in candidates}

    # Filter KEEP selections in candidate order
    kept_states = []
    kept_p_ids = []
    p_number = next_p_number

    # Process selections in candidate order (not selection order)
    for candidate in candidates:
        selection = next(
            (s for s in selections if s.candidate_id == candidate.candidate_id),
            None,
        )
        if selection and selection.disposition == "KEEP":
            p_id = f"P{p_number}"
            identity = PerspectiveIdentity(
                p_id=p_id,
                candidate_id=candidate.candidate_id,
                identity_core=candidate.semantic_core,
            )
            state = PerspectiveState(
                identity=identity,
                current_version=1,
                epistemics=candidate.epistemics,
                deep_refs=[],
                terminal_state=None,
            )
            kept_states.append(state)
            kept_p_ids.append(p_id)
            p_number += 1

    return kept_states, kept_p_ids


def render_perspective(state: PerspectiveState, candidate: PerspectiveCandidate) -> str:
    """Render a perspective state as user-visible text.

    Args:
        state: Perspective state
        candidate: Source candidate

    Returns:
        Rendered text
    """
    core = state.identity.identity_core

    lines = [
        f"## {state.identity.p_id}: {core.central_problem}",
        "",
        f"**Structural shift:** {candidate.shift}",
        "",
        f"**Source anchor:** {core.load_bearing_claim}",
        "",
        f"**Mechanism:** {core.mechanism}",
        "",
        f"**Visible consequence:** {', '.join(candidate.new_consequences[:3])}",
        "",
        f"**Load-bearing assumption:** {core.agency_model or 'Not specified'}",
        "",
        f"**Boundary:** {core.system_boundary or 'Not specified'}",
        "",
        f"**Payoff:** {candidate.return_path.why_it_matters}",
    ]

    return "\n".join(lines)
