"""CLI for Beerlight Runtime v1.
 
Entrypoint: python -m beerlight.runtime
 
Commands:
    run <input_file> --task "<task>" [options]     Direct document run
    run-json <request.json>                        JSON external invocation
    inspect <run_id> [--show-pool] [--show-judge] [--show-errors]
               [--calibrate]
    session create <input_file> [session_dir]      Create a new session
    session run <session_dir> [--task ...] [--mode ...]
    session update <session_dir> <text | --file ...>
    session event <session_dir> <run_id> <candidate_id> <type> [--reason]
    session outcomes <session_dir>
    session show <session_dir>
    trajectory show <session_dir>
    trajectory apply <session_dir> [--dry-run]
    handoff <session_dir> --output <dir> [--yes] [--include-traces]
 
No console script (Amendment 2) — use `python -m beerlight.runtime`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .contracts import RunRequest, RunResponse, ExitCode
from .service import run, run_json_file
from .session import (
    create_session,
    read_current,
    update_current,
    read_trajectory,
    is_valid_session,
    get_session_metadata,
    list_session_runs,
    resolve_run_path,
)
from .trajectory import (
    read_trajectory_file,
    write_trajectory_file,
    Trajectory,
    TRAJECTORY_HELP,
)
from .inspect import inspect_run, format_inspect_output, calibration_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prism",
        description="Beerlight Runtime v1 — productized angle-finder.",
    )
    sub = parser.add_subparsers(dest="command")

    # --- run ---
    run_p = sub.add_parser("run", help="Run Beerlight on an input file")
    run_p.add_argument("input_file", help="Path to the input text file")
    run_p.add_argument("--task", required=True,
                       help="Task description for generation")
    run_p.add_argument("--mode", choices=("normal", "360"), default="normal")
    run_p.add_argument("--trajectory", default=None,
                       help="Path to trajectory.md")
    run_p.add_argument("--context-mode", choices=("trajectory", "full"),
                       default="trajectory")
    run_p.add_argument("--trace-level", choices=("compact", "full"),
                       default="compact")
    run_p.add_argument("--privacy", choices=("private", "project", "shareable"),
                       default="private")
    run_p.add_argument("--session", dest="session_dir", default=None,
                       help="Session directory for persistence")
    run_p.add_argument("--output-dir", default="beerlight-runs",
                       help="Output directory for traces")

    # --- run-json ---
    json_p = sub.add_parser("run-json",
                            help="Run Beerlight from a JSON request file")
    json_p.add_argument("request_file", help="Path to JSON request file")

    # --- inspect ---
    insp_p = sub.add_parser("inspect", help="Inspect a run trace")
    insp_p.add_argument("run_id", help="Run ID or trace directory path")
    insp_p.add_argument("--show-pool", action="store_true",
                        help="Show full candidate pool")
    insp_p.add_argument("--show-judge", action="store_true",
                        help="Show judge decisions")
    insp_p.add_argument("--show-errors", action="store_true",
                        help="Show raw invalid outputs and errors")
    insp_p.add_argument("--calibrate", action="store_true",
                        help="Show 'strong dropped' candidates (potential false negatives)")
    insp_p.add_argument("--session", dest="session_dir", default=None,
                        help="Session directory for trace resolution (R1)")

    # --- session ---
    sess_p = sub.add_parser("session", help="Session management")
    sess_sub = sess_p.add_subparsers(dest="session_command")

    sess_create = sess_sub.add_parser("create", help="Create a new session")
    sess_create.add_argument("input_file", help="Original document path")
    sess_create.add_argument("session_dir", nargs="?",
                             help="Session directory (default: auto-generated)")

    sess_run = sess_sub.add_parser("run", help="Run on current document")
    sess_run.add_argument("session_dir", help="Session directory")
    sess_run.add_argument("--task", required=True, help="Task description")
    sess_run.add_argument("--mode", choices=("normal", "360"),
                          default="normal")

    sess_update = sess_sub.add_parser("update",
                                      help="Update current document in session")
    sess_update.add_argument("session_dir", help="Session directory")
    sess_update.add_argument("text", nargs="?", help="New text (inline)")
    sess_update.add_argument("--file", dest="file_path",
                             help="Read new text from file")

    sess_show = sess_sub.add_parser("show", help="Show session info")
    sess_show.add_argument("session_dir", help="Session directory")

    sess_event = sess_sub.add_parser("event", help="Write an outcome event")
    sess_event.add_argument("session_dir", help="Session directory")
    sess_event.add_argument("run_id", help="Run ID")
    sess_event.add_argument("candidate_id", help="Candidate ID")
    sess_event.add_argument("type", help="Event type (shown, selected, applied, retained, reverted, rejected, etc.)")
    sess_event.add_argument("--reason", default="", help="Optional reason for the event")

    sess_outcomes = sess_sub.add_parser("outcomes", help="Show session outcomes derived from events")
    sess_outcomes.add_argument("session_dir", help="Session directory")

    # --- trajectory ---
    traj_p = sub.add_parser("trajectory", help="Trajectory management")
    traj_sub = traj_p.add_subparsers(dest="trajectory_command")

    traj_show = traj_sub.add_parser("show", help="Show trajectory")
    traj_show.add_argument("session_dir", help="Session directory")
    traj_show.add_argument("--raw", action="store_true",
                           help="Show raw markdown file")

    traj_apply = traj_sub.add_parser("apply",
                                     help="Apply proposed trajectory update")
    traj_apply.add_argument("session_dir", help="Session directory")
    traj_apply.add_argument("--dry-run", action="store_true",
                            help="Show what would change without applying")

    traj_help = traj_sub.add_parser("help", help="Show trajectory format help")

    # --- handoff ---
    handoff_p = sub.add_parser("handoff", help="Export session bundle for handoff")
    handoff_p.add_argument("session_dir", help="Session directory")
    handoff_p.add_argument("--output", required=True, help="Output directory for the bundle")
    handoff_p.add_argument("--yes", action="store_true",
                           help="Skip preview confirmation (non-interactive)")
    handoff_p.add_argument("--include-traces", action="store_true",
                           help="Include raw traces in the bundle (opt-in)")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    # --- dispatch ---

    if args.command == "run":
        return _cmd_run(args)

    elif args.command == "run-json":
        return _cmd_run_json(args)

    elif args.command == "inspect":
        return _cmd_inspect(args)

    elif args.command == "session":
        if args.session_command is None:
            sess_p.print_help()
            return 1
        if args.session_command == "create":
            return _cmd_session_create(args)
        elif args.session_command == "run":
            return _cmd_session_run(args)
        elif args.session_command == "update":
            return _cmd_session_update(args)
        elif args.session_command == "show":
            return _cmd_session_show(args)
        elif args.session_command == "event":
            return _cmd_session_event(args)
        elif args.session_command == "outcomes":
            return _cmd_session_outcomes(args)
        return 1

    elif args.command == "trajectory":
        if args.trajectory_command is None:
            traj_p.print_help()
            return 1
        if args.trajectory_command == "show":
            return _cmd_trajectory_show(args)
        elif args.trajectory_command == "apply":
            return _cmd_trajectory_apply(args)
        elif args.trajectory_command == "help":
            print(TRAJECTORY_HELP)
            return 0
        return 1

    elif args.command == "handoff":
        return _cmd_handoff(args)

    return 0


# --- command implementations ---

def _cmd_run(args) -> int:
    """Handle `run` command."""
    input_file = Path(args.input_file)
    if not input_file.exists():
        print(f"Error: input file not found: {args.input_file}",
              file=sys.stderr)
        return ExitCode.INPUT_NOT_FOUND

    try:
        document = input_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        return ExitCode.INPUT_NOT_FOUND

    trajectory = None
    if args.trajectory:
        traj_path = Path(args.trajectory)
        if traj_path.exists():
            try:
                trajectory = traj_path.read_text(encoding="utf-8")
            except Exception as e:
                print(f"Error reading trajectory: {e}", file=sys.stderr)
                return ExitCode.INVALID_REQUEST

    resp = run(
        document=document,
        task=args.task,
        mode=args.mode,
        trajectory=trajectory,
        context_mode=args.context_mode,
        trace_level=args.trace_level,
        privacy=args.privacy,
        session_dir=args.session_dir,
        output_dir=args.output_dir,
    )

    if resp.warnings:
        for w in resp.warnings:
            print(f"Warning: {w}", file=sys.stderr)

    if resp.status == "error":
        print(f"Error: {resp.error}", file=sys.stderr)
        return ExitCode.GENERATOR_FAILED

    if resp.status == "no_useful_output":
        print("(no useful output)", file=sys.stderr)

    return ExitCode.OK


def _cmd_run_json(args) -> int:
    """Handle `run-json` command."""
    resp, exit_code = run_json_file(args.request_file)
    print(resp.to_json())
    return exit_code.value


def _cmd_inspect(args) -> int:
    """Handle `inspect` command."""
    run_id = args.run_id

    # Accept either a run ID or a direct path
    trace_dir = Path(run_id)

    # R1: If --session is provided, resolve through session.json
    if args.session_dir and not trace_dir.exists():
        from .session import resolve_run_path
        resolved = resolve_run_path(args.session_dir, run_id)
        if resolved:
            trace_dir = Path(resolved)

    # Legacy fallback: look in beerlight-runs/
    if not trace_dir.exists():
        trace_dir = Path("beerlight-runs") / run_id

    if not trace_dir.exists():
        print(f"Error: trace not found: {run_id}", file=sys.stderr)
        return 1

    # Calibration mode: show "strong dropped" candidates (potential false negatives)
    if args.calibrate:
        report = calibration_report(str(trace_dir))
        print(report)
        return 0

    result = inspect_run(
        str(trace_dir),
        show_pool=args.show_pool,
        show_judge=args.show_judge,
        show_errors=args.show_errors,
    )
    print(format_inspect_output(result))
    return 0


def _cmd_session_create(args) -> int:
    """Handle `session create` command."""
    session_dir = args.session_dir
    if not session_dir:
        import uuid
        session_dir = f"beerlight-sessions/{uuid.uuid4().hex[:12]}"

    try:
        meta = create_session(args.input_file, session_dir)
        print(f"Session created: {session_dir}")
        print(f"  session_id: {meta['session_id']}")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error creating session: {e}", file=sys.stderr)
        return 1
    return 0


def _cmd_session_run(args) -> int:
    """Handle `session run` command."""
    if not is_valid_session(args.session_dir):
        print(f"Error: not a valid session: {args.session_dir}",
              file=sys.stderr)
        return 1

    try:
        document = read_current(args.session_dir)
    except Exception as e:
        print(f"Error reading session: {e}", file=sys.stderr)
        return 1

    trajectory = read_trajectory(args.session_dir)

    # R1 repair: session run writes traces into session/runs/<run_id>/
    output_dir = str(Path(args.session_dir) / "runs")
    resp = run(
        document=document,
        task=args.task,
        mode=args.mode,
        trajectory=trajectory or None,
        session_dir=args.session_dir,
        output_dir=output_dir,
    )

    if resp.status == "error":
        print(f"Error: {resp.error}", file=sys.stderr)
        return ExitCode.GENERATOR_FAILED

    return ExitCode.OK


def _cmd_session_update(args) -> int:
    """Handle `session update` command."""
    if args.file_path:
        try:
            new_text = Path(args.file_path).read_text(encoding="utf-8")
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            return 1
    elif args.text:
        new_text = args.text
    else:
        print("Error: provide --file or inline text", file=sys.stderr)
        return 1

    try:
        update_current(args.session_dir, new_text)
        print(f"Session updated: {args.session_dir}")
    except Exception as e:
        print(f"Error updating session: {e}", file=sys.stderr)
        return 1
    return 0


def _cmd_session_show(args) -> int:
    """Handle `session show` command."""
    try:
        meta = get_session_metadata(args.session_dir)
        current = read_current(args.session_dir)
        traj = read_trajectory(args.session_dir)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Session: {args.session_dir}")
    print(f"  ID: {meta.get('session_id', '?')}")
    print(f"  Created: {meta.get('created_at', '?')}")
    print(f"  Runs: {len(meta.get('runs', []))}")
    print(f"  Current document: {len(current)} chars")
    print(f"  Trajectory: {'present' if traj else 'empty'}")
    return 0


def _cmd_trajectory_show(args) -> int:
    """Handle `trajectory show` command."""
    try:
        if args.raw:
            text = read_trajectory(args.session_dir)
            print(text if text else "(empty)")
        else:
            traj_path = Path(args.session_dir) / "trajectory.md"
            traj = read_trajectory_file(str(traj_path))
            print(traj.to_markdown())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


def _cmd_trajectory_apply(args) -> int:
    """Handle `trajectory apply` command."""
    traj_path = Path(args.session_dir) / "trajectory.md"
    try:
        traj = read_trajectory_file(str(traj_path))
    except Exception as e:
        print(f"Error reading trajectory: {e}", file=sys.stderr)
        return 1

    if traj.proposed is None:
        print("No proposed update to apply.")
        return 0

    if args.dry_run:
        print("Would apply:")
        print(f"  explored: {traj.proposed.explored}")
        print(f"  shown: {traj.proposed.shown}")
        print(f"  open questions: {traj.proposed.open_questions}")
        return 0

    traj.apply_proposed()
    try:
        write_trajectory_file(traj, str(traj_path))
        print("Proposed update applied.")
    except Exception as e:
        print(f"Error writing trajectory: {e}", file=sys.stderr)
        return 1
    return 0


def _cmd_session_event(args) -> int:
    """Handle `session event` command — write an outcome event."""
    from .events import write_event

    if not is_valid_session(args.session_dir):
        print(f"Error: not a valid session: {args.session_dir}",
              file=sys.stderr)
        return 1

    try:
        event = write_event(
            session_dir=args.session_dir,
            run_id=args.run_id,
            candidate_id=args.candidate_id,
            event_type=args.type,
            reason=args.reason,
        )
        print(json.dumps(event, indent=2, ensure_ascii=False))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error writing event: {e}", file=sys.stderr)
        return 1
    return 0


def _cmd_session_outcomes(args) -> int:
    """Handle `session outcomes` command — show derived outcomes table."""
    from .outcomes import derive_outcomes, format_outcomes_table

    if not is_valid_session(args.session_dir):
        print(f"Error: not a valid session: {args.session_dir}",
              file=sys.stderr)
        return 1

    try:
        outcomes = derive_outcomes(args.session_dir)
        print(format_outcomes_table(outcomes))
    except Exception as e:
        print(f"Error computing outcomes: {e}", file=sys.stderr)
        return 1
    return 0


def _cmd_handoff(args) -> int:
    """Handle `handoff` command — export session bundle for handoff."""
    import shutil
    from datetime import datetime, timezone
    from .outcomes import derive_outcomes, build_outcomes_json

    session_dir = Path(args.session_dir)
    if not is_valid_session(str(session_dir)):
        print(f"Error: not a valid session: {args.session_dir}",
              file=sys.stderr)
        return 1

    output_dir = Path(args.output)
    bundle_files: dict[str, str] = {}

    # Source files to include
    current_path = session_dir / "current.md"
    trajectory_path = session_dir / "trajectory.md"
    session_json_path = session_dir / "session.json"

    if current_path.exists():
        bundle_files["current.md"] = str(current_path)
    if trajectory_path.exists():
        bundle_files["trajectory.md"] = str(trajectory_path)
    if session_json_path.exists():
        bundle_files["session.json"] = str(session_json_path)

    # Outcomes JSON (from events)
    try:
        outcomes = derive_outcomes(str(session_dir))
        outcomes_json = build_outcomes_json(outcomes)
    except Exception as e:
        print(f"Warning: could not derive outcomes: {e}", file=sys.stderr)
        outcomes_json = {"error": str(e)}

    # Raw traces (opt-in only) — R2 repair: copy to traces/ not runs/
    if args.include_traces:
        # Resolve each registered run via resolve_run_path, which handles
        # both the session/runs/ layout and the legacy flat
        # beerlight-runs/<run_id>/ fallback.
        run_ids: list[str] = []
        try:
            meta = get_session_metadata(str(session_dir))
            for entry in meta.get("runs", []):
                run_ids.append(entry["run_id"] if isinstance(entry, dict) else entry)
        except Exception:
            run_ids = []
        resolved_dirs: list[Path] = []
        for rid in run_ids:
            rpath = resolve_run_path(str(session_dir), rid)
            if rpath and Path(rpath).is_dir():
                resolved_dirs.append(Path(rpath))
        if not resolved_dirs:
            # Fallback: scan session_dir/runs directly (unregistered runs).
            runs_dir = session_dir / "runs"
            if runs_dir.exists():
                resolved_dirs = [d for d in sorted(runs_dir.iterdir()) if d.is_dir()]
        for run_dir in resolved_dirs:
            for fpath in sorted(run_dir.iterdir()):
                if fpath.is_file():
                    # Normalize to relative path under traces/
                    rel = f"traces/{run_dir.name}/{fpath.name}"
                    bundle_files[rel] = str(fpath)

    # --- Preview ---
    print("Handoff bundle preview:")
    print(f"  Output directory: {output_dir}")
    print(f"  Files to include ({len(bundle_files)}):")
    for rel_path in sorted(bundle_files.keys()):
        print(f"    {rel_path}")
    print(f"  outcomes.json: {'yes' if outcomes_json else 'no'}")
    print(f"  Include raw traces: {'yes' if args.include_traces else 'no (use --include-traces to opt in)'}")
    print()

    # Require confirmation
    if not args.yes:
        try:
            response = input("Proceed with export? [y/N] ").strip().lower()
        except EOFError:
            response = "n"
        if response not in ("y", "yes"):
            print("Export cancelled.")
            return 0

    # --- Write bundle ---
    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        # Copy files with normalized (relative) paths
        for rel_path, src_path in bundle_files.items():
            dest_path = output_dir / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dest_path)

        # Write outcomes.json
        out_json_path = output_dir / "outcomes.json"
        out_json_path.write_text(
            json.dumps(outcomes_json, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Write handoff metadata
        meta = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "session_dir": str(session_dir),
            "include_traces": args.include_traces,
            "files": sorted(bundle_files.keys()),
        }
        (output_dir / "handoff.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print(f"Bundle exported to: {output_dir}")
    except Exception as e:
        print(f"Error writing bundle: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
