"""
Tests for the deterministic run.md renderer (`bin/pizm-session-bundle render`, Slice C3).

Fixtures are built through the REAL checkpoint primitive (`bin/pizm-checkpoint freeze`),
so every artifact is a genuine frozen checkpoint output with sidecars.

Covers:
- required readable sections; ALL generated candidates appear compactly;
- machine bookkeeping omitted (no JSON dumps, hashes, schema strings);
- byte-identical determinism for identical inputs;
- pure function of current frozen inputs (mutated input -> changed output);
- fail-closed exit codes: missing artifact, incomplete lever pair, sidecar
  mismatch, non-AUTO route;
- P-target and B-target happy paths; honest-stop rendering;
- zero provider/network vocabulary in the renderer source.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_CLI = str(REPO_ROOT / "bin" / "pizm-session-bundle")
CHECKPOINT_CLI = str(REPO_ROOT / "bin" / "pizm-checkpoint")
SKILL_ROOT = REPO_ROOT / "docs" / "pizm-skill-staged-2026-08-24"

TASK_TEXT = "Reduce PR cycle time in our platform team"


def run_render(run_dir, task, output):
    return subprocess.run(
        [sys.executable, BUNDLE_CLI, "render", "--run-dir", str(run_dir),
         "--task", task, "--output", str(output)],
        capture_output=True, text=True,
    )


def freeze_stage(project_root: Path, stage: str, run_id: str, payload: dict, target: str = None, artifact_suffix: str = None) -> None:
    """Freeze one stage through the real checkpoint CLI."""
    import tempfile

    fd_input = project_root / f"_input_{stage}_{target or 'main'}_{artifact_suffix or 'none'}.json"
    fd_input.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    cmd = [
        sys.executable, CHECKPOINT_CLI, "freeze", "--stage", stage,
        "--run-id", run_id, "--input", str(fd_input),
        "--project-root", str(project_root), "--skill-root", str(SKILL_ROOT),
    ]
    if target:
        cmd.extend(["--target", target])
    if artifact_suffix:
        cmd.extend(["--artifact-suffix", artifact_suffix])
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"{stage} freeze failed: {res.stderr}"
    fd_input.unlink()

# ---------------------------------------------------------------------------
# Frozen artifact payloads (checkpoint-schema-valid)
# ---------------------------------------------------------------------------


def candidates_payload():
    return {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "Feedback Latency Constraint",
                "semantic_core": {
                    "claim": "Review latency drives batch inflation",
                    "structural_shift": "From capacity to feedback frequency",
                    "mechanism": "Slow reviews induce batching",
                    "grounding_anchor": "Three-day PR turnaround observed",
                    "what_becomes_visible": "Batch size is adaptive",
                    "boundary": "Round-trip exceeds task duration",
                },
                "epistemics": {"supported": ["turnaround"], "inferred": ["amortization"],
                               "speculative": [], "unknown": []},
            },
            {
                "candidate_id": "c02",
                "title": "Meeting Load Spiral",
                "semantic_core": {
                    "claim": "Meetings spawn coordination meetings",
                    "structural_shift": "Coordination as load",
                    "mechanism": "Each meeting books two more",
                    "grounding_anchor": "Calendar audit",
                    "what_becomes_visible": "Coordination debt",
                    "boundary": "Orgs over twenty people",
                },
                "epistemics": {"supported": [], "inferred": [], "speculative": ["spiral"],
                               "unknown": []},
            },
        ],
    }


def pass2_candidates_payload():
    return {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "360",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "Ownership Diffusion Boundary",
                "semantic_core": {
                    "claim": "Shared ownership creates tragedy of review queue",
                    "structural_shift": "Shift from queue length to accountability location",
                    "mechanism": "No single owner for multi-service changes",
                    "grounding_anchor": "PRs touching multiple repos stall longest",
                    "what_becomes_visible": "Cross-boundary coordination cost",
                    "boundary": "Mono-repo vs multi-repo architecture",
                },
                "difference_from_prior": "Attacks ownership locus rather than latency or meetings.",
                "epistemics": {"supported": ["stall data"], "inferred": ["agency diffusion"], "speculative": [], "unknown": []},
            }
        ],
    }

def search_field_payload(candidates_sha1: str, candidates_sha2: str = None):
    passes = [
        {"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": candidates_sha1}
    ]
    entries = ["pass01:c01", "pass01:c02"]
    if candidates_sha2:
        passes.append({
            "pass_id": "pass02",
            "candidates_ref": "candidates-pass02.json",
            "frozen_hash": candidates_sha2,
        })
        entries.append("pass02:c01")
    return {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "passes": passes,
        "entries": entries,
    }


def portfolio_payload(field_hash: str, target_type="P", target_id="P1"):
    data = {
        "schema_version": "pizm-portfolio-selection-v1",
        "stage": "portfolio",
        "route": "AUTO",
        "field_hash": field_hash,
        "candidate_assessments": [
            {
                "candidate_ref": "pass01:c01",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "Latency-to-batching mechanism",
                "nearest_overlap": None,
                "reason": "Clear causal mechanism linking latency to batch sizing",
            },
            {
                "candidate_ref": "pass01:c02",
                "disposition": "DROP",
                "standalone_quality": "weak",
                "unique_residue": "",
                "nearest_overlap": None,
                "reason": "Generic platitude lacking structural mechanism",
            },
        ],
        "bundles": [],
        "auto_target": {"target_type": target_type, "target_id": target_id},
    }
    if target_type == "B":
        data["candidate_assessments"][1]["disposition"] = "KEEP"
        data["bundles"] = [
            {
                "bundle_id": "B1",
                "member_refs": ["pass01:c01", "pass01:c02"],
                "bundle_thesis": "Latency and coordination form one scheduling system",
                "composition_gain": "Predicts oscillation neither member predicts",
                "new_consequence_or_prediction": "Batch size tracks meeting cadence",
                "internal_tension": "Meetings reduce batching need while adding load",
                "weakest_link": "c02 grounding is thin",
                "member_roles": {"pass01:c01": "mechanism core",
                                 "pass01:c02": "counter-mechanism"},
                "member_ablation": {"pass01:c01": "loses mechanism",
                                    "pass01:c02": "loses tension"},
            }
        ]
    return data


def development_payload(target_type="P", target_id="P1"):
    if target_type == "P":
        identity_lock = {
            "p_id": target_id,
            "title": "Feedback Latency Constraint",
            "core_claim": "Review latency drives batch inflation",
            "structural_shift": "Capacity to feedback frequency",
            "mechanism": "Slow reviews induce batching",
            "boundary": "Round-trip exceeds task duration",
        }
    else:
        identity_lock = {
            "bundle_id": target_id,
            "member_refs": ["pass01:c01", "pass01:c02"],
            "title": "Scheduling System Bundle",
            "core_claim": "Latency and coordination form one scheduler",
            "structural_shift": "Two pressures unified",
            "mechanism": "Latency batches work; meetings reset it",
            "boundary": "Small orgs exempt",
        }
    model = {
        "thesis": "Review latency is the hidden scheduler of engineering output.",
        "synthesis": (
            "When review round-trips exceed task duration, engineers rationally batch "
            "changes, which inflates review size, which further slows reviews: a "
            "self-reinforcing queue that no capacity fix dissolves."
        ),
        "dynamics": "The loop equilibrates at the maximum batch size the culture tolerates.",
        "mechanism_chain": [
            "Review latency rises",
            "Workers batch changes to amortize switching",
            "Reviews grow larger and slower",
        ],
        "implications": ["Small-batch mandates fail without latency fixes"],
        "predictions_or_observables": [
            "Batch size correlates with review latency",
            "Latency reduction shrinks batches within weeks",
        ],
        "break_conditions": ["Async review cultures"],
        "unresolved_tensions": [],
        "evidence_debt": ["Measure latency-batch correlation on real logs"],
        "load_bearing_claims": [
            {
                "claim": "Batching is rational amortization",
                "role_in_model": "core mechanism",
                "what_would_weaken_or_refute": "Batch size unchanged when latency varies",
                "epistemic_status": "INFERRED",
            },
            {
                "claim": "Three-day turnaround observed",
                "role_in_model": "grounding anchor",
                "what_would_weaken_or_refute": "Logs show sub-day turnaround",
                "epistemic_status": "SUPPORTED",
            },
        ],
    }
    if target_type == "B":
        members = identity_lock["member_refs"]
        model["unresolved_tensions"] = ["Meeting time trades off against batch time"]
        model["member_contributions"] = {m: f"{m} contributes its mechanism" for m in members}
        model["member_ablation"] = {m: f"removing {m} loses its residue" for m in members}
    return {
        "schema_version": "pizm-development-v2",
        "stage": "development-v2",
        "target": {"target_type": target_type, "target_id": target_id},
        "identity_lock": identity_lock,
        "developed_model": model,
    }


def review_payload(target_type="P", target_id="P1"):
    findings = {
        "cross_field_contradictions": [],
        "unsupported_specificity": [],
        "epistemic_laundering": [],
        "unresolved_load_bearing_contradiction": False,
        "identity_drift": None,
        "cost_relocation": None,
        "round_trip_skeleton": "latency -> batching -> larger diffs -> slower reviews",
    }
    if target_type == "B":
        findings["member_ablation"] = "Both members load-bearing; ablation reasoning holds."
    return {
        "schema_version": "pizm-deep-review-v2",
        "stage": "deep-review-v2",
        "frozen_hash": "b" * 64,
        "target_type": target_type,
        "target_id": target_id,
        "terminal_state": "MODEL_READY",
        "identity_verified": True,
        "independent_countermodel": "Batching could be status ritual rather than latency response.",
        "cheapest_discriminating_test": "Correlate per-developer batch size with observed latency.",
        "load_bearing_reassessment": [
            {"claim": "Batching is rational amortization", "critic_epistemic_status": "INFERRED"}
        ],
        "findings": findings,
        "evidence_debt": [],
        "verdict_rationale": "Mechanism survives the countermodel; predictions observable.",
    }


def lever_design_payload():
    return {
        "schema_version": "pizm-lever-design-v1",
        "stage": "lever",
        "levers": [
            {
                "lever_id": "L1",
                "intervention_or_test_point": "Cap synchronous meeting hours per week",
                "model_link": "Coordination pressure feeds the latency loop",
                "minimum_bounded_move": "One team, two weeks",
                "expected_observation_or_response": "Batch size drops measurably",
                "disconfirming_signal": "No change in batch size",
                "stop_condition": "Two cycles without effect",
                "remaining_assumptions": "Teams report hours honestly",
            }
        ],
    }


def lever_review_payload(outcome="LEVER"):
    verdicts = [{"lever_id": "L1", "verdict": "ACCEPT"}] if outcome == "LEVER" else []
    return {
        "schema_version": "pizm-lever-review-v1",
        "stage": "lever",
        "frozen_hash": "c" * 64,
        "outcome": outcome,
        "verdicts": verdicts,
        "verdict_rationale": (
            "Move is bounded and observable."
            if outcome == "LEVER"
            else "Nothing decision-relevant to try."
        ),
    }


# ---------------------------------------------------------------------------
# Fixtures built through the real checkpoint primitive
# ---------------------------------------------------------------------------


def _freeze_full_run(project_root: Path, target_type="P", with_lever=True,
                     terminal_state="MODEL_READY"):
    run_id = f"render{target_type.lower()}"
    tid = "P1" if target_type == "P" else "B1"
    cand_data = candidates_payload()
    freeze_stage(project_root, "explore", run_id, cand_data)
    candidates_sha = (project_root / ".ai" / "pizm" / f"run-{run_id}" / "candidates.sha256").read_text().strip()

    search_field_data = search_field_payload(candidates_sha)
    freeze_stage(project_root, "search-field", run_id, search_field_data)
    field_hash = (project_root / ".ai" / "pizm" / f"run-{run_id}" / "search-field.sha256").read_text().strip()

    freeze_stage(project_root, "portfolio", run_id, portfolio_payload(field_hash, target_type, tid))

    dev_data = development_payload(target_type, tid)
    freeze_stage(project_root, "development-v2", run_id, dev_data)
    dev_sha = (project_root / ".ai" / "pizm" / f"run-{run_id}" / "development-v2.sha256").read_text().strip()

    review = review_payload(target_type, tid)
    review["terminal_state"] = terminal_state
    review["frozen_hash"] = dev_sha
    freeze_stage(project_root, "deep-review-v2", run_id, review)

    if with_lever:
        lever_data = lever_design_payload()
        freeze_stage(project_root, "lever-design", run_id, lever_data)
        lever_sha = (project_root / ".ai" / "pizm" / f"run-{run_id}" / "design.sha256").read_text().strip()
        lever_rev = lever_review_payload()
        lever_rev["frozen_hash"] = lever_sha
        freeze_stage(project_root, "lever-review", run_id, lever_rev)

    return project_root / ".ai" / "pizm" / f"run-{run_id}"
@pytest.fixture
def frozen_run_p(tmp_path):
    return _freeze_full_run(tmp_path, "P")


@pytest.fixture
def frozen_run_b(tmp_path):
    return _freeze_full_run(tmp_path, "B")


# ---------------------------------------------------------------------------
# Section coverage and readability
# ---------------------------------------------------------------------------


def test_required_sections_and_all_candidates_present(frozen_run_p, tmp_path):
    out = tmp_path / "run.md"
    res = run_render(frozen_run_p, TASK_TEXT, out)
    assert res.returncode == 0, res.stderr
    text = out.read_text(encoding="utf-8")

    for heading in (
        "# Prism AUTO",
        "## Task",
        "## Search",
        "## Portfolio",
        "## Selected model",
        "## Deep",
        "### Mechanism and dynamics",
        "### Load-bearing claims",
        "### Predictions",
        "### Evidence debt",
        "## Critic",
        "## Lever",
        "## Final",
        "## Machine artifacts",
    ):
        assert heading in text, f"missing heading: {heading}"

    assert TASK_TEXT in text
    # No Bundles section when the portfolio proposes none
    assert "## Bundles" not in text

    # ALL generated candidates appear compactly under Search
    assert text.count("### Candidate:") == 2
    assert "Feedback Latency Constraint" in text
    assert "Meeting Load Spiral" in text

    # Portfolio card for the promoted perspective
    assert "### P1 — Feedback Latency Constraint" in text

    # Deep rendered fully enough for normal reading
    assert "self-reinforcing queue that no capacity fix dissolves" in text
    assert "Batching is rational amortization" in text

    # Critic rendered fully enough for normal reading
    assert "status ritual rather than latency response" in text
    assert "Correlate per-developer batch size with observed latency" in text

    # Lever outcome and verdict visible
    assert "### L1" in text
    assert "ACCEPT" in text

    # Final block summarizes verdict
    assert "- Terminal state: MODEL_READY" in text


def test_honest_stop_rendered_when_not_ready(tmp_path):
    run_dir = _freeze_full_run(tmp_path, "P", with_lever=False,
                               terminal_state="NEED_EVIDENCE")
    out = tmp_path / "run.md"
    res = run_render(run_dir, TASK_TEXT, out)
    assert res.returncode == 0, res.stderr
    text = out.read_text(encoding="utf-8")
    assert "## Lever" not in text
    assert "- Terminal state: NEED_EVIDENCE" in text
    assert "Honest stop: NEED_EVIDENCE" in text


def test_bundle_target_renders_members_and_composition(frozen_run_b, tmp_path):
    out = tmp_path / "run.md"
    res = run_render(frozen_run_b, TASK_TEXT, out)
    assert res.returncode == 0, res.stderr
    text = out.read_text(encoding="utf-8")

    assert "## Bundles" in text
    assert "### B1 — P1 + P2" in text
    assert "Bundle thesis: Latency and coordination form one scheduling system" in text
    assert "Composition gain: Predicts oscillation neither member predicts" in text
    assert "### B1 — Scheduling System Bundle" in text
    assert "Member contributions (bundle):" in text
    assert "Both members load-bearing; ablation reasoning holds." in text
    assert "- Selected: B1 — Scheduling System Bundle" in text


# ---------------------------------------------------------------------------
# Machine bookkeeping stays out of the readable document
# ---------------------------------------------------------------------------


def test_machine_bookkeeping_absent(frozen_run_p, tmp_path):
    out = tmp_path / "run.md"
    res = run_render(frozen_run_p, TASK_TEXT, out)
    assert res.returncode == 0, res.stderr
    text = out.read_text(encoding="utf-8")

    # No raw JSON dumps
    assert "{" not in text
    assert "}" not in text
    # No schema strings, hashes, byte counts, repair/host counters
    lowered = text.lower()
    for term in (
        "schema_version",
        "sha256",
        ".sha256",
        "meta.json",
        "frozen_hash",
        "payload",
        "repair",
        "host_inference",
        "semantic_stage_count",
    ):
        assert term not in lowered, f"machine bookkeeping leaked: {term}"

    # Machine artifacts lists short relative names only
    machine = text.split("## Machine artifacts")[1]
    for name in (
        "candidates.json",
        "portfolio.json",
        "development-v2.json",
        "deep-review-v2.json",
        "search-field.json",
        "design.json",
        "review.json",
    ):
        assert name in machine


# ---------------------------------------------------------------------------
# Determinism and purity
# ---------------------------------------------------------------------------


def test_render_is_byte_identical_across_runs(frozen_run_p, tmp_path):
    out1 = tmp_path / "a.md"
    out2 = tmp_path / "b.md"
    assert run_render(frozen_run_p, TASK_TEXT, out1).returncode == 0
    assert run_render(frozen_run_p, TASK_TEXT, out2).returncode == 0
    assert out1.read_bytes() == out2.read_bytes()


def test_pure_function_of_current_inputs(frozen_run_p, tmp_path):
    out1 = tmp_path / "before.md"
    assert run_render(frozen_run_p, TASK_TEXT, out1).returncode == 0

    # Mutate a frozen input (and refresh its sidecar): output must follow the
    # new input — the renderer is a pure function of current inputs, no cache.
    dev = json.loads((frozen_run_p / "development-v2.json").read_text())
    dev["developed_model"]["synthesis"] = "A wholly different synthesis sentence appears here."
    raw = json.dumps(dev, indent=2).encode("utf-8")
    (frozen_run_p / "development-v2.json").write_bytes(raw)
    import hashlib

    (frozen_run_p / "development-v2.sha256").write_text(
        hashlib.sha256(raw).hexdigest(), encoding="ascii"
    )

    out2 = tmp_path / "after.md"
    assert run_render(frozen_run_p, TASK_TEXT, out2).returncode == 0
    text2 = out2.read_text(encoding="utf-8")
    assert out1.read_bytes() != out2.read_bytes()
    assert "A wholly different synthesis sentence appears here." in text2
    assert "self-reinforcing queue" not in text2

    # An added stray file does not affect the output
    (frozen_run_p / "stray.txt").write_text("noise", encoding="utf-8")
    out3 = tmp_path / "stray.md"
    assert run_render(frozen_run_p, TASK_TEXT, out3).returncode == 0
    assert out3.read_bytes() == out2.read_bytes()


# ---------------------------------------------------------------------------
# Fail-closed behavior
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "victim",
    ["candidates.json", "portfolio.json", "development-v2.json", "deep-review-v2.json"],
)
def test_missing_artifact_fails_closed(frozen_run_p, tmp_path, victim):
    (frozen_run_p / victim).unlink()
    out = tmp_path / "run.md"
    res = run_render(frozen_run_p, TASK_TEXT, out)
    assert res.returncode != 0
    assert f"missing artifact: {victim}" in res.stderr
    assert not out.exists()


def test_missing_task_fails_closed(frozen_run_p, tmp_path):
    res = subprocess.run(
        [sys.executable, BUNDLE_CLI, "render", "--run-dir", str(frozen_run_p),
         "--task", "", "--output", str(tmp_path / "run.md")],
        capture_output=True, text=True,
    )
    assert res.returncode != 0
    assert "--task must be non-empty" in res.stderr


def test_incomplete_lever_pair_fails_closed(frozen_run_p, tmp_path):
    (frozen_run_p / "review.json").unlink()
    res = run_render(frozen_run_p, TASK_TEXT, tmp_path / "run.md")
    assert res.returncode != 0
    assert "missing artifact: review.json" in res.stderr


def test_sidecar_mismatch_fails_closed(frozen_run_p, tmp_path):
    path = frozen_run_p / "development-v2.json"
    path.write_bytes(path.read_bytes() + b" ")
    res = run_render(frozen_run_p, TASK_TEXT, tmp_path / "run.md")
    assert res.returncode != 0
    assert "hash mismatch for development-v2.json" in res.stderr


def test_non_auto_route_fails_closed(frozen_run_p, tmp_path):
    port = json.loads((frozen_run_p / "portfolio.json").read_text())
    port["route"] = "MANUAL"
    port["auto_target"] = None
    raw = json.dumps(port, indent=2).encode("utf-8")
    (frozen_run_p / "portfolio.json").write_bytes(raw)
    import hashlib

    (frozen_run_p / "portfolio.sha256").write_text(
        hashlib.sha256(raw).hexdigest(), encoding="ascii"
    )
    res = run_render(frozen_run_p, TASK_TEXT, tmp_path / "run.md")
    assert res.returncode != 0
    assert "AUTO portfolio" in res.stderr


def test_missing_run_dir_fails_closed(tmp_path):
    res = run_render(tmp_path / "does-not-exist", TASK_TEXT, tmp_path / "run.md")
    assert res.returncode != 0
    assert "does not exist" in res.stderr


# ---------------------------------------------------------------------------
# Zero-model guarantee in the code path
# ---------------------------------------------------------------------------


def test_renderer_source_has_no_provider_or_network_calls():
    source = Path(BUNDLE_CLI).read_text(encoding="utf-8").lower()
    for term in (
        "openai",
        "anthropic",
        "api_key",
        "urllib",
        "http.client",
        "requests.",
        "socket",
        "llm_call",
        "model_invoke",
    ):
        assert term not in source, f"forbidden provider/network term: {term}"


# ---------------------------------------------------------------------------
# Strict composite candidate index and reference validation tests (§1.4)
# ---------------------------------------------------------------------------


def test_exact_pass02_lookup_on_local_id_collision(tmp_path):
    """When pass01 and pass02 share local candidate ID 'c01', lookup resolves exact composite pass02:c01."""
    run_id = "test-collision"
    p1 = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "Pass 1 Title",
                "semantic_core": {"claim": "Pass 1 Claim", "structural_shift": "Shift 1", "mechanism": "Mech 1", "grounding_anchor": "Anchor 1", "what_becomes_visible": "Vis 1", "boundary": "Bound 1"},
                "epistemics": {"supported": ["t1"], "inferred": [], "speculative": [], "unknown": []},
            }
        ],
    }
    freeze_stage(tmp_path, "explore", run_id, p1)
    sha1 = (tmp_path / ".ai" / "pizm" / f"run-{run_id}" / "candidates.sha256").read_text().strip()

    p2 = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "360",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "Pass 2 Title",
                "semantic_core": {"claim": "Pass 2 Claim", "structural_shift": "Shift 2", "mechanism": "Mech 2", "grounding_anchor": "Anchor 2", "what_becomes_visible": "Vis 2", "boundary": "Bound 2"},
                "difference_from_prior": "Diff 2",
                "epistemics": {"supported": ["t2"], "inferred": [], "speculative": [], "unknown": []},
            }
        ],
    }
    freeze_stage(tmp_path, "explore", run_id, p2, artifact_suffix="pass02")
    sha2 = (tmp_path / ".ai" / "pizm" / f"run-{run_id}" / "candidates-pass02.sha256").read_text().strip()

    sf = {
        "schema_version": "pizm-search-field-v1",
        "stage": "search-field",
        "passes": [
            {"pass_id": "pass01", "candidates_ref": "candidates.json", "frozen_hash": sha1},
            {"pass_id": "pass02", "candidates_ref": "candidates-pass02.json", "frozen_hash": sha2},
        ],
        "entries": ["pass01:c01", "pass02:c01"],
    }
    freeze_stage(tmp_path, "search-field", run_id, sf)
    sf_sha = (tmp_path / ".ai" / "pizm" / f"run-{run_id}" / "search-field.sha256").read_text().strip()

    port = {
        "schema_version": "pizm-portfolio-selection-v2",
        "stage": "portfolio",
        "route": "AUTO",
        "field_ref": "search-field.json",
        "field_hash": sf_sha,
        "perspectives": {"P1": "pass02:c01"},
        "competition_status": "NO_SECOND_DEFENSIBLE_BUNDLE",
        "candidate_assessments": [
            {
                "candidate_ref": "pass02:c01",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "Pass 2 residue",
                "nearest_overlap": None,
                "reason": "Pass 2 selected",
            }
        ],
        "bundles": [],
        "auto_target": {"target_type": "P", "target_id": "P1"},
    }
    freeze_stage(tmp_path, "portfolio", run_id, port)

    dev = development_payload("P", "P1")
    dev["identity_lock"]["title"] = "Pass 2 Title"
    dev["identity_lock"]["core_claim"] = "Pass 2 Claim"
    freeze_stage(tmp_path, "development-v2", run_id, dev)
    dev_sha = (tmp_path / ".ai" / "pizm" / f"run-{run_id}" / "development-v2.sha256").read_text().strip()

    rev = review_payload("P", "P1")
    rev["frozen_hash"] = dev_sha
    freeze_stage(tmp_path, "deep-review-v2", run_id, rev)

    run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
    out = tmp_path / "collision.md"
    res = run_render(run_dir, TASK_TEXT, out)
    assert res.returncode == 0, res.stderr
    content = out.read_text(encoding="utf-8")
    # Must render Pass 2 Title under Portfolio for P1
    assert "### P1 — Pass 2 Title (`pass02:c01`)" in content
    assert "Pass 1 Title" not in content.split("## Portfolio")[1].split("## Machine artifacts")[0]


def test_duplicate_composite_candidate_keys_fails_closed(tmp_path):
    """Duplicate composite candidate keys within candidate payload fail closed."""
    run_dir = tmp_path / "run-dup"
    run_dir.mkdir(parents=True)
    p1 = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {"candidate_id": "c01", "title": "First", "semantic_core": {"claim": "A"}},
            {"candidate_id": "c01", "title": "Second", "semantic_core": {"claim": "B"}},
        ],
    }
    (run_dir / "candidates.json").write_text(json.dumps(p1))
    (run_dir / "candidates.sha256").write_text(__import__("hashlib").sha256(json.dumps(p1).encode()).hexdigest())

    port = {
        "schema_version": "pizm-portfolio-selection-v1",
        "stage": "portfolio",
        "route": "AUTO",
        "candidate_assessments": [{"candidate_ref": "pass01:c01", "disposition": "KEEP"}],
        "auto_target": {"target_type": "P", "target_id": "P1"},
    }
    (run_dir / "portfolio.json").write_text(json.dumps(port))
    (run_dir / "portfolio.sha256").write_text(__import__("hashlib").sha256(json.dumps(port).encode()).hexdigest())

    dev = {"schema_version": "pizm-development-v2", "stage": "development-v2", "target": {"target_type": "P", "target_id": "P1"}}
    (run_dir / "development-v2.json").write_text(json.dumps(dev))
    (run_dir / "development-v2.sha256").write_text(__import__("hashlib").sha256(json.dumps(dev).encode()).hexdigest())

    rev = {"schema_version": "pizm-deep-review-v2", "stage": "deep-review-v2", "target_type": "P", "target_id": "P1", "terminal_state": "MODEL_READY"}
    (run_dir / "deep-review-v2.json").write_text(json.dumps(rev))
    (run_dir / "deep-review-v2.sha256").write_text(__import__("hashlib").sha256(json.dumps(rev).encode()).hexdigest())

    out = tmp_path / "dup.md"
    res = run_render(run_dir, TASK_TEXT, out)
    assert res.returncode != 0
    assert "duplicate composite candidate key" in res.stderr


def test_unknown_candidate_reference_fails_closed(frozen_run_p, tmp_path):
    """Portfolio referencing an unknown candidate fails closed."""
    port = json.loads((frozen_run_p / "portfolio.json").read_text())
    port["candidate_assessments"].append({
        "candidate_ref": "pass01:c99",
        "disposition": "KEEP",
        "standalone_quality": "strong",
        "reason": "Ghost candidate",
    })
    raw = json.dumps(port, indent=2).encode("utf-8")
    (frozen_run_p / "portfolio.json").write_bytes(raw)
    (frozen_run_p / "portfolio.sha256").write_text(
        __import__("hashlib").sha256(raw).hexdigest(), encoding="ascii"
    )
    res = run_render(frozen_run_p, TASK_TEXT, tmp_path / "run.md")
    assert res.returncode != 0
    assert "unknown candidate ref" in res.stderr


def test_colon_bearing_ref_no_fallback_fails_closed(frozen_run_p, tmp_path):
    """Colon-bearing ref 'pass02:c01' when only pass01 is present must NOT fallback to local c01."""
    port = json.loads((frozen_run_p / "portfolio.json").read_text())
    port["candidate_assessments"][0]["candidate_ref"] = "pass02:c01"
    raw = json.dumps(port, indent=2).encode("utf-8")
    (frozen_run_p / "portfolio.json").write_bytes(raw)
    (frozen_run_p / "portfolio.sha256").write_text(
        __import__("hashlib").sha256(raw).hexdigest(), encoding="ascii"
    )
    res = run_render(frozen_run_p, TASK_TEXT, tmp_path / "run.md")
    assert res.returncode != 0
    assert "unknown candidate ref" in res.stderr


def test_canonical_perspectives_controls_rendered_labels_and_continued_p_id(tmp_path):
    """V2 portfolio 'perspectives' map defines canonical P-IDs across passes, controlling bundle labels."""
    run_id = "test-canon-persp"
    p1 = candidates_payload()
    freeze_stage(tmp_path, "explore", run_id, p1)
    sha1 = (tmp_path / ".ai" / "pizm" / f"run-{run_id}" / "candidates.sha256").read_text().strip()

    p2 = pass2_candidates_payload()
    freeze_stage(tmp_path, "explore", run_id, p2, artifact_suffix="pass02")
    sha2 = (tmp_path / ".ai" / "pizm" / f"run-{run_id}" / "candidates-pass02.sha256").read_text().strip()

    sf = search_field_payload(sha1, sha2)
    freeze_stage(tmp_path, "search-field", run_id, sf)
    sf_sha = (tmp_path / ".ai" / "pizm" / f"run-{run_id}" / "search-field.sha256").read_text().strip()

    # Canonical portfolio perspectives mapping P1 -> pass01:c01, P2 -> pass01:c02, P3 -> pass02:c01
    port = {
        "schema_version": "pizm-portfolio-selection-v2",
        "stage": "portfolio",
        "route": "AUTO",
        "field_ref": "search-field.json",
        "field_hash": sf_sha,
        "competition_status": "NO_SECOND_DEFENSIBLE_BUNDLE",
        "perspectives": {
            "P1": "pass01:c01",
            "P2": "pass01:c02",
            "P3": "pass02:c01",
        },
        "candidate_assessments": [
            {"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Res 1", "nearest_overlap": None, "reason": "R1"},
            {"candidate_ref": "pass01:c02", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Res 2", "nearest_overlap": None, "reason": "R2"},
            {"candidate_ref": "pass02:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Res 3", "nearest_overlap": None, "reason": "R3"},
        ],
        "bundles": [
            {
                "bundle_id": "B1",
                "member_refs": ["pass01:c02", "pass02:c01"],
                "bundle_thesis": "Thesis B1",
                "composition_gain": "Gain B1",
                "internal_tension": "Tension B1",
                "weakest_link": "Link B1",
                "new_consequence_or_prediction": "Pred B1",
                "member_roles": {"pass01:c02": "Role 1", "pass02:c01": "Role 2"},
                "member_ablation": {"pass01:c02": "Abl 1", "pass02:c01": "Abl 2"},
            }
        ],
        "auto_target": {"target_type": "B", "target_id": "B1"},
    }
    freeze_stage(tmp_path, "portfolio", run_id, port)

    dev = development_payload("B", "B1")
    dev["identity_lock"]["member_refs"] = ["pass01:c02", "pass02:c01"]
    dev["developed_model"]["member_contributions"] = {
        "pass01:c02": "Contribution 1",
        "pass02:c01": "Contribution 2",
    }
    dev["developed_model"]["member_ablation"] = {
        "pass01:c02": "Ablation 1",
        "pass02:c01": "Ablation 2",
    }
    freeze_stage(tmp_path, "development-v2", run_id, dev, target="B1")
    dev_sha = (tmp_path / ".ai" / "pizm" / f"run-{run_id}" / "development-v2-B1.sha256").read_text().strip()

    rev = review_payload("B", "B1")
    rev["frozen_hash"] = dev_sha
    freeze_stage(tmp_path, "deep-review-v2", run_id, rev)

    run_dir = tmp_path / ".ai" / "pizm" / f"run-{run_id}"
    out = tmp_path / "persp.md"
    res = run_render(run_dir, TASK_TEXT, out)
    assert res.returncode == 0, res.stderr
    content = out.read_text(encoding="utf-8")

    # Canonical continued P-ID rendered in Portfolio
    assert "### P3 — Ownership Diffusion Boundary (`pass02:c01`)" in content
    # Bundle members labeled with canonical P-IDs P2 + P3
    assert "### B1 — P2 + P3" in content
