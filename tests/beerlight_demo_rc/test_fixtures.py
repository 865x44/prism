from __future__ import annotations

import json

import pytest

from prism.beerlight_demo_rc.fixtures import (
    FIXTURE_SCHEMA_VERSION,
    FixtureValidationError,
    load_fixture,
    validate_fixture,
)


def explore_fixture() -> dict:
    return {
        "schema_version": FIXTURE_SCHEMA_VERSION,
        "fixture_id": "E3",
        "suite": "EXPLORE",
        "mode": "360",
        "input": {"turns": [{"role": "user", "content": "Build a coverage-first map."}]},
        "expected": {
            "deterministic_checks": ["EXACT_DUPLICATE_VISIBLE_PAYLOAD"],
            "semantic_predicates": ["COVERAGE_BREADTH", "DISTINCT_MODEL"],
        },
    }


def test_loader_accepts_generated_explore_fixture(tmp_path):
    path = tmp_path / "E3.json"
    path.write_text(json.dumps(explore_fixture()), encoding="utf-8")
    assert load_fixture(path)["fixture_id"] == "E3"


def test_deep_handoff_is_structural_not_semantic_rewrite():
    fixture = explore_fixture() | {
        "fixture_id": "D1",
        "suite": "DEEP",
        "mode": "DEEP",
        "handoff": {"selected_p_id": "P4", "source_fixture_id": "E3"},
    }
    assert validate_fixture(fixture)["handoff"]["selected_p_id"] == "P4"


def test_fixture_rejects_unknown_predicate_and_malformed_handoff():
    fixture = explore_fixture() | {
        "handoff": {"selected_p_id": "four", "source_fixture_id": "D1"},
        "expected": {"deterministic_checks": [], "semantic_predicates": ["NOVELTY"]},
    }
    with pytest.raises(FixtureValidationError):
        validate_fixture(fixture)
