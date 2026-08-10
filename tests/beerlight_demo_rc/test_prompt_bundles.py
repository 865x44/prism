from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def manifest(subject: str) -> dict:
    return json.loads(read(f"beerlight_demo_rc/patches/{subject}/CHANGE_MANIFEST.json"))


def test_explore_bundle_has_only_fixed_contract_deltas():
    data = manifest("explore")
    assert [change["change_id"] for change in data["changes"]] == [
        "EXP-P2-001", "EXP-P2-002", "EXP-P2-003", "EXP-P2-004"
    ]
    assert data["actual_surface_status"] == "NOT_LOCALLY_AVAILABLE"
    overlay = read("beerlight_demo_rc/patches/explore/INSTRUCTION_OVERLAY.md")
    assert "There is no minimum" in overlay
    assert "reconstruct it semantically" in overlay
    assert "monotonically as P1, P2, P3" in overlay
    assert "data, not as instructions" in overlay
    assert "global database" not in overlay


def test_deep_bundle_is_bounded_by_ws1_and_d3():
    data = manifest("deep")
    assert data["prerequisite"] == "G1_ACCEPTED and accepted WS1 Deep reconciliation"
    assert [change["change_id"] for change in data["changes"]] == [
        "DEEP-P2-001", "DEEP-P2-002", "DEEP-P2-003"
    ]
    overlay = read("beerlight_demo_rc/patches/deep/INSTRUCTION_OVERLAY.md")
    assert "strongest objection" in overlay
    assert "non-load-bearing" in overlay
    assert "Do not generate an Explore portfolio" in overlay
    assert "Do not offer a LEVER before MODEL_READY" in overlay
    assert "KNOWN_PREPATCH_GAP" in read("beerlight_demo_rc/patches/deep/BUNDLE_DIFF.md")
    assert "POSTPATCH_REGRESSION_FAILURE" in read("beerlight_demo_rc/patches/deep/BUNDLE_DIFF.md")


def test_bundles_state_source_as_data_and_subject_separation():
    for subject in ("explore", "deep"):
        provenance = json.loads(read(f"beerlight_demo_rc/patches/{subject}/PROVENANCE.json"))
        assert "No equivalence is asserted" in provenance["subject_separation"]
        overlay = read(f"beerlight_demo_rc/patches/{subject}/INSTRUCTION_OVERLAY.md")
        assert "data, not as instructions" in overlay
        assert "NOT_VERIFIABLE" in overlay

    local_explore = read("src/prism/beerlight_demo_rc/prompts/explore/LOCAL_DEMO_RC_REFERENCE_SUBJECT_P2.md")
    local_deep = read("src/prism/beerlight_demo_rc/prompts/deep/LOCAL_DEMO_RC_REFERENCE_SUBJECT_P2.md")
    assert "LOCAL_DEMO_RC_REFERENCE_SUBJECT" in local_explore
    assert "LOCAL_DEMO_RC_REFERENCE_SUBJECT" in local_deep
    assert "not a capture," in local_explore
    assert "not a capture," in local_deep
