"""Tests for Perspective Core v0 provider abstraction.

Covers:
- ScriptedProvider stage routing
- Stage-indexed queues (not FIFO)
- Exhausted queue detection
- Unknown stage detection
- assert_exhausted() for unused responses
- Schema repair stage detection
- ProviderResult structure
"""

from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from prism.perspective_core import (
    ProviderResult,
    QwenCliProvider,
    ScriptedProvider,
    TransportError,
    get_repair_parent,
    is_repair_stage,
    make_default_provider,
    make_scripted_provider,
)


# ─────────────────────────────────────────────────────────────────────────────
# ProviderResult structure (§8, requirement 1)
# ─────────────────────────────────────────────────────────────────────────────


def test_provider_result_creation():
    """ProviderResult stores all required fields."""
    result = ProviderResult(
        invocation_id="inv_001",
        stage="EXPLORE_GENERATE",
        raw_text="Generated candidates",
        model="qwen3.7-plus",
        transport="cli",
        duration_ms=1500,
        exit_code=0,
    )

    assert result.invocation_id == "inv_001"
    assert result.stage == "EXPLORE_GENERATE"
    assert result.raw_text == "Generated candidates"
    assert result.model == "qwen3.7-plus"
    assert result.transport == "cli"
    assert result.duration_ms == 1500
    assert result.exit_code == 0


def test_provider_result_to_dict():
    """ProviderResult serializes to dict."""
    result = ProviderResult(
        invocation_id="inv_001",
        stage="EXPLORE_GENERATE",
        raw_text="text",
        model="qwen3.7-plus",
        transport="cli",
        duration_ms=1500,
        exit_code=0,
    )

    data = result.to_dict()
    assert data["invocation_id"] == "inv_001"
    assert data["stage"] == "EXPLORE_GENERATE"
    assert data["raw_text"] == "text"
    assert data["model"] == "qwen3.7-plus"
    assert data["transport"] == "cli"
    assert data["duration_ms"] == 1500
    assert data["exit_code"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# ScriptedProvider stage routing (§8.1, requirement 6, 7)
# ─────────────────────────────────────────────────────────────────────────────


def test_scripted_provider_basic_routing():
    """ScriptedProvider routes to correct stage queue."""
    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult("inv_1", "EXPLORE_GENERATE", "gen1", "test", "scripted", 100, 0),
        ],
        "EXPLORE_SELECT": [
            ProviderResult("inv_2", "EXPLORE_SELECT", "sel1", "test", "scripted", 100, 0),
        ],
    }

    provider = ScriptedProvider(responses)

    # Call EXPLORE_GENERATE
    result1 = provider.complete("prompt1", stage="EXPLORE_GENERATE", invocation_id="inv_1")
    assert result1.raw_text == "gen1"

    # Call EXPLORE_SELECT
    result2 = provider.complete("prompt2", stage="EXPLORE_SELECT", invocation_id="inv_2")
    assert result2.raw_text == "sel1"


def test_scripted_provider_stage_indexed_queues():
    """ScriptedProvider uses per-stage queues, not global FIFO."""
    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult("inv_1", "EXPLORE_GENERATE", "gen1", "test", "scripted", 100, 0),
            ProviderResult("inv_2", "EXPLORE_GENERATE", "gen2", "test", "scripted", 100, 0),
        ],
        "EXPLORE_SELECT": [
            ProviderResult("inv_3", "EXPLORE_SELECT", "sel1", "test", "scripted", 100, 0),
        ],
    }

    provider = ScriptedProvider(responses)

    # Call EXPLORE_GENERATE twice
    result1 = provider.complete("p1", stage="EXPLORE_GENERATE", invocation_id="inv_1")
    result2 = provider.complete("p2", stage="EXPLORE_GENERATE", invocation_id="inv_2")
    assert result1.raw_text == "gen1"
    assert result2.raw_text == "gen2"

    # Call EXPLORE_SELECT (different stage)
    result3 = provider.complete("p3", stage="EXPLORE_SELECT", invocation_id="inv_3")
    assert result3.raw_text == "sel1"


def test_scripted_provider_unknown_stage_fails():
    """ScriptedProvider fails on unknown stage."""
    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult("inv_1", "EXPLORE_GENERATE", "gen1", "test", "scripted", 100, 0),
        ],
    }

    provider = ScriptedProvider(responses)

    with pytest.raises(TransportError, match="Unknown stage"):
        provider.complete("prompt", stage="UNKNOWN_STAGE", invocation_id="inv_1")


