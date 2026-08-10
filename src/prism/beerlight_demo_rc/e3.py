"""Fixture-local deterministic lower-bound support for Explore E3.

The anchors in this module are test/evaluator inputs, never subject inputs.
They make one concrete fake-breadth omission observable without turning 360
breadth into a global quota or changing an E1--E12 fixture body.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


E3_ANCHOR_SCHEMA_VERSION = "beerlight-demo-rc-e3-anchors-v1"
PROVISIONAL_FIXTURE_ANCHORS = "PROVISIONAL_FIXTURE_ANCHORS"
_TERRITORY_ID = re.compile(r"^T[0-9]{2}_[A-Z0-9_]+$")


class E3AnchorValidationError(ValueError):
    """Raised when a fixture-local E3 anchor or its evidence is malformed."""


@dataclass(frozen=True)
class KnownSupportedTerritory:
    """A lower-bound territory visibly supported by the E3 setup text."""

    territory_id: str
    label: str
    source_excerpt: str


@dataclass(frozen=True)
class TerritoryEvidence:
    """Fixture-authored exact output excerpt for one known territory."""

    territory_id: str
    excerpt: str


@dataclass(frozen=True)
class E3CoverageResult:
    """A deterministic result, not a semantic evaluator verdict."""

    layer: str
    check_id: str
    status: str
    covered_territory_ids: tuple[str, ...]
    missing_territory_ids: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "layer": self.layer,
            "check_id": self.check_id,
            "status": self.status,
            "covered_territory_ids": list(self.covered_territory_ids),
            "missing_territory_ids": list(self.missing_territory_ids),
        }


def validate_e3_anchor_fixture(data: Any) -> dict[str, Any]:
    """Validate fixture-local lower-bound anchors without interpreting E3."""
    if not isinstance(data, dict):
        raise E3AnchorValidationError("E3 anchor fixture must be an object")
    errors: list[str] = []
    if data.get("schema_version") != E3_ANCHOR_SCHEMA_VERSION:
        errors.append(f"schema_version must be {E3_ANCHOR_SCHEMA_VERSION!r}")
    if data.get("fixture_id") != "E3":
        errors.append("fixture_id must be 'E3'")
    if data.get("status") != PROVISIONAL_FIXTURE_ANCHORS:
        errors.append(f"status must be {PROVISIONAL_FIXTURE_ANCHORS!r}")
    visibility = data.get("visibility")
    if visibility != {"subject": "INVISIBLE", "test": "VISIBLE", "evaluator": "VISIBLE"}:
        errors.append("visibility must keep anchors subject-invisible and test/evaluator-visible")
    territories = data.get("known_supported_territories")
    if not isinstance(territories, list) or not territories:
        errors.append("known_supported_territories must be a non-empty list")
    else:
        ids: list[str] = []
        for territory in territories:
            if not isinstance(territory, dict):
                errors.append("each territory must be an object")
                continue
            territory_id = territory.get("territory_id")
            if not isinstance(territory_id, str) or not _TERRITORY_ID.fullmatch(territory_id):
                errors.append("territory_id must match TNN_UPPER_SNAKE_CASE")
            else:
                ids.append(territory_id)
            for key in ("label", "source_excerpt"):
                if not isinstance(territory.get(key), str) or not territory[key].strip():
                    errors.append(f"territory.{key} must be a non-empty string")
        if len(ids) != len(set(ids)):
            errors.append("territory_id values must be unique")
    if errors:
        raise E3AnchorValidationError("; ".join(errors))
    return data


def load_e3_anchor_fixture(path: str | Path) -> dict[str, Any]:
    """Load the isolated anchor artifact; it is not a subject packet."""
    fixture_path = Path(path)
    try:
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise E3AnchorValidationError(f"invalid JSON in {fixture_path}: {exc.msg}") from exc
    return validate_e3_anchor_fixture(data)


def known_supported_territories(anchor_fixture: Mapping[str, Any]) -> tuple[KnownSupportedTerritory, ...]:
    """Return validated fixture-local anchors for tests or an evaluator packet."""
    validated = validate_e3_anchor_fixture(dict(anchor_fixture))
    return tuple(
        KnownSupportedTerritory(
            territory_id=item["territory_id"],
            label=item["label"],
            source_excerpt=item["source_excerpt"],
        )
        for item in validated["known_supported_territories"]
    )


def subject_visible_e3_input(e3_setup: str, e3_execution: str) -> dict[str, str]:
    """Build the subject packet explicitly without fixture-local anchor material."""
    if not isinstance(e3_setup, str) or not e3_setup.strip():
        raise E3AnchorValidationError("E3 setup must be a non-empty string")
    if not isinstance(e3_execution, str) or not e3_execution.strip():
        raise E3AnchorValidationError("E3 execution must be a non-empty string")
    return {"setup": e3_setup, "execution": e3_execution}


def validate_known_territory_coverage(
    *,
    visible_output: str,
    anchors: Sequence[KnownSupportedTerritory],
    evidence: Sequence[TerritoryEvidence],
) -> E3CoverageResult:
    """Prove an annotated fixture output includes every local lower bound.

    Evidence is fixture-authored test metadata.  This function validates only
    exact excerpts and anchor IDs; it does not infer semantic coverage from a
    model response, rank territory quality, or impose a global count.
    """
    if not isinstance(visible_output, str) or not visible_output.strip():
        raise E3AnchorValidationError("visible_output must be a non-empty string")
    anchor_ids = [anchor.territory_id for anchor in anchors]
    if not anchor_ids or len(anchor_ids) != len(set(anchor_ids)):
        raise E3AnchorValidationError("anchors must contain unique territory IDs")
    known_ids = set(anchor_ids)
    covered: set[str] = set()
    for item in evidence:
        if item.territory_id not in known_ids:
            raise E3AnchorValidationError(f"evidence names unknown territory {item.territory_id!r}")
        if not isinstance(item.excerpt, str) or not item.excerpt or item.excerpt not in visible_output:
            raise E3AnchorValidationError(
                f"evidence excerpt for {item.territory_id!r} must be a non-empty exact output substring"
            )
        covered.add(item.territory_id)
    missing = tuple(territory_id for territory_id in anchor_ids if territory_id not in covered)
    return E3CoverageResult(
        layer="DETERMINISTIC_CHECK",
        check_id="E3_KNOWN_SUPPORTED_TERRITORIES_LOWER_BOUND",
        status="FAIL" if missing else "PASS",
        covered_territory_ids=tuple(territory_id for territory_id in anchor_ids if territory_id in covered),
        missing_territory_ids=missing,
    )
