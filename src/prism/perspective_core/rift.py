"""RIFT exploration for Perspective Core v0.

Implements replan §19, Wave 4 execution contract:
- RIFT as a farther search profile over the accepted session/candidate/selection core.
- Stages: RIFT_GENERATE, RIFT_SELECT.
- Cross-domain structural transfer and conceptual distance.
- Mandatory donor-vocabulary ablation test in selection.
- Concrete return path required.
- Binding source constraints.
- Free-lane candidates with empty operator_ids preserved.
- Only KEEP receives P-ID / rendering.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .models import (
    ConstraintLedger,
    Diagnosis,
    Epistemics,
    ExploreRunResult,
    PassRecord,
    PerspectiveCandidate,
    PerspectiveRequest,
    PerspectiveState,
    ReturnPath,
    SelectionRecord,
    SemanticCore,
    compute_source_hash,
    validate_selections,
)
from .prompts import prompt_path
from .selection import (
    register_kept_perspectives,
    render_perspective,
    selection_record_from_dict,
    validate_selection_structure,
)
from .trace import TraceWriter

if TYPE_CHECKING:
    from .provider import LLMProvider
    from .session import SessionStore


# ─────────────────────────────────────────────────────────────────────────────
# Prompt rendering helpers
# ─────────────────────────────────────────────────────────────────────────────


def _render_constraints(ledger: ConstraintLedger) -> str:
    """Render active constraints for prompt inclusion."""
    active = ledger.active_entries()
    if not active:
        return "(none)"
    lines = []
    for entry in active:
        kind_label = "HARD" if entry.kind == "hard" else "PREFERENCE"
        lines.append(f"- [{kind_label}] {entry.constraint_id}: {entry.value}")
    return "\n".join(lines)


def _render_must_not_claim(must_not_claim: list[str]) -> str:
    """Render must_not_claim list."""
    if not must_not_claim:
        return "(none)"
    return "\n".join(f"- {item}" for item in must_not_claim)


def _render_operator_hints() -> str:
    """Render operator hints from registry."""
    from .operators import OPERATORS

    lines = []
    for op in OPERATORS:
        lines.append(f"- {op.id}: {op.instruction}")
    return "\n".join(lines)


def _render_existing_perspectives(session: Any) -> str:
    """Render existing perspectives for Call B."""
    if not session or not session.perspectives:
        return "(none — this is the first pass)"
    lines = []
    for p_id, state in session.perspectives.items():
        core = state.identity.identity_core
        lines.append(f"- {p_id}: {core.central_problem} — {core.mechanism}")
    return "\n".join(lines)


def _render_candidates_for_selection(candidates: list[PerspectiveCandidate]) -> str:
    """Render candidates for Call B evaluation."""
    parts = []
    for c in candidates:
        core = c.semantic_core
        parts.append(
            f"### {c.candidate_id}\n"
            f"- Central problem: {core.central_problem}\n"
            f"- Mechanism: {core.mechanism}\n"
            f"- Load-bearing claim: {core.load_bearing_claim}\n"
            f"- Shift: {c.shift}\n"
            f"- Perspective: {c.perspective}\n"
            f"- Default frame: {c.default_frame}\n"
            f"- Blind spot: {c.blind_spot}\n"
            f"- New consequences: {', '.join(c.new_consequences)}\n"
            f"- Return path: [Changed: {c.return_path.dimension_changed}] [Chain: {', '.join(c.return_path.consequence_chain)}] [Why: {c.return_path.why_it_matters}]\n"
            f"- Operator IDs: {', '.join(c.operator_ids) if c.operator_ids else '(free-lane)'}\n"
        )
    return "\n".join(parts)


def _render_diagnosis_for_selection(diagnosis: Diagnosis) -> str:
    """Render diagnosis for Call B."""
    return (
        f"Central problem: {diagnosis.central_problem}\n"
        f"Search profile: {diagnosis.search_profile}\n"
        f"Priority dimensions: {', '.join(diagnosis.priority_dimensions)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# JSON parsing helpers
# ─────────────────────────────────────────────────────────────────────────────


def _extract_json_object(text: str) -> dict[str, Any]:
    """Extract a JSON object from provider response text.

    Handles fenced code blocks and surrounding text.
    """
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)

    if "```" in text:
        blocks = text.split("```")
        for block in blocks[1::2]:
            lines = block.strip().split("\n")
            if lines and lines[0].strip().startswith("{"):
                continue
            candidate = "\n".join(
                lines[1:]
                if lines and not lines[0].strip().startswith("{")
                else lines
            )
            try:
                result = json.loads(candidate)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                continue

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start : end + 1])

    raise ValueError("No JSON object found in response")


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    """Extract a JSON array from provider response text."""
    text = text.strip()
    if text.startswith("["):
        return json.loads(text)

    if "```" in text:
        blocks = text.split("```")
        for block in blocks[1::2]:
            lines = block.strip().split("\n")
            if lines and lines[0].strip().startswith("["):
                continue
            candidate = "\n".join(
                lines[1:]
                if lines and not lines[0].strip().startswith("[")
                else lines
            )
            try:
                result = json.loads(candidate)
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                continue

    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        return json.loads(text[start : end + 1])

    raise ValueError("No JSON array found in response")


# ─────────────────────────────────────────────────────────────────────────────
# Candidate parsing from RIFT Call A response
# ─────────────────────────────────────────────────────────────────────────────


def _parse_rift_generate_response(
    raw_text: str, candidate_budget: int
) -> tuple[Diagnosis, list[PerspectiveCandidate]]:
    """Parse Call A RIFT response into Diagnosis and candidates.

    Assigns deterministic candidate_id based on response order.
    Preserves free-lane candidates with empty operator_ids.
    """
    data = _extract_json_object(raw_text)

    diag_data = data.get("diagnosis")
    if not diag_data:
        raise ValueError("Missing diagnosis in generate response")

    diagnosis = Diagnosis(
        central_problem=diag_data["central_problem"],
        search_profile=diag_data["search_profile"],
        priority_dimensions=diag_data.get("priority_dimensions", []),
    )

    candidates_data = data.get("candidates", [])
    if not isinstance(candidates_data, list):
        raise ValueError("candidates must be a list")

    if len(candidates_data) > candidate_budget:
        candidates_data = candidates_data[:candidate_budget]

    candidates = []
    for idx, c_data in enumerate(candidates_data):
        candidate_id = f"C{idx + 1}"

        sc_data = c_data.get("semantic_core", {})
        semantic_core = SemanticCore(
            central_problem=sc_data.get("central_problem", ""),
            mechanism=sc_data.get("mechanism", ""),
            load_bearing_claim=sc_data.get("load_bearing_claim", ""),
            central_object=sc_data.get("central_object"),
            unit_of_analysis=sc_data.get("unit_of_analysis"),
            system_boundary=sc_data.get("system_boundary"),
            agency_model=sc_data.get("agency_model"),
            temporal_logic=sc_data.get("temporal_logic"),
            key_constraint=sc_data.get("key_constraint"),
            downstream_consequences=sc_data.get("downstream_consequences", []),
        )

        rp_data = c_data.get("return_path", {})
        return_path = ReturnPath(
            dimension_changed=rp_data.get("dimension_changed", ""),
            consequence_chain=rp_data.get("consequence_chain", []),
            why_it_matters=rp_data.get("why_it_matters", ""),
        )

        ep_data = c_data.get("epistemics", {})
        epistemics = Epistemics(
            supported=ep_data.get("supported", []),
            inferred=ep_data.get("inferred", []),
            speculative=ep_data.get("speculative", []),
            unknown=ep_data.get("unknown", []),
            break_condition=ep_data.get("break_condition", []),
        )

        raw_operator_ids = c_data.get("operator_ids")
        if raw_operator_ids is None:
            operator_ids = []
        elif isinstance(raw_operator_ids, list):
            operator_ids = [str(op) for op in raw_operator_ids]
        else:
            operator_ids = [str(raw_operator_ids)]

        candidate = PerspectiveCandidate(
            candidate_id=candidate_id,
            semantic_core=semantic_core,
            preserved=c_data.get("preserved", []),
            default_frame=c_data.get("default_frame", ""),
            blind_spot=c_data.get("blind_spot", ""),
            operator_ids=operator_ids,
            shift=c_data.get("shift", ""),
            perspective=c_data.get("perspective", ""),
            new_consequences=c_data.get("new_consequences", []),
            return_path=return_path,
            epistemics=epistemics,
        )
        candidates.append(candidate)

    return diagnosis, candidates


# ─────────────────────────────────────────────────────────────────────────────
# Stage invocation with bounded repair
# ─────────────────────────────────────────────────────────────────────────────


def _invoke_stage(
    provider: "LLMProvider",
    trace_writer: TraceWriter,
    *,
    stage: str,
    prompt: str,
    invocation_id: str | None = None,
    repair_parent: str | None = None,
) -> str:
    """Invoke a provider stage and record the result."""
    if invocation_id is None:
        invocation_id = str(uuid.uuid4())

    result = provider.complete(prompt, stage=stage, invocation_id=invocation_id)
    trace_writer.record_provider_result(result, repair_parent=repair_parent)
    filename = f"{stage.lower().replace(':', '_')}-response.json"
    trace_writer.write_json(filename, {"raw_text": result.raw_text})

    return result.raw_text

def _invoke_stage_with_repair(
    provider: "LLMProvider",
    trace_writer: TraceWriter,
    *,
    parent_stage: str,
    prompt: str,
    repair_prompt: str,
    parse_fn: Any,
    invocation_id: str | None = None,
) -> Any:
    """Invoke a stage with one bounded repair attempt."""
    raw_text = _invoke_stage(
        provider,
        trace_writer,
        stage=parent_stage,
        prompt=prompt,
        invocation_id=invocation_id,
    )

    try:
        return parse_fn(raw_text)
    except (ValueError, json.JSONDecodeError, KeyError) as primary_error:
        repair_stage = f"SCHEMA_REPAIR:{parent_stage}"
        repair_text = repair_prompt.replace("<<ERROR>>", str(primary_error))
        repair_invocation_id = str(uuid.uuid4())

        repair_raw = _invoke_stage(
            provider,
            trace_writer,
            stage=repair_stage,
            prompt=repair_text,
            invocation_id=repair_invocation_id,
            repair_parent=parent_stage,
        )
        try:
            return parse_fn(repair_raw)
        except (ValueError, json.JSONDecodeError, KeyError) as repair_error:
            raise ValueError(
                f"Stage {parent_stage} failed after repair: {repair_error}"
            ) from repair_error


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions for invocations and trace refs
# ─────────────────────────────────────────────────────────────────────────────


def _collect_provider_invocation_ids(trace_writer: TraceWriter) -> list[str]:
    """Collect all provider invocation IDs recorded in the trace so far."""
    if trace_writer.current_run_dir is None:
        return []
    invocations_file = trace_writer.current_run_dir / "provider-invocations.json"
    if invocations_file.exists():
        invocations = json.loads(invocations_file.read_text(encoding="utf-8"))
        return [inv["invocation_id"] for inv in invocations if "invocation_id" in inv]
    return []


def _get_relative_trace_ref(trace_writer: TraceWriter, trace_root: Path) -> str:
    """Get trace_ref relative to trace_root (typically run_id)."""
    if trace_writer.current_run_dir is None:
        return ""
    try:
        return trace_writer.current_run_dir.relative_to(trace_root).as_posix()
    except ValueError:
        return trace_writer.current_run_dir.name


# ─────────────────────────────────────────────────────────────────────────────
# Main RIFT Entry Point
# ─────────────────────────────────────────────────────────────────────────────


def run_rift(
    request: PerspectiveRequest,
    *,
    session_store: "SessionStore",
    provider: "LLMProvider",
    trace_root: Path,
) -> ExploreRunResult:
    """Run RIFT exploration.

    Signature is frozen by Wave 1 execution contract.
    """
    if request.mode != "rift":
        raise ValueError(f"rift.run_rift requires mode 'rift', got: {request.mode}")

    # ── Load or create session ──────────────────────────────────────────────
    session_id = request.session_id or str(uuid.uuid4())

    if session_store.exists(session_id):
        session = session_store.load(session_id)
        source = session_store.load_verified_source(session)

        # Verify request.source matches stored session source hash
        request_source_hash = compute_source_hash(request.source)
        if request_source_hash != session.source_hash:
            raise ValueError(
                f"Request source hash ({request_source_hash}) does not match stored session source hash ({session.source_hash})"
            )

        # Verify request.objective matches immutable session.objective
        if request.objective != session.objective:
            raise ValueError(
                f"Request objective ({request.objective!r}) does not match immutable session objective ({session.objective!r})"
            )
    else:
        session = session_store.create(
            session_id=session_id,
            source=request.source,
            objective=request.objective,
        )
        if request.constraint_ledger.entries:
            session.constraint_ledger = ConstraintLedger.from_dict(
                request.constraint_ledger.to_dict()
            )
            session_store.save(session)
        source = request.source

    # ── Setup trace ─────────────────────────────────────────────────────────
    run_id = str(uuid.uuid4())
    trace_writer = TraceWriter(trace_root)
    trace_writer.start_run(run_id=run_id, session_id=session_id)

    # Record request and session-before
    trace_writer.write_json(
        "request.json",
        {
            "source_length": len(source),
            "objective": request.objective,
            "mode": request.mode,
            "candidate_budget": request.candidate_budget,
            "must_not_claim": request.must_not_claim,
        },
    )
    trace_writer.write_json("constraints.json", session.constraint_ledger.to_dict())
    trace_writer.write_json("session-before.json", session.to_dict())

    # ── Load prompt templates ───────────────────────────────────────────────
    generate_prompt_template = prompt_path("rift_generate.md").read_text(
        encoding="utf-8"
    )
    select_prompt_template = prompt_path("rift_select.md").read_text(
        encoding="utf-8"
    )
    repair_generate_template = prompt_path("rift_repair_generate.md").read_text(
        encoding="utf-8"
    )
    repair_select_template = prompt_path("rift_repair_select.md").read_text(
        encoding="utf-8"
    )

    generate_stage = "RIFT_GENERATE"
    select_stage = "RIFT_SELECT"

    generate_prompt = (
        generate_prompt_template.replace("<<SOURCE>>", source)
        .replace("<<OBJECTIVE>>", session.objective)
        .replace("<<CONSTRAINTS>>", _render_constraints(session.constraint_ledger))
        .replace("<<MUST_NOT_CLAIM>>", _render_must_not_claim(request.must_not_claim))
        .replace("<<OPERATOR_HINTS>>", _render_operator_hints())
        .replace("<<CANDIDATE_BUDGET>>", str(request.candidate_budget))
    )

    def parse_generate(text: str) -> tuple[Diagnosis, list[PerspectiveCandidate]]:
        return _parse_rift_generate_response(text, request.candidate_budget)

    diagnosis, candidates = _invoke_stage_with_repair(
        provider,
        trace_writer,
        parent_stage=generate_stage,
        prompt=generate_prompt,
        repair_prompt=repair_generate_template.replace("<<SOURCE>>", source).replace(
            "<<OBJECTIVE>>", session.objective
        ),
        parse_fn=parse_generate,
    )

    # Persist diagnosis and candidates
    trace_writer.write_json("diagnosis.json", diagnosis.to_dict())
    trace_writer.write_json(
        "candidates.json", {"candidates": [c.to_dict() for c in candidates]}
    )

    if not candidates:
        provider_invocations = _collect_provider_invocation_ids(trace_writer)
        relative_trace_ref = _get_relative_trace_ref(trace_writer, trace_root)
        pass_record = PassRecord(
            pass_id=str(uuid.uuid4()),
            mode=request.mode,
            created_at=datetime.now(timezone.utc).isoformat(),
            diagnosis=diagnosis,
            candidates=[],
            selections=[],
            kept_p_ids=[],
            provider_invocation_ids=provider_invocations,
            trace_ref=relative_trace_ref,
        )
        session.passes.append(pass_record)
        session_store.save(session)

        trace_writer.write_json(
            "result.json", {"outcome": "NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS"}
        )
        trace_writer.write_json("session-after.json", session.to_dict())

        return ExploreRunResult(
            run_id=run_id,
            session_id=session_id,
            kept=[],
            selections=[],
            rendered="",
            outcome="NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS",
        )

    # ── Call B: Selection with Donor-Vocabulary Ablation ────────────────────
    select_prompt = (
        select_prompt_template.replace("<<SOURCE>>", source)
        .replace("<<CONSTRAINTS>>", _render_constraints(session.constraint_ledger))
        .replace("<<DIAGNOSIS>>", _render_diagnosis_for_selection(diagnosis))
        .replace("<<EXISTING_PERSPECTIVES>>", _render_existing_perspectives(session))
        .replace("<<CANDIDATES>>", _render_candidates_for_selection(candidates))
    )

    existing_p_ids = set(session.perspectives.keys())
    candidate_ids = {c.candidate_id for c in candidates}

    def parse_select(text: str) -> list[SelectionRecord]:
        raw_selections = _extract_json_array(text)

        errors = validate_selection_structure(
            raw_selections, candidate_ids, existing_p_ids
        )
        if errors:
            raise ValueError("Selection validation errors: " + "; ".join(errors))

        return [selection_record_from_dict(s) for s in raw_selections]

    selections = _invoke_stage_with_repair(
        provider,
        trace_writer,
        parent_stage=select_stage,
        prompt=select_prompt,
        repair_prompt=repair_select_template,
        parse_fn=parse_select,
    )

    # ── Persist selection and validation ────────────────────────────────────
    trace_writer.write_json(
        "selection.json", {"selections": [s.to_dict() for s in selections]}
    )

    validation_issues = validate_selections(candidates, selections, existing_p_ids)
    trace_writer.write_json(
        "validation.json",
        {k: [i.to_dict() for i in v] for k, v in validation_issues.items()},
    )

    if any(validation_issues.values()):
        formatted_issues = [
            f"{cid} [{issue.code}]: {issue.message}"
            for cid, issues in sorted(validation_issues.items())
            for issue in issues
        ]
        raise ValueError("Selection validation failed: " + "; ".join(formatted_issues))

    # ── Register KEEP perspectives ──────────────────────────────────────────
    kept_states, kept_p_ids = register_kept_perspectives(
        candidates, selections, session.next_p_number
    )

    for state in kept_states:
        session.perspectives[state.identity.p_id] = state

    if kept_p_ids:
        last_p = int(kept_p_ids[-1][1:])
        session.next_p_number = last_p + 1

    # ── Persist PassRecord ──────────────────────────────────────────────────
    provider_invocations = _collect_provider_invocation_ids(trace_writer)
    relative_trace_ref = _get_relative_trace_ref(trace_writer, trace_root)

    pass_record = PassRecord(
        pass_id=str(uuid.uuid4()),
        mode=request.mode,
        created_at=datetime.now(timezone.utc).isoformat(),
        diagnosis=diagnosis,
        candidates=candidates,
        selections=selections,
        kept_p_ids=kept_p_ids,
        provider_invocation_ids=provider_invocations,
        trace_ref=relative_trace_ref,
    )
    session.passes.append(pass_record)
    session_store.save(session)

    trace_writer.write_json("session-after.json", session.to_dict())

    # ── Render KEEP perspectives ────────────────────────────────────────────
    candidate_map = {c.candidate_id: c for c in candidates}
    rendered_parts = []
    for state in kept_states:
        candidate = candidate_map.get(state.identity.candidate_id)
        if candidate:
            rendered_parts.append(render_perspective(state, candidate))

    rendered = "\n\n---\n\n".join(rendered_parts)

    # ── Determine outcome ───────────────────────────────────────────────────
    outcome = "OK" if kept_states else "NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS"

    trace_writer.write_json(
        "result.json",
        {
            "outcome": outcome,
            "kept_count": len(kept_states),
            "kept_p_ids": kept_p_ids,
        },
    )

    return ExploreRunResult(
        run_id=run_id,
        session_id=session_id,
        kept=kept_states,
        selections=selections,
        rendered=rendered,
        outcome=outcome,
    )
