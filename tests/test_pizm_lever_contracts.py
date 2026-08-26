"""
Contract tests for Pizm LEVER primitive (R2).

Covers test IDs:
- L1: MODEL_READY -> staged LEVER accepted end-to-end (checkpoint freeze + session bundle)
- L2: Non-ready Deep status blocked (NEED_EVIDENCE / RETURN_TO_EXPLORE produce zero lever stages)
- L3: Ambiguous/invalid P-ID deterministic refusal
- L4: Generic advice negative control (MODEL DEPENDENCE rule + required model_link validation)
- L5: Adaptive vs non-adaptive (adaptation_or_countermove optional)
- L6: Irreversible domain (risk boundary statement + no fake reversibility enforcement)
- L7: Rubric hidden pre-freeze (blindness clause + freeze stdout lacks rubric body)
- L8: Payload/hash/archive fail-closed (>64 KiB PAYLOAD_TOO_LARGE + bad outcome rejection)
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = REPO_ROOT / "skills" / "pizm"
CHECKPOINT_CLI = str(REPO_ROOT / "bin" / "pizm-checkpoint")
BUNDLE_CLI = str(REPO_ROOT / "bin" / "pizm-session-bundle")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_cli(cmd_args, cwd=None):
    return subprocess.run(
        [sys.executable, *cmd_args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


@pytest.fixture
def lever_md_text():
    return (SKILL_ROOT / "references" / "lever.md").read_text(encoding="utf-8")


@pytest.fixture
def lever_reviewer_md_text():
    return (SKILL_ROOT / "references" / "lever-reviewer.md").read_text(encoding="utf-8")


@pytest.fixture
def skill_md_text():
    return (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")


@pytest.fixture
def explore_md_text():
    return (SKILL_ROOT / "references" / "explore.md").read_text(encoding="utf-8")


def valid_lever_design():
    return {
        "schema_version": "pizm-lever-design-v1",
        "stage": "lever",
        "levers": [
            {
                "lever_id": "L1",
                "intervention_or_test_point": "API rate-limiting boundary between ingress and worker queue",
                "model_link": "Engages the load-bearing constraint that queue backpressure triggers cascade timeouts",
                "minimum_bounded_move": "Inject synthetic 50 req/sec surge for 30 seconds on staging canary",
                "expected_observation_or_response": "Worker queue depth stabilizes within 5s with backoff shedding",
                "disconfirming_signal": "Ingress drop-rate spikes while workers remain under-utilized",
                "stop_condition": "Ingress 5xx rate exceeds 0.5% or canary latency exceeds 200ms",
                "remaining_assumptions": "Canary worker configuration mirrors production shedding threshold",
                "adaptation_or_countermove": "Client retries may amplify backpressure if exponential backoff is disabled",
            }
        ],
    }


def valid_lever_review(frozen_hash: str):
    return {
        "schema_version": "pizm-lever-review-v1",
        "stage": "lever",
        "frozen_hash": frozen_hash,
        "outcome": "LEVER",
        "verdicts": [
            {
                "lever_id": "L1",
                "verdict": "ACCEPT",
                "reason": "Directly derives from the cascade timeout mechanism and provides a discriminating test",
            }
        ],
        "verdict_rationale": "L1 satisfies all mandatory checks: model-dependent, bounded, and discriminating",
    }


# ---------------------------------------------------------------------------
# L1: MODEL_READY -> staged LEVER accepted end-to-end
# ---------------------------------------------------------------------------


def test_L1_staged_lever_accepted_end_to_end(tmp_path):
    """L1: Fixture lever-design JSON passes checkpoint freeze and bundle groups under lever-P<id>/."""
    project = tmp_path / "project"
    project.mkdir()
    skill = tmp_path / "skill"
    skill.mkdir()
    refs = skill / "references"
    refs.mkdir()
    (refs / "lever-reviewer.md").write_text("# LEVER REVIEWER RUBRIC\nreviewer contract")
    (skill / "SKILL.md").write_text("# Pizm Skill\n")

    # 1. Freeze lever-design
    design_data = valid_lever_design()
    design_raw = json.dumps(design_data, indent=2).encode("utf-8")
    design_input = project / "design_input.json"
    design_input.write_bytes(design_raw)

    res_design = run_cli(
        [
            CHECKPOINT_CLI,
            "freeze",
            "--stage",
            "lever-design",
            "--run-id",
            "run-l1",
            "--input",
            str(design_input),
            "--project-root",
            str(project),
            "--skill-root",
            str(skill),
        ]
    )
    assert res_design.returncode == 0, res_design.stderr
    assert "FREEZE_OK" in res_design.stdout
    design_hash = _sha256_hex(design_raw)
    assert design_hash in res_design.stdout

    run_dir = project / ".ai" / "pizm" / "run-run-l1"
    assert (run_dir / "design.json").exists()
    assert (run_dir / "design.sha256").exists()
    assert (run_dir / "design.meta.json").exists()

    # 2. Write review.json in run_dir and freeze lever-review
    review_data = valid_lever_review(design_hash)
    review_raw = json.dumps(review_data, indent=2).encode("utf-8")
    review_input = project / "review_input.json"
    review_input.write_bytes(review_raw)

    res_review = run_cli(
        [
            CHECKPOINT_CLI,
            "freeze",
            "--stage",
            "lever-review",
            "--run-id",
            "run-l1",
            "--input",
            str(review_input),
            "--project-root",
            str(project),
            "--skill-root",
            str(skill),
        ]
    )
    assert res_review.returncode == 0, res_review.stderr
    assert "FREEZE_OK" in res_review.stdout
    assert (run_dir / "review.json").exists()
    assert (run_dir / "review.sha256").exists()

    # 3. Bundle the session with a lever stage
    out_root = tmp_path / "bundles"
    out_root.mkdir()
    dummy_input = tmp_path / "task.txt"
    dummy_input.write_text("Test task prompt")

    res_bundle = run_cli(
        [
            BUNDLE_CLI,
            "create",
            "--output-root",
            str(out_root),
            "--slug",
            "l1-test-slug",
            "--skill-root",
            str(skill),
            "--input",
            str(dummy_input),
            "--stage",
            f"lever-P1={run_dir}",
        ]
    )
    assert res_bundle.returncode == 0, res_bundle.stderr
    assert "BUNDLE_OK" in res_bundle.stdout

    bundle_dir = out_root / "session-l1-test-slug"
    assert (bundle_dir / "lever-P1").is_dir()
    assert (bundle_dir / "lever-P1" / "design.json").exists()
    assert (bundle_dir / "lever-P1" / "design.sha256").exists()
    assert (bundle_dir / "lever-P1" / "review.json").exists()
    assert (bundle_dir / "lever-P1" / "review.sha256").exists()

    manifest = json.loads((bundle_dir / "manifest.json").read_text())
    assert "lever-P1" in manifest["stages"]
    assert "lever-P1/design.json" in manifest["artifacts"]
    assert "lever-P1/review.json" in manifest["artifacts"]


# ---------------------------------------------------------------------------
# L2: Non-ready Deep status blocked
# ---------------------------------------------------------------------------


def test_L2_non_ready_deep_status_blocked(lever_md_text, skill_md_text):
    """L2: Static assertions on lever.md and SKILL.md that non-ready Deep statuses block LEVER."""
    assert "MODEL_READY" in lever_md_text
    assert "NEED_EVIDENCE" in lever_md_text
    assert "RETURN_TO_EXPLORE" in lever_md_text
    assert "zero" in lever_md_text.lower() or "0" in lever_md_text
    assert "semantic stages" in lever_md_text

    # SKILL.md routing notes blocked cases produce zero lever semantic stages
    assert "MODEL_READY" in skill_md_text
    assert "zero lever semantic stages" in skill_md_text


# ---------------------------------------------------------------------------
# L3: Ambiguous or invalid P-ID deterministic failure
# ---------------------------------------------------------------------------


def test_L3_ambiguous_invalid_pid_deterministic_refusal(lever_md_text, skill_md_text):
    """L3: Static assertion on routing text that ambiguous or invalid P-ID yields deterministic refusal."""
    assert "unknown" in lever_md_text.lower() or "stale" in lever_md_text.lower()
    assert "deterministic error" in lever_md_text or "deterministic refusal" in lever_md_text
    assert "bare `/pizm lever`" in lever_md_text or "bare `/pizm lever`" in skill_md_text
    assert "unambiguous" in lever_md_text or "unambiguous" in skill_md_text


# ---------------------------------------------------------------------------
# L4: Generic advice negative control
# ---------------------------------------------------------------------------


def test_L4_generic_advice_negative_control(lever_reviewer_md_text, tmp_path):
    """L4: Reviewer contract contains MODEL DEPENDENCE reject rule verbatim; validator rejects missing model_link."""
    # Verbatim check on MODEL DEPENDENCE question
    assert "MODEL DEPENDENCE" in lever_reviewer_md_text
    assert "If the developed model disappeared, could essentially the same recommendation be written? YES → reject" in lever_reviewer_md_text

    # Validator rejects lever missing model_link
    project = tmp_path / "project"
    project.mkdir()
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "references").mkdir()
    (skill / "references" / "lever-reviewer.md").write_text("hidden")

    bad_data = valid_lever_design()
    del bad_data["levers"][0]["model_link"]
    inp = project / "missing_link.json"
    inp.write_text(json.dumps(bad_data))

    res = run_cli(
        [
            CHECKPOINT_CLI,
            "freeze",
            "--stage",
            "lever-design",
            "--run-id",
            "l4-fail",
            "--input",
            str(inp),
            "--project-root",
            str(project),
            "--skill-root",
            str(skill),
        ]
    )
    assert res.returncode != 0
    assert "model_link" in res.stderr
    assert not (project / ".ai" / "pizm" / "run-l4-fail" / "design.json").exists()


# ---------------------------------------------------------------------------
# L5: Adaptive vs non-adaptive counter-move
# ---------------------------------------------------------------------------


def test_L5_adaptive_vs_non_adaptive(lever_reviewer_md_text, tmp_path):
    """L5: Validator accepts design WITHOUT adaptation_or_countermove; reviewer text marks it conditional."""
    assert "ADAPTATION" in lever_reviewer_md_text
    assert re.search(r"structurally\s+relevant|adaptive|conditional", lever_reviewer_md_text, re.IGNORECASE)

    # Design without adaptation_or_countermove is accepted by checkpoint validator
    project = tmp_path / "project"
    project.mkdir()
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "references").mkdir()
    (skill / "references" / "lever-reviewer.md").write_text("hidden")

    data = valid_lever_design()
    del data["levers"][0]["adaptation_or_countermove"]
    inp = project / "no_adaptation.json"
    inp.write_text(json.dumps(data))

    res = run_cli(
        [
            CHECKPOINT_CLI,
            "freeze",
            "--stage",
            "lever-design",
            "--run-id",
            "l5-pass",
            "--input",
            str(inp),
            "--project-root",
            str(project),
            "--skill-root",
            str(skill),
        ]
    )
    assert res.returncode == 0, res.stderr
    assert "FREEZE_OK" in res.stdout


# ---------------------------------------------------------------------------
# L6: Irreversible domain risk boundary
# ---------------------------------------------------------------------------


def test_L6_irreversible_domain_risk_boundary(lever_reviewer_md_text, tmp_path):
    """L6: Reviewer text requires risk boundary statement; validator does not require reversibility keywords."""
    assert "BOUNDEDNESS" in lever_reviewer_md_text
    assert re.search(r"risk.*boundary|fake\s+reversibility", lever_reviewer_md_text, re.IGNORECASE)

    # Validator accepts minimum_bounded_move without any specific "reversible" word
    project = tmp_path / "project"
    project.mkdir()
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "references").mkdir()
    (skill / "references" / "lever-reviewer.md").write_text("hidden")

    data = valid_lever_design()
    data["levers"][0]["minimum_bounded_move"] = "Permanently delete deprecated database table partition with 2-day backup archive"
    inp = project / "irreversible.json"
    inp.write_text(json.dumps(data))

    res = run_cli(
        [
            CHECKPOINT_CLI,
            "freeze",
            "--stage",
            "lever-design",
            "--run-id",
            "l6-pass",
            "--input",
            str(inp),
            "--project-root",
            str(project),
            "--skill-root",
            str(skill),
        ]
    )
    assert res.returncode == 0, res.stderr
    assert "FREEZE_OK" in res.stdout


# ---------------------------------------------------------------------------
# L7: Rubric hidden pre-freeze
# ---------------------------------------------------------------------------


def test_L7_rubric_hidden_pre_freeze(lever_md_text, explore_md_text, tmp_path):
    """L7: Static assertion on blindness clause matching explore.md:9; checkpoint freeze reveals only path/name, not rubric body."""
    # Check that lever.md has the future-contract prohibition clause mirroring explore.md
    assert "Pre-freeze future-contract prohibition" in lever_md_text
    assert "Pre-freeze future-contract prohibition" in explore_md_text
    assert "references/lever-reviewer.md" in lever_md_text
    assert "FREEZE_OK" in lever_md_text

    # Check that checkpoint freeze stdout reveals ONLY reference name/path, not rubric content
    project = tmp_path / "project"
    project.mkdir()
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "references").mkdir()
    rubric_secret = "SECRET_RUBRIC_BODY_MODEL_DEPENDENCE_LOAD_BEARING_REJECT_CRITERIA"
    (skill / "references" / "lever-reviewer.md").write_text(f"# RUBRIC\n{rubric_secret}\n")

    inp = project / "design.json"
    inp.write_text(json.dumps(valid_lever_design()))

    res = run_cli(
        [
            CHECKPOINT_CLI,
            "freeze",
            "--stage",
            "lever-design",
            "--run-id",
            "l7-blind",
            "--input",
            str(inp),
            "--project-root",
            str(project),
            "--skill-root",
            str(skill),
        ]
    )
    assert res.returncode == 0, res.stderr
    assert "FREEZE_OK" in res.stdout
    assert "references/lever-reviewer.md" in res.stdout
    # Crucial: rubric body must NOT be printed in stdout/stderr
    assert rubric_secret not in res.stdout
    assert "MODEL DEPENDENCE" not in res.stdout
    assert rubric_secret not in res.stderr


# ---------------------------------------------------------------------------
# L8: Payload/hash/archive fail-closed
# ---------------------------------------------------------------------------


def test_L8_payload_hash_fail_closed(tmp_path):
    """L8: Oversized design (>64 KiB) -> PAYLOAD_TOO_LARGE fail-closed; bad outcome enum rejected."""
    project = tmp_path / "project"
    project.mkdir()
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "references").mkdir()
    rubric_secret = "SECRET_HIDDEN_RUBRIC_DO_NOT_REVEAL"
    (skill / "references" / "lever-reviewer.md").write_text(rubric_secret)

    # 1. Oversized design (>64 KiB = 65536 bytes)
    big_data = valid_lever_design()
    big_data["levers"][0]["intervention_or_test_point"] = "x" * 70000
    big_inp = project / "oversized_design.json"
    big_inp.write_text(json.dumps(big_data))

    res_big = run_cli(
        [
            CHECKPOINT_CLI,
            "freeze",
            "--stage",
            "lever-design",
            "--run-id",
            "l8-oversized",
            "--input",
            str(big_inp),
            "--project-root",
            str(project),
            "--skill-root",
            str(skill),
        ]
    )
    assert res_big.returncode != 0
    assert "PAYLOAD_TOO_LARGE" in res_big.stderr
    assert "65536" in res_big.stderr or "64 KiB" in res_big.stderr
    # Fail-closed: contract not revealed, artifact not written
    assert rubric_secret not in res_big.stdout
    assert "NEXT CONTRACT" not in res_big.stdout
    assert not (project / ".ai" / "pizm" / "run-l8-oversized" / "design.json").exists()

    # 2. Bad outcome enum in lever-review rejected
    bad_review = valid_lever_review("somehash")
    bad_review["outcome"] = "INVALID_OUTCOME"
    bad_rev_inp = project / "bad_review.json"
    bad_rev_inp.write_text(json.dumps(bad_review))

    res_bad_rev = run_cli(
        [
            CHECKPOINT_CLI,
            "freeze",
            "--stage",
            "lever-review",
            "--run-id",
            "l8-bad-review",
            "--input",
            str(bad_rev_inp),
            "--project-root",
            str(project),
            "--skill-root",
            str(skill),
        ]
    )
    assert res_bad_rev.returncode != 0
    assert "outcome" in res_bad_rev.stderr
    assert not (project / ".ai" / "pizm" / "run-l8-bad-review" / "review.json").exists()
