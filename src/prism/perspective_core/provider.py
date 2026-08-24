"""Provider abstraction for Perspective Core v0.

Implements replan §8 and execution contract frozen APIs.
Stage-aware provider with ScriptedProvider for deterministic testing.
"""

from __future__ import annotations

import subprocess
import shutil
import time
from collections import deque
from pathlib import Path
from typing import Protocol

from .models import ProviderResult


# ─────────────────────────────────────────────────────────────────────────────
# Provider Protocol (§8)
# ─────────────────────────────────────────────────────────────────────────────


class LLMProvider(Protocol):
    """Provider protocol for staged orchestration."""

    def complete(
        self,
        prompt: str,
        *,
        stage: str,
        invocation_id: str,
    ) -> ProviderResult:
        """Complete a prompt for a specific stage."""
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Transport errors
# ─────────────────────────────────────────────────────────────────────────────


class TransportError(Exception):
    """Raised when provider transport fails."""

    pass


# ─────────────────────────────────────────────────────────────────────────────
# Exact provider stage names (execution contract)
# ─────────────────────────────────────────────────────────────────────────────

STAGES = {
    "EXPLORE_GENERATE",
    "EXPLORE_SELECT",
    "EXPLORE_360_GENERATE",
    "EXPLORE_360_SELECT",
    "RIFT_GENERATE",
    "RIFT_SELECT",
    "DEEP_DEVELOP",
    "DEEP_REVIEW",
    "DEEP_REBUILD",
}


def is_repair_stage(stage: str) -> bool:
    """Check if stage is a schema repair stage."""
    return stage.startswith("SCHEMA_REPAIR:")


def get_repair_parent(stage: str) -> str | None:
    """Extract parent stage from repair stage name."""
    if is_repair_stage(stage):
        return stage.split(":", 1)[1]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# ScriptedProvider (§8.1)
# ─────────────────────────────────────────────────────────────────────────────


class ScriptedProvider:
    """Stage-indexed scripted provider for deterministic testing.

    Uses per-stage queues to prevent stage mismatch and repair call shifts.
    """

    def __init__(self, responses_by_stage: dict[str, list[ProviderResult]]):
        self._queues: dict[str, deque[ProviderResult]] = {
            stage: deque(responses) for stage, responses in responses_by_stage.items()
        }
        self._call_count = 0

    def complete(
        self,
        prompt: str,
        *,
        stage: str,
        invocation_id: str,
    ) -> ProviderResult:
        """Return next scripted response for stage."""
        if stage not in self._queues:
            raise TransportError(f"Unknown stage: {stage}")

        queue = self._queues[stage]
        if not queue:
            raise TransportError(f"Exhausted stage queue: {stage}")

        result = queue.popleft()
        self._call_count += 1

        # Verify invocation_id matches if provided in result
        if result.invocation_id != invocation_id:
            raise TransportError(
                f"Invocation ID mismatch: expected {result.invocation_id}, got {invocation_id}"
            )

        # Verify stage matches
        if result.stage != stage:
            raise TransportError(f"Stage mismatch: expected {result.stage}, got {stage}")

        return result

    def assert_exhausted(self) -> None:
        """Assert all scripted responses were consumed."""
        for stage, queue in self._queues.items():
            if queue:
                raise AssertionError(
                    f"Unused scripted responses in stage {stage}: {len(queue)} remaining"
                )


# ─────────────────────────────────────────────────────────────────────────────
# Qwen CLI provider (transport exists but not called in Wave 1)
# ─────────────────────────────────────────────────────────────────────────────


class QwenCliProvider:
    """Qwen CLI transport provider.

    Exists for Wave 1 but is not invoked until runtime manifest approval.
    """

    def __init__(
        self,
        *,
        binary_path: Path,
        model: str = "qwen3.7-plus",
        safe_mode: bool = False,
    ):
        self._binary_path = binary_path
        self._model = model
        self._safe_mode = safe_mode

    def complete(
        self,
        prompt: str,
        *,
        stage: str,
        invocation_id: str,
    ) -> ProviderResult:
        """Execute Qwen CLI and return result."""
        start = time.time()

        argv = [
            str(self._binary_path),
            "--model",
            self._model,
            "--output-format",
            "text",
            "--prompt",
            "",
        ]
        if self._safe_mode:
            argv.append("--safe-mode")

        try:
            result = subprocess.run(
                argv,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=300,
            )
            duration_ms = int((time.time() - start) * 1000)

            return ProviderResult(
                invocation_id=invocation_id,
                stage=stage,
                raw_text=result.stdout,
                model=self._model,
                transport="cli",
                duration_ms=duration_ms,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start) * 1000)
            raise TransportError(f"Qwen CLI timeout after {duration_ms}ms")
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            raise TransportError(f"Qwen CLI error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Provider factory
# ─────────────────────────────────────────────────────────────────────────────


def make_default_provider() -> LLMProvider:
    """Create default Qwen CLI provider.

    This is the live provider factory. Wave 1 does not invoke it.
    Actual invocation requires runtime manifest and human approval (Wave 6).
    """
    qwen_path = shutil.which("qwen")
    if qwen_path is None:
        raise TransportError("Qwen binary not found on PATH")

    return QwenCliProvider(binary_path=Path(qwen_path))


def make_scripted_provider(responses_by_stage: dict[str, list[ProviderResult]]) -> ScriptedProvider:
    """Create scripted provider for testing."""
    return ScriptedProvider(responses_by_stage)
