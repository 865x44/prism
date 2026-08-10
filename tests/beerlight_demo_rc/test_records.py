from __future__ import annotations

import json

import pytest

from prism.beerlight_demo_rc.records import (
    RUN_RECORD_SCHEMA_VERSION,
    RunRecordValidationError,
    validate_run_record,
    write_run_record,
    write_visible_output,
)


def material_record() -> dict:
    return {
        "schema_version": RUN_RECORD_SCHEMA_VERSION,
        "run_id": "beerlight-demo-rc-p1-ws3-test",
        "phase": "P1",
        "started_at": "2026-08-10T00:00:00+05:00",
        "git_head": "f8315e8ae2c8b6cc0d3adbf87d8b3f9d330c3bd4",
        "subject_config_identity": "LOCAL_DEMO_RC_REFERENCE_SUBJECT",
        "subject_config_sha256": "f62ab8b26b33c3bb1a00402644e7ebbf2d533d3893381056b168f9e771be2d2f",
        "evaluator_config_identity": "UNQUALIFIED_DIAGNOSTIC_INSTRUMENT",
        "evaluator_config_sha256": "fd61b09224ed93c9c8778a9676003501c2dbb0d75d2a38a80ea92ef385bd9993",
        "fixture_schema_version": "beerlight-demo-rc-fixture-v1",
        "predicate_version": "semantic-predicates-v1-provisional",
        "input_sha256_manifest": "prism-runs/p0/input-manifest.json",
        "raw_visible_outputs": ["raw/E3-output.md"],
        "deterministic_results": [{"layer": "DETERMINISTIC_CHECK", "status": "PASS"}],
        "semantic_diagnostic_results": [
            {"layer": "SEMANTIC_JUDGMENT", "status": "EVAL_ERROR", "reason": "provider unavailable"}
        ],
        "classification": ["EVAL_ERROR", "INFRASTRUCTURE_ERROR"],
        "cost": {"subject_calls": 0, "evaluator_calls": 0},
        "notes": ["No provider call was attempted."],
    }


def test_writer_preserves_result_layer_separation_and_is_write_once(tmp_path):
    record = material_record()
    write_visible_output(tmp_path, "raw/E3-output.md", "Visible fixture output")
    path = write_run_record(tmp_path, record)
    assert json.loads(path.read_text(encoding="utf-8"))["classification"] == ["EVAL_ERROR", "INFRASTRUCTURE_ERROR"]
    with pytest.raises(FileExistsError):
        write_run_record(tmp_path, record)


def test_eval_error_cannot_be_subject_failure():
    record = material_record() | {
        "classification": ["SUBJECT_FAILURE", "EVAL_ERROR"],
    }
    with pytest.raises(RunRecordValidationError, match="EVAL_ERROR alone"):
        validate_run_record(record)


def test_record_rejects_artifact_path_escape():
    record = material_record() | {"raw_visible_outputs": ["../outside.md"]}
    with pytest.raises(RunRecordValidationError, match="unsafe artifact path"):
        validate_run_record(record)
