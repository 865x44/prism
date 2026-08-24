"""Tests for Perspective Core v0 CLI.

Covers:
- CLI command parsing and routing
- Provider dependency injection
- Session creation and reuse
- Source/objective immutability enforcement
- Constraint management commands
- Error handling and edge cases
"""

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock
import pytest

from prism.perspective_core import (
    ProviderResult,
    ScriptedProvider,
    TransportError,
)
from prism.perspective_core.cli import main


# ─────────────────────────────────────────────────────────────────────────────
# CLI injection and provider factory (requirement 6, 11)
# ─────────────────────────────────────────────────────────────────────────────


def test_cli_accepts_provider_factory():
    """CLI accepts provider_factory parameter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        source_file = Path(tmpdir) / "source.md"
        source_file.write_text("Test source")

        # Create scripted provider
        responses = {
            "EXPLORE_GENERATE": [
                ProviderResult("inv_1", "EXPLORE_GENERATE", '{"candidates": []}', "test", "scripted", 100, 0),
            ],
            "EXPLORE_SELECT": [
                ProviderResult("inv_2", "EXPLORE_SELECT", '{"selections": []}', "test", "scripted", 100, 0),
            ],
        }

        provider = ScriptedProvider(responses)

        def factory():
            return provider

        # Should not raise (even if explore raises NotImplementedError)
        exit_code = main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Test task",
                "--session", str(session_dir),
                "--mode", "normal",
            ],
            provider_factory=factory,
        )

        # Expected to fail due to stub
        assert exit_code != 0


def test_cli_provider_factory_injection():
    """CLI uses injected provider factory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        source_file = Path(tmpdir) / "source.md"
        source_file.write_text("Test source")

        factory_called = []

        def factory():
            factory_called.append(True)
            responses = {
                "EXPLORE_GENERATE": [
                    ProviderResult("inv_1", "EXPLORE_GENERATE", "{}", "test", "scripted", 100, 0),
                ],
            }
            return ScriptedProvider(responses)

        # Should call factory
        main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Test task",
                "--session", str(session_dir),
            ],
            provider_factory=factory,
        )

        assert len(factory_called) == 1


# ─────────────────────────────────────────────────────────────────────────────
# CLI command parsing (requirement 9)
# ─────────────────────────────────────────────────────────────────────────────


def test_cli_run_command_parsing():
    """CLI parses run command with required arguments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        source_file = Path(tmpdir) / "source.md"
        source_file.write_text("Test source")

        # Missing required argument should fail
        exit_code = main(
            ["run", "--source-file", str(source_file)],  # Missing --task and --session
            provider_factory=lambda: Mock(),
        )
        assert exit_code != 0


def test_cli_deep_command_parsing():
    """CLI parses deep command with required arguments."""
    exit_code = main(
        ["deep"],  # Missing required arguments
        provider_factory=lambda: Mock(),
    )
    assert exit_code != 0


def test_cli_session_show_command():
    """CLI parses session show command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"

        exit_code = main(
            ["session", "show", str(session_dir)],
            provider_factory=lambda: Mock(),
        )

        # Should fail gracefully (session doesn't exist)
        assert exit_code != 0


def test_cli_session_add_constraint_command():
    """CLI parses session add-constraint command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"

        exit_code = main(
            [
                "session",
                "add-constraint",
                str(session_dir),
                "--id", "c1",
                "--value", "Test constraint",
            ],
            provider_factory=lambda: Mock(),
        )

        # Should fail gracefully (session doesn't exist)
        assert exit_code != 0


# ─────────────────────────────────────────────────────────────────────────────
# Session creation and reuse (requirement 10)
# ─────────────────────────────────────────────────────────────────────────────


def test_cli_creates_session_on_first_run():
    """CLI creates session directory on first run."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        source_file = Path(tmpdir) / "source.md"
        source_file.write_text("Test source")

        responses = {
            "EXPLORE_GENERATE": [
                ProviderResult("inv_1", "EXPLORE_GENERATE", '{"candidates": []}', "test", "scripted", 100, 0),
            ],
            "EXPLORE_SELECT": [
                ProviderResult("inv_2", "EXPLORE_SELECT", '{"selections": []}', "test", "scripted", 100, 0),
            ],
        }

        provider = ScriptedProvider(responses)

        # First run should create session
        main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Test task",
                "--session", str(session_dir),
            ],
            provider_factory=lambda: provider,
        )

        # Session directory should exist
        assert session_dir.exists()
        assert (session_dir / "session.json").exists()
        assert (session_dir / "source.md").exists()


