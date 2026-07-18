"""Data models for Beerlight Runtime.

These are the public types used throughout the runtime layer.
They wrap/adapt the validated slice internals without rewriting them.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class PrivacyLevel(str, enum.Enum):
    """Privacy classification for traces and sessions."""
    PRIVATE = "private"
    PROJECT = "project"
    SHAREABLE = "shareable"


class TraceLevel(str, enum.Enum):
    """Compact: request + candidates + decisions + visible output.
    Full: additionally raw model responses, full context, repair prompts.
    """
    COMPACT = "compact"
    FULL = "full"


class RunMode(str, enum.Enum):
    NORMAL = "normal"
    MODE_360 = "360"


class ContextMode(str, enum.Enum):
    TRAJECTORY = "trajectory"
    FULL = "full"


@dataclass
class Candidate:
    """A generator candidate (from slice schema, runtime-adapted)."""
    id: str
    title: str
    core_shift: str
    source_basis: list[str]
    practical_return: str
    boundary: str
    operator: str | None = None

    @staticmethod
    def from_dict(data: dict) -> Candidate:
        return Candidate(
            id=data["id"],
            title=data["title"],
            core_shift=data["core_shift"],
            source_basis=data["source_basis"],
            practical_return=data["practical_return"],
            boundary=data["boundary"],
            operator=data.get("operator"),
        )


@dataclass
class Card:
    """User-facing output card (from judge output)."""
    title: str
    shift: str
    basis: str
    action: str
    boundary: str

    @staticmethod
    def from_dict(data: dict) -> Card:
        return Card(
            title=data["title"],
            shift=data["shift"],
            basis=data["basis"],
            action=data["action"],
            boundary=data["boundary"],
        )


@dataclass
class JudgeJudgment:
    """Per-candidate judge decision."""
    candidate_id: str
    action: str  # keep, merge, rescue, drop
    novelty: str  # real, partial, false
    fidelity: str  # grounded, mixed, distorted
    failure_tags: list[str]
    reason: str

    @staticmethod
    def from_dict(data: dict) -> JudgeJudgment:
        return JudgeJudgment(
            candidate_id=data["candidate_id"],
            action=data["action"],
            novelty=data["novelty"],
            fidelity=data["fidelity"],
            failure_tags=data.get("failure_tags", []),
            reason=data["reason"],
        )


@dataclass
class JudgeResult:
    """Full judge output (adapted from judge.json)."""
    overall_decision: str  # useful_output, no_useful_output
    cards: list[Card]
    judgments: list[JudgeJudgment]
    abstention_source: str | None = None
    trajectory_update: dict | None = None

    @staticmethod
    def from_dict(data: dict) -> JudgeResult:
        cards = [Card.from_dict(c) for c in data.get("cards", [])]
        judgments = [JudgeJudgment.from_dict(j) for j in data.get("judgments", [])]
        return JudgeResult(
            overall_decision=data["overall_decision"],
            cards=cards,
            judgments=judgments,
            abstention_source=data.get("abstention_source"),
            trajectory_update=data.get("trajectory_update"),
        )


@dataclass
class TraceMetadata:
    """Metadata for a run trace (v1 format)."""
    trace_schema_version: str = "1"
    run_id: str = ""
    mode: str = "normal"
    generator_prompt_version: str = ""
    judge_prompt_version: str = ""
    generator_model: str = ""
    judge_model: str = ""
    judge_family_fallback: bool = True
    created_at: str = ""
    status: str = "ok"
    privacy: PrivacyLevel = PrivacyLevel.PRIVATE
    trace_level: str = "compact"
    token_usage_estimate: int = 0
    token_usage_breakdown: dict = field(default_factory=dict)
    duration_sec: float = 0.0
    retry_count: int = 0
    input_hash: str = ""
    warnings: list[str] = field(default_factory=list)
    abstention_source: str | None = None

    def to_dict(self) -> dict:
        d = {
            "trace_schema_version": self.trace_schema_version,
            "run_id": self.run_id,
            "mode": self.mode,
            "generator_prompt_version": self.generator_prompt_version,
            "judge_prompt_version": self.judge_prompt_version,
            "generator_model": self.generator_model,
            "judge_model": self.judge_model,
            "judge_family_fallback": self.judge_family_fallback,
            "created_at": self.created_at,
            "status": self.status,
            "privacy": self.privacy.value,
            "trace_level": self.trace_level,
            "token_usage_estimate": self.token_usage_estimate,
            "token_usage_breakdown": self.token_usage_breakdown,
            "duration_sec": self.duration_sec,
            "retry_count": self.retry_count,
            "input_hash": self.input_hash,
            "warnings": self.warnings,
        }
        if self.abstention_source:
            d["abstention_source"] = self.abstention_source
        return d


@dataclass
class TrajectoryEntry:
    """A single run's trajectory update entry."""
    run_id: str
    explored: list[str] = field(default_factory=list)
    shown: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [f"## Run {self.run_id}", ""]
        if self.explored:
            lines.append("Исследовано:")
            for item in self.explored:
                lines.append(f"- {item}")
            lines.append("")
        if self.shown:
            lines.append("Показано пользователю:")
            for item in self.shown:
                lines.append(f"- {item}")
            lines.append("")
        if self.open_questions:
            lines.append("Новые открытые вопросы:")
            for item in self.open_questions:
                lines.append(f"- {item}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def from_dict(data: dict, run_id: str = "") -> TrajectoryEntry:
        return TrajectoryEntry(
            run_id=run_id,
            explored=data.get("explored", []),
            shown=data.get("shown", []),
            open_questions=data.get("open_questions", []),
        )


@dataclass
class InspectResult:
    """Result of inspecting a run trace.

    Three cardinality sets (R1 semantics):
        shown_cards — cards actually in output.md (source: output.md/run result)
        kept_hidden — judge-kept cards hidden by cap (source: judge.json, beyond cap)
        dropped_candidates — dropped by judge judgments (source: judge.json)
    """
    run_id: str = ""
    trace_dir: str = ""
    schema_version: str = "unknown"
    candidates: list[dict] = field(default_factory=list)
    cards: list[dict] = field(default_factory=list)          # deprecated alias for shown_cards
    shown_cards: list[dict] = field(default_factory=list)     # actually shown (from output.md)
    kept_hidden: list[dict] = field(default_factory=list)     # judge-kept, hidden by cap
    judge_result: dict | None = None
    dropped_candidates: list[dict] = field(default_factory=list)
    rescue_provenance: list[dict] = field(default_factory=list)
    raw_outputs: dict = field(default_factory=dict)
    abstention_source: str | None = None
    errors: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