def test_scripted_provider_exhausted_queue_fails():
    """ScriptedProvider fails when stage queue is exhausted."""
    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult("inv_1", "EXPLORE_GENERATE", "gen1", "test", "scripted", 100, 0),
        ],
    }

    provider = ScriptedProvider(responses)

    # First call succeeds
    provider.complete("p1", stage="EXPLORE_GENERATE", invocation_id="inv_1")

    # Second call fails (queue exhausted)
    with pytest.raises(TransportError, match="Exhausted stage queue"):
        provider.complete("p2", stage="EXPLORE_GENERATE", invocation_id="inv_2")


def test_scripted_provider_invocation_id_mismatch():
    """ScriptedProvider fails on invocation ID mismatch."""
    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult("inv_1", "EXPLORE_GENERATE", "gen1", "test", "scripted", 100, 0),
        ],
    }

    provider = ScriptedProvider(responses)

    with pytest.raises(TransportError, match="Invocation ID mismatch"):
        provider.complete("prompt", stage="EXPLORE_GENERATE", invocation_id="wrong_id")


def test_scripted_provider_stage_mismatch():
    """ScriptedProvider fails on stage mismatch in response."""
    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult("inv_1", "EXPLORE_SELECT", "gen1", "test", "scripted", 100, 0),
        ],
    }

    provider = ScriptedProvider(responses)

    with pytest.raises(TransportError, match="Stage mismatch"):
        provider.complete("prompt", stage="EXPLORE_GENERATE", invocation_id="inv_1")


# ─────────────────────────────────────────────────────────────────────────────
# assert_exhausted (requirement 7)
# ─────────────────────────────────────────────────────────────────────────────


def test_scripted_provider_assert_exhausted_success():
    """assert_exhausted succeeds when all responses consumed."""
    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult("inv_1", "EXPLORE_GENERATE", "gen1", "test", "scripted", 100, 0),
        ],
        "EXPLORE_SELECT": [
            ProviderResult("inv_2", "EXPLORE_SELECT", "sel1", "test", "scripted", 100, 0),
        ],
    }

    provider = ScriptedProvider(responses)

    # Consume all responses
    provider.complete("p1", stage="EXPLORE_GENERATE", invocation_id="inv_1")
    provider.complete("p2", stage="EXPLORE_SELECT", invocation_id="inv_2")

    # Should not raise
    provider.assert_exhausted()


def test_scripted_provider_assert_exhausted_fails():
    """assert_exhausted fails when unused responses remain."""
    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult("inv_1", "EXPLORE_GENERATE", "gen1", "test", "scripted", 100, 0),
            ProviderResult("inv_2", "EXPLORE_GENERATE", "gen2", "test", "scripted", 100, 0),
        ],
    }

    provider = ScriptedProvider(responses)

    # Consume only first response
    provider.complete("p1", stage="EXPLORE_GENERATE", invocation_id="inv_1")

    # Should raise due to unused response
    with pytest.raises(AssertionError, match="Unused scripted responses"):
        provider.assert_exhausted()


# ─────────────────────────────────────────────────────────────────────────────
# Schema repair stages (requirement 6)
# ─────────────────────────────────────────────────────────────────────────────


def test_is_repair_stage():
    """is_repair_stage detects schema repair stages."""
    assert is_repair_stage("SCHEMA_REPAIR:EXPLORE_GENERATE")
    assert is_repair_stage("SCHEMA_REPAIR:DEEP_DEVELOP")
    assert not is_repair_stage("EXPLORE_GENERATE")
    assert not is_repair_stage("SCHEMA_REPAIR")


def test_get_repair_parent():
    """get_repair_parent extracts parent stage from repair stage."""
    assert get_repair_parent("SCHEMA_REPAIR:EXPLORE_GENERATE") == "EXPLORE_GENERATE"
    assert get_repair_parent("SCHEMA_REPAIR:DEEP_DEVELOP") == "DEEP_DEVELOP"
    assert get_repair_parent("EXPLORE_GENERATE") is None
    assert get_repair_parent("SCHEMA_REPAIR") is None


def test_scripted_provider_with_repair_stage():
    """ScriptedProvider handles repair stages correctly."""
    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult("inv_1", "EXPLORE_GENERATE", "gen1", "test", "scripted", 100, 0),
        ],
        "SCHEMA_REPAIR:EXPLORE_GENERATE": [
            ProviderResult(
                "inv_2",
                "SCHEMA_REPAIR:EXPLORE_GENERATE",
                "repaired",
                "test",
                "scripted",
                100,
                0,
            ),
        ],
    }

    provider = ScriptedProvider(responses)

    # Call original stage
    result1 = provider.complete("p1", stage="EXPLORE_GENERATE", invocation_id="inv_1")
    assert result1.raw_text == "gen1"

    # Call repair stage
    result2 = provider.complete(
        "p2",
        stage="SCHEMA_REPAIR:EXPLORE_GENERATE",
        invocation_id="inv_2",
    )
    assert result2.raw_text == "repaired"


