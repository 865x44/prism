"""
Unit and regression tests for pizm_run_state and route-aware artifact projection.

Covers:
- Matrix of (route, artifact_shape, execution_completion, semantic_outcome)
- Transliteration / deterministic slugification rules
- Regression Case A: Comparison-only BONK (2 Developments + comparison review, no single reviews)
- Regression Case B: BONK single fallback (NO_SECOND_DEFENSIBLE_BUNDLE + 1 Dev + 1 Review)
- Regression Case C: AUTO with Critic verdict rationale in Final
- Regression Case D: MANUAL / legacy runs with unrecorded metadata
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = REPO_ROOT / "bin"
if str(BIN_DIR) not in sys.path:
    sys.path.insert(0, str(BIN_DIR))

import pizm_run_state
from pizm_render_html import render_run_html

BUNDLE_CLI = str(BIN_DIR / "pizm-session-bundle")
CHECKPOINT_CLI = str(BIN_DIR / "pizm-checkpoint")
SKILL_ROOT = REPO_ROOT / "skills" / "pizm"


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Slugification and Transliteration
# ---------------------------------------------------------------------------

def test_slugify_subject_transliteration_and_ascii():
    assert pizm_run_state.slugify_subject("Комки") == "komki"
    assert pizm_run_state.slugify_subject("Voices of Nerat") == "voices-of-nerat"
    assert pizm_run_state.slugify_subject("Prism next step") == "prism-next-step"
    assert pizm_run_state.slugify_subject("Target Voice Pipeline v1.1 — analysis") == "target-voice-pipeline-v1-1-analysis"
    assert pizm_run_state.slugify_subject("") == "untitled"
    assert pizm_run_state.slugify_subject(None) == "untitled"
    assert pizm_run_state.slugify_subject("   ---   ") == "untitled"


def test_generate_run_id_format():
    rid = pizm_run_state.generate_run_id("Комки")
    assert rid.startswith("komki-")
    parts = rid.split("-")
    assert len(parts) >= 3
    # Suffix length 4
    assert len(parts[-1]) == 4


# ---------------------------------------------------------------------------
# State Resolution Matrix
# ---------------------------------------------------------------------------

def test_state_resolution_portfolio_terminal():
    # GATHER_INFORMATION
    s1 = pizm_run_state.resolve_run_state(
        portfolio={
            "schema_version": "pizm-portfolio-selection-v2",
            "route": "AUTO",
            "next_reasoning_move": "GATHER_INFORMATION",
        }
    )
    assert s1.route == "AUTO"
    assert s1.artifact_shape == "PORTFOLIO_TERMINAL"
    assert s1.execution_completion == "COMPLETE"
    assert s1.semantic_outcome == "GATHER_INFORMATION"
    assert s1.is_complete is True

    # PRESERVE_ONLY
    s2 = pizm_run_state.resolve_run_state(
        portfolio={
            "schema_version": "pizm-portfolio-selection-v2",
            "route": "AUTO",
            "next_reasoning_move": "PRESERVE_ONLY",
        }
    )
    assert s2.route == "AUTO"
    assert s2.artifact_shape == "PORTFOLIO_TERMINAL"
    assert s2.execution_completion == "COMPLETE"
    assert s2.semantic_outcome == "PRESERVE_ONLY"
    assert s2.is_complete is True


def test_state_resolution_comparison_only_bonk():
    for pref in ("LEFT", "RIGHT", "CONDITIONAL", "UNRESOLVED"):
        state = pizm_run_state.resolve_run_state(
            portfolio={
                "schema_version": "pizm-portfolio-selection-v2",
                "route": "BONK",
                "competition_status": "TWO_DEFENSIBLE_BUNDLES",
            },
            developments=[
                {"target": {"target_id": "B1"}},
                {"target": {"target_id": "B2"}},
            ],
            reviews=[],  # No standalone reviews!
            comparison={
                "comparison": {
                    "current_preference": pref,
                    "competition_axis": "Latency vs Coordination",
                }
            },
        )
        assert state.route == "BONK"
        assert state.artifact_shape == "COMPARISON_REVIEW"
        assert state.execution_completion == "COMPLETE"
        assert state.semantic_outcome == pref
        assert state.is_complete is True
        assert state.missing_next is None


def test_state_resolution_bonk_single_fallback():
    # NO_SECOND_DEFENSIBLE_BUNDLE
    state = pizm_run_state.resolve_run_state(
        portfolio={
            "schema_version": "pizm-portfolio-selection-v2",
            "route": "BONK",
            "competition_status": "NO_SECOND_DEFENSIBLE_BUNDLE",
            "single_target": {"target_type": "B", "target_id": "B1"},
        },
        developments=[{"target": {"target_id": "B1"}}],
        reviews=[{"target_id": "B1", "terminal_state": "MODEL_READY"}],
    )
    assert state.route == "BONK"
    assert state.artifact_shape == "SINGLE_DEEP_REVIEW"
    assert state.execution_completion == "COMPLETE"
    assert state.semantic_outcome == "MODEL_READY"
    assert state.is_complete is True


def test_state_resolution_auto_and_manual():
    # Standard complete AUTO
    s_auto = pizm_run_state.resolve_run_state(
        portfolio={
            "schema_version": "pizm-portfolio-selection-v1",
            "route": "AUTO",
            "auto_target": {"target_type": "P", "target_id": "P1"},
        },
        developments=[{"target": {"target_id": "P1"}}],
        reviews=[{"target_id": "P1", "terminal_state": "NEED_EVIDENCE"}],
    )
    assert s_auto.route == "AUTO"
    assert s_auto.artifact_shape == "SINGLE_DEEP_REVIEW"
    assert s_auto.execution_completion == "COMPLETE"
    assert s_auto.semantic_outcome == "NEED_EVIDENCE"

    # Manual route without portfolio
    s_man = pizm_run_state.resolve_run_state(
        developments=[{"target": {"target_id": "P1"}}],
        reviews=[{"target_id": "P1", "terminal_state": "MODEL_READY"}],
    )
    assert s_man.route == "MANUAL"
    assert s_man.artifact_shape == "SINGLE_DEEP_REVIEW"
    assert s_man.execution_completion == "COMPLETE"
    assert s_man.semantic_outcome == "MODEL_READY"


# ---------------------------------------------------------------------------
# Regression A: Comparison-only BONK E2E
# ---------------------------------------------------------------------------

def test_regression_a_comparison_only_bonk_bundle_and_render(tmp_path):
    """Case A: 2 Developments + comparison review, ZERO single reviews.
    Must create session bundle without fake reviews, mark run complete,
    render comparison, show CONDITIONAL/UNRESOLVED correctly without 'not reached'.
    """
    out_root = tmp_path / "bundles"
    out_root.mkdir()

    # Create stage dirs
    p1_dir = tmp_path / "p1"
    p1_dir.mkdir()
    c1 = {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "NORMAL", "candidates": [{"candidate_id": "c01", "title": "C1"}]}
    c1_b = json.dumps(c1).encode()
    (p1_dir / "candidates.json").write_bytes(c1_b)
    (p1_dir / "candidates.sha256").write_text(_sha256_hex(c1_b))

    port_dir = tmp_path / "port"
    port_dir.mkdir()
    port = {
        "schema_version": "pizm-portfolio-selection-v2",
        "stage": "portfolio",
        "route": "BONK",
        "competition_status": "TWO_DEFENSIBLE_BUNDLES",
        "perspectives": {"P1": "pass01:c01"},
        "bundles": [
            {"bundle_id": "B1", "member_refs": ["pass01:c01"], "bundle_thesis": "Thesis 1"},
            {"bundle_id": "B2", "member_refs": ["pass01:c01"], "bundle_thesis": "Thesis 2"},
        ],
        "recommended_competition": {"left_bundle_id": "B1", "right_bundle_id": "B2"},
    }
    port_b = json.dumps(port).encode()
    (port_dir / "portfolio.json").write_bytes(port_b)
    (port_dir / "portfolio.sha256").write_text(_sha256_hex(port_b))

    db1_dir = tmp_path / "db1"
    db1_dir.mkdir()
    db1 = {"schema_version": "pizm-development-v2", "stage": "development-v2", "target": {"target_type": "B", "target_id": "B1"}, "developed_model": {"thesis": "B1 Thesis"}}
    db1_b = json.dumps(db1).encode()
    (db1_dir / "development-v2-B1.json").write_bytes(db1_b)
    (db1_dir / "development-v2-B1.sha256").write_text(_sha256_hex(db1_b))

    db2_dir = tmp_path / "db2"
    db2_dir.mkdir()
    db2 = {"schema_version": "pizm-development-v2", "stage": "development-v2", "target": {"target_type": "B", "target_id": "B2"}, "developed_model": {"thesis": "B2 Thesis"}}
    db2_b = json.dumps(db2).encode()
    (db2_dir / "development-v2-B2.json").write_bytes(db2_b)
    (db2_dir / "development-v2-B2.sha256").write_text(_sha256_hex(db2_b))

    comp_dir = tmp_path / "comp"
    comp_dir.mkdir()
    comp = {
        "schema_version": "pizm-comparison-review-v1",
        "stage": "comparison-review-v1",
        "left_target_id": "B1",
        "right_target_id": "B2",
        "left_review": {
            "target_id": "B1",
            "development_ref": "development-v2-B1.json",
            "frozen_hash": _sha256_hex(db1_b),
            "terminal_state": "MODEL_READY",
        },
        "right_review": {
            "target_id": "B2",
            "development_ref": "development-v2-B2.json",
            "frozen_hash": _sha256_hex(db2_b),
            "terminal_state": "MODEL_READY",
        },
        "comparison": {
            "current_preference": "CONDITIONAL",
            "competition_axis": "Feedback loop latency vs Coordination overhead",
            "strongest_reason_for_left": "High throughput",
            "strongest_reason_for_right": "Low coordination tax",
            "discriminating_observation": "Cross-repo PR turnaround telemetry",
            "what_would_change_the_decision": "Evidence of team split",
        },
    }
    comp_b = json.dumps(comp).encode()
    (comp_dir / "comparison-review-v1.json").write_bytes(comp_b)
    (comp_dir / "comparison-review-v1.sha256").write_text(_sha256_hex(comp_b))

    acc_file = tmp_path / "acc.json"
    acc_file.write_text(json.dumps({
        "host_inference_count": 6,
        "model_repair_count": 0,
        "checkpoint_retry_count": 0,
    }))

    # 1. Test create_bundle with ZERO single reviews
    cmd = [
        sys.executable, BUNDLE_CLI, "create",
        "--output-root", str(out_root),
        "--slug", "session-comp-only",
        "--skill-root", str(SKILL_ROOT),
        "--stage", f"pass-01-normal={p1_dir}",
        "--stage", f"portfolio={port_dir}",
        "--stage", f"deep-B1={db1_dir}",
        "--stage", f"deep-B2={db2_dir}",
        "--stage", f"comparison-review={comp_dir}",
        "--accounting", str(acc_file),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    bundle = out_root / "session-comp-only"
    assert bundle.is_dir()

    # 2. Render HTML from a run directory containing the frozen artifacts
    run_dir = tmp_path / "bonk-comp-run"
    run_dir.mkdir()
    (run_dir / "candidates-pass01.json").write_bytes(c1_b)
    (run_dir / "candidates-pass01.sha256").write_text(_sha256_hex(c1_b))
    (run_dir / "portfolio.json").write_bytes(port_b)
    (run_dir / "portfolio.sha256").write_text(_sha256_hex(port_b))
    (run_dir / "development-v2-B1.json").write_bytes(db1_b)
    (run_dir / "development-v2-B1.sha256").write_text(_sha256_hex(db1_b))
    (run_dir / "development-v2-B2.json").write_bytes(db2_b)
    (run_dir / "development-v2-B2.sha256").write_text(_sha256_hex(db2_b))
    (run_dir / "comparison-review-v1.json").write_bytes(comp_b)
    (run_dir / "comparison-review-v1.sha256").write_text(_sha256_hex(comp_b))

    html_out = tmp_path / "run.html"
    rc = render_run_html(str(run_dir), "Compare PR models", str(html_out))
    assert rc == 0
    html_text = html_out.read_text(encoding="utf-8")

    # Assertions on HTML
    assert "CONDITIONAL" in html_text
    assert "Feedback loop latency vs Coordination overhead" in html_text
    assert "Cross-repo PR turnaround telemetry" in html_text
    assert "Final: not reached" not in html_text
    assert "W1 content notice" not in html_text
    # Critic section is not empty
    critic_sec = html_text.split('id="critic"', 1)[1].split("</section>", 1)[0]
    assert "Comparison review" in critic_sec
    assert "CONDITIONAL" in critic_sec


# ---------------------------------------------------------------------------
# Regression B: BONK Single Fallback
# ---------------------------------------------------------------------------

def test_regression_b_bonk_single_fallback_renders(tmp_path):
    run_dir = tmp_path / "bonk-single"
    run_dir.mkdir()

    port = {
        "schema_version": "pizm-portfolio-selection-v2",
        "stage": "portfolio",
        "route": "BONK",
        "competition_status": "NO_SECOND_DEFENSIBLE_BUNDLE",
        "single_target": {"target_type": "B", "target_id": "B1"},
        "perspectives": {"P1": "pass01:c01"},
    }
    (run_dir / "portfolio.json").write_text(json.dumps(port))
    (run_dir / "portfolio.sha256").write_text(_sha256_hex(json.dumps(port).encode()))

    dev = {"schema_version": "pizm-development-v2", "stage": "development-v2", "target": {"target_type": "B", "target_id": "B1"}, "developed_model": {"thesis": "Solo Thesis"}}
    (run_dir / "development-v2-B1.json").write_text(json.dumps(dev))
    (run_dir / "development-v2-B1.sha256").write_text(_sha256_hex(json.dumps(dev).encode()))

    rev = {"schema_version": "pizm-deep-review-v2", "stage": "deep-review-v2", "target_id": "B1", "terminal_state": "MODEL_READY", "verdict_rationale": "Solid standalone model"}
    (run_dir / "deep-review-v2-B1.json").write_text(json.dumps(rev))
    (run_dir / "deep-review-v2-B1.sha256").write_text(_sha256_hex(json.dumps(rev).encode()))

    html_out = tmp_path / "run.html"
    rc = render_run_html(str(run_dir), "Solo bundle task", str(html_out))
    assert rc == 0
    html_text = html_out.read_text(encoding="utf-8")
    assert "MODEL_READY" in html_text
    assert "Solid standalone model" in html_text
    assert "Final: not reached" not in html_text


# ---------------------------------------------------------------------------
# Regression C: AUTO with Critic verdict rationale
# ---------------------------------------------------------------------------

def test_regression_c_auto_critic_rationale_projected_in_final(tmp_path):
    run_dir = tmp_path / "auto-run"
    run_dir.mkdir()

    port = {
        "schema_version": "pizm-portfolio-selection-v1",
        "stage": "portfolio",
        "route": "AUTO",
        "auto_target": {"target_type": "P", "target_id": "P1"},
        "perspectives": {"P1": "pass01:c01"},
    }
    (run_dir / "portfolio.json").write_text(json.dumps(port))
    (run_dir / "portfolio.sha256").write_text(_sha256_hex(json.dumps(port).encode()))

    dev = {"schema_version": "pizm-development-v2", "stage": "development-v2", "target": {"target_type": "P", "target_id": "P1"}, "identity_lock": {"title": "Feedback Loop"}}
    (run_dir / "development-v2.json").write_text(json.dumps(dev))
    (run_dir / "development-v2.sha256").write_text(_sha256_hex(json.dumps(dev).encode()))

    rev = {
        "schema_version": "pizm-deep-review-v2",
        "stage": "deep-review-v2",
        "target_id": "P1",
        "terminal_state": "NEED_EVIDENCE",
        "verdict_rationale": "Batch size hypothesis lacks empirical calibration data.",
    }
    (run_dir / "deep-review-v2.json").write_text(json.dumps(rev))
    (run_dir / "deep-review-v2.sha256").write_text(_sha256_hex(json.dumps(rev).encode()))
    html_out = tmp_path / "run.html"
    rc = render_run_html(str(run_dir), "Auto task", str(html_out))
    assert rc == 0
    html_text = html_out.read_text(encoding="utf-8")
    final_sec = html_text.split('id="final"', 1)[1].split("</section>", 1)[0]
    assert "Batch size hypothesis lacks empirical calibration data." in final_sec
    assert "Honest stop" in final_sec

def test_regression_d_manual_legacy_unrecorded_metadata_renders_safely(tmp_path):
    run_dir = tmp_path / "legacy-manual"
    run_dir.mkdir()

    dev = {"schema_version": "pizm-development-v2", "stage": "development-v2", "target": {"target_type": "P", "target_id": "P1"}}
    (run_dir / "development-v2.json").write_text(json.dumps(dev))
    (run_dir / "development-v2.sha256").write_text(_sha256_hex(json.dumps(dev).encode()))

    rev = {"schema_version": "pizm-deep-review-v2", "stage": "deep-review-v2", "target_id": "P1", "terminal_state": "MODEL_READY"}
    (run_dir / "deep-review-v2.json").write_text(json.dumps(rev))
    (run_dir / "deep-review-v2.sha256").write_text(_sha256_hex(json.dumps(rev).encode()))
    html_out = tmp_path / "run.html"
    rc = render_run_html(str(run_dir), "Legacy manual", str(html_out))
    assert rc == 0
    html_text = html_out.read_text(encoding="utf-8")
    assert "not recorded (legacy)" in html_text
    assert "MODEL_READY" in html_text


# ---------------------------------------------------------------------------
# Regression F: Model Metadata
# ---------------------------------------------------------------------------

def test_regression_f_model_metadata_live_and_legacy(tmp_path):
    out_root = tmp_path / "bundles"
    out_root.mkdir()

    p1_dir = tmp_path / "p1"
    p1_dir.mkdir()
    c1 = {"schema_version": "pizm-candidates-v1", "stage": "explore", "mode": "NORMAL", "candidates": [{"candidate_id": "c01", "title": "Claude 3.7 Mention in Text"}]}
    c1_b = json.dumps(c1).encode()
    (p1_dir / "candidates.json").write_bytes(c1_b)
    (p1_dir / "candidates.sha256").write_text(_sha256_hex(c1_b))
    (p1_dir / "selection.json").write_text('{"schema_version":"pizm-candidates-v1","kept":["c01"]}')

    # 1. Live bundle with host-reported metadata
    cmd1 = [
        sys.executable, BUNDLE_CLI, "create",
        "--output-root", str(out_root),
        "--slug", "session-live-model",
        "--skill-root", str(SKILL_ROOT),
        "--stage", f"pass-01-normal={p1_dir}",
        "--evidence-kind", "live",
        "--model", "gemini-3.7-flash",
        "--provider", "google",
        "--model-source", "HOST_RUNTIME",
    ]
    assert subprocess.run(cmd1, capture_output=True, text=True).returncode == 0
    m1 = json.loads((out_root / "session-live-model" / "manifest.json").read_text())
    assert m1["model"] == "gemini-3.7-flash"
    assert m1["provider"] == "google"
    assert m1["model_source"] == "HOST_RUNTIME"
    assert m1["pizm_version"] == "2026.09.09.1"

    # 2. Live bundle with unavailable metadata -> fallback UNKNOWN
    cmd2 = [
        sys.executable, BUNDLE_CLI, "create",
        "--output-root", str(out_root),
        "--slug", "session-live-unknown",
        "--skill-root", str(SKILL_ROOT),
        "--stage", f"pass-01-normal={p1_dir}",
        "--evidence-kind", "live",
    ]
    assert subprocess.run(cmd2, capture_output=True, text=True).returncode == 0
    m2 = json.loads((out_root / "session-live-unknown" / "manifest.json").read_text())
    assert m2["model"] == "UNKNOWN"
    assert m2["provider"] == "UNKNOWN"
    assert m2["model_source"] == "UNKNOWN"
    assert m2["pizm_version"] == "2026.09.09.1"

    # Ensure candidate prose "Claude 3.7" was NOT inferred as model
    assert m2["model"] != "Claude 3.7"


# ---------------------------------------------------------------------------
# Regression G: Version Fingerprint
# ---------------------------------------------------------------------------

def test_regression_g_version_fingerprint_and_skill_hash(tmp_path, monkeypatch):
    # 1. Installer copies VERSION to both roots
    monkeypatch.setenv("HOME", str(tmp_path))
    installer_script = str(BIN_DIR / "install-pizm")
    res = subprocess.run([sys.executable, installer_script, "--host", "both"], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert (tmp_path / ".claude" / "skills" / "pizm" / "VERSION").is_file()
    assert (tmp_path / ".config" / "opencode" / "skills" / "pizm" / "VERSION").is_file()
    assert (tmp_path / ".claude" / "skills" / "pizm" / "VERSION").read_text().strip() == "2026.09.09.1"

    # 2. _compute_skill_hash changes when VERSION changes
    fake_skill = tmp_path / "fake_skill"
    fake_skill.mkdir()
    (fake_skill / "SKILL.md").write_text("# Test Skill\n")
    (fake_skill / "VERSION").write_text("2026.09.09.1\n")
    load_code = (
        f"from importlib.machinery import SourceFileLoader; "
        f"from pathlib import Path; "
        f"mod = SourceFileLoader('b', '{BIN_DIR}/pizm-session-bundle').load_module(); "
        f"print(mod._compute_skill_hash(Path('{fake_skill}')))"
    )
    h1 = subprocess.run([sys.executable, "-c", load_code], capture_output=True, text=True)
    assert h1.returncode == 0, h1.stderr
    hash1 = h1.stdout.strip()

    (fake_skill / "VERSION").write_text("2026.09.09.2\n")
    h2 = subprocess.run([sys.executable, "-c", load_code], capture_output=True, text=True)
    assert h2.returncode == 0, h2.stderr
    hash2 = h2.stdout.strip()



# ---------------------------------------------------------------------------
# Regression E: New Naming & Reader Resolution
# ---------------------------------------------------------------------------

def test_regression_e_new_naming_and_reader_resolution(tmp_path):
    run_id = "prism-next-step-20260909t110536z-a7k2"
    run_dir = tmp_path / f"run-{run_id}"
    run_dir.mkdir()

    html_content = "<html><body><h1>Prism Next Step</h1><p>Record rendered.</p></body></html>"
    html_file = run_dir / "run-prism-next-step.html"
    html_file.write_text(html_content, encoding="utf-8")

    md_file = run_dir / "run-prism-next-step.md"
    md_file.write_text("# Prism Next Step\n\nRecord rendered.\n", encoding="utf-8")

    manifest = {
        "schema_version": "pizm-session-bundle-v1",
        "slug": run_id,
        "subject_slug": "prism-next-step",
        "records": {
            "html": "run-prism-next-step.html",
            "markdown": "run-prism-next-step.md",
        },
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # 1. State resolution finds records
    resolved_html = pizm_run_state.resolve_html_record(run_dir)
    assert resolved_html == html_file
    resolved_md = pizm_run_state.resolve_markdown_record(run_dir)
    assert resolved_md == md_file

    # 2. Reader server endpoint resolves `/run/<run-id>/`
    reader_script = str(BIN_DIR / "pizm-reader-server")
    cmd = [
        sys.executable,
        reader_script,
        "start",
        "--port", "0",
        "--root", str(tmp_path),
        "--foreground",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        line = proc.stdout.readline()
        import re
        import http.client
        import time
        m = re.search(r"127\.0\.0\.1:(\d+)", line)
        assert m is not None, f"Could not parse port: {line}"
        port = int(m.group(1))

        deadline = time.time() + 3.0
        conn = None
        while time.time() < deadline:
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=0.5)
                conn.request("GET", f"/run/{run_id}/", headers={"Host": f"127.0.0.1:{port}"})
                resp = conn.getresponse()
                if resp.status == 200:
                    body = resp.read().decode("utf-8")
                    assert "Prism Next Step" in body
                    break
            except Exception:
                time.sleep(0.05)
        else:
            pytest.fail("Reader server failed to serve named run record")
    finally:
        proc.terminate()
        proc.wait(timeout=2.0)


# ---------------------------------------------------------------------------
# Regression H: Determinism
# ---------------------------------------------------------------------------

def test_regression_h_determinism(tmp_path):
    """Same frozen artifacts + same metadata -> byte-identical rendered output."""
    run_dir1 = tmp_path / "run-det1"
    run_dir2 = tmp_path / "run-det2"
    run_dir1.mkdir()
    run_dir2.mkdir()

    manifest = {"schema_version": "pizm-session-bundle-v1", "slug": "det-fixed-id", "subject_slug": "det-fixed", "model": "test-model"}
    m_b = json.dumps(manifest, indent=2).encode("utf-8")
    (run_dir1 / "manifest.json").write_bytes(m_b)
    (run_dir2 / "manifest.json").write_bytes(m_b)
    cand = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "Invariant Determinism",
                "semantic_core": {"claim": "c", "structural_shift": "s", "mechanism": "m", "grounding_anchor": "a", "what_becomes_visible": "v", "boundary": "b"},
                "epistemics": {"supported": ["s"], "inferred": [], "speculative": [], "unknown": []},
            }
        ],
    }
    c_b = json.dumps(cand, indent=2).encode("utf-8")
    for rd in (run_dir1, run_dir2):
        (rd / "candidates-pass01.json").write_bytes(c_b)
        (rd / "candidates-pass01.sha256").write_text(_sha256_hex(c_b))

    port = {
        "schema_version": "pizm-portfolio-selection-v1",
        "stage": "portfolio",
        "route": "AUTO",
        "auto_target": {"target_type": "P", "target_id": "P1"},
        "perspectives": {"P1": "pass01:c01"},
    }
    p_b = json.dumps(port, indent=2).encode("utf-8")
    for rd in (run_dir1, run_dir2):
        (rd / "portfolio.json").write_bytes(p_b)
        (rd / "portfolio.sha256").write_text(_sha256_hex(p_b))

    dev = {"schema_version": "pizm-development-v2", "stage": "development-v2", "target": {"target_type": "P", "target_id": "P1"}, "developed_model": {"thesis": "Fixed Thesis"}}
    d_b = json.dumps(dev, indent=2).encode("utf-8")
    for rd in (run_dir1, run_dir2):
        (rd / "development-v2.json").write_bytes(d_b)
        (rd / "development-v2.sha256").write_text(_sha256_hex(d_b))
    rev = {
        "schema_version": "pizm-deep-review-v2",
        "stage": "deep-review-v2",
        "target": {"target_type": "P", "target_id": "P1"},
        "target_id": "P1",
        "terminal_state": "MODEL_READY",
        "verdict_rationale": "Proven deterministic",
    }
    r_b = json.dumps(rev, indent=2).encode("utf-8")
    for rd in (run_dir1, run_dir2):
        (rd / "deep-review-v2.json").write_bytes(r_b)
        (rd / "deep-review-v2.sha256").write_text(_sha256_hex(r_b))

    out_html1 = tmp_path / "out1.html"
    out_html2 = tmp_path / "out2.html"
    render_run_html(str(run_dir1), "Determinism task", str(out_html1))
    render_run_html(str(run_dir2), "Determinism task", str(out_html2))

    assert out_html1.read_bytes() == out_html2.read_bytes(), "HTML output must be byte-identical"

    out_md1 = tmp_path / "out1.md"
    out_md2 = tmp_path / "out2.md"
    subprocess.run([sys.executable, BUNDLE_CLI, "render", "--run-dir", str(run_dir1), "--task", "Determinism task", "--output", str(out_md1)], check=True)
    subprocess.run([sys.executable, BUNDLE_CLI, "render", "--run-dir", str(run_dir2), "--task", "Determinism task", "--output", str(out_md2)], check=True)

    assert out_md1.read_bytes() == out_md2.read_bytes(), "Markdown output must be byte-identical"