def test_cli_reuses_existing_session():
    """CLI reuses existing session if source and objective match."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        source_file = Path(tmpdir) / "source.md"
        source_file.write_text("Test source")

        responses = {
            "EXPLORE_GENERATE": [
                ProviderResult("inv_1", "EXPLORE_GENERATE", '{"candidates": []}', "test", "scripted", 100, 0),
            ],
            "EXPLORE_SELECT": [
                ProviderResult("inv_2", "EXPLORE_SELECT", '{"selections": []}', "test", "scripted", 100, 0),
            ],
        }

        # First run
        main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Test task",
                "--session", str(session_dir),
            ],
            provider_factory=lambda: ScriptedProvider(responses),
        )

        # Second run with same source
        main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Test task",
                "--session", str(session_dir),
            ],
            provider_factory=lambda: ScriptedProvider(responses),
        )

        # Should succeed (same session reused)
        assert session_dir.exists()


def test_cli_fails_on_source_mismatch():
    """CLI fails when source changes for existing session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        source_file = Path(tmpdir) / "source.md"
        source_file.write_text("Original source")

        responses = {
            "EXPLORE_GENERATE": [
                ProviderResult("inv_1", "EXPLORE_GENERATE", '{"candidates": []}', "test", "scripted", 100, 0),
            ],
            "EXPLORE_SELECT": [
                ProviderResult("inv_2", "EXPLORE_SELECT", '{"selections": []}', "test", "scripted", 100, 0),
            ],
        }

        # First run
        main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Test task",
                "--session", str(session_dir),
            ],
            provider_factory=lambda: ScriptedProvider(responses),
        )

        # Change source
        source_file.write_text("Changed source")

        # Second run should fail
        exit_code = main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Test task",
                "--session", str(session_dir),
            ],
            provider_factory=lambda: ScriptedProvider(responses),
        )

        assert exit_code != 0


def test_cli_fails_on_objective_mismatch():
    """CLI fails when objective changes for existing session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        source_file = Path(tmpdir) / "source.md"
        source_file.write_text("Test source")

        responses = {
            "EXPLORE_GENERATE": [
                ProviderResult("inv_1", "EXPLORE_GENERATE", '{"candidates": []}', "test", "scripted", 100, 0),
            ],
            "EXPLORE_SELECT": [
                ProviderResult("inv_2", "EXPLORE_SELECT", '{"selections": []}', "test", "scripted", 100, 0),
            ],
        }

        # First run with objective
        main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Task 1",
                "--session", str(session_dir),
            ],
            provider_factory=lambda: ScriptedProvider(responses),
        )

        # Second run with different objective
        exit_code = main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Task 2",
                "--session", str(session_dir),
            ],
            provider_factory=lambda: ScriptedProvider(responses),
        )

        assert exit_code != 0


# ─────────────────────────────────────────────────────────────────────────────
# Constraint management (requirement 9)
# ─────────────────────────────────────────────────────────────────────────────


def test_cli_session_add_constraint():
    """CLI adds constraint to session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        source_file = Path(tmpdir) / "source.md"
        source_file.write_text("Test source")

        responses = {
            "EXPLORE_GENERATE": [
                ProviderResult("inv_1", "EXPLORE_GENERATE", '{"candidates": []}', "test", "scripted", 100, 0),
            ],
            "EXPLORE_SELECT": [
                ProviderResult("inv_2", "EXPLORE_SELECT", '{"selections": []}', "test", "scripted", 100, 0),
            ],
        }

        # Create session
        main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Test task",
                "--session", str(session_dir),
            ],
            provider_factory=lambda: ScriptedProvider(responses),
        )

        # Add constraint
        exit_code = main(
            [
                "session",
                "add-constraint",
                str(session_dir),
                "--id", "c1",
                "--value", "Test constraint",
            ],
            provider_factory=lambda: Mock(),
        )

        assert exit_code == 0

        # Verify constraint added
        session_file = session_dir / "session.json"
        session_data = json.loads(session_file.read_text())
        assert len(session_data["constraint_ledger"]["entries"]) == 1
        assert session_data["constraint_ledger"]["entries"][0]["constraint_id"] == "c1"


def test_cli_session_show():
    """CLI shows session information."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        source_file = Path(tmpdir) / "source.md"
        source_file.write_text("Test source")

        responses = {
            "EXPLORE_GENERATE": [
                ProviderResult("inv_1", "EXPLORE_GENERATE", '{"candidates": []}', "test", "scripted", 100, 0),
            ],
            "EXPLORE_SELECT": [
                ProviderResult("inv_2", "EXPLORE_SELECT", '{"selections": []}', "test", "scripted", 100, 0),
            ],
        }

        # Create session
        main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Test task",
                "--session", str(session_dir),
            ],
            provider_factory=lambda: ScriptedProvider(responses),
        )

        # Show session
        exit_code = main(
            ["session", "show", str(session_dir)],
            provider_factory=lambda: Mock(),
        )

        assert exit_code == 0


# ─────────────────────────────────────────────────────────────────────────────
# Error handling
# ─────────────────────────────────────────────────────────────────────────────


def test_cli_missing_source_file():
    """CLI fails gracefully when source file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        source_file = Path(tmpdir) / "nonexistent.md"

        exit_code = main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Test task",
                "--session", str(session_dir),
            ],
            provider_factory=lambda: Mock(),
        )

        assert exit_code != 0


