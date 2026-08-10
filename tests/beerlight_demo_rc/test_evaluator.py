from __future__ import annotations

import pytest

from prism.beerlight_demo_rc.evaluator import (
    DisabledEvaluatorAdapter,
    EvaluationPacket,
    EvaluatorCallsDisabled,
    EvaluatorOutputValidationError,
    LanguageMetadata,
    Operand,
    Criterion,
    aggregate_two_calls,
    build_evaluator_prompt,
    parse_evaluator_output,
    validate_call_with_retry,
)


def packet() -> EvaluationPacket:
    return EvaluationPacket(
        criterion=Criterion(
            criterion_id="DISTINCT_MODEL",
            definition="Judge local structural distinctness, not wording or actor variation.",
            met_anchor="A material causal structure differs.",
            violated_anchor="Only wording, actor, or metaphor changes.",
            unclear_anchor="The supplied relation cannot safely be classified.",
            does_not_establish="Global novelty or response quality.",
        ),
        operands=(
            Operand("candidate_a", "Один approval node создаёт serial bottleneck."),
            Operand("candidate_b", "Lighthouse не меняет один approval node."),
        ),
        language=LanguageMetadata(primary_language="RU", contains_code_switch=True),
    )


def valid_output(verdict: str = "VIOLATED") -> dict:
    return {
        "criterion_id": "DISTINCT_MODEL",
        "verdict": verdict,
        "evidence": [
            {"origin": "candidate_a", "excerpt": "approval node"},
            {"origin": "candidate_b", "excerpt": "approval node"},
        ],
        "justification": "Both excerpts describe the same visible gate.",
    }


def test_prompt_producer_round_trip_uses_canonical_origin_key_and_retains_language_metadata():
    prompt = build_evaluator_prompt(packet())
    assert "exactly ONE" in prompt
    assert '"criterion_id": "DISTINCT_MODEL"' in prompt
    assert '"evidence": [{"origin": "<supplied operand origin_id>", "excerpt": "<exact non-empty operand substring>"}]' in prompt
    assert '"origin_id" is not a valid output evidence key' in prompt
    assert '"primary_language": "RU"' in prompt
    assert '"contains_code_switch": true' in prompt
    assert parse_evaluator_output(valid_output(), packet()).evidence[0].origin == "candidate_a"


def test_parser_requires_exact_evidence_origin_and_excerpt():
    result = parse_evaluator_output(valid_output(), packet())
    assert result.verdict == "VIOLATED"
    assert result.language.contains_code_switch is True
    invalid = valid_output()
    invalid["evidence"][1] = {"origin": "candidate_b", "excerpt": "invented quote"}
    with pytest.raises(EvaluatorOutputValidationError, match="exact substring"):
        parse_evaluator_output(invalid, packet())


def test_parser_rejects_origin_id_as_an_output_evidence_key():
    invalid = valid_output()
    invalid["evidence"][0] = {"origin_id": "candidate_a", "excerpt": "approval node"}
    with pytest.raises(EvaluatorOutputValidationError, match="only origin and excerpt"):
        parse_evaluator_output(invalid, packet())


def test_two_call_aggregation_keeps_borderline_and_eval_error_separate_from_fail():
    first = validate_call_with_retry([valid_output("MET")], packet())
    second = validate_call_with_retry([valid_output("VIOLATED")], packet())
    borderline = aggregate_two_calls(first, second)
    assert borderline.status == "BORDERLINE"
    assert borderline.disagreement is True

    failed_call = validate_call_with_retry(["not json", "still not json"], packet())
    eval_error = aggregate_two_calls(first, failed_call)
    assert eval_error.status == "EVAL_ERROR"
    assert eval_error.status != "FAIL"


def test_one_invalid_result_can_use_exactly_one_retry_and_remains_auditable():
    outcome = validate_call_with_retry(["bad json", valid_output("MET")], packet())
    assert outcome.status == "VALID"
    assert outcome.result is not None and outcome.result.verdict == "MET"
    assert outcome.invalid_attempts == ("invalid JSON: Expecting value",)


def test_default_evaluator_adapter_fails_closed_without_provider_call():
    with pytest.raises(EvaluatorCallsDisabled):
        DisabledEvaluatorAdapter().execute("offline prompt")
