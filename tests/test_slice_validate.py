"""Unit tests for the slice JSON validation layer.

Mock transport, no LLM calls. (Legacy runner tests intentionally not ported —
the output-cap behavior is covered by test_runtime_service.py.)
"""
import json

from prism.slice.validate import (
    extract_json,
    validate_candidates,
    validate_judge,
)


def test_extract_json_from_fenced_block():
    """JSON inside ```json ... ``` fenced block is extracted."""
    text = 'Some text\n```json\n[{"id": "c1"}]\n```\nMore text'
    result = extract_json(text)
    assert result == '[{"id": "c1"}]', f"Got: {result!r}"


def test_validate_schema_rejects_missing_fields():
    """validate_candidates rejects objects missing required fields."""
    # Missing core_shift, source_basis, practical_return, boundary
    data, error = validate_candidates('[{"id": "c1", "title": "X"}]')
    assert error is not None, "Should reject incomplete candidate"


def test_validate_judge_no_useful_output():
    """validate_judge accepts a valid no_useful_output response."""
    judge_json = json.dumps({
        "overall_decision": "no_useful_output",
        "cards": [],
        "judgments": [{
            "candidate_id": "c1",
            "action": "drop",
            "novelty": "false",
            "fidelity": "distorted",
            "failure_tags": ["paraphrase"],
            "reason": "nothing new"
        }]
    })
    data, error = validate_judge(judge_json)
    assert error is None, f"Should accept valid judge: {error}"
    assert data["overall_decision"] == "no_useful_output"


# ---------- abstention judgments ----------

def _judgment(cid: str) -> dict:
    return {
        "candidate_id": cid,
        "action": "drop",
        "novelty": "false",
        "fidelity": "grounded",
        "failure_tags": ["banal"],
        "reason": "short concrete reason",
    }


def test_judge_abstention_requires_judgment_coverage():
    """Judge dropped all candidates but gave no per-candidate reasons."""
    judge_json = json.dumps({
        "overall_decision": "no_useful_output",
        "cards": [],
        "judgments": [],
    })
    data, error = validate_judge(judge_json, expected_ids=["c1", "c2"])
    assert data is None
    assert error is not None and "missing" in error


def test_judge_abstention_with_full_coverage_ok():
    """Judge abstained but kept a decision for every candidate."""
    judge_json = json.dumps({
        "overall_decision": "no_useful_output",
        "cards": [],
        "judgments": [_judgment("c1"), _judgment("c2")],
    })
    data, error = validate_judge(judge_json, expected_ids=["c1", "c2"])
    assert error is None, f"Should accept full coverage: {error}"
    assert data["overall_decision"] == "no_useful_output"


def test_generator_abstention_empty_judgments_allowed():
    """Zero candidates (generator abstention) permits empty judgments."""
    judge_json = json.dumps({
        "overall_decision": "no_useful_output",
        "cards": [],
        "judgments": [],
        "abstention_source": "generator",
    })
    data, error = validate_judge(judge_json, expected_ids=[])
    assert error is None, f"Generator abstention must be valid: {error}"