def test_cli_provider_transport_error():
    """CLI handles provider transport errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        source_file = Path(tmpdir) / "source.md"
        source_file.write_text("Test source")

        class FailingProvider:
            def complete(self, prompt, *, stage, invocation_id):
                raise TransportError("Simulated transport failure")

        exit_code = main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Test task",
                "--session", str(session_dir),
            ],
            provider_factory=lambda: FailingProvider(),
        )

        assert exit_code != 0


def test_cli_invalid_mode():
    """CLI fails on invalid mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        source_file = Path(tmpdir) / "source.md"
        source_file.write_text("Test source")

        exit_code = main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Test task",
                "--session", str(session_dir),
                "--mode", "invalid",
            ],
            provider_factory=lambda: Mock(),
        )

        assert exit_code != 0


# ─────────────────────────────────────────────────────────────────────────────
# Deep command (requirement 9)
# ─────────────────────────────────────────────────────────────────────────────


def test_cli_deep_command_requires_session():
    """CLI deep command requires existing session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "nonexistent_session"

        exit_code = main(
            ["deep", "--session", str(session_dir), "--p-id", "P1"],
            provider_factory=lambda: Mock(),
        )

        assert exit_code != 0


def test_cli_deep_command_requires_p_id():
    """CLI deep command requires P-ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        source_file = Path(tmpdir) / "source.md"
        source_file.write_text("Test source")

        responses = {
            "EXPLORE_GENERATE": [
                ProviderResult("inv_1", "EXPLORE_GENERATE", '{"candidates": []}', "test", "scripted", 100, 0),
            ],
            "EXPLORE_SELECT": [
                ProviderResult("inv_2", "EXPLORE_SELECT", '{"selections": []}', "test", "scripted", 100, 0),
            ],
        }

        # Create session
        main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Test task",
                "--session", str(session_dir),
            ],
            provider_factory=lambda: ScriptedProvider(responses),
        )

        # Deep without P-ID should fail
        exit_code = main(
            ["deep", "--session", str(session_dir)],
            provider_factory=lambda: Mock(),
        )

        assert exit_code != 0


# ─────────────────────────────────────────────────────────────────────────────
# Trace output (requirement 8)
# ─────────────────────────────────────────────────────────────────────────────


def test_cli_creates_trace_directory():
    """CLI creates trace directory for runs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        trace_dir = Path(tmpdir) / "traces"
        source_file = Path(tmpdir) / "source.md"
        source_file.write_text("Test source")

        responses = {
            "EXPLORE_GENERATE": [
                ProviderResult("inv_1", "EXPLORE_GENERATE", '{"candidates": []}', "test", "scripted", 100, 0),
            ],
            "EXPLORE_SELECT": [
                ProviderResult("inv_2", "EXPLORE_SELECT", '{"selections": []}', "test", "scripted", 100, 0),
            ],
        }

        # Run with trace root
        main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Test task",
                "--session", str(session_dir),
                "--trace-root", str(trace_dir),
            ],
            provider_factory=lambda: ScriptedProvider(responses),
        )

        # Trace root should exist
        assert trace_dir.exists()


# ─────────────────────────────────────────────────────────────────────────────
# Provider injection after NORMAL implementation
# ─────────────────────────────────────────────────────────────────────────────


def test_cli_uses_only_the_injected_provider():
    """The real NORMAL CLI path executes the injected provider, not the default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = Path(tmpdir) / "test_session"
        source_file = Path(tmpdir) / "source.md"
        source_file.write_text("Test source")
        calls = []

        class CountingProvider:
            def complete(self, prompt, *, stage, invocation_id):
                calls.append((stage, invocation_id))
                return ProviderResult(
                    invocation_id=invocation_id,
                    stage=stage,
                    raw_text=json.dumps(
                        {
                            "diagnosis": {
                                "central_problem": "Test problem",
                                "search_profile": "normal",
                                "priority_dimensions": [],
                            },
                            "candidates": [],
                        }
                    ),
                    model="scripted",
                    transport="injected",
                    duration_ms=0,
                    exit_code=0,
                )

        exit_code = main(
            [
                "run",
                "--source-file", str(source_file),
                "--task", "Test task",
                "--session", str(session_dir),
            ],
            provider_factory=lambda: CountingProvider(),
        )

        assert exit_code == 0
        assert [stage for stage, _ in calls] == ["EXPLORE_GENERATE"]


