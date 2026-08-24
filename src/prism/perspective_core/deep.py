"""Deep entrypoint for Perspective Core v0.

Implements source-verified, P-ID-locked Deep development, load-bearing review,
bounded rebuild with a final gate, and versioned persistence.

Stages: DEEP_DEVELOP, DEEP_REVIEW, optional DEEP_REBUILD.
Maximum 3 semantic invocations per run (excluding schema repair).
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .models import (
    DeepDevelopment,
    DeepRebuildResult,
    DeepReview,
    DeepRunRef,
    DeepRunResult,
)

if TYPE_CHECKING:
    from .provider import LLMProvider
    from .session import SessionStore


# ─────────────────────────────────────────────────────────────────────────────
# Normalization
# ─────────────────────────────────────────────────────────────────────────────


def _normalize_semantic_core(core: Any) -> str:
    """Produce deterministic canonical serialization of a SemanticCore.

    Sorted keys, strict JSON, no whitespace variance. Used for strict
    equality comparison between semantic_lock_echo and identity_core.
    """
    return json.dumps(core.to_dict(), sort_keys=True, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# JSON extraction from provider raw_text
# ─────────────────────────────────────────────────────────────────────────────


def _extract_json(raw_text: str) -> dict[str, Any]:
    """Extract JSON object from provider raw_text.

    Handles:
    - Direct JSON object
    - JSON wrapped in markdown code blocks (```json ... ```)
    - JSON embedded in surrounding text (first { to last })
    """
    text = raw_text.strip()
    if text.startswith("{"):
        return json.loads(text)

    if "```" in text:
        for block in text.split("```"):
            stripped = block.strip()
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()
            if stripped.startswith("{"):
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    continue

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return json.loads(text[first_brace : last_brace + 1])

    raise ValueError(f"No JSON object found in provider output")


# ─────────────────────────────────────────────────────────────────────────────
# Response parsers
# ─────────────────────────────────────────────────────────────────────────────


def _parse_development(raw_text: str) -> DeepDevelopment:
    """Parse DEEP_DEVELOP response into DeepDevelopment."""
    return DeepDevelopment.from_dict(_extract_json(raw_text))


def _parse_review(raw_text: str) -> DeepReview:
    """Parse DEEP_REVIEW response into DeepReview."""
    return DeepReview.from_dict(_extract_json(raw_text))


def _parse_rebuild_result(raw_text: str) -> DeepRebuildResult:
    """Parse DEEP_REBUILD response into DeepRebuildResult."""
    return DeepRebuildResult.from_dict(_extract_json(raw_text))



# ─────────────────────────────────────────────────────────────────────────────
# Prompt construction (loads from tracked .md assets)
# ─────────────────────────────────────────────────────────────────────────────


def _load_prompt_asset(name: str) -> str:
    """Load a Deep prompt asset by filename from the prompts package."""
    from .prompts import prompt_path

    return prompt_path(name).read_text(encoding="utf-8")


def _build_develop_prompt(
    *,
    source: str,
    objective: str,
    identity_core_json: str,
    constraints_json: str,
    state_json: str,
    p_id: str,
) -> str:
    """Build the DEEP_DEVELOP prompt from tracked asset + runtime data."""
    asset = _load_prompt_asset("deep_develop.md")
    return (
        f"# Deep Development — {p_id}\n\n"
        f"{asset}\n\n"
        f"# ── Runtime Data ──\n\n"
        f"## Source Material\n\n{source}\n\n"
        f"## Objective\n\n{objective}\n\n"
        f"## Perspective Identity Core "
        f"(IMMUTABLE — echo exactly in semantic_lock_echo)\n\n"
        f"{identity_core_json}\n\n"
        f"## Active Constraints\n\n{constraints_json}\n\n"
        f"## Current State\n\n{state_json}\n\n"
        f"## Response\n\n"
        f"Respond with a single JSON object matching the DeepDevelopment "
        f"schema above. Set `p_id` to `{p_id}` and `semantic_lock_echo` "
        f"to the exact identity core object."
    )


def _build_review_prompt(
    *,
    source: str,
    objective: str,
    identity_core_json: str,
    development_json: str,
    identity_echo_mismatch: bool,
    p_id: str,
) -> str:
    """Build the DEEP_REVIEW prompt from tracked asset + runtime data."""
    asset = _load_prompt_asset("deep_review.md")
    mismatch_section = ""
    if identity_echo_mismatch:
        mismatch_section = (
            "\n\n## WARNING: Identity Echo Mismatch Detected\n"
            "The semantic_lock_echo in the development does NOT match the "
            "immutable identity core. Per the asset invariant #1, "
            "`identity_preserved` MUST be false and drift MUST be documented."
        )
    return (
        f"# Deep Review — {p_id}\n\n"
        f"{asset}"
        f"{mismatch_section}\n\n"
        f"# ── Runtime Data ──\n\n"
        f"## Source Material\n\n{source}\n\n"
        f"## Objective\n\n{objective}\n\n"
        f"## Immutable Identity Core\n\n{identity_core_json}\n\n"
        f"## Developed Model\n\n{development_json}\n\n"
        f"## Response\n\n"
        f"Respond with a single JSON object matching the DeepReview "
        f"schema above."
    )


def _build_rebuild_prompt(
    *,
    source: str,
    objective: str,
    identity_core_json: str,
    development_json: str,
    review_json: str,
    constraints_json: str,
    p_id: str,
) -> str:
    """Build the DEEP_REBUILD prompt from tracked asset + runtime data."""
    asset = _load_prompt_asset("deep_rebuild.md")
    return (
        f"# Deep Rebuild — {p_id}\n\n"
        f"{asset}\n\n"
        f"# ── Runtime Data ──\n\n"
        f"## Source Material\n\n{source}\n\n"
        f"## Objective\n\n{objective}\n\n"
        f"## Immutable Identity Core "
        f"(MUST be echoed exactly in semantic_lock_echo)\n\n"
        f"{identity_core_json}\n\n"
        f"## Active Constraints\n\n{constraints_json}\n\n"
        f"## Previous Development\n\n{development_json}\n\n"
        f"## Review Feedback\n\n{review_json}\n\n"
        f"## Response\n\n"
        f"Respond with a single JSON object containing both `development` "
        f"and `final_review` as specified in the asset schema above. "
        f"Set `p_id` to `{p_id}`."
    )




# ─────────────────────────────────────────────────────────────────────────────
# Main entrypoint
# ─────────────────────────────────────────────────────────────────────────────


def run_deep(
    *,
    session_id: str,
    p_id: str,
    session_store: "SessionStore",
    provider: "LLMProvider",
    trace_root: Path,
) -> DeepRunResult:
    """Run Deep analysis for a P-ID.

    Signature is frozen by Wave 1 execution contract.

    Pipeline:
    1. Resolve session, verify source hash (fails before provider on mismatch).
    2. Resolve P-ID from session (fails before provider if unknown).
    3. DEEP_DEVELOP → parse DeepDevelopment.
    4. Normalize and compare semantic_lock_echo with identity_core.
    5. DEEP_REVIEW → parse DeepReview (mismatch info passed in).
    6. If rebuild_required: DEEP_REBUILD → parse DeepRebuildResult.
       Second rebuild request → RETURN_TO_EXPLORE.
    7. Persist artifacts, append DeepRunRef, update state version.
    """
    from .trace import TraceWriter

    run_id = f"deep-run-{uuid.uuid4().hex[:12]}"
    deep_id = f"deep-{uuid.uuid4().hex[:12]}"

    # ── 1. Resolve session and verify source ────────────────────────────
    # Raises FileNotFoundError or RuntimeError on hash mismatch —
    # both propagate before any provider call.
    session = session_store.load(session_id)
    source = session_store.load_verified_source(session)

    # ── 2. Resolve P-ID ─────────────────────────────────────────────────
    # Raises ValueError on unknown P-ID — before any provider call.
    if p_id not in session.perspectives:
        raise ValueError(
            f"Unknown P-ID: {p_id} not found in session {session_id}"
        )

    state = session.perspectives[p_id]
    identity = state.identity
    identity_core = identity.identity_core

    # ── 3. Start trace run ──────────────────────────────────────────────
    trace_writer = TraceWriter(trace_root)
    trace_writer.start_run(run_id=run_id, session_id=session_id)

    identity_core_json = json.dumps(
        identity_core.to_dict(), indent=2, ensure_ascii=False
    )
    constraints_json = json.dumps(
        session.constraint_ledger.to_dict(), indent=2, ensure_ascii=False
    )
    state_json = json.dumps(state.to_dict(), indent=2, ensure_ascii=False)

    # ── 4. DEEP_DEVELOP ─────────────────────────────────────────────────
    dev_invocation_id = f"inv-deep-dev-{uuid.uuid4().hex[:12]}"
    dev_prompt = _build_develop_prompt(
        source=source,
        objective=session.objective,
        identity_core_json=identity_core_json,
        constraints_json=constraints_json,
        state_json=state_json,
        p_id=p_id,
    )

    dev_result = provider.complete(
        dev_prompt, stage="DEEP_DEVELOP", invocation_id=dev_invocation_id
    )
    trace_writer.record_provider_result(dev_result)

    development = _parse_development(dev_result.raw_text)

    # ── 5. Lock echo check ──────────────────────────────────────────────
    normalized_echo = _normalize_semantic_core(development.semantic_lock_echo)
    normalized_core = _normalize_semantic_core(identity_core)
    identity_echo_mismatch = normalized_echo != normalized_core

    # ── 6. DEEP_REVIEW ──────────────────────────────────────────────────
    review_invocation_id = f"inv-deep-rev-{uuid.uuid4().hex[:12]}"
    development_json = json.dumps(
        development.to_dict(), indent=2, ensure_ascii=False
    )
    review_prompt = _build_review_prompt(
        source=source,
        objective=session.objective,
        identity_core_json=identity_core_json,
        development_json=development_json,
        identity_echo_mismatch=identity_echo_mismatch,
        p_id=p_id,
    )

    review_result = provider.complete(
        review_prompt, stage="DEEP_REVIEW", invocation_id=review_invocation_id
    )
    trace_writer.record_provider_result(review_result)

    initial_review = _parse_review(review_result.raw_text)

    # ── 7a. Code-enforced lock echo gate (§10.3) ─────────────────────────
    # If initial development has lock echo mismatch and review did not request
    # rebuild, the development cannot be accepted. Force RETURN_TO_EXPLORE.
    if identity_echo_mismatch and not initial_review.rebuild_required:
        initial_review = DeepReview(
            identity_preserved=False,
            identity_drift=initial_review.identity_drift
            + ["semantic_lock_echo mismatch detected by code gate"],
            load_bearing_claim=initial_review.load_bearing_claim,
            strongest_objection=initial_review.strongest_objection,
            objection_target=initial_review.objection_target,
            objection_is_load_bearing=initial_review.objection_is_load_bearing,
            counterevidence=initial_review.counterevidence,
            evidence_debt=initial_review.evidence_debt,
            rebuild_required=False,
            rebuild_instructions=initial_review.rebuild_instructions,
            terminal_state="RETURN_TO_EXPLORE",
            rationale=(
                initial_review.rationale
                + " [Code gate: lock echo mismatch without rebuild → RETURN_TO_EXPLORE]"
            ),
        )


    # ── 7. Determine flow ───────────────────────────────────────────────
    rebuilt_development: DeepDevelopment | None = None
    final_review = initial_review
    terminal_state = initial_review.terminal_state

    if initial_review.rebuild_required:
        # ── 8. DEEP_REBUILD (one bounded call) ──────────────────────────
        rebuild_invocation_id = f"inv-deep-rbd-{uuid.uuid4().hex[:12]}"
        review_json = json.dumps(
            initial_review.to_dict(), indent=2, ensure_ascii=False
        )
        rebuild_prompt = _build_rebuild_prompt(
            source=source,
            objective=session.objective,
            identity_core_json=identity_core_json,
            development_json=development_json,
            review_json=review_json,
            constraints_json=constraints_json,
            p_id=p_id,
        )

        rebuild_result = provider.complete(
            rebuild_prompt,
            stage="DEEP_REBUILD",
            invocation_id=rebuild_invocation_id,
        )
        trace_writer.record_provider_result(rebuild_result)

        deep_rebuild = _parse_rebuild_result(rebuild_result.raw_text)
        rebuilt_development = deep_rebuild.development
        final_review = deep_rebuild.final_review

        # Re-check lock echo after rebuild
        rebuilt_echo = _normalize_semantic_core(
            rebuilt_development.semantic_lock_echo
        )
        rebuilt_mismatch = rebuilt_echo != normalized_core

        # Second rebuild request is invalid → RETURN_TO_EXPLORE
        if final_review.rebuild_required:
            final_review = DeepReview(
                identity_preserved=final_review.identity_preserved,
                identity_drift=final_review.identity_drift,
                load_bearing_claim=final_review.load_bearing_claim,
                strongest_objection=final_review.strongest_objection,
                objection_target=final_review.objection_target,
                objection_is_load_bearing=final_review.objection_is_load_bearing,
                counterevidence=final_review.counterevidence,
                evidence_debt=final_review.evidence_debt,
                rebuild_required=False,
                rebuild_instructions=[],
                terminal_state="RETURN_TO_EXPLORE",
                rationale=(
                    "Second rebuild request is invalid in v0; "
                    "returning to explore for fresh perspective development."
                ),
            )
            terminal_state = "RETURN_TO_EXPLORE"
        else:
            terminal_state = final_review.terminal_state
            if rebuilt_mismatch:
                final_review = DeepReview(
                    identity_preserved=False,
                    identity_drift=final_review.identity_drift
                    + [
                        "semantic_lock_echo mismatch persists after rebuild"
                    ],
                    load_bearing_claim=final_review.load_bearing_claim,
                    strongest_objection=final_review.strongest_objection,
                    objection_target=final_review.objection_target,
                    objection_is_load_bearing=final_review.objection_is_load_bearing,
                    counterevidence=final_review.counterevidence,
                    evidence_debt=final_review.evidence_debt,
                    rebuild_required=False,
                    rebuild_instructions=[],
                    terminal_state="RETURN_TO_EXPLORE",
                    rationale=(
                        "Identity echo mismatch persists after rebuild; "
                        "returning to explore."
                    ),
                )
                terminal_state = "RETURN_TO_EXPLORE"

    # ── 9. Persist artifacts ────────────────────────────────────────────
    trace_writer.write_json(
        "deep_request.json",
        {
            "session_id": session_id,
            "p_id": p_id,
            "deep_id": deep_id,
            "identity_core": identity_core.to_dict(),
        },
    )
    trace_writer.write_json("development.json", development.to_dict())
    trace_writer.write_json("review.json", initial_review.to_dict())
    if rebuilt_development is not None:
        trace_writer.write_json(
            "rebuild.json",
            DeepRebuildResult(
                development=rebuilt_development,
                final_review=final_review,
            ).to_dict(),
        )
        trace_writer.write_json(
            "rebuilt_development.json", rebuilt_development.to_dict()
        )
    trace_writer.write_json(
        "result.json",
        {
            "run_id": run_id,
            "deep_id": deep_id,
            "p_id": p_id,
            "terminal_state": terminal_state,
        },
    )

    # ── 10. Update session ──────────────────────────────────────────────
    deep_ref = DeepRunRef(
        deep_id=deep_id,
        p_id=p_id,
        terminal_state=terminal_state,
        trace_ref=run_id,
    )
    session.deep_runs.append(deep_ref)

    # Increment version and set terminal state only after successful result
    state.current_version += 1
    state.terminal_state = terminal_state
    state.deep_refs.append(deep_id)

    session_store.save(session)

    return DeepRunResult(
        run_id=run_id,
        deep_id=deep_id,
        p_id=p_id,
        development=development,
        review=final_review,
        rebuilt_development=rebuilt_development,
        terminal_state=terminal_state,
    )