# ─────────────────────────────────────────────────────────────────────────────
# Factory function
# ─────────────────────────────────────────────────────────────────────────────


def test_make_scripted_provider():
    """make_scripted_provider creates ScriptedProvider instance."""
    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult("inv_1", "EXPLORE_GENERATE", "gen1", "test", "scripted", 100, 0),
        ],
    }

    provider = make_scripted_provider(responses)
    assert isinstance(provider, ScriptedProvider)

    result = provider.complete("p1", stage="EXPLORE_GENERATE", invocation_id="inv_1")
    assert result.raw_text == "gen1"


def test_qwen_cli_uses_explicit_noninteractive_argv():
    """Qwen transport sends the prompt on stdin with an explicit model and no fallback."""
    completed = Mock(stdout='{"ok": true}', returncode=0)
    with patch("prism.perspective_core.provider.subprocess.run", return_value=completed) as run:
        provider = QwenCliProvider(
            binary_path=Path("/opt/qwen"),
            model="qwen3.7-plus",
            safe_mode=True,
        )
        result = provider.complete(
            "private source",
            stage="EXPLORE_GENERATE",
            invocation_id="inv_qwen",
        )

    argv = run.call_args.args[0]
    assert argv == [
        "/opt/qwen",
        "--model",
        "qwen3.7-plus",
        "--output-format",
        "text",
        "--prompt",
        "",
        "--safe-mode",
    ]
    assert run.call_args.kwargs["input"] == "private source"
    assert "--fallback-model" not in argv
    assert result.raw_text == '{"ok": true}'
    assert result.model == "qwen3.7-plus"
    assert result.transport == "cli"


def test_default_provider_resolves_qwen_from_path():
    """Default provider uses the installed qwen binary rather than a fixed location."""
    with patch("prism.perspective_core.provider.shutil.which", return_value="/home/test/bin/qwen"):
        provider = make_default_provider()

    assert isinstance(provider, QwenCliProvider)
    assert provider._binary_path == Path("/home/test/bin/qwen")


def test_default_provider_fails_without_qwen():
    """Missing Qwen fails closed instead of substituting a provider."""
    with patch("prism.perspective_core.provider.shutil.which", return_value=None):
        with pytest.raises(TransportError, match="not found on PATH"):
            make_default_provider()

# ─────────────────────────────────────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────────────────────────────────────


def test_scripted_provider_empty_responses():
    """ScriptedProvider with empty responses dict."""
    provider = ScriptedProvider({})

    with pytest.raises(TransportError, match="Unknown stage"):
        provider.complete("prompt", stage="EXPLORE_GENERATE", invocation_id="inv_1")


def test_scripted_provider_multiple_stages_independent():
    """Different stage queues are independent."""
    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult("inv_1", "EXPLORE_GENERATE", "gen1", "test", "scripted", 100, 0),
        ],
        "EXPLORE_SELECT": [
            ProviderResult("inv_2", "EXPLORE_SELECT", "sel1", "test", "scripted", 100, 0),
        ],
    }

    provider = ScriptedProvider(responses)

    # Consume EXPLORE_GENERATE
    provider.complete("p1", stage="EXPLORE_GENERATE", invocation_id="inv_1")

    # EXPLORE_SELECT should still work
    result = provider.complete("p2", stage="EXPLORE_SELECT", invocation_id="inv_2")
    assert result.raw_text == "sel1"

    # EXPLORE_GENERATE should be exhausted
    with pytest.raises(TransportError, match="Exhausted stage queue"):
        provider.complete("p3", stage="EXPLORE_GENERATE", invocation_id="inv_3")


def test_scripted_provider_call_count():
    """ScriptedProvider tracks call count."""
    responses = {
        "EXPLORE_GENERATE": [
            ProviderResult("inv_1", "EXPLORE_GENERATE", "gen1", "test", "scripted", 100, 0),
            ProviderResult("inv_2", "EXPLORE_GENERATE", "gen2", "test", "scripted", 100, 0),
        ],
    }

    provider = ScriptedProvider(responses)

    assert provider._call_count == 0

    provider.complete("p1", stage="EXPLORE_GENERATE", invocation_id="inv_1")
    assert provider._call_count == 1

    provider.complete("p2", stage="EXPLORE_GENERATE", invocation_id="inv_2")
    assert provider._call_count == 2
