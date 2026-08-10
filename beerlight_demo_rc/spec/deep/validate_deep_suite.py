#!/usr/bin/env python3
"""Offline structural validator for the provisional Deep D1-D8 suite."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

EXPECTED_IDS = {f"D{number}" for number in range(1, 9)}
PREDICATES = {
    "DISTINCT_MODEL", "COVERAGE_BREADTH", "SEMANTIC_PRESERVATION",
    "SOURCE_GROUNDING", "EPISTEMIC_HONESTY", "MODE_BOUNDARY",
    "GATE_INTEGRITY", "SOURCE_AS_DATA",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--hash-manifest", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    spec = root / "beerlight_demo_rc/spec/deep"
    fixtures = load_json(spec / "deep_d1_d8_fixtures.json")
    mapping = load_json(spec / "deep_sparse_mapping.json")
    sequences = load_json(spec / "deep_sequence_metadata.json")
    hashes = load_json(args.hash_manifest)
    errors: list[str] = []

    ids = [item.get("id") for item in fixtures.get("fixtures", [])]
    if set(ids) != EXPECTED_IDS or len(ids) != len(EXPECTED_IDS):
        errors.append(f"fixture IDs must be exactly D1-D8 once; got {ids}")
    if set(fixtures.get("fixed_fixture_ids", [])) != EXPECTED_IDS:
        errors.append("fixed_fixture_ids must be exactly D1-D8")
    map_ids = [item.get("fixture_id") for item in mapping.get("mapping", [])]
    if set(map_ids) != EXPECTED_IDS or len(map_ids) != len(EXPECTED_IDS):
        errors.append(f"mapping IDs must resolve exactly D1-D8 once; got {map_ids}")
    for row in mapping.get("mapping", []):
        unknown = set(row.get("semantic_predicates", [])) - PREDICATES
        if unknown:
            errors.append(f"{row.get('fixture_id')} has unknown predicates: {sorted(unknown)}")
    d3 = sequences.get("D3", {})
    if "unchanged_conclusion" not in d3 or "strongest" not in d3["unchanged_conclusion"]:
        errors.append("D3 must state the strongest-objection unchanged-conclusion proof condition")
    d8 = sequences.get("D8", {})
    if d8.get("pre_patch_classification") != "KNOWN_PREPATCH_GAP":
        errors.append("D8 pre-patch classification must be KNOWN_PREPATCH_GAP")
    if d8.get("post_patch_failure_classification") != "POSTPATCH_REGRESSION_FAILURE":
        errors.append("D8 post-patch classification must be POSTPATCH_REGRESSION_FAILURE")
    d8_fixture = next((item for item in fixtures.get("fixtures", []) if item.get("id") == "D8"), {})
    if d8_fixture.get("execution_phase") != "POST_PATCH_ONLY":
        errors.append("D8 must be POST_PATCH_ONLY")
    expected_hashes = hashes.get("files", {})
    if not expected_hashes:
        errors.append("hash manifest has no files")
    for relative, expected in expected_hashes.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing immutable-pack file: {relative}")
        elif digest(path) != expected:
            errors.append(f"immutable-pack hash mismatch: {relative}")
    if errors:
        print("DEEP_SUITE_VALIDATION_FAIL")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("DEEP_SUITE_VALIDATION_OK")
    print("fixture_ids=" + ",".join(sorted(ids)))
    print("mapping_ids=" + ",".join(sorted(map_ids)))
    print(f"immutable_pack_files_verified={len(expected_hashes)}")
    print("provider_calls=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
