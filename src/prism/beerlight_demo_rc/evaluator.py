"""Offline evaluator packet, output validation, and two-call aggregation.

This module deliberately has no transport implementation.  It prepares and
checks the diagnostic protocol while keeping provider calls explicitly out of
scope until a separately authorized smoke run.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence


EVALUATOR_OUTPUT_SCHEMA_VERSION = "beerlight-semantic-evaluator-output-v1"
EVALUATOR_PROMPT_VERSION = "beerlight-semantic-evaluator-prompt-v1-provisional"
VERDICTS = frozenset({"MET", "VIOLATED", "UNCLEAR"})
CASE_STATUSES = frozenset({"PASS", "FAIL", "BORDERLINE", "EVAL_ERROR"})


class EvaluatorOutputValidationError(ValueError):
    """Raised when evaluator output cannot safely enter aggregation."""


class EvaluatorCallsDisabled(RuntimeError):
    """Signals a prohibited evaluator call, never a subject failure."""


@dataclass(frozen=True)
class Criterion:
    criterion_id: str
    definition: str
    met_anchor: str
    violated_anchor: str
    unclear_anchor: str
    does_not_establish: str


@dataclass(frozen=True)
class Operand:
    origin_id: str
    text: str


@dataclass(frozen=True)
class LanguageMetadata:
    primary_language: str
    contains_code_switch: bool

    def __post_init__(self) -> None:
        if self.primary_language not in {"RU", "EN", "MIXED", "UNKNOWN"}:
            raise ValueError("primary_language must be RU, EN, MIXED, or UNKNOWN")


@dataclass(frozen=True)
class EvaluationPacket:
    criterion: Criterion
    operands: tuple[Operand, ...]
    language: LanguageMetadata

    def __post_init__(self) -> None:
        _validate_criterion(self.criterion)
        if not self.operands:
            raise ValueError("at least one visible operand is required")
        origins = [operand.origin_id for operand in self.operands]
        if len(origins) != len(set(origins)):
            raise ValueError("operand origin_id values must be unique")
        for operand in self.operands:
            if not isinstance(operand.origin_id, str) or not operand.origin_id.strip():
                raise ValueError("operand origin_id must be a non-empty string")
            if not isinstance(operand.text, str) or not operand.text.strip():
                raise ValueError("operand text must be a non-empty string")

    def as_dict(self) -> dict[str, Any]:
        return {
            "criterion": {
                "criterion_id": self.criterion.criterion_id,
                "definition": self.criterion.definition,
                "met_anchor": self.criterion.met_anchor,
                "violated_anchor": self.criterion.violated_anchor,
                "unclear_anchor": self.criterion.unclear_anchor,
                "does_not_establish": self.criterion.does_not_establish,
            },
            "operands": [{"origin_id": item.origin_id, "text": item.text} for item in self.operands],
            "language_metadata": {
                "primary_language": self.language.primary_language,
                "contains_code_switch": self.language.contains_code_switch,
            },
        }


@dataclass(frozen=True)
class EvidenceExcerpt:
    origin: str
    excerpt: str


@dataclass(frozen=True)
class EvaluatorResult:
    criterion_id: str
    verdict: str
    evidence: tuple[EvidenceExcerpt, ...]
    justification: str
    language: LanguageMetadata


@dataclass(frozen=True)
class SemanticCallOutcome:
    """One planned call after at most one format/evidence retry."""

    status: str
    result: EvaluatorResult | None
    invalid_attempts: tuple[str, ...]


@dataclass(frozen=True)
class TwoCallAggregation:
    status: str
    verdicts: tuple[str, ...]
    disagreement: bool
    human_review_required: bool
    invalid_attempts: tuple[str, ...]


class EvaluatorAdapter(Protocol):
    """Future explicit adapter seam; this infrastructure never invokes it."""

    def execute(self, prompt: str) -> str: ...


class DisabledEvaluatorAdapter:
    """Fail closed until a bounded provider run is separately authorized."""

    def execute(self, prompt: str) -> str:
        raise EvaluatorCallsDisabled("Beerlight evaluator calls are disabled in offline infrastructure")


def _validate_criterion(criterion: Criterion) -> None:
    if not isinstance(criterion.criterion_id, str) or not criterion.criterion_id.strip():
        raise ValueError("criterion_id must be a non-empty string")
    for field in ("definition", "met_anchor", "violated_anchor", "unclear_anchor", "does_not_establish"):
        value = getattr(criterion, field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"criterion.{field} must be a non-empty string")


def build_evaluator_prompt(packet: EvaluationPacket) -> str:
    """Build the frozen one-criterion prompt and audit-only language metadata."""
    header = """You are the Beerlight Semantic Evaluator.

Judge exactly ONE supplied semantic criterion against ONLY the supplied visible texts.
Use the supplied criterion definition and MET / VIOLATED / UNCLEAR anchors exactly.
Do not judge general quality, global novelty, causal truth, hidden reasoning, or facts not available in the supplied texts.

