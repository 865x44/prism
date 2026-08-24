"""CLI for Perspective Core v0.

Implements execution contract frozen CLI with dependency injection.
Commands: run, deep, session show, session add-constraint.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

from .models import ConstraintLedger, PerspectiveRequest
from .provider import LLMProvider, make_default_provider
from .session import SessionStore


# ─────────────────────────────────────────────────────────────────────────────
# CLI main entrypoint
# ─────────────────────────────────────────────────────────────────────────────


class _ParserExit(Exception):
    """Internal replacement for argparse's SystemExit.

    Carries the requested status so ``main`` can return it as a plain
    integer exit code instead of leaking ``SystemExit`` to callers.
    """

    def __init__(self, status: int):
        super().__init__(status)
        self.status = status


class _ArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that raises ``_ParserExit`` rather than exiting.

    Console behavior is unchanged: argparse still prints usage and error
    messages to stderr exactly as it renders them by default.
    """

    def exit(self, status: int = 0, message: str | None = None) -> None:
        if message:
            self._print_message(message, sys.stderr)
        raise _ParserExit(status)


def main(
    argv: list[str] | None = None,
    *,
    provider_factory: Callable[[], LLMProvider] = make_default_provider,
) -> int:
    """CLI main entrypoint with provider injection.

    Args:
        argv: Command-line arguments (defaults to sys.argv)
        provider_factory: Factory function to create LLMProvider

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = _ArgumentParser(
        prog="prism-perspective",
        description="Perspective Core v0 CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ─────────────────────────────────────────────────────────────────────────
    # run command
    # ─────────────────────────────────────────────────────────────────────────
    run_parser = subparsers.add_parser("run", help="Run perspective exploration")
    run_parser.add_argument("--source-file", required=True, help="Path to source material")
    run_parser.add_argument("--task", required=True, help="Task/objective")
    run_parser.add_argument(
        "--mode",
        choices=["normal", "rift", "360"],
        default="normal",
        help="Exploration mode",
    )
    run_parser.add_argument("--session", required=True, help="Session ID")
    run_parser.add_argument("--trace-root", type=Path, help="Trace output directory")
    run_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # ─────────────────────────────────────────────────────────────────────────
    # deep command
    # ─────────────────────────────────────────────────────────────────────────
    deep_parser = subparsers.add_parser("deep", help="Run deep analysis")
    deep_parser.add_argument("--session", required=True, help="Session ID")
    deep_parser.add_argument("--p-id", required=True, help="Perspective ID (e.g., P7)")
    deep_parser.add_argument("--trace-root", type=Path, help="Trace output directory")
    deep_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # ─────────────────────────────────────────────────────────────────────────
    # session command
    # ─────────────────────────────────────────────────────────────────────────
    session_parser = subparsers.add_parser("session", help="Session management")
    session_subparsers = session_parser.add_subparsers(dest="session_command", required=True)

    # session show
    show_parser = session_subparsers.add_parser("show", help="Show session details")
    show_parser.add_argument("session_id", help="Session ID to show")

    # session add-constraint
    constraint_parser = session_subparsers.add_parser(
        "add-constraint", help="Add constraint to session"
    )
    constraint_parser.add_argument("session_id", help="Session ID")
    constraint_parser.add_argument("--id", required=True, dest="constraint_id", help="Constraint ID")
    constraint_parser.add_argument("--value", required=True, help="Constraint value")
    constraint_parser.add_argument(
        "--kind",
        choices=["hard", "preference"],
        default="hard",
        help="Constraint kind",
    )
    constraint_parser.add_argument("--turn", help="Provenance turn reference")

    try:
        args = parser.parse_args(argv)
    except _ParserExit as e:
        return e.status

    # ─────────────────────────────────────────────────────────────────────────
    # Execute command
    # ─────────────────────────────────────────────────────────────────────────
    try:
        if args.command == "run":
            return _cmd_run(args, provider_factory)
        elif args.command == "deep":
            return _cmd_deep(args, provider_factory)
        elif args.command == "session":
            return _cmd_session(args)
        else:
            parser.print_help()
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


# ─────────────────────────────────────────────────────────────────────────────
# Command implementations
# ─────────────────────────────────────────────────────────────────────────────


def _cmd_run(args, provider_factory: Callable[[], LLMProvider]) -> int:
    """Execute run command."""
    from . import core

    # Load source
    source_path = Path(args.source_file)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    source_text = source_path.read_text(encoding="utf-8")

    # Setup session store
    session_store = SessionStore()

    # Load or create session
    if session_store.exists(args.session):
        session = session_store.load(args.session)
        # Verify source and objective match
        verified_source = session_store.load_verified_source(session)
        if verified_source != source_text:
            raise RuntimeError(
                "Source material mismatch. Use a new session for different source."
            )
        if session.objective != args.task:
            raise RuntimeError(
                "Objective mismatch. Use a new session for different objective."
            )
    else:
        session = session_store.create(
            session_id=args.session,
            source=source_text,
            objective=args.task,
        )

    # Establish the trace root up front so it exists even when the owner
    # entrypoint raises its permitted Wave 1 not-implemented error.
    trace_root = args.trace_root or Path("traces")
    trace_root.mkdir(parents=True, exist_ok=True)

    # Create request
    request = PerspectiveRequest(
        source=source_text,
        objective=args.task,
        mode=args.mode,
        session_id=args.session,
        constraint_ledger=session.constraint_ledger,
    )

    # Create provider
    provider = provider_factory()

    # Dispatch based on mode
    if args.mode in ("normal", "360"):
        result = core.dispatch_explore(
            request,
            session_store=session_store,
            provider=provider,
            trace_root=trace_root,
        )
    elif args.mode == "rift":
        result = core.dispatch_rift(
            request,
            session_store=session_store,
            provider=provider,
            trace_root=trace_root,
        )
    else:
        raise ValueError(f"Unknown mode: {args.mode}")

    # Output result
    if args.json:
        import json

        output = {
            "outcome": result.outcome,
            "rendered": result.rendered,
            "kept": [
                {
                    "identity": {
                        "p_id": state.identity.p_id,
                        "identity_core": state.identity.identity_core.to_dict(),
                    },
                    "current_version": state.current_version,
                    "epistemics": state.epistemics.to_dict(),
                    "deep_refs": list(state.deep_refs),
                    "terminal_state": state.terminal_state,
                }
                for state in result.kept
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        if result.rendered:
            print(result.rendered)
        else:
            print(result.outcome)

    return 0


def _cmd_deep(args, provider_factory: Callable[[], LLMProvider]) -> int:
    """Execute deep command."""
    from . import core

    # Setup
    session_store = SessionStore()
    trace_root = args.trace_root or Path("traces")
    trace_root.mkdir(parents=True, exist_ok=True)

    # Load session
    session = session_store.load(args.session)

    # Verify P-ID exists
    if args.p_id not in session.perspectives:
        raise ValueError(f"Perspective {args.p_id} not found in session {args.session}")

    # Dispatch
    result = core.dispatch_deep(
        session_id=args.session,
        p_id=args.p_id,
        session_store=session_store,
        provider=provider_factory(),
        trace_root=trace_root,
    )

    # Output
    if args.json:
        import json

        output = {
            "p_id": result.p_id,
            "terminal_state": result.terminal_state,
            "development": result.development.to_dict(),
            "review": result.review.to_dict(),
            "rebuilt_development": (
                result.rebuilt_development.to_dict()
                if result.rebuilt_development
                else None
            ),
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"Perspective: {result.p_id}")
        print(f"Terminal state: {result.terminal_state}")
        if result.rebuilt_development:
            print("Rebuild: yes")

    return 0


def _cmd_session(args) -> int:
    """Execute session command."""
    session_store = SessionStore()

    if args.session_command == "show":
        session = session_store.load(args.session_id)
        source = session_store.load_verified_source(session)

        print(f"Session ID: {session.session_id}")
        print(f"Objective: {session.objective}")
        print(f"Source hash: {session.source_hash}")
        print(f"Next P-number: {session.next_p_number}")
        print(f"Perspectives: {len(session.perspectives)}")
        print(f"Passes: {len(session.passes)}")
        print(f"Deep runs: {len(session.deep_runs)}")
        print(f"Active constraints: {len(session.constraint_ledger.active_entries())}")

        for p_id, state in session.perspectives.items():
            print(f"  {p_id}: {state.identity.identity_core.central_problem}")

    elif args.session_command == "add-constraint":
        session = session_store.load(args.session_id)

        session.constraint_ledger.add(
            constraint_id=args.constraint_id,
            value=args.value,
            kind=args.kind,
            provenance_turn=args.turn,
        )

        session_store.save(session)
        print(f"Added constraint {args.constraint_id} to session {args.session_id}")

    return 0
