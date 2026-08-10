#!/usr/bin/env python3
"""Standalone CLI runner for P4-B demo scenarios.

Uses a ScriptedAdapter (in-process, no network) to execute scenarios from
``scenarios.json`` deterministically.

Usage::

    .venv/bin/python docs/beerlight_demo_rc/demo_runner.py S1
    .venv/bin/python docs/beerlight_demo_rc/demo_runner.py --all
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from prism.beerlight_demo_rc.auto import AUTO_PROTOCOL_VERSION, run_auto


_HERE = Path(__file__).resolve().parent
_SCENARIOS_PATH = _HERE / "scenarios.json"


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


class ScriptedAdapter:
    """In-process fake that returns pre-scripted responses in order."""

    def __init__(self, responses: list[Mapping[str, Any]]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def invoke(self, stage: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        payload_copy = deepcopy(dict(payload))
        self.calls.append(
            {
                "ordinal": len(self.calls) + 1,
                "stage": stage,
                "payload_sha256": _digest(payload_copy),
                "payload": payload_copy,
            }
        )
        return self.responses.pop(0)


def _load_scenarios() -> list[dict[str, Any]]:
    data = json.loads(_SCENARIOS_PATH.read_text(encoding="utf-8"))
    return data["scenarios"]


def _run_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    adapter = ScriptedAdapter(scenario["adapter_responses"])
    result = run_auto(
        task=scenario["task"],
        context=scenario["context"],
        source_data=scenario["source_data"],
        adapter=adapter,
        explore_mode=scenario["explore_mode"],
    )
    return {
        "schema_version": "beerlight-demo-rc-p4-b-runner-v1",
        "protocol_version": AUTO_PROTOCOL_VERSION,
        "scenario_id": scenario["id"],
        "scenario_name": scenario["name"],
        "result": {
            "gate": result.gate,
            "selected_p_id": result.selected_p_id,
            "alternative_p_ids": [item.p_id for item in result.alternatives],
            "final_artifact": result.final_artifact,
        },
        "visible_outputs": {
            "EXPLORE": result.explore_visible_output,
            "DEEP": result.deep_visible_output,
            "MAKE": result.make_visible_output,
        },
        "call_ledger": adapter.calls,
        "call_counts": {
            "fake_adapter": len(adapter.calls),
            "real_subject_provider": 0,
            "evaluator": 0,
            "fallback": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run P4-B Beerlight demo scenarios."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("scenario_id", nargs="?", help="Scenario ID (e.g. S1)")
    group.add_argument("--all", action="store_true", help="Run all scenarios")
    args = parser.parse_args()

    scenarios = _load_scenarios()

    if args.all:
        targets = scenarios
    else:
        targets = [s for s in scenarios if s["id"] == args.scenario_id]
        if not targets:
            print(f"ERROR: scenario {args.scenario_id!r} not found", file=sys.stderr)
            return 1

    results: list[dict[str, Any]] = []
    for scenario in targets:
        output = _run_scenario(scenario)
        results.append(output)

    if args.all:
        print(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(results[0], ensure_ascii=False, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