# ─────────────────────────────────────────────────────────────────────────────
# Behavioral output sanitization tests (Replan §1.1, Wave 5 Fixed Decision 13)
# ─────────────────────────────────────────────────────────────────────────────


class _CliTestStageProvider:
    """Stage-indexed scripted provider for CLI behavioral tests."""

    def __init__(self, responses_by_stage: dict[str, list[ProviderResult]]):
        self._queues = {
            stage: list(responses) for stage, responses in responses_by_stage.items()
        }

    def complete(self, prompt: str, *, stage: str, invocation_id: str) -> ProviderResult:
        if stage not in self._queues or not self._queues[stage]:
            raise TransportError(f"Exhausted/unknown stage in CLI test: {stage}")
        res = self._queues[stage].pop(0)
        return ProviderResult(
            invocation_id=invocation_id,
            stage=stage,
            raw_text=res.raw_text,
            model=res.model,
            transport=res.transport,
            duration_ms=res.duration_ms,
            exit_code=res.exit_code,
        )


def _make_test_candidate(
    candidate_id: str = "C1",
    central_problem: str = "Cognitive framing under uncertainty",
    shift: str = "Focus on temporal discounting instead of risk aversion",
    mechanism: str = "Hyperbolic discounting of delayed payoffs",
    load_bearing_claim: str = "Temporal discounting dominates choices",
    perspective: str = "Perspective framing choices via hyperbolic discounting",
    default_frame: str = "Standard expected utility and risk aversion framing",
    blind_spot: str = "Ignores time-inconsistent preferences across decision horizons",
    **overrides: Any,
) -> dict[str, Any]:
    base = {
        "candidate_id": candidate_id,
        "semantic_core": {
            "central_problem": central_problem,
            "mechanism": mechanism,
            "load_bearing_claim": load_bearing_claim,
            "central_object": "Decision agent",
            "unit_of_analysis": "Individual",
            "system_boundary": "Cognitive horizon",
            "agency_model": "Bounded rationality",
            "temporal_logic": "Hyperbolic",
            "key_constraint": "Attention budget",
            "downstream_consequences": ["Suboptimal retirement allocation"],
        },
        "preserved": ["Preserve decision tree", "Core payoff structure"],
        "default_frame": default_frame,
        "blind_spot": blind_spot,
        "operator_ids": ["temporal_logic"],
        "shift": shift,
        "perspective": perspective,
        "new_consequences": ["Shift in long-term savings", "Policy bias"],
        "return_path": {
            "dimension_changed": "temporal_logic",
            "consequence_chain": [
                "Re-evaluates delayed payoffs",
                "Changes economic intervention design",
            ],
            "why_it_matters": "Changes economic intervention design",
        },
        "epistemics": {
            "supported": ["Empirical discounting data"],
            "inferred": ["Suboptimal retirement allocation"],
            "speculative": ["Long-term policy shift"],
            "unknown": ["Cross-domain stability"],
            "break_condition": ["Unbounded attention budget"],
        },
    }
    base.update(overrides)
    return base


