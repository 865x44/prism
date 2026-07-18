"""Public Runtime API for Prism.

Provides:
    prism.runtime.run(document=..., task=..., mode="normal", ...)
    prism.runtime.run_json(request: RunRequest) -> RunResponse

Orchestrates: input reading → generate → judge → resolve → trace → session.
All core logic delegates to the validated slice (wrap over move).

Graceful degradation:
    - No trajectory: normal run works
    - Judge fails: preserve generator pool, return degraded status
    - Trace write fails: return cards + warning
    - NO_USEFUL_OUTPUT: normal status, not exception
    - Full-history unavailable: fail clearly or use trajectory
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import RunRequest, RunResponse, ExitCode
from .models import (
    TraceMetadata,
    PrivacyLevel,
    TraceLevel,
    RunMode,
    ContextMode,
    Card,
)
from .provider import get_generator_model, get_judge_model
from .generator import build_generator_prompt, generate_with_repair
from .judge import build_judge_prompt, judge_with_repair, judge_abstention
from .trace import (
    write_trace_v1,
    read_trace_metadata,
    read_trace_judge,
    compute_input_hash,
)
from .session import (
    read_current,
    read_trajectory,
    register_run,
    apply_trajectory_update,
)

MAX_CARDS = 3  # preserved invariant


def _format_cards(cards: list[dict]) -> str:
    """Format cards as user-facing markdown (reuses slice format)."""
    if not cards:
        return ""

    lines = []
    for card in cards:
        title = card.get("title", "Без названия")
        shift = card.get("shift", "")
        basis = card.get("basis", "")
        action = card.get("action", "")
        boundary = card.get("boundary", "")

        lines.append(f"## {title}")
        lines.append("")
        lines.append("**Сдвиг**")
        lines.append(shift)
        lines.append("")
        lines.append("**На чём держится**")
        lines.append(basis)
        lines.append("")
        lines.append("**Что с этим сделать**")
        lines.append(action)
        lines.append("")
        lines.append("**Граница**")
        lines.append(boundary)
        lines.append("")

    return "\n".join(lines)


def _format_trajectory_update_block(
    run_id: str,
    traj_update: dict | None,
    cards: list[dict],
) -> str:
    """Build a trajectory update markdown block."""
    if traj_update is None:
        traj_update = {}

    explored = traj_update.get("explored", [])
    shown = traj_update.get("shown", [])
    open_q = traj_update.get("open_questions", [])

    # If no trajectory update from judge, derive from cards
    if not shown and cards:
        shown = [c.get("title", "") for c in cards if c.get("title")]

    lines = [f"## Run {run_id}", ""]
    if explored:
        lines.append("Исследовано:")
        for item in explored:
            lines.append(f"- {item}")
        lines.append("")
    if shown:
        lines.append("Показано пользователю:")
        for item in shown:
            lines.append(f"- {item}")
        lines.append("")
    if open_q:
        lines.append("Новые открытые вопросы:")
        for item in open_q:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines)


def run(
    document: str,
    task: str,
    mode: str = "normal",
    profile: str = "practical",
    trajectory: str | None = None,
    context_mode: str = "trajectory",
    trace_level: str = "compact",
    trailer: str | None = None,
    privacy: str = "private",
    session_dir: str | None = None,
    output_dir: str = "prism-runs",
) -> RunResponse:
    """Run Prism on a document.

    Args:
        document: The input text to analyze.
        task: What to find — "найти сильные направления для развития" etc.
        mode: "normal" or "360".
        profile: "practical" or "rift".
        trajectory: Optional accumulated trajectory text.
        context_mode: "trajectory" or "full".
        trace_level: "compact" or "full".
        trailer: Unused in Wave 1 (reserved for future context injection).
        privacy: "private", "project", or "shareable".
        session_dir: Optional session directory for trajectory persistence.
        output_dir: Base output directory for traces.

    Returns:
        RunResponse with status, cards, trace_dir, etc.
    """
    t_start = time.time()
    run_id = uuid.uuid4().hex[:12]
    run_dir = Path(output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    generator_model = get_generator_model()
    judge_model = get_judge_model()
    warnings: list[str] = []
    gen_raw = None
    judge_raw = None
    gen_prompt = None
    judge_prompt = None
    gen_repair_prompt = None
    judge_repair_prompt = None
    retry_count = 0
    token_usage_breakdown: dict = {}
    total_chars = 0

    # --- context resolution ---
    effective_trajectory = trajectory
    if context_mode == "full" and session_dir:
        try:
            effective_trajectory = read_trajectory(session_dir) or trajectory
        except Exception:
            if not trajectory:
                warnings.append("full-history unavailable, using trajectory")
                # No silent fallback: we use trajectory if available,
                # otherwise we proceed without.

    # ---------- generate ----------
    gen_prompt_version = f"360-rift-v0" if mode == "360" and profile == "rift" else \
                         f"generator-rift-v0" if profile == "rift" else \
                         f"360-v1" if mode == "360" else "generator-v1"
    gen_prompt = build_generator_prompt(
        document, task, effective_trajectory, mode, profile,
    )
    candidates, gen_status, gen_raw, repair_prompt = \
        generate_with_repair(gen_prompt, run_dir)

    if repair_prompt is not None:
        gen_repair_prompt = repair_prompt
        retry_count += 1

    # --- token usage: generator ---
    gen_chars = len(gen_prompt or "") + len(gen_raw or "")
    if gen_repair_prompt:
        gen_chars += len(gen_repair_prompt)
    token_usage_breakdown["generator"] = gen_chars // 4
    total_chars += gen_chars

    if gen_status == "error" or candidates is None:
        gen_prompt = gen_prompt  # captured above
        return _build_error_response(
            run_id, output_dir, run_dir,
            generator_model, judge_model, mode,
            "generator_failed",
            warnings,
        )

    candidates_list = candidates if isinstance(candidates, list) else []
    (run_dir / "candidates.json").write_text(
        json.dumps(candidates_list, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ---------- judge ----------
    judge_dict: dict = {}
    traj_update = {}

    if not candidates_list:
        # Generator abstention
        jr = judge_abstention(candidates_list)
        judge_dict = {
            "overall_decision": "no_useful_output",
            "cards": [],
            "judgments": [],
            "abstention_source": "generator",
            "note": "generator returned zero candidates",
        }
    else:
        judge_prompt_version = "judge-rift-v0" if profile == "rift" else "judge-v1"
        judge_prompt = build_judge_prompt(
            document, task,
            json.dumps(candidates_list, indent=2, ensure_ascii=False),
            effective_trajectory,
            profile,
        )
        judge_data, judge_status, judge_raw, j_repair = judge_with_repair(
            judge_prompt, run_dir,
            expected_ids=[c["id"] for c in candidates_list
                          if c.get("id")],
        )

        if j_repair is not None:
            judge_repair_prompt = j_repair
            retry_count += 1

        # --- token usage: judge ---
        judge_chars = len(judge_prompt or "") + len(judge_raw or "")
        if judge_repair_prompt:
            judge_chars += len(judge_repair_prompt)
        token_usage_breakdown["judge"] = judge_chars // 4
        total_chars += judge_chars

        if judge_data is None or judge_status == "error":
            warnings.append("Judge failed after bounded repair. Returning degraded status with original generator pool.")
            judge_dict = {
                "overall_decision": "degraded",
                "cards": [],
                "judgments": [],
                "note": "judge failed to parse or crashed"
            }
        else:
            judge_dict = {
                "overall_decision": judge_data.overall_decision,
                "cards": [c.__dict__ for c in judge_data.cards],
                "judgments": [j.__dict__ for j in judge_data.judgments],
            }
            if judge_data.abstention_source:
                judge_dict["abstention_source"] = judge_data.abstention_source
            if judge_data.trajectory_update:
                judge_dict["trajectory_update"] = judge_data.trajectory_update

            traj_update = judge_data.trajectory_update or {}
        if judge_repair_prompt:
            gen_repair_prompt = gen_repair_prompt  # keep existing gen repair if any

    # ------ resolve output (cap at MAX_CARDS) ------
    overall = judge_dict.get("overall_decision", "useful_output")
    abstention_source = judge_dict.get("abstention_source")

    if overall == "no_useful_output":
        status = "no_useful_output"
        cards_out: list[dict] = []
        abstention_source = abstention_source or "judge"
    elif overall == "degraded":
        status = "degraded"
        cards_out: list[dict] = []
        abstention_source = None
    else:
        status = "ok"
        raw_cards = judge_dict.get("cards", [])
        cards_out = raw_cards[:MAX_CARDS]
        abstention_source = None

    # Write judge.json (full decisions, uncapped)
    (run_dir / "judge.json").write_text(
        json.dumps(judge_dict, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Write output.md
    output_md = _format_cards(cards_out)
    output_md += f"\nRun: {run_id}\n"
    output_md += f"Trace: {run_dir}\n"
    (run_dir / "output.md").write_text(output_md, encoding="utf-8")

    # ---------- request ----------
    request = {
        "input_path": "(inline document)" if session_dir else "(direct)",
        "task": task,
        "mode": mode,
        "profile": profile,
        "context_mode": context_mode,
        "trace_level": trace_level,
    }
    (run_dir / "request.json").write_text(
        json.dumps(request, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ---------- metadata (v1) ----------
    duration = time.time() - t_start
    input_hash = compute_input_hash(document)
    token_usage_estimate = total_chars // 4 if total_chars > 0 else 0
    metadata = TraceMetadata(
        trace_schema_version="1",
        run_id=run_id,
        mode=mode,
        profile=profile,
        generator_prompt_version=gen_prompt_version,
        judge_prompt_version=judge_prompt_version if 'judge_prompt_version' in locals() else "judge-v1",
        generator_model=generator_model,
        judge_model=judge_model,
        judge_family_fallback=True,
        created_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        privacy=PrivacyLevel(privacy),
        trace_level=trace_level,
        token_usage_estimate=token_usage_estimate,
        token_usage_breakdown=token_usage_breakdown,
        duration_sec=round(duration, 2),
        retry_count=retry_count,
        input_hash=input_hash,
        warnings=warnings,
    )
    if abstention_source:
        metadata.abstention_source = abstention_source

    # Write v1 trace
    try:
        write_trace_v1(
            run_dir,
            metadata=metadata,
            request=request,
            candidates=candidates_list,
            judge=judge_dict,
            cards=cards_out,
            input_text=document,
            trajectory=effective_trajectory,
            raw_generator=gen_raw,
            raw_judge=judge_raw,
            gen_prompt=(gen_prompt if trace_level == "full" else None),
            judge_prompt=(judge_prompt if trace_level == "full" else None),
            repair_prompt=(
                gen_repair_prompt or judge_repair_prompt
                if trace_level == "full" else None
            ),
        )
    except Exception as e:
        # Trace write failure: return cards + warning (graceful degradation)
        warnings.append(f"trace_write_failed: {e}")
        # Still write metadata as best-effort
        try:
            (run_dir / "metadata.json").write_text(
                json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ---------- trajectory update ----------
    traj_update_path = None
    if traj_update or cards_out:
        traj_block = _format_trajectory_update_block(
            run_id, traj_update, cards_out,
        )
        (run_dir / "trajectory-update.md").write_text(
            traj_block, encoding="utf-8",
        )

        if session_dir:
            try:
                apply_trajectory_update(session_dir, traj_block)
                traj_update_path = str(
                    Path(session_dir) / "trajectory.md"
                )
            except Exception as e:
                warnings.append(f"trajectory_update_failed: {e}")

    # Register run in session (R1: compute relative path from session_dir)
    if session_dir:
        try:
            # Compute rel_path: run_dir relative to session_dir
            session_path = Path(session_dir).resolve()
            run_dir_resolved = run_dir.resolve()
            try:
                rel_path = str(run_dir_resolved.relative_to(session_path))
            except ValueError:
                # run_dir is not under session_dir (e.g. standalone run --session)
                rel_path = ""
            register_run(session_dir, run_id, rel_path=rel_path)
        except Exception as e:
            warnings.append(f"session_register_failed: {e}")

    # ---------- stdout ----------
    print(output_md)

    return RunResponse(
        status=status,
        run_id=run_id,
        cards=cards_out,
        trace_dir=str(run_dir),
        trajectory_update_path=traj_update_path,
        warnings=warnings,
    )


def run_json(request: RunRequest) -> RunResponse:
    """Execute a Prism run from a machine-readable RunRequest.

    Implements External Contract v0: deterministic exit codes,
    no interactive prompts, machine-readable errors.
    """
    errors = request.validate()
    if errors:
        return RunResponse(
            status="error",
            error="; ".join(errors),
        )

    # Read input file
    try:
        input_path = Path(request.input_path)
        document = input_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return RunResponse(
            status="error",
            error=f"input file not found: {request.input_path}",
        )
    except Exception as e:
        return RunResponse(
            status="error",
            error=f"failed to read input: {e}",
        )

    # Read trajectory if provided
    trajectory = None
    if request.trajectory_path:
        traj_path = Path(request.trajectory_path)
        if traj_path.exists():
            try:
                trajectory = traj_path.read_text(encoding="utf-8")
            except Exception as e:
                return RunResponse(
                    status="error",
                    error=f"failed to read trajectory: {e}",
                )

    return run(
        document=document,
        task=request.task,
        mode=request.mode,
        trajectory=trajectory,
        context_mode=request.context_mode,
        trace_level=request.trace_level,
        output_dir=request.output_dir or "prism-runs",
    )


def run_json_file(request_path: str) -> tuple[RunResponse, ExitCode]:
    """Read a JSON request file and execute it.

    Returns (response, exit_code) for CLI integration.
    """
    try:
        data = json.loads(Path(request_path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return (
            RunResponse(status="error", error=f"file not found: {request_path}"),
            ExitCode.INPUT_NOT_FOUND,
        )
    except json.JSONDecodeError as e:
        return (
            RunResponse(status="error", error=f"invalid JSON: {e}"),
            ExitCode.INVALID_REQUEST,
        )
    except Exception as e:
        return (
            RunResponse(status="error", error=str(e)),
            ExitCode.INTERNAL_ERROR,
        )

    req = RunRequest.from_dict(data)
    errors = req.validate()
    if errors:
        return (
            RunResponse(status="error", error="; ".join(errors)),
            ExitCode.INVALID_REQUEST,
        )

    resp = run_json(req)

    if resp.status == "error":
        return resp, ExitCode.INTERNAL_ERROR
    elif resp.status == "no_useful_output":
        return resp, ExitCode.OK
    elif resp.status == "degraded":
        return resp, ExitCode.DEGRADED
    else:
        return resp, ExitCode.OK


def _build_error_response(
    run_id: str,
    output_dir: str,
    run_dir: Path,
    generator_model: str,
    judge_model: str,
    mode: str,
    error_kind: str,
    warnings: list[str],
) -> RunResponse:
    """Build a RunResponse for generator or judge failure."""
    try:
        request = {
            "error_kind": error_kind,
            "mode": mode,
        }
        (run_dir / "request.json").write_text(
            json.dumps(request, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        meta = {
            "trace_schema_version": "1",
            "run_id": run_id,
            "mode": mode,
            "generator_prompt_version": (
                "360-v1" if mode == "360" else "generator-v1"
            ),
            "judge_prompt_version": "judge-v1",
            "generator_model": generator_model,
            "judge_model": judge_model,
            "judge_family_fallback": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "error_kind": error_kind,
        }
        (run_dir / "metadata.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass

    return RunResponse(
        status="error",
        run_id=run_id,
        trace_dir=str(run_dir),
        warnings=warnings,
        error=error_kind,
    )
