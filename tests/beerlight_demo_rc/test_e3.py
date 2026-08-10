from __future__ import annotations

import json
from pathlib import Path

import pytest

from prism.beerlight_demo_rc.e3 import (
    E3AnchorValidationError,
    TerritoryEvidence,
    known_supported_territories,
    load_e3_anchor_fixture,
    subject_visible_e3_input,
    validate_known_territory_coverage,
)


SPEC = Path(__file__).parents[2] / "beerlight_demo_rc/spec/explore"


def test_e3_subject_invisible_lower_bound_concretely_fails_fake_breadth():
    anchors = known_supported_territories(load_e3_anchor_fixture(SPEC / "e3_known_supported_territories.json"))
    regression = json.loads((SPEC / "e3_fake_breadth_regression.json").read_text(encoding="utf-8"))
    result = validate_known_territory_coverage(
        visible_output=regression["visible_output"],
        anchors=anchors,
        evidence=tuple(TerritoryEvidence(**item) for item in regression["coverage_evidence"]),
    )
    assert result.status == "FAIL"
    assert result.check_id == "E3_KNOWN_SUPPORTED_TERRITORIES_LOWER_BOUND"
    assert result.missing_territory_ids == tuple(regression["expected_missing_territory_ids"])


def test_e3_anchor_evidence_must_be_an_exact_visible_excerpt():
    anchors = known_supported_territories(load_e3_anchor_fixture(SPEC / "e3_known_supported_territories.json"))
    with pytest.raises(E3AnchorValidationError, match="exact output substring"):
        validate_known_territory_coverage(
            visible_output="Видимый ответ.",
            anchors=anchors,
            evidence=(TerritoryEvidence("T01_HOME_CARE_CAPACITY", "невидимый фрагмент"),),
        )


def test_e3_subject_packet_cannot_include_fixture_anchor_material():
    packet = subject_visible_e3_input("Контекст E3", "Сделай 360.")
    serialized = json.dumps(packet, ensure_ascii=False)
    assert "T01_HOME_CARE_CAPACITY" not in serialized
    assert "Контекст E3" in serialized
