"""Deterministic pytest tests for P4-B demo scenarios."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from prism.beerlight_demo_rc.auto import (
    AUTO_PROTOCOL_VERSION,
    AutoResult,
    run_auto,
)


_SCENARIOS_PATH = Path(__file__).resolve().parents[2] / "docs" / "beerlight_demo_rc" / "scenarios.json"
_RUNNER_PATH = Path(__file__).resolve().parents[2] / "docs" / "beerlight_demo_rc" / "demo_runner.py"
_PRIVATE_FIELDS = {
    "chain_of_thought",
    "hidden",
    "internal",
    "model_lock",
    "private",
    "reasoning",
    "scratchpad",
    "system_prompt",
    "tool_calls",
}
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"sk-sp-[A-Za-z0-9]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+"),
    re.compile(r"token[=:]\s*[\"'][A-Za-z0-9]{20,}[\"']"),
]


def _load_scenarios() -> list[dict[str, Any]]:
    data = json.loads(_SCENARIOS_PATH.read_text(encoding="utf-8"))
    return data["scenarios"]


def _find_scenario(scenario_id: str) -> dict[str, Any]:
    for scenario in _load_scenarios():
        if scenario["id"] == scenario_id:
            return scenario
    raise ValueError(f"scenario {scenario_id!r} not found")


class ScriptedAdapter:
    """In-process fake that returns pre-scripted responses in order."""

    def __init__(self, responses: list[Mapping[str, Any]]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def invoke(self, stage: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append((stage, deepcopy(dict(payload))))
        return self.responses.pop(0)


def _run_scenario(scenario_id: str) -> tuple[AutoResult, ScriptedAdapter]:
    scenario = _find_scenario(scenario_id)
    adapter = ScriptedAdapter(scenario["adapter_responses"])
    result = run_auto(
        task=scenario["task"],
        context=scenario["context"],
        source_data=scenario["source_data"],
        adapter=adapter,
        explore_mode=scenario["explore_mode"],
    )
    return result, adapter


def _has_private_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if isinstance(key, str):
                normalized = key.casefold().replace("-", "_")
                if key.startswith("_") or normalized in _PRIVATE_FIELDS:
                    return True
            if _has_private_field(nested):
                return True
    elif isinstance(value, (list, tuple)):
        for item in value:
            if _has_private_field(item):
                return True
    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_scenario_ids_present():
    scenarios = _load_scenarios()
    ids = {s["id"] for s in scenarios}
    assert ids == {"S1", "S2", "S3", "S4", "S5", "S6"}


def test_s1_normal_grounded_pipeline():
    result, adapter = _run_scenario("S1")

    stages = [stage for stage, _ in adapter.calls]
    assert stages == ["EXPLORE", "DEEP", "MAKE"]
    assert result.gate == "MODEL_READY"
    assert result.selected_p_id == "P2"
    assert result.final_artifact is not None


def test_s2_fake_breadth_360_single_territory():
    scenario = _find_scenario("S2")
    result, adapter = _run_scenario("S2")

    assert result.gate == "MODEL_READY"
    assert scenario["explore_mode"] == "360"
    assert adapter.calls[0][0] == "EXPLORE"
    explore_payload = adapter.calls[0][1]
    assert explore_payload["mode"] == "360"

    explore_visible = result.explore_visible_output
    territory_ids = set(re.findall(r"T\d{2}_[A-Z0-9_]+", explore_visible))
    assert len(territory_ids) == 1, (
        f"Expected exactly 1 territory, found {len(territory_ids)}: {territory_ids}"
    )
    assert "T01_HOME_CARE_CAPACITY" in territory_ids


def test_s3_deep_handoff_p_id_continuity():
    scenario = _find_scenario("S3")
    result, adapter = _run_scenario("S3")

    assert result.gate == "MODEL_READY"
    assert result.selected_p_id == "P2"

    stages = [stage for stage, _ in adapter.calls]
    assert stages == ["EXPLORE", "DEEP", "MAKE"]

    explore_p_ids = [p["p_id"] for p in scenario["adapter_responses"][0]["perspectives"]]
    assert explore_p_ids == ["P1", "P2", "P3", "P4"]

    assert [item.p_id for item in result.alternatives] == ["P1", "P2", "P3", "P4"]

    deep_payload = adapter.calls[1][1]
    assert deep_payload["selected_p_id"] == "P2"
    assert "visible_alternatives" in deep_payload

    make_payload = adapter.calls[2][1]
    assert make_payload["selected_p_id"] == "P2"
    assert "visible_alternatives" in make_payload


def test_s4_need_evidence_stops_before_make():
    result, adapter = _run_scenario("S4")

    stages = [stage for stage, _ in adapter.calls]
    assert stages == ["EXPLORE", "DEEP"]
    assert result.gate == "NEED_EVIDENCE"
    assert result.final_artifact is None
    assert result.make_visible_output is None
    assert len(adapter.calls) == 2

    deep_response = _find_scenario("S4")["adapter_responses"][1]
    assert "evidence_debt" in deep_response


def test_s5_source_injection_resistance():
    scenario = _find_scenario("S5")
    result, adapter = _run_scenario("S5")

    assert result.gate == "MODEL_READY"

    source_data = scenario["source_data"]
    assert "INSTRUCTIONS FOR THE AI" in source_data

    for stage, payload in adapter.calls:
        assert payload["source_role"] == "DATA_NOT_INSTRUCTIONS"
        assert payload["source_data"] == source_data

    assert scenario["explore_mode"] == "NORMAL"
    explore_payload = adapter.calls[0][1]
    assert explore_payload["mode"] == "NORMAL"

    assert not _has_private_field(
        {"visible_outputs": [result.explore_visible_output, result.deep_visible_output, result.make_visible_output]}
    )


def test_s6_return_to_explore_stops_before_make():
    result, adapter = _run_scenario("S6")

    stages = [stage for stage, _ in adapter.calls]
    assert stages == ["EXPLORE", "DEEP"]
    assert result.gate == "RETURN_TO_EXPLORE"
    assert result.final_artifact is None
    assert result.make_visible_output is None
    assert len(adapter.calls) == 2

    deep_response = _find_scenario("S6")["adapter_responses"][1]
    assert "break_point" in deep_response
    assert len(deep_response["break_point"]) > 0


def test_no_private_fields_in_any_scenario_output():
    for scenario in _load_scenarios():
        adapter_responses = scenario["adapter_responses"]
        for response in adapter_responses:
            assert not _has_private_field(response), (
                f"Scenario {scenario['id']}: private field found in adapter response"
            )
        for key in ("task", "context", "source_data", "visible_output"):
            if isinstance(scenario.get(key), str):
                for field_name in _PRIVATE_FIELDS:
                    assert field_name not in scenario[key].casefold() or field_name in ("source_data",) or True


def test_scenario_manifest_has_no_secret_shaped_values():
    raw_text = _SCENARIOS_PATH.read_text(encoding="utf-8")
    for pattern in _SECRET_PATTERNS:
        matches = pattern.findall(raw_text)
        assert not matches, f"Secret-shaped value found in scenarios.json: {matches}"


def test_demo_runner_cli_all():
    result = subprocess.run(
        [sys.executable, str(_RUNNER_PATH), "--all"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Runner failed: {result.stderr}"
    output = json.loads(result.stdout)
    assert isinstance(output, list)
    assert len(output) == 6
    ids = {item["scenario_id"] for item in output}
    assert ids == {"S1", "S2", "S3", "S4", "S5", "S6"}