def _make_test_selection(
    candidate_id: str = "C1",
    disposition: str = "KEEP",
    reason: str = "High novelty and strong mechanism differentiation.",
    admissible: bool = True,
    constraint_failures: list[str] | None = None,
    merge_target: dict[str, Any] | None = None,
    standalone_quality: str = "strong",
    marginal_contribution: str = "high",
    structurally_distinct: bool = True,
    novelty_dimensions: list[str] | None = None,
    nearest_candidate_id: str | None = None,
    nearest_existing_p_id: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    base = {
        "candidate_id": candidate_id,
        "admissible": admissible,
        "constraint_failures": constraint_failures if constraint_failures is not None else [],
        "structurally_distinct": structurally_distinct,
        "novelty_dimensions": (
            novelty_dimensions
            if novelty_dimensions is not None
            else ["mechanism", "temporal_logic"]
        ),
        "nearest_candidate_id": nearest_candidate_id,
        "nearest_existing_p_id": nearest_existing_p_id,
        "standalone_quality": standalone_quality,
        "marginal_contribution": marginal_contribution,
        "disposition": disposition,
        "merge_target": merge_target,
        "reason": reason,
    }
    base.update(overrides)
    return base


def _make_test_dev_json(p_id: str, echo: dict) -> str:
    return json.dumps({
        "p_id": p_id,
        "semantic_lock_echo": echo,
        "developed_model": "Refined model of hyperbolic discounting in retirement choices",
        "what_became_more_precise": ["Attention allocation mechanism"],
        "assumptions": ["Decision-makers experience temporal drift"],
        "supporting_basis": ["Empirical studies on choice architecture"],
        "evidence_missing": ["Longitudinal intervention data"],
        "unknowns": ["Cross-domain stability"],
        "strongest_countermodel": "Risk premium model",
        "break_conditions": ["If attention budget is unbounded"],
        "downstream_implications": ["Nudges must target decision friction points"],
        "optional_analysis": None,
    })


def _make_test_review_json(
    terminal_state: str = "MODEL_READY",
    rebuild_required: bool = False,
    rationale: str = "Identity preserved and mechanism is robust.",
) -> str:
    return json.dumps({
        "identity_preserved": True,
        "identity_drift": [],
        "load_bearing_claim": "Temporal discounting dominates choices",
        "strongest_objection": "None",
        "objection_target": "None",
        "objection_is_load_bearing": False,
        "counterevidence": [],
        "evidence_debt": [],
        "rebuild_required": rebuild_required,
        "rebuild_instructions": ["Address missing evidence"] if rebuild_required else [],
        "terminal_state": terminal_state,
        "rationale": rationale,
    })


def _make_test_rebuild_json(
    p_id: str,
    echo: dict,
    terminal_state: str = "MODEL_READY",
    rationale: str = "Rebuild resolved review objections successfully.",
) -> str:
    return json.dumps({
        "development": {
            "p_id": p_id,
            "semantic_lock_echo": echo,
            "developed_model": "Rebuilt and refined model of hyperbolic discounting",
            "what_became_more_precise": ["Rebuild addressed evidence debt"],
            "assumptions": ["Decision-makers experience temporal drift"],
            "supporting_basis": ["Empirical studies and new longitudinal basis"],
            "evidence_missing": [],
            "unknowns": [],
            "strongest_countermodel": "Risk premium model",
            "break_conditions": ["If attention budget is unbounded"],
            "downstream_implications": ["Nudges must target decision friction points"],
            "optional_analysis": None,
        },
        "final_review": {
            "identity_preserved": True,
            "identity_drift": [],
            "load_bearing_claim": "Temporal discounting dominates choices",
            "strongest_objection": "None",
            "objection_target": "None",
            "objection_is_load_bearing": False,
            "counterevidence": [],
            "evidence_debt": [],
            "rebuild_required": False,
            "rebuild_instructions": [],
            "terminal_state": terminal_state,
            "rationale": rationale,
        },
    })


def test_cli_run_default_output_shows_rendered_and_hides_internal_ids(tmp_path: Path, capsys: pytest.CaptureFixture):
    """Ordinary run prints rendered perspectives and hides run/session/candidate/provider IDs."""
    source_file = tmp_path / "source.md"
    source_file.write_text("Source on decision architecture.")
    session_dir = tmp_path / "test_session_run_default"

    candidate = _make_test_candidate(candidate_id="cand_secret_123")
    selection = _make_test_selection(candidate_id="C1", disposition="KEEP")

    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult(
                invocation_id="inv_gen_secret_456",
                stage="EXPLORE_GENERATE",
                raw_text=json.dumps({
                    "diagnosis": {
                        "central_problem": "Cognitive framing under uncertainty",
                        "search_profile": "normal",
                        "priority_dimensions": [],
                    },
                    "candidates": [candidate],
                }),
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
        "EXPLORE_SELECT": [
            ProviderResult(
                invocation_id="inv_sel_secret_789",
                stage="EXPLORE_SELECT",
                raw_text=json.dumps([selection]),
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
    }

    exit_code = main(
        [
            "run",
            "--source-file", str(source_file),
            "--task", "Test run output",
            "--session", str(session_dir),
            "--mode", "normal",
        ],
        provider_factory=lambda: _CliTestStageProvider(responses),
    )
    assert exit_code == 0

    captured = capsys.readouterr().out

    # Visible observable content
    assert "## P1: Cognitive framing under uncertainty" in captured
    assert "**Structural shift:** Focus on temporal discounting instead of risk aversion" in captured
    assert "**Mechanism:** Hyperbolic discounting of delayed payoffs" in captured
    assert "**Source anchor:** Temporal discounting dominates choices" in captured

    # Hidden internal identifiers
    assert "Run ID:" not in captured
    assert "Session:" not in captured
    assert "cand_secret_123" not in captured
    assert "candidate_id" not in captured
    assert "inv_gen_secret_456" not in captured
    assert "inv_sel_secret_789" not in captured
    assert "traces" not in captured


def test_cli_run_default_output_zero_keep_shows_bounded_outcome_and_hides_internal_ids(tmp_path: Path, capsys: pytest.CaptureFixture):
    """Ordinary run with zero KEEP prints bounded outcome and hides internal IDs."""
    source_file = tmp_path / "source.md"
    source_file.write_text("Source on decision architecture.")
    session_dir = tmp_path / "test_session_run_zero"

    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult(
                invocation_id="inv_gen_secret_456",
                stage="EXPLORE_GENERATE",
                raw_text=json.dumps({
                    "diagnosis": {
                        "central_problem": "No perspectives found",
                        "search_profile": "normal",
                        "priority_dimensions": [],
                    },
                    "candidates": [],
                }),
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
    }

    exit_code = main(
        [
            "run",
            "--source-file", str(source_file),
            "--task", "Test run output zero keep",
            "--session", str(session_dir),
            "--mode", "normal",
        ],
        provider_factory=lambda: _CliTestStageProvider(responses),
    )
    assert exit_code == 0

    captured = capsys.readouterr().out

    # Visible bounded outcome
    assert "NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS" in captured

    # Hidden internal identifiers
    assert "Run ID:" not in captured
    assert "Session:" not in captured
    assert "candidate_id" not in captured
    assert "inv_gen_secret_456" not in captured
    assert "traces" not in captured


def test_cli_run_json_output_sanitized_and_hides_internal_ids(tmp_path: Path, capsys: pytest.CaptureFixture):
    """run --json emits sanitized user-facing object omitting run_id, session_id, selections, candidate_id."""
    source_file = tmp_path / "source.md"
    source_file.write_text("Source on decision architecture.")
    session_dir = tmp_path / "test_session_run_json"

    candidate = _make_test_candidate(candidate_id="cand_secret_json_123")
    selection = _make_test_selection(candidate_id="C1", disposition="KEEP")

    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult(
                invocation_id="inv_gen_secret_json",
                stage="EXPLORE_GENERATE",
                raw_text=json.dumps({
                    "diagnosis": {
                        "central_problem": "Cognitive framing under uncertainty",
                        "search_profile": "normal",
                        "priority_dimensions": [],
                    },
                    "candidates": [candidate],
                }),
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
        "EXPLORE_SELECT": [
            ProviderResult(
                invocation_id="inv_sel_secret_json",
                stage="EXPLORE_SELECT",
                raw_text=json.dumps([selection]),
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
    }

    exit_code = main(
        [
            "run",
            "--source-file", str(source_file),
            "--task", "Test json output",
            "--session", str(session_dir),
            "--mode", "normal",
            "--json",
        ],
        provider_factory=lambda: _CliTestStageProvider(responses),
    )
    assert exit_code == 0

    raw_captured = capsys.readouterr().out
    parsed = json.loads(raw_captured)

    # Visible required fields
    assert parsed["outcome"] == "OK"
    assert "## P1: Cognitive framing under uncertainty" in parsed["rendered"]
    assert len(parsed["kept"]) == 1
    kept_item = parsed["kept"][0]
    assert kept_item["identity"]["p_id"] == "P1"
    assert kept_item["identity"]["identity_core"]["central_problem"] == "Cognitive framing under uncertainty"
    assert kept_item["identity"]["identity_core"]["mechanism"] == "Hyperbolic discounting of delayed payoffs"
    assert "current_version" in kept_item
    assert "epistemics" in kept_item
    assert "deep_refs" in kept_item
    assert "terminal_state" in kept_item

    # Hidden fields MUST NOT be present in parsed JSON
    assert "run_id" not in parsed
    assert "session_id" not in parsed
    assert "selections" not in parsed
    assert "candidate_id" not in kept_item["identity"]
    assert "candidate_id" not in kept_item

    # Hidden fields MUST NOT be present anywhere in raw output
    assert "cand_secret_json_123" not in raw_captured
    assert "inv_gen_secret_json" not in raw_captured
    assert "inv_sel_secret_json" not in raw_captured
    assert "traces" not in raw_captured


def test_cli_run_json_output_zero_keep_sanitized(tmp_path: Path, capsys: pytest.CaptureFixture):
    """run --json with zero KEEP returns sanitized outcome and empty kept list."""
    source_file = tmp_path / "source.md"
    source_file.write_text("Source on decision architecture.")
    session_dir = tmp_path / "test_session_run_json_zero"

    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult(
                invocation_id="inv_gen_zero",
                stage="EXPLORE_GENERATE",
                raw_text=json.dumps({
                    "diagnosis": {
                        "central_problem": "No perspectives found",
                        "search_profile": "normal",
                        "priority_dimensions": [],
                    },
                    "candidates": [],
                }),
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
    }

    exit_code = main(
        [
            "run",
            "--source-file", str(source_file),
            "--task", "Test json zero keep",
            "--session", str(session_dir),
            "--mode", "normal",
            "--json",
        ],
        provider_factory=lambda: _CliTestStageProvider(responses),
    )
    assert exit_code == 0

    raw_captured = capsys.readouterr().out
    parsed = json.loads(raw_captured)

    assert parsed["outcome"] == "NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS"
    assert parsed["rendered"] == ""
    assert parsed["kept"] == []
    assert "run_id" not in parsed
    assert "session_id" not in parsed
    assert "selections" not in parsed


def test_cli_deep_default_output_shows_p_id_and_terminal_state_and_hides_internal_ids(tmp_path: Path, capsys: pytest.CaptureFixture):
    """Ordinary deep prints Perspective and Terminal state, hiding deep_id/run_id/session_id."""
    source_file = tmp_path / "source.md"
    source_file.write_text("Source for deep analysis.")
    session_dir = tmp_path / "test_session_deep_default"

    candidate = _make_test_candidate(candidate_id="cand_deep_01")
    selection = _make_test_selection(candidate_id="C1", disposition="KEEP")

    # 1. Populate session with P1 via run
    explore_responses = {
        "EXPLORE_GENERATE": [
            ProviderResult(
                invocation_id="inv_exp_1",
                stage="EXPLORE_GENERATE",
                raw_text=json.dumps({
                    "diagnosis": {
                        "central_problem": "Cognitive framing under uncertainty",
                        "search_profile": "normal",
                        "priority_dimensions": [],
                    },
                    "candidates": [candidate],
                }),
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
        "EXPLORE_SELECT": [
            ProviderResult(
                invocation_id="inv_exp_2",
                stage="EXPLORE_SELECT",
                raw_text=json.dumps([selection]),
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
    }

    main(
        [
            "run",
            "--source-file", str(source_file),
            "--task", "Setup for deep",
            "--session", str(session_dir),
            "--mode", "normal",
        ],
        provider_factory=lambda: _CliTestStageProvider(explore_responses),
    )
    capsys.readouterr()  # Clear explore stdout

    # 2. Run deep
    echo = candidate["semantic_core"]
    dev_json = _make_test_dev_json("P1", echo)
    review_json = _make_test_review_json(terminal_state="MODEL_READY")

    deep_responses = {
        "DEEP_DEVELOP": [
            ProviderResult(
                invocation_id="inv_dev_secret_111",
                stage="DEEP_DEVELOP",
                raw_text=dev_json,
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
        "DEEP_REVIEW": [
            ProviderResult(
                invocation_id="inv_rev_secret_222",
                stage="DEEP_REVIEW",
                raw_text=review_json,
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
    }

    exit_code = main(
        [
            "deep",
            "--session", str(session_dir),
            "--p-id", "P1",
        ],
        provider_factory=lambda: _CliTestStageProvider(deep_responses),
    )
    assert exit_code == 0

    captured = capsys.readouterr().out

    # Visible observable content
    assert "Perspective: P1" in captured
    assert "Terminal state: MODEL_READY" in captured

    # Hidden internal identifiers
    assert "Deep ID:" not in captured
    assert "Run ID:" not in captured
    assert "Session:" not in captured
    assert "deep_id" not in captured
    assert "run_id" not in captured
    assert "session_id" not in captured
    assert "inv_dev_secret_111" not in captured
    assert "inv_rev_secret_222" not in captured
    assert "traces" not in captured


def test_cli_deep_default_output_shows_rebuild_indicator_and_hides_internal_ids(tmp_path: Path, capsys: pytest.CaptureFixture):
    """Ordinary deep with rebuild prints Rebuild: yes, Perspective, Terminal state, and hides internal IDs."""
    source_file = tmp_path / "source.md"
    source_file.write_text("Source for deep analysis.")
    session_dir = tmp_path / "test_session_deep_rebuild"

    candidate = _make_test_candidate(candidate_id="cand_deep_02")
    selection = _make_test_selection(candidate_id="C1", disposition="KEEP")

    # 1. Setup session with P1
    explore_responses = {
        "EXPLORE_GENERATE": [
            ProviderResult(
                invocation_id="inv_exp_1",
                stage="EXPLORE_GENERATE",
                raw_text=json.dumps({
                    "diagnosis": {
                        "central_problem": "Cognitive framing under uncertainty",
                        "search_profile": "normal",
                        "priority_dimensions": [],
                    },
                    "candidates": [candidate],
                }),
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
        "EXPLORE_SELECT": [
            ProviderResult(
                invocation_id="inv_exp_2",
                stage="EXPLORE_SELECT",
                raw_text=json.dumps([selection]),
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
    }

    main(
        [
            "run",
            "--source-file", str(source_file),
            "--task", "Setup for deep rebuild",
            "--session", str(session_dir),
            "--mode", "normal",
        ],
        provider_factory=lambda: _CliTestStageProvider(explore_responses),
    )
    capsys.readouterr()  # Clear explore stdout

    # 2. Run deep with rebuild
    echo = candidate["semantic_core"]
    dev_json = _make_test_dev_json("P1", echo)
    review_json = _make_test_review_json(
        terminal_state="NEED_EVIDENCE",
        rebuild_required=True,
        rationale="Evidence debt requires rebuild.",
    )
    rebuild_json = _make_test_rebuild_json("P1", echo, terminal_state="MODEL_READY")

    deep_responses = {
        "DEEP_DEVELOP": [
            ProviderResult(
                invocation_id="inv_dev_rebuild_1",
                stage="DEEP_DEVELOP",
                raw_text=dev_json,
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
        "DEEP_REVIEW": [
            ProviderResult(
                invocation_id="inv_rev_rebuild_2",
                stage="DEEP_REVIEW",
                raw_text=review_json,
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
        "DEEP_REBUILD": [
            ProviderResult(
                invocation_id="inv_reb_rebuild_3",
                stage="DEEP_REBUILD",
                raw_text=rebuild_json,
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
    }

    exit_code = main(
        [
            "deep",
            "--session", str(session_dir),
            "--p-id", "P1",
        ],
        provider_factory=lambda: _CliTestStageProvider(deep_responses),
    )
    assert exit_code == 0

    captured = capsys.readouterr().out

    # Visible observable content
    assert "Perspective: P1" in captured
    assert "Terminal state: MODEL_READY" in captured
    assert "Rebuild: yes" in captured

    # Hidden internal identifiers
    assert "Deep ID:" not in captured
    assert "Run ID:" not in captured
    assert "Session:" not in captured
    assert "deep_id" not in captured
    assert "run_id" not in captured


def test_cli_deep_json_output_sanitized_and_hides_internal_ids(tmp_path: Path, capsys: pytest.CaptureFixture):
    """deep --json emits sanitized user-facing object omitting deep_id, run_id, session_id."""
    source_file = tmp_path / "source.md"
    source_file.write_text("Source for deep analysis.")
    session_dir = tmp_path / "test_session_deep_json"

    candidate = _make_test_candidate(candidate_id="cand_deep_json_01")
    selection = _make_test_selection(candidate_id="C1", disposition="KEEP")

    # 1. Setup session with P1
    explore_responses = {
        "EXPLORE_GENERATE": [
            ProviderResult(
                invocation_id="inv_exp_1",
                stage="EXPLORE_GENERATE",
                raw_text=json.dumps({
                    "diagnosis": {
                        "central_problem": "Cognitive framing under uncertainty",
                        "search_profile": "normal",
                        "priority_dimensions": [],
                    },
                    "candidates": [candidate],
                }),
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
        "EXPLORE_SELECT": [
            ProviderResult(
                invocation_id="inv_exp_2",
                stage="EXPLORE_SELECT",
                raw_text=json.dumps([selection]),
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
    }

    main(
        [
            "run",
            "--source-file", str(source_file),
            "--task", "Setup for deep json",
            "--session", str(session_dir),
            "--mode", "normal",
        ],
        provider_factory=lambda: _CliTestStageProvider(explore_responses),
    )
    capsys.readouterr()  # Clear explore stdout

    # 2. Run deep --json
    echo = candidate["semantic_core"]
    dev_json = _make_test_dev_json("P1", echo)
    review_json = _make_test_review_json(terminal_state="MODEL_READY")

    deep_responses = {
        "DEEP_DEVELOP": [
            ProviderResult(
                invocation_id="inv_dev_json_secret",
                stage="DEEP_DEVELOP",
                raw_text=dev_json,
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
        "DEEP_REVIEW": [
            ProviderResult(
                invocation_id="inv_rev_json_secret",
                stage="DEEP_REVIEW",
                raw_text=review_json,
                model="test",
                transport="injected",
                duration_ms=10,
                exit_code=0,
            ),
        ],
    }

    exit_code = main(
        [
            "deep",
            "--session", str(session_dir),
            "--p-id", "P1",
            "--json",
        ],
        provider_factory=lambda: _CliTestStageProvider(deep_responses),
    )
    assert exit_code == 0

    raw_captured = capsys.readouterr().out
    parsed = json.loads(raw_captured)

    # Visible observable fields
    assert parsed["p_id"] == "P1"
    assert parsed["terminal_state"] == "MODEL_READY"
    assert parsed["development"]["p_id"] == "P1"
    assert parsed["development"]["developed_model"] == "Refined model of hyperbolic discounting in retirement choices"
    assert parsed["review"]["terminal_state"] == "MODEL_READY"
    assert parsed["rebuilt_development"] is None

    # Hidden fields MUST NOT be present in parsed JSON
    assert "deep_id" not in parsed
    assert "run_id" not in parsed
    assert "session_id" not in parsed

    # Hidden fields MUST NOT be present in raw stdout
    assert "inv_dev_json_secret" not in raw_captured
    assert "inv_rev_json_secret" not in raw_captured
    assert "traces" not in raw_captured
