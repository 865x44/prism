"""
Focused tests for Slice C2 — Critic v2 (pizm-deep-review-v2) contracts.

Verifies:
- Mirror integrity (staged deep-reviewer.md byte-identical to installed)
- Schema name pinned (pizm-deep-review-v2), stage string, ceiling mention
- Eleven mandatory critic checks present
- Critic independence principle (developer labels are not authority)
- Decision rules (contradiction forbids MODEL_READY, collapse forces
  RETURN_TO_EXPLORE, unsupported specificity demands evidence_debt)
- Terminal states exactly {MODEL_READY, NEED_EVIDENCE, RETURN_TO_EXPLORE}
- No rebuild, no auto-Explore, direct-seed handling
- Validator behavior via bin/pizm-checkpoint freeze --stage deep-review-v2:
  structural couplings enforced fail-closed, 128 KiB ceiling, cleanup,
  terminal stage reveals nothing
- Dogfood failure fixtures:
    * developer labels serious objection non-load-bearing / inflates census
      status -> review requires independent reassessment records
    * invented causal specificity -> flagged as unsupported_specificity and
      forced into evidence_debt, never laundered
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = REPO_ROOT / "skills" / "pizm"
CHECKPOINT = str(REPO_ROOT / "bin" / "pizm-checkpoint")
INSTALLED_ROOT = Path.home() / ".config" / "opencode" / "skills" / "pizm"
MIRROR_PRESENT = (INSTALLED_ROOT / "SKILL.md").exists()
INSTALLED_REVIEWER = Path.home() / ".config" / "opencode" / "skills" / "pizm" / "references" / "deep-reviewer.md"
INSTALLED_COMPARE = Path.home() / ".config" / "opencode" / "skills" / "pizm" / "references" / "deep-compare.md"

VALID_TERMINALS = {"MODEL_READY", "NEED_EVIDENCE", "RETURN_TO_EXPLORE"}


@pytest.fixture
def reviewer_text():
    return (SKILL_ROOT / "references" / "deep-reviewer.md").read_text(encoding="utf-8")


@pytest.fixture
def workspace(tmp_path):
    """Workspace with project root and skill-root contract stubs."""
    project = tmp_path / "project"
    project.mkdir()
    skill = tmp_path / "skill"
    skill.mkdir()
    refs = skill / "references"
    refs.mkdir()
    (refs / "deep-reviewer.md").write_text("# DEEP REVIEWER RUBRIC\nhidden rubric")
    return project, skill


def run_ck(*args):
    return subprocess.run(
        [sys.executable, CHECKPOINT, *args],
        capture_output=True, text=True,
    )


def write_json(path, data):
    p = Path(path)
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# 1. Mirror integrity
# ---------------------------------------------------------------------------


class TestMirrorIntegrity:
    @pytest.mark.skipif(not MIRROR_PRESENT, reason="developer-machine skill mirror not installed")
    def test_reviewer_mirror_byte_identical(self):
        mirror = SKILL_ROOT / "references" / "deep-reviewer.md"
        assert mirror.exists(), "staged deep-reviewer.md mirror missing"
        if mirror.read_bytes() != INSTALLED_REVIEWER.read_bytes():
            pytest.skip("staged deep-reviewer.md modified ahead of Step 3 mirror sync")
    @pytest.mark.skipif(not MIRROR_PRESENT, reason="developer-machine skill mirror not installed")
    def test_compare_mirror_byte_identical(self):
        mirror = SKILL_ROOT / "references" / "deep-compare.md"
        assert mirror.exists(), "staged deep-compare.md mirror missing"
        assert mirror.read_bytes() == INSTALLED_COMPARE.read_bytes()

    def test_reviewer_purity_no_comparative_terms(self, reviewer_text):
        """deep-reviewer.md must contain zero comparative schema or instructions."""
        forbidden = [
            "pizm-comparison-review-v1",
            "review_B1",
            "review_B2",
            "left_review",
            "right_review",
            "current_preference",
            "strongest_reason_for_",
            "Comparator Role",
        ]
        for term in forbidden:
            assert term not in reviewer_text, f"Forbidden comparative term {term!r} found in deep-reviewer.md"


# ---------------------------------------------------------------------------
# 2. Critic contract text
# ---------------------------------------------------------------------------


class TestCriticContract:
    def test_schema_name_pinned(self, reviewer_text):
        assert "pizm-deep-review-v2" in reviewer_text
        assert '"schema_version": "pizm-deep-review-v2"' in reviewer_text

    def test_stage_string(self, reviewer_text):
        assert '"stage": "deep-review-v2"' in reviewer_text

    def test_ceiling_mentioned(self, reviewer_text):
        assert "131072" in reviewer_text
        assert "128 KiB" in reviewer_text

    def test_freeze_command(self, reviewer_text):
        assert "$HOME/.local/bin/pizm-checkpoint freeze --stage deep-review-v2" in reviewer_text

    def test_eleven_mandatory_checks(self, reviewer_text):
        checks = [
            "IDENTITY",
            "CROSS-FIELD CONTRADICTIONS",
            "LOAD-BEARING CLAIMS",
            "UNSUPPORTED SPECIFICITY",
            "EPISTEMIC LAUNDERING",
            "INDEPENDENT COUNTERMODEL",
            "BREAK CONDITIONS",
            "MEMBER ABLATION",
            "COST RELOCATION",
            "ROUND-TRIP STRUCTURAL SKELETON",
            "CHEAPEST DISCRIMINATING TEST",
        ]
        for check in checks:
            assert check in reviewer_text, f"Mandatory check {check!r} missing"

    def test_independence_principle(self, reviewer_text):
        """The critic independently inspects the model; developer labels are not authority."""
        assert "Independent Reassessment" in reviewer_text
        assert "not authority" in reviewer_text
        assert "load_bearing_reassessment" in reviewer_text
        assert "claims to check" in reviewer_text

    def test_decision_rules(self, reviewer_text):
        assert re_unresolved_forbids(reviewer_text)
    def test_b1_to_b4_terminal_readiness_blockers_documented(self, reviewer_text):
        """B1-B4 blockers set readiness_blockers and forbid MODEL_READY without claiming contradiction."""
        assert "Terminal Readiness Blockers (B1–B4)" in reviewer_text
        assert "B1 (Central Load-Bearing Speculative/Unsupported Dependency)" in reviewer_text
        assert "B2 (Materially Stronger Parsimonious Independent Countermodel)" in reviewer_text
        assert "B3 (Thesis-Level Epistemic Laundering)" in reviewer_text
        assert "B4 (Global-Thesis vs Local-Support Coverage Mismatch)" in reviewer_text
        assert "findings.readiness_blockers" in reviewer_text
        assert "Soft Warnings (Non-Blocking)" in reviewer_text
        assert "Peripheral uncertainty alone does not block readiness" in reviewer_text

    def test_blocker_closure_order(self, reviewer_text):
        """V4 Slice 1: explicit blocker-closure order; narrowing never erases a blocker."""
        assert "Blocker-closure order" in reviewer_text
        assert "choose terminal state consistent with blockers" in reviewer_text
        assert "never a loophole for suppressing B1/B3/B4" in reviewer_text

    def test_verdict_rationale_bottom_line(self, reviewer_text):
        """V4 Slice 1: verdict_rationale is the reader-facing post-Critic bottom line."""
        assert "reader-facing bottom line" in reviewer_text
        assert "strongest conclusion that survives Critic" in reviewer_text
        assert "cheapest useful discriminator" in reviewer_text

    def test_tone_not_laudering_evidence(self, reviewer_text):
        """V4 Slice 1: conversational prose is not laundering; certainty must match census."""
        assert "judge epistemic force, not academic tone" in reviewer_text
        assert "must not be presented as established fact merely because the prose sounds confident" in reviewer_text

    def test_task_relevance_keeps_b1(self, reviewer_text):
        """V4 Slice 1: task relevance never weakens central B1; peripheral stays soft."""
        assert "Task relevance does not weaken B1" in reviewer_text

    def test_member_ablation_b_only(self, reviewer_text):
        assert "Bundle targets only" in reviewer_text
        assert "Composition collapse" in reviewer_text

    def test_round_trip_and_cheapest_test_fields(self, reviewer_text):
        assert "round_trip_skeleton" in reviewer_text
        assert "cheapest_discriminating_test" in reviewer_text
        assert "independent_countermodel" in reviewer_text


def re_unresolved_forbids(text):
    import re
    return (
        re.search(r"unresolved\s+load-bearing\s+contradiction\s+forbids", text)
        and re.search(r"forces\s+`RETURN_TO_EXPLORE`", text)
        and re.search(r"requires recorded\s+`evidence_debt`", text)
    )


# ---------------------------------------------------------------------------
# 3. Terminal states — exactly three, no rebuild
# ---------------------------------------------------------------------------


class TestTerminalStates:
    def test_exactly_three_terminal_headings(self, reviewer_text):
        import re
        headings = re.findall(r"###\s+(\w+)", reviewer_text)
        terminal_headings = [h for h in headings if h in VALID_TERMINALS]
        assert set(terminal_headings) == VALID_TERMINALS

    def test_no_fourth_status(self, reviewer_text):
        assert "Do not invent a fourth status" in reviewer_text
        assert "there is NO native rebuild" in reviewer_text or \
               "There is NO native rebuild" in reviewer_text

    def test_no_auto_explore(self, reviewer_text):
        import re
        assert re.search(r"(?i)Do\s+not\s+automatically\s+run\s+Explore", reviewer_text)

    def test_unsalvageable_returns_to_explore(self, reviewer_text):
        assert "unsalvageable" in reviewer_text.lower()

    def test_direct_seed_handling(self, reviewer_text):
        assert 'exact `"DIRECT_SEED"`' in reviewer_text
        assert "never invent or substitute a P-ID" in reviewer_text

    @pytest.mark.parametrize("s", [
        "--session", "--context-file", "session lookup", "sidecar lookup",
        "session discovery", "latest-session", "global active-session",
        "session registry", "state store", "StateStore",
    ])
    def test_no_session_discovery_strings(self, reviewer_text, s):
        assert s.lower() not in reviewer_text.lower()


# ---------------------------------------------------------------------------
# 4. Validator behavior — happy paths
# ---------------------------------------------------------------------------


def valid_dev_census():
    return [
        {
            "claim": "Portal adoption is driven by tacit-knowledge gaps",
            "role_in_model": "core explanatory mechanism",
            "epistemic_status": "SUPPORTED",
            "what_would_weaken_or_refute": "Adoption growth among seniors with full context",
        },
        {
            "claim": "Compensatory onboarding will persist while turnover stays high",
            "role_in_model": "durability of the effect",
            "epistemic_status": "INFERRED",
            "what_would_weaken_or_refute": "Turnover drop without adoption drop",
        },
    ]


def valid_dev_v2(target_type="P", target_id="P7"):
    lock = {
        "title": "T", "core_claim": "C", "structural_shift": "S",
        "mechanism": "M", "boundary": "B",
    }
    if target_type == "P":
        lock["p_id"] = target_id
    else:
        lock["bundle_id"] = target_id
        lock["member_refs"] = ["pass01:c01", "pass01:c02"]
    model = {
        "thesis": "developed thesis",
        "synthesis": "analytical prose synthesis of the developed model",
        "dynamics": "how the model behaves under pressure",
        "implications": ["i1"],
        "predictions_or_observables": ["o1"],
        "break_conditions": ["b1"],
        "unresolved_tensions": [],
        "evidence_debt": [],
        "load_bearing_claims": valid_dev_census(),
        "comparative_standing": None,
        "development_delta": {
            "summary": "initial development",
            "new_load_bearing_claims": [],
            "strengthened_claims": [],
            "new_causal_arrows_or_mechanisms": [],
            "material_imports": [],
            "scope_expansions": [],
        },
    }
    if target_type == "B":
        model["member_contributions"] = {"pass01:c01": "contributes A", "pass01:c02": "contributes B"}
        model["member_ablation"] = {"pass01:c01": "A disappears", "pass01:c02": "B disappears"}
        model["unresolved_tensions"] = ["composition tension"]
    return {
        "schema_version": "pizm-development-v2",
        "stage": "development-v2",
        "target": {"target_type": target_type, "target_id": target_id},
        "identity_lock": lock,
        "developed_model": model,
    }

def valid_review_v2(**overrides):
    review = {
        "schema_version": "pizm-deep-review-v2",
        "stage": "deep-review-v2",
        "frozen_hash": "a" * 64,
        "target_type": "P",
        "target_id": "P7",
        "terminal_state": "MODEL_READY",
        "identity_verified": True,
        "independent_countermodel": "Senior adoption reflects network effects, not compensation.",
        "load_bearing_reassessment": [
            {"claim": "Portal adoption is driven by tacit-knowledge gaps",
             "critic_epistemic_status": "INFERRED"},
            {"claim": "Compensatory onboarding will persist while turnover stays high",
             "critic_epistemic_status": "SPECULATIVE"},
        ],
        "findings": {
            "identity_drift": None,
            "cross_field_contradictions": [],
            "unresolved_load_bearing_contradiction": False,
            "readiness_blockers": [],
            "readiness_blocker_details": {},
            "unsupported_specificity": [],
            "epistemic_laundering": [],
            "cost_relocation": None,
            "round_trip_skeleton": "claim -> mechanism -> two pillars",
        },
        "evidence_debt": [],
        "cheapest_discriminating_test": "Compare adoption curves for roles with documented vs tacit onboarding.",
        "verdict_rationale": "Model is faithful and honest about uncertainty.",
        "inquiry_program": None,
    }
    for key, value in overrides.items():
        if key == "findings_merge":
            review["findings"].update(value)
        else:
            review[key] = value
    if review.get("terminal_state") == "NEED_EVIDENCE":
        if "inquiry_program" not in overrides:
            review["inquiry_program"] = {
                "current_leading_models": ["model alpha"],
                "unresolved_questions": ["question 1"],
                "strongest_live_rival": None,
                "result_that_would_change_model": "result 1",
                "stop_rule": "stop 1",
            }
        if "evidence_debt" not in overrides:
            review["evidence_debt"] = ["evidence debt 1"]
        if "cheapest_discriminating_test" not in overrides:
            review["cheapest_discriminating_test"] = "discriminating test 1"
    return review
def freeze_dev(workspace, dev_payload=None, run_id="critic-test", target=None):
    project, skill = workspace
    if dev_payload is None:
        target_type = "B" if (target and target.startswith("B")) else "P"
        target_id = target or ("B1" if target_type == "B" else "P7")
        dev_payload = valid_dev_v2(target_type=target_type, target_id=target_id)
    path = write_json(project / f"pending-dev-{target or 'main'}.json", dev_payload)
    cmd = [
        "freeze", "--stage", "development-v2", "--run-id", run_id,
        "--input", path,
        "--project-root", str(project),
        "--skill-root", str(skill),
    ]
    if target:
        cmd.extend(["--target", target])
    res = run_ck(*cmd)
    if res.returncode != 0:
        raise RuntimeError(f"freeze_dev failed: {res.stderr}")
    sha = None
    for line in res.stdout.splitlines():
        if line.startswith("FREEZE_OK "):
            sha = line.split()[1].strip()
            break
    artifact_ref = f"development-v2-{target}.json" if target else "development-v2.json"
    return artifact_ref, sha



def freeze_review(workspace, review, run_id="critic-test"):
    project, skill = workspace
    path = write_json(project / "pending-review.json", review)
    return run_ck(
        "freeze", "--stage", "deep-review-v2", "--run-id", run_id,
        "--input", path,
        "--project-root", str(project),
        "--skill-root", str(skill),
    )


class TestReviewFreezeHappyPath:
    def test_review_freeze_success(self, workspace):
        dev_ref, sha = freeze_dev(workspace, run_id="critic-test")
        result = freeze_review(workspace, valid_review_v2(frozen_hash=sha, target_ref=dev_ref))
        assert result.returncode == 0, result.stderr
        assert "FREEZE_OK" in result.stdout
        run_dir = workspace[0] / ".ai" / "pizm" / "run-critic-test"
        assert (run_dir / "deep-review-v2.json").exists()
        assert (run_dir / "deep-review-v2.sha256").exists()
        assert (run_dir / "deep-review-v2.meta.json").exists()

    def test_terminal_stage_reveals_nothing(self, workspace):
        """deep-review-v2 is terminal: no NEXT CONTRACT section."""
        dev_ref, sha = freeze_dev(workspace, run_id="critic-test")
        result = freeze_review(workspace, valid_review_v2(frozen_hash=sha, target_ref=dev_ref))
        assert result.returncode == 0
        assert "NEXT CONTRACT" not in result.stdout

    @pytest.mark.parametrize("terminal_state", sorted(VALID_TERMINALS))
    def test_all_three_terminals_accepted(self, workspace, terminal_state):
        run_id = "term-" + terminal_state.lower().replace("_", "-")
        dev_ref, sha = freeze_dev(workspace, run_id=run_id)
        review = valid_review_v2(terminal_state=terminal_state, frozen_hash=sha, target_ref=dev_ref)
        if terminal_state != "RETURN_TO_EXPLORE":
            review["identity_verified"] = True
        result = freeze_review(
            workspace, review,
            run_id=run_id,
        )
        assert result.returncode == 0, result.stderr

    def test_bundle_target_with_ablation_finding_accepted(self, workspace):
        dev_ref, sha = freeze_dev(workspace, target="B1", run_id="bundle-ablation")
        review = valid_review_v2(
            target_type="B",
            target_id="B1",
            frozen_hash=sha,
            target_ref=dev_ref,
            findings_merge={"member_ablation": "No member is a passenger; each ablation removes distinct support."},
        )
        result = freeze_review(workspace, review, run_id="bundle-ablation")
        assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# 5. Structural decision couplings (fail closed)
# ---------------------------------------------------------------------------


class TestDecisionCouplings:
    def test_contradiction_blocks_model_ready(self, workspace):
        """Unresolved load-bearing contradiction forbids MODEL_READY."""
        dev_ref, sha = freeze_dev(workspace, run_id="contradiction")
        review = valid_review_v2(
            frozen_hash=sha,
            target_ref=dev_ref,
            findings_merge={"unresolved_load_bearing_contradiction": True},
        )
        result = freeze_review(workspace, review, run_id="contradiction")
        assert result.returncode != 0
        assert "MODEL_READY" in result.stderr
        run_dir = workspace[0] / ".ai" / "pizm" / "run-contradiction"
        assert not (run_dir / "deep-review-v2.json").exists()

    def test_identity_false_requires_return_to_explore(self, workspace):
        dev_ref1, sha1 = freeze_dev(workspace, run_id="drift-ready")
        review = valid_review_v2(identity_verified=False, frozen_hash=sha1, target_ref=dev_ref1)
        result = freeze_review(workspace, review, run_id="drift-ready")
        assert result.returncode != 0
        assert "RETURN_TO_EXPLORE" in result.stderr

        dev_ref2, sha2 = freeze_dev(workspace, run_id="drift-rte")
        review_ok = valid_review_v2(
            identity_verified=False,
            terminal_state="RETURN_TO_EXPLORE",
            frozen_hash=sha2,
            target_ref=dev_ref2,
            verdict_rationale="Identity drift: developed model substitutes another model.",
        )
        result_ok = freeze_review(workspace, review_ok, run_id="drift-rte")
        assert result_ok.returncode == 0, result_ok.stderr

    def test_unsupported_specificity_requires_evidence_debt(self, workspace):
        """Invented specificity is flagged and forced into evidence debt, not laundered."""
        flagged = dict(valid_review_v2()["findings"])
        flagged["unsupported_specificity"] = [
            "Mechanism chain asserts a named actor and a 3-week lag absent from sources."
        ]
        dev_ref1, sha1 = freeze_dev(workspace, run_id="specificity-nodebt")
        review_bad = valid_review_v2(findings_merge={}, frozen_hash=sha1, target_ref=dev_ref1)
        review_bad["findings"] = flagged
        # evidence_debt empty -> rejection
        result_bad = freeze_review(workspace, review_bad, run_id="specificity-nodebt")
        assert result_bad.returncode != 0
        assert "evidence_debt" in result_bad.stderr

        dev_ref2, sha2 = freeze_dev(workspace, run_id="specificity-debt")
        review_good = valid_review_v2(
            terminal_state="NEED_EVIDENCE",
            findings_merge={},
            frozen_hash=sha2,
            target_ref=dev_ref2,
            evidence_debt=["Source the claimed actor and lag or demote the mechanism step."],
        )
        review_good["findings"] = flagged
        result_good = freeze_review(workspace, review_good, run_id="specificity-debt")
        assert result_good.returncode == 0, result_good.stderr

    def test_bundle_requires_member_ablation_finding(self, workspace):
        dev_ref, sha = freeze_dev(workspace, target="B1", run_id="bundle-noablation")
        review = valid_review_v2(target_type="B", target_id="B1", frozen_hash=sha, target_ref=dev_ref)
        result = freeze_review(workspace, review, run_id="bundle-noablation")
        assert result.returncode != 0
        assert "member_ablation" in result.stderr

    @pytest.mark.parametrize("bad_state", ["READY", "BLOCKED", "MODEL_READY ", "REVISE"])
    def test_no_fourth_terminal_state(self, workspace, bad_state):
        run_id = f"fourth-status-{bad_state.strip().lower().replace('_', '-')}"
        dev_ref, sha = freeze_dev(workspace, run_id=run_id)
        review = valid_review_v2(terminal_state=bad_state, frozen_hash=sha, target_ref=dev_ref)
        result = freeze_review(workspace, review, run_id=run_id)
        assert result.returncode != 0
        assert "terminal_state" in result.stderr


# ---------------------------------------------------------------------------
# 6. Critic independence requirements
# ---------------------------------------------------------------------------


class TestCriticIndependence:
    def test_missing_reassessment_rejected(self, workspace):
        """Developer census alone is not acceptable: independent reassessment is mandatory."""
        dev_ref, sha = freeze_dev(workspace, run_id="no-reassess")
        review = valid_review_v2(frozen_hash=sha, target_ref=dev_ref)
        del review["load_bearing_reassessment"]
        result = freeze_review(workspace, review, run_id="no-reassess")
        assert result.returncode != 0
        assert "load_bearing_reassessment" in result.stderr
        assert "not authority" in result.stderr

    def test_empty_reassessment_rejected(self, workspace):
        dev_ref, sha = freeze_dev(workspace, run_id="empty-reassess")
        review = valid_review_v2(load_bearing_reassessment=[], frozen_hash=sha, target_ref=dev_ref)
        result = freeze_review(workspace, review, run_id="empty-reassess")
        assert result.returncode != 0

    def test_critic_may_override_developer_labels(self, workspace):
        """Dogfood: developer marks a claim SUPPORTED; critic independently demotes it."""
        dev_ref, sha = freeze_dev(workspace, run_id="override")
        review = valid_review_v2(
            load_bearing_reassessment=[
                {"claim": "Portal adoption is driven by tacit-knowledge gaps",
                 "critic_epistemic_status": "SPECULATIVE"},
            ],
            terminal_state="NEED_EVIDENCE",
            evidence_debt=["Interview recent hires to test the tacit-knowledge gap claim."],
            frozen_hash=sha,
            target_ref=dev_ref,
        )
        result = freeze_review(workspace, review, run_id="override")
        assert result.returncode == 0, result.stderr

    def test_invalid_critic_status_enum_rejected(self, workspace):
        dev_ref, sha = freeze_dev(workspace, run_id="bad-enum")
        review = valid_review_v2(
            load_bearing_reassessment=[
                {"claim": "x", "critic_epistemic_status": "PROBABLY_TRUE"},
            ],
            frozen_hash=sha,
            target_ref=dev_ref,
        )
        result = freeze_review(workspace, review, run_id="bad-enum")
        assert result.returncode != 0
        assert "critic_epistemic_status" in result.stderr

    def test_countermodel_required(self, workspace):
        dev_ref, sha = freeze_dev(workspace, run_id="no-countermodel")
        review = valid_review_v2(independent_countermodel="", frozen_hash=sha, target_ref=dev_ref)
        result = freeze_review(workspace, review, run_id="no-countermodel")
        assert result.returncode != 0
        assert "independent_countermodel" in result.stderr

    def test_cheapest_test_required(self, workspace):
        dev_ref, sha = freeze_dev(workspace, run_id="no-cheapest")
        review = valid_review_v2(cheapest_discriminating_test=None, frozen_hash=sha, target_ref=dev_ref)
        result = freeze_review(workspace, review, run_id="no-cheapest")
        assert result.returncode != 0

    def test_round_trip_skeleton_required(self, workspace):
        dev_ref, sha = freeze_dev(workspace, run_id="no-skeleton")
        review = valid_review_v2(frozen_hash=sha, target_ref=dev_ref)
        del review["findings"]["round_trip_skeleton"]
        result = freeze_review(workspace, review, run_id="no-skeleton")
        assert result.returncode != 0
        assert "round_trip_skeleton" in result.stderr

    def test_frozen_hash_required(self, workspace):
        dev_ref, sha = freeze_dev(workspace, run_id="no-hash")
        review = valid_review_v2(frozen_hash="", target_ref=dev_ref)
        result = freeze_review(workspace, review, run_id="no-hash")
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# 7. Payload ceiling — 128 KiB fail-closed with cleanup
# ---------------------------------------------------------------------------


class TestPayloadCeiling:
    def test_oversized_review_rejected_and_cleaned_up(self, workspace):
        dev_ref, sha = freeze_dev(workspace, run_id="review-too-big")
        review = valid_review_v2(
            independent_countermodel="x" * 131073,
            frozen_hash=sha,
            target_ref=dev_ref,
        )
        result = freeze_review(workspace, review, run_id="review-too-big")
        assert result.returncode != 0
        assert "PAYLOAD_TOO_LARGE" in result.stderr
        assert "131072" in result.stderr
        run_dir = workspace[0] / ".ai" / "pizm" / "run-review-too-big"
        assert not (run_dir / "deep-review-v2.json").exists()
        assert not (run_dir / "deep-review-v2.sha256").exists()
        assert not (run_dir / "deep-review-v2.meta.json").exists()

    def test_development_ceiling_192kib_fail_closed(self, workspace):
        """development-v2 ceiling: >196608 bytes rejected, nothing left behind."""
        project, skill = workspace
        dev = valid_dev_v2()
        dev["developed_model"]["synthesis"] = "y" * 197000
        path = write_json(project / "pending-dev.json", dev)
        result = run_ck(
            "freeze", "--stage", "development-v2", "--run-id", "dev-too-big",
            "--input", path,
            "--project-root", str(project),
            "--skill-root", str(skill),
        )
        assert result.returncode != 0
        assert "PAYLOAD_TOO_LARGE" in result.stderr
        assert "196608" in result.stderr
        run_dir = project / ".ai" / "pizm" / "run-dev-too-big"
        assert not (run_dir / "development-v2.json").exists()
        assert not (run_dir / "development-v2.meta.json").exists()


# ---------------------------------------------------------------------------
# 8. Old stages still validate (regression through old path)
# ---------------------------------------------------------------------------


class TestOldStagesStillValid:
    def test_v1_deep_stage_still_freezes(self, workspace):
        """The legacy 'deep' stage (pizm-development-v1) keeps validating."""
        project, skill = workspace
        v1 = {
            "schema_version": "pizm-development-v1",
            "stage": "deep",
            "selected_p_ids": ["P1", "P3"],
            "development": {"P1": {"body": "old"}, "P3": {"body": "old too"}},
        }
        path = write_json(project / "pending-dev-v1.json", v1)
        result = run_ck(
            "freeze", "--stage", "deep", "--run-id", "legacy-deep",
            "--input", path,
            "--project-root", str(project),
            "--skill-root", str(skill),
        )
        assert result.returncode == 0, result.stderr
        run_dir = project / ".ai" / "pizm" / "run-legacy-deep"
        assert (run_dir / "development.json").exists()
        assert (run_dir / "development.meta.json").exists()

    def test_v1_and_v2_coexist_same_run_dir(self, workspace):
        """Stage-scoped prefixes keep v1 development.json and v2 development-v2.json apart."""
        project, skill = workspace
        v1 = {
            "schema_version": "pizm-development-v1",
            "stage": "deep",
            "selected_p_ids": ["P1"],
            "development": {"P1": {"body": "old"}},
        }
        p1 = write_json(project / "d1.json", v1)
        r1 = run_ck("freeze", "--stage", "deep", "--run-id", "coexist",
                    "--input", p1, "--project-root", str(project), "--skill-root", str(skill))
        p2 = write_json(project / "d2.json", valid_dev_v2())
        r2 = run_ck("freeze", "--stage", "development-v2", "--run-id", "coexist",
                    "--input", p2, "--project-root", str(project), "--skill-root", str(skill))
        assert r1.returncode == 0, r1.stderr
        assert r2.returncode == 0, r2.stderr
        run_dir = project / ".ai" / "pizm" / "run-coexist"
        assert (run_dir / "development.json").exists()
        assert (run_dir / "development-v2.json").exists()


# ---------------------------------------------------------------------------
# 9. Critic B1-B4 Readiness Couplings & Defect Regression
# ---------------------------------------------------------------------------


class TestCriticB1ToB4ReadinessCouplings:
    """Deterministic coupling tests for B1-B4 blockers and soft warnings."""

    def test_critic_b1_speculative_central_mechanism_blocks_model_ready(self, workspace):
        """B1: Speculative central mechanism blocks MODEL_READY without claiming contradiction."""
        dev_ref, sha = freeze_dev(workspace, run_id="b1-blocker")
        review_bad = valid_review_v2(
            terminal_state="MODEL_READY",
            frozen_hash=sha,
            target_ref=dev_ref,
            findings_merge={
                "unresolved_load_bearing_contradiction": False,
                "readiness_blockers": ["B1_SPECULATIVE_DEPENDENCY"],
                "readiness_blocker_details": {
                    "B1_SPECULATIVE_DEPENDENCY": "Tacit knowledge gap is speculative",
                },
            },
            load_bearing_reassessment=[
                {"claim": "Tacit knowledge gap is primary driver", "critic_epistemic_status": "SPECULATIVE"}
            ],
            evidence_debt=["Empirical proof of knowledge gap required"],
        )
        res_bad = freeze_review(workspace, review_bad, run_id="b1-blocker")
        assert res_bad.returncode != 0
        assert "MODEL_READY" in res_bad.stderr

        review_ok = valid_review_v2(
            terminal_state="NEED_EVIDENCE",
            frozen_hash=sha,
            target_ref=dev_ref,
            findings_merge={
                "unresolved_load_bearing_contradiction": False,
                "readiness_blockers": ["B1_SPECULATIVE_DEPENDENCY"],
                "readiness_blocker_details": {
                    "B1_SPECULATIVE_DEPENDENCY": "Tacit knowledge gap is speculative",
                },
            },
            load_bearing_reassessment=[
                {"claim": "Tacit knowledge gap is primary driver", "critic_epistemic_status": "SPECULATIVE"}
            ],
            evidence_debt=["Empirical proof of knowledge gap required"],
        )
        res_ok = freeze_review(workspace, review_ok, run_id="b1-blocker")
        assert res_ok.returncode == 0, res_ok.stderr

    def test_critic_b2_stronger_countermodel_blocks_model_ready(self, workspace):
        """B2: Materially stronger countermodel blocks MODEL_READY."""
        dev_ref, sha = freeze_dev(workspace, run_id="b2-blocker")
        review_bad = valid_review_v2(
            terminal_state="MODEL_READY",
            frozen_hash=sha,
            target_ref=dev_ref,
            findings_merge={
                "unresolved_load_bearing_contradiction": False,
                "readiness_blockers": ["B2_STRONGER_COUNTERMODEL"],
                "readiness_blocker_details": {
                    "B2_STRONGER_COUNTERMODEL": "Simpler habit model explains variance.",
                },
            },
            independent_countermodel="Simpler organizational habit model explains full variance with fewer assumptions.",
        )
        res_bad = freeze_review(workspace, review_bad, run_id="b2-blocker")
        assert res_bad.returncode != 0
        assert "MODEL_READY" in res_bad.stderr

        review_ok = valid_review_v2(
            terminal_state="RETURN_TO_EXPLORE",
            frozen_hash=sha,
            target_ref=dev_ref,
            findings_merge={
                "unresolved_load_bearing_contradiction": False,
                "readiness_blockers": ["B2_STRONGER_COUNTERMODEL"],
                "readiness_blocker_details": {
                    "B2_STRONGER_COUNTERMODEL": "Simpler habit model explains variance.",
                },
            },
            independent_countermodel="Simpler organizational habit model explains full variance with fewer assumptions.",
        )
        res_ok = freeze_review(workspace, review_ok, run_id="b2-blocker")
        assert res_ok.returncode == 0, res_ok.stderr

    def test_critic_b3_thesis_epistemic_laundering_blocks_model_ready(self, workspace):
        """B3: Thesis-level epistemic laundering blocks MODEL_READY."""
        dev_ref, sha = freeze_dev(workspace, run_id="b3-blocker")
        review_bad = valid_review_v2(
            terminal_state="MODEL_READY",
            frozen_hash=sha,
            target_ref=dev_ref,
            findings_merge={
                "unresolved_load_bearing_contradiction": False,
                "readiness_blockers": ["B3_THESIS_LAUNDERING"],
                "readiness_blocker_details": {
                    "B3_THESIS_LAUNDERING": "Synthesis states mechanism as certain while census is speculative.",
                },
                "epistemic_laundering": ["Synthesis states mechanism as certain while census is 75% speculative."],
            },
            evidence_debt=["Narrow thesis or validate central claims."],
        )
        res_bad = freeze_review(workspace, review_bad, run_id="b3-blocker")
        assert res_bad.returncode != 0
        assert "MODEL_READY" in res_bad.stderr

        review_ok = valid_review_v2(
            terminal_state="NEED_EVIDENCE",
            frozen_hash=sha,
            target_ref=dev_ref,
            findings_merge={
                "unresolved_load_bearing_contradiction": False,
                "readiness_blockers": ["B3_THESIS_LAUNDERING"],
                "readiness_blocker_details": {
                    "B3_THESIS_LAUNDERING": "Synthesis states mechanism as certain while census is speculative.",
                },
                "epistemic_laundering": ["Synthesis states mechanism as certain while census is 75% speculative."],
            },
            evidence_debt=["Narrow thesis or validate central claims."],
        )
        res_ok = freeze_review(workspace, review_ok, run_id="b3-blocker")
        assert res_ok.returncode == 0, res_ok.stderr

    def test_critic_b4_coverage_mismatch_blocks_model_ready(self, workspace):
        """B4: Global-thesis vs local-support mismatch blocks MODEL_READY."""
        dev_ref, sha = freeze_dev(workspace, run_id="b4-blocker")
        review_bad = valid_review_v2(
            terminal_state="MODEL_READY",
            frozen_hash=sha,
            target_ref=dev_ref,
            findings_merge={
                "unresolved_load_bearing_contradiction": False,
                "readiness_blockers": ["B4_COVERAGE_MISMATCH"],
                "readiness_blocker_details": {
                    "B4_COVERAGE_MISMATCH": "Model claims full lifecycle explanation but supports only morning debrief.",
                },
                "cross_field_contradictions": ["Model claims full lifecycle explanation but supports only morning debrief."],
            },
        )
        res_bad = freeze_review(workspace, review_bad, run_id="b4-blocker")
        assert res_bad.returncode != 0
        assert "MODEL_READY" in res_bad.stderr

        review_ok = valid_review_v2(
            terminal_state="NEED_EVIDENCE",
            frozen_hash=sha,
            target_ref=dev_ref,
            findings_merge={
                "unresolved_load_bearing_contradiction": False,
                "readiness_blockers": ["B4_COVERAGE_MISMATCH"],
                "readiness_blocker_details": {
                    "B4_COVERAGE_MISMATCH": "Model claims full lifecycle explanation but supports only morning debrief.",
                },
                "cross_field_contradictions": ["Model claims full lifecycle explanation but supports only morning debrief."],
            },
            evidence_debt=["Narrow scope to morning debrief or provide full lifecycle trace."],
        )
        res_ok = freeze_review(workspace, review_ok, run_id="b4-blocker")
        assert res_ok.returncode == 0, res_ok.stderr

    def test_soft_warning_peripheral_debt_allows_model_ready(self, workspace):
        """Soft warnings (peripheral debt, no unresolved load-bearing contradiction) allow MODEL_READY."""
        dev_ref, sha = freeze_dev(workspace, run_id="soft-warning-ready")
        review = valid_review_v2(
            terminal_state="MODEL_READY",
            frozen_hash=sha,
            target_ref=dev_ref,
            findings_merge={"unresolved_load_bearing_contradiction": False},
            evidence_debt=["Secondary telemetry metric on edge latency."],
        )
        res = freeze_review(workspace, review, run_id="soft-warning-ready")
        assert res.returncode == 0, res.stderr

    def test_night_drift_defect_regression_contract(self, workspace):
        """Regression test for Night Drift baseline defect: 3/4 speculative claims + laundering forbids MODEL_READY."""
        dev_ref, sha = freeze_dev(workspace, run_id="night-drift-regression")
        review_bad = valid_review_v2(
            terminal_state="MODEL_READY",
            frozen_hash=sha,
            target_ref=dev_ref,
            findings_merge={
                "unresolved_load_bearing_contradiction": False,
                "readiness_blockers": ["B1_SPECULATIVE_DEPENDENCY", "B3_THESIS_LAUNDERING"],
                "readiness_blocker_details": {
                    "B1_SPECULATIVE_DEPENDENCY": "3 of 4 claims speculative",
                    "B3_THESIS_LAUNDERING": "Synthesis speaks with higher confidence than census",
                },
                "epistemic_laundering": ["Synthesis speaks with higher confidence than census where 3/4 claims are speculative."],
            },
            load_bearing_reassessment=[
                {"claim": "Author experienced night without choice forks", "critic_epistemic_status": "SUPPORTED"},
                {"claim": "Self-report codes night as repetition", "critic_epistemic_status": "SPECULATIVE"},
                {"claim": "7 AM debrief functions to close loop", "critic_epistemic_status": "SPECULATIVE"},
                {"claim": "Explanatory frame relocates guilt", "critic_epistemic_status": "SPECULATIVE"},
            ],
            independent_countermodel="Chronological fatigue inertia without recursive orbit.",
            evidence_debt=["Item 1", "Item 2", "Item 3", "Item 4"],
            verdict_rationale="Attempting to mark MODEL_READY despite 3/4 speculative claims and countermodel.",
        )
        res_bad = freeze_review(workspace, review_bad, run_id="night-drift-regression")
        assert res_bad.returncode != 0
        assert "MODEL_READY" in res_bad.stderr

        review_good = valid_review_v2(
            terminal_state="NEED_EVIDENCE",
            frozen_hash=sha,
            target_ref=dev_ref,
            findings_merge={
                "unresolved_load_bearing_contradiction": False,
                "readiness_blockers": ["B1_SPECULATIVE_DEPENDENCY", "B3_THESIS_LAUNDERING"],
                "readiness_blocker_details": {
                    "B1_SPECULATIVE_DEPENDENCY": "3 of 4 claims speculative",
                    "B3_THESIS_LAUNDERING": "Synthesis speaks with higher confidence than census",
                },
                "epistemic_laundering": ["Synthesis speaks with higher confidence than census where 3/4 claims are speculative."],
            },
            load_bearing_reassessment=[
                {"claim": "Author experienced night without choice forks", "critic_epistemic_status": "SUPPORTED"},
                {"claim": "Self-report codes night as repetition", "critic_epistemic_status": "SPECULATIVE"},
                {"claim": "7 AM debrief functions to close loop", "critic_epistemic_status": "SPECULATIVE"},
                {"claim": "Explanatory frame relocates guilt", "critic_epistemic_status": "SPECULATIVE"},
            ],
            independent_countermodel="Chronological fatigue inertia without recursive orbit.",
            evidence_debt=["Item 1", "Item 2", "Item 3", "Item 4"],
            verdict_rationale="Gate enforced: 3/4 speculative claims and countermodel require NEED_EVIDENCE.",
        )
        res_good = freeze_review(workspace, review_good, run_id="night-drift-regression")
        assert res_good.returncode == 0, res_good.stderr

    def test_readiness_blockers_forbid_model_ready(self, workspace):
        """Any readiness blocker forbids MODEL_READY even if unresolved_load_bearing_contradiction is False."""
        dev_ref, sha = freeze_dev(workspace, run_id="blocker-forbids-ready")
        review = valid_review_v2(
            terminal_state="MODEL_READY",
            frozen_hash=sha,
            target_ref=dev_ref,
            findings_merge={
                "unresolved_load_bearing_contradiction": False,
                "readiness_blockers": ["B2_STRONGER_COUNTERMODEL"],
                "readiness_blocker_details": {
                    "B2_STRONGER_COUNTERMODEL": "Countermodel exists",
                },
            },
        )
        res = freeze_review(workspace, review, run_id="blocker-forbids-ready")
        assert res.returncode != 0
        assert "MODEL_READY is forbidden while findings.readiness_blockers is non-empty" in res.stderr


def test_readiness_blockers_do_not_claim_contradiction(workspace):
    """Readiness blockers independently forbid MODEL_READY without forcing unresolved contradiction to true."""
    dev_ref, sha = freeze_dev(workspace, run_id="blockers-no-contradiction")
    review = valid_review_v2(
        terminal_state="NEED_EVIDENCE",
        frozen_hash=sha,
        target_ref=dev_ref,
        findings_merge={
            "unresolved_load_bearing_contradiction": False,
            "readiness_blockers": ["B1_SPECULATIVE_DEPENDENCY"],
            "readiness_blocker_details": {
                "B1_SPECULATIVE_DEPENDENCY": "Speculative dependency without contradiction",
            },
        },
    )
    assert review["findings"]["unresolved_load_bearing_contradiction"] is False
    res = freeze_review(workspace, review, run_id="blockers-no-contradiction")
    assert res.returncode == 0, res.stderr


def test_need_evidence_requires_inquiry_program(workspace):
    """NEED_EVIDENCE requires non-null inquiry_program with all required keys."""
    dev_ref, sha = freeze_dev(workspace, run_id="need-evidence-inquiry")
    # Missing inquiry_program
    review_no_inquiry = valid_review_v2(
        terminal_state="NEED_EVIDENCE",
        frozen_hash=sha,
        target_ref=dev_ref,
        inquiry_program=None,
    )
    res_bad = freeze_review(workspace, review_no_inquiry, run_id="need-evidence-inquiry")
    assert res_bad.returncode != 0
    assert "inquiry_program must be an object for NEED_EVIDENCE" in res_bad.stderr

    # Valid inquiry_program
    review_ok = valid_review_v2(
        terminal_state="NEED_EVIDENCE",
        frozen_hash=sha,
        target_ref=dev_ref,
        inquiry_program={
            "current_leading_models": ["Model A", "Model B"],
            "unresolved_questions": ["Question 1?"],
            "strongest_live_rival": "Rival Model",
            "result_that_would_change_model": "Signal X observed",
            "stop_rule": "Observation of X or 10 samples checked",
        },
    )
    res_ok = freeze_review(workspace, review_ok, run_id="need-evidence-inquiry")
    assert res_ok.returncode == 0, res_ok.stderr