Return JSON only with criterion_id, verdict, evidence, and justification.
Verdict is exactly one of MET, VIOLATED, UNCLEAR.
Return exactly this object shape (with one or more evidence objects):
{
  "criterion_id": "<requested criterion_id>",
  "verdict": "MET | VIOLATED | UNCLEAR",
  "evidence": [{"origin": "<supplied operand origin_id>", "excerpt": "<exact non-empty operand substring>"}],
  "justification": "<concise observable justification>"
}
Each evidence object must use the exact key "origin". Its value must equal a supplied input operand "origin_id"; "origin_id" is not a valid output evidence key. Evidence excerpts must be copied verbatim from the corresponding operand text. Do not calculate offsets or present paraphrase as evidence.
Justification must be concise and observable; do not expose chain-of-thought.
If material evidence is missing or the boundary is underdetermined, return UNCLEAR rather than guessing.
"""
    packet_json = json.dumps(packet.as_dict(), ensure_ascii=False, indent=2)
    return f"{header}\nPrompt version: {EVALUATOR_PROMPT_VERSION}\n\nCriterion packet:\n{packet_json}\n"


def parse_evaluator_output(raw: str | Mapping[str, Any], packet: EvaluationPacket) -> EvaluatorResult:
    """Parse a model result and validate criterion, enums, origins, and excerpts."""
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EvaluatorOutputValidationError(f"invalid JSON: {exc.msg}") from exc
    elif isinstance(raw, Mapping):
        data = dict(raw)
    else:
        raise EvaluatorOutputValidationError("evaluator output must be JSON text or an object")
    if not isinstance(data, dict):
        raise EvaluatorOutputValidationError("evaluator output must be an object")
    if data.get("criterion_id") != packet.criterion.criterion_id:
        raise EvaluatorOutputValidationError("criterion_id does not match requested criterion")
    verdict = data.get("verdict")
    if verdict not in VERDICTS:
        raise EvaluatorOutputValidationError("verdict must be MET, VIOLATED, or UNCLEAR")
    justification = data.get("justification")
    if not isinstance(justification, str) or not justification.strip():
        raise EvaluatorOutputValidationError("justification must be a non-empty string")
    evidence_data = data.get("evidence")
    if not isinstance(evidence_data, list) or not evidence_data:
        raise EvaluatorOutputValidationError("evidence must be a non-empty list")
    texts_by_origin = {operand.origin_id: operand.text for operand in packet.operands}
    evidence: list[EvidenceExcerpt] = []
    for item in evidence_data:
        if not isinstance(item, Mapping):
            raise EvaluatorOutputValidationError("each evidence item must be an object")
        if set(item) != {"origin", "excerpt"}:
            raise EvaluatorOutputValidationError("each evidence item must contain only origin and excerpt")
        origin = item.get("origin")
        excerpt = item.get("excerpt")
        if origin not in texts_by_origin:
            raise EvaluatorOutputValidationError("evidence origin is not a supplied operand")
        if not isinstance(excerpt, str) or not excerpt:
            raise EvaluatorOutputValidationError("evidence excerpt must be a non-empty string")
        if excerpt not in texts_by_origin[origin]:
            raise EvaluatorOutputValidationError("evidence excerpt is not an exact substring of its origin")
        evidence.append(EvidenceExcerpt(origin=origin, excerpt=excerpt))
    return EvaluatorResult(
        criterion_id=packet.criterion.criterion_id,
        verdict=verdict,
        evidence=tuple(evidence),
        justification=justification,
        language=packet.language,
    )


def validate_call_with_retry(raw_attempts: Sequence[str | Mapping[str, Any]], packet: EvaluationPacket) -> SemanticCallOutcome:
    """Validate one planned call with its permitted single format/evidence retry."""
    if not raw_attempts or len(raw_attempts) > 2:
        raise ValueError("one planned call requires one result and at most one retry")
    failures: list[str] = []
    for raw in raw_attempts:
        try:
            result = parse_evaluator_output(raw, packet)
        except EvaluatorOutputValidationError as exc:
            failures.append(str(exc))
            continue
        return SemanticCallOutcome(status="VALID", result=result, invalid_attempts=tuple(failures))
    return SemanticCallOutcome(status="EVAL_ERROR", result=None, invalid_attempts=tuple(failures))


def aggregate_two_calls(first: SemanticCallOutcome, second: SemanticCallOutcome) -> TwoCallAggregation:
    """Aggregate two valid calls without voting away disagreement or error."""
    invalid_attempts = first.invalid_attempts + second.invalid_attempts
    if first.status == "EVAL_ERROR" or second.status == "EVAL_ERROR":
        return TwoCallAggregation(
            status="EVAL_ERROR",
            verdicts=tuple(result.verdict for result in (first.result, second.result) if result is not None),
            disagreement=False,
            human_review_required=True,
            invalid_attempts=invalid_attempts,
        )
    if first.result is None or second.result is None:
        raise ValueError("VALID outcomes require parsed evaluator results")
    verdicts = (first.result.verdict, second.result.verdict)
    if verdicts == ("MET", "MET"):
        status = "PASS"
    elif verdicts == ("VIOLATED", "VIOLATED"):
        status = "FAIL"
    else:
        status = "BORDERLINE"
    return TwoCallAggregation(
        status=status,
        verdicts=verdicts,
        disagreement=verdicts[0] != verdicts[1],
        human_review_required=status == "BORDERLINE" or bool(invalid_attempts),
        invalid_attempts=invalid_attempts,
    )
