"""Behavioral tests for `pizm-session-bundle render-html` (spec H1–H16)."""
from __future__ import annotations

import json
import hashlib
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_CLI = str(REPO_ROOT / "bin" / "pizm-session-bundle")
HTML_RENDERER = REPO_ROOT / "bin" / "pizm_render_html.py"
RUN_H4 = REPO_ROOT / ".ai" / "pizm" / "run-h4q9vn"
RUN_TELE = REPO_ROOT / ".ai" / "pizm" / "run-20260825-telecorpus"
RUN_INCOMPLETE = REPO_ROOT / ".ai" / "pizm" / "run-k7n2qm"

FORBIDDEN_SOURCE_TERMS = (
    "openai",
    "anthropic",
    "api_key",
    "urllib",
    "http.client",
    "requests.",
    "websocket",
    "llm_call",
    "model_invoke",
)


def run_html(run_dir, output, task=None):
    cmd = [
        sys.executable,
        BUNDLE_CLI,
        "render-html",
        "--run-dir",
        str(run_dir),
        "--output",
        str(output),
    ]
    if task is not None:
        cmd.extend(["--task", task])
    return subprocess.run(cmd, capture_output=True, text=True)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _minimal_run(root: Path, *, hostile=False, accounting=None, lever=False, stage_wise=None, complete=False):
    root.mkdir(parents=True, exist_ok=True)
    title = "Alpha"
    claim = "plain claim"
    if hostile:
        title = '<script>alert(1)</script>'
        claim = '<img onerror="alert(1)"> javascript:alert(1)'
    candidates = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": title,
                "semantic_core": {"claim": claim},
                "epistemics": {},
            }
        ],
    }
    portfolio = {
        "schema_version": "pizm-portfolio-selection-v1",
        "stage": "portfolio",
        "route": "AUTO",
        "candidate_assessments": [
            {
                "candidate_ref": "pass01:c01",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "residue",
                "nearest_overlap": None,
                "reason": "keep",
            }
        ],
        "bundles": [],
        "auto_target": {"target_type": "P", "target_id": "P1"},
    }
    (root / "candidates.json").write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (root / "portfolio.json").write_text(
        json.dumps(portfolio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if complete:
        dev = {
            "schema_version": "pizm-deep-model-v2",
            "stage": "deep",
            "target": {"target_type": "P", "target_id": "P1"},
            "identity_lock": {"title": title, "core_claim": claim},
            "developed_model": {"thesis": claim},
        }
        rev = {
            "schema_version": "pizm-deep-review-v2",
            "stage": "critic",
            "target": {"target_type": "P", "target_id": "P1"},
            "terminal_state": "MODEL_READY",
            "verdict_rationale": "Solid",
        }
        (root / "development-v2.json").write_text(
            json.dumps(dev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (root / "deep-review-v2.json").write_text(
            json.dumps(rev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    if accounting is not None or stage_wise is not None:
        acc = dict(accounting or {})
        if stage_wise is not None:
            acc["stage_wise"] = stage_wise
        manifest = {"schema_version": "pizm-session-bundle-v1", "accounting": acc}
        (root / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
    if lever:
        design = {
            "schema_version": "pizm-lever-design-v1",
            "stage": "lever",
            "levers": [
                {
                    "lever_id": "L1",
                    "intervention_or_test_point": "Cap meeting hours",
                    "model_link": "Coordination pressure",
                    "minimum_bounded_move": "One team, two weeks",
                    "expected_observation_or_response": "Batch size drops",
                    "disconfirming_signal": "No change",
                    "stop_condition": "Two cycles",
                    "remaining_assumptions": "Honest reporting",
                }
            ],
        }
        review = {
            "schema_version": "pizm-lever-review-v1",
            "stage": "lever",
            "outcome": "LEVER",
            "verdicts": [{"lever_id": "L1", "verdict": "ACCEPT"}],
            "verdict_rationale": "Move is bounded and observable.",
        }
        (root / "design.json").write_text(
            json.dumps(design, indent=2) + "\n", encoding="utf-8"
        )
        (root / "review.json").write_text(
            json.dumps(review, indent=2) + "\n", encoding="utf-8"
        )
    return root


# ---------------------------------------------------------------------------
# H1 full AUTO
# ---------------------------------------------------------------------------


def test_h1_full_auto_run_renders(tmp_path):
    out = tmp_path / "run.html"
    res = run_html(RUN_H4, out)
    assert res.returncode == 0, res.stderr
    text = out.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in text
    assert "AUTO" in text
    assert "Prism AUTO" not in text.split("<h1>", 1)[1].split("</h1>", 1)[0]
    for needle in (
        'id="task"',
        'id="summary"',
        'id="final"',
        'id="perspectives"',
        'id="bundles"',
        'id="deep"',
        'id="critic"',
        'id="economics"',
    ):
        assert needle in text
    for forbidden in (
        'id="search"',
        'id="portfolio"',
        'id="trace"',
        'id="extra-stages"',
        "Pipeline artifacts",
    ):
        assert forbidden not in text
    assert "MODEL_READY" in text
    assert "B8" in text
    assert "Ночь дрейфа" in text


# ---------------------------------------------------------------------------
# H2 incomplete
# ---------------------------------------------------------------------------


def test_h2_incomplete_run_renders(tmp_path):
    out = tmp_path / "run.html"
    res = run_html(RUN_INCOMPLETE, out)
    assert res.returncode == 0, res.stderr
    text = out.read_text(encoding="utf-8")
    assert "incomplete" in text.lower()
    assert "MANUAL" in text
    assert "Deep: not reached" in text
    assert "Critic: not reached" in text
    assert "Final: not reached" in text
    assert "no terminal synthesis invented" in text
    assert 'id="task"' in text
    assert 'id="summary"' in text
    assert 'id="final"' in text
    assert 'id="perspectives"' in text
    assert 'id="bundles"' in text
    assert 'id="deep"' in text
    assert 'id="critic"' in text
    assert 'id="lever"' in text
    assert 'id="economics"' in text
    assert 'id="trace"' not in text
    assert 'id="search"' not in text
    assert 'id="portfolio"' not in text
    assert 'id="extra-stages"' not in text
    assert "Pipeline artifacts" not in text
    assert "Other stages" not in text
    final = text.split('id="final"', 1)[1].split("</section>", 1)[0]
    assert "MODEL_READY" not in final
    assert "stage missing" in text


# ---------------------------------------------------------------------------
# H3 Search intermediate trace suppressed from reader HTML
# ---------------------------------------------------------------------------


def test_h3_search_intermediate_trace_suppressed_from_reader_html(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assert 'id="search"' not in text
    assert 'id="trace"' not in text
    assert "Search candidates" not in text
    assert "Pipeline artifacts" not in text


# ---------------------------------------------------------------------------
# H4 Portfolio intermediate trace suppressed from reader HTML
# ---------------------------------------------------------------------------


def test_h4_portfolio_intermediate_trace_suppressed_from_reader_html(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_TELE, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assert 'id="portfolio"' not in text
    assert 'id="trace"' not in text
    assert "Portfolio triage" not in text
    assert "Pipeline artifacts" not in text
    assert "Disposition." not in text

# ---------------------------------------------------------------------------
# H5 every P-ID
# ---------------------------------------------------------------------------


def test_h5_all_p_ids_represented(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assessments = _load(RUN_H4 / "portfolio.json")["candidate_assessments"]
    kept = sorted(
        a["candidate_ref"] for a in assessments if a.get("disposition") == "KEEP"
    )
    persp = text.split('id="perspectives"', 1)[1].split('id="bundles"', 1)[0]
    for i, ref in enumerate(kept, start=1):
        pid = f"P{i}"
        assert f'id="perspective-{pid}"' in persp
        assert ref in persp


# ---------------------------------------------------------------------------
# H6 bundle ids + member anchors
# ---------------------------------------------------------------------------


def test_h6_bundle_ids_and_member_links_resolve(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    bundles = _load(RUN_H4 / "portfolio.json")["bundles"]
    assessments = _load(RUN_H4 / "portfolio.json")["candidate_assessments"]
    kept = sorted(
        a["candidate_ref"] for a in assessments if a.get("disposition") == "KEEP"
    )
    p_map = {ref: f"P{i}" for i, ref in enumerate(kept, start=1)}
    for b in bundles:
        bid = b["bundle_id"]
        assert f'id="bundle-{bid}"' in text
        for ref in b["member_refs"]:
            pid = p_map[ref]
            href = f'href="#perspective-{pid}"'
            assert href in text
            assert f'id="perspective-{pid}"' in text


# ---------------------------------------------------------------------------
# H7 full Deep
# ---------------------------------------------------------------------------


def test_h7_full_deep_content_present(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    deep = text.split('id="deep"', 1)[1].split('id="critic"', 1)[0]
    model = _load(RUN_H4 / "development-v2.json")["developed_model"]
    assert model["thesis"] in deep
    assert model["synthesis"][:80] in deep
    assert model["dynamics"][:40] in deep
    assert model["mechanism_chain"][0] in deep
    assert model["implications"][0] in deep
    assert model["predictions_or_observables"][0] in deep
    assert model["load_bearing_claims"][0]["claim"] in deep
    assert model["break_conditions"][0] in deep
    assert model["unresolved_tensions"][0] in deep
    assert model["evidence_debt"][0] in deep


# ---------------------------------------------------------------------------
# H8 full Critic
# ---------------------------------------------------------------------------


def test_h8_full_critic_content_present(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    critic = text.split('id="critic"', 1)[1].split('id="lever"', 1)[0]
    rev = _load(RUN_H4 / "deep-review-v2.json")
    assert rev["independent_countermodel"][:60] in critic
    assert rev["cheapest_discriminating_test"][:40] in critic
    assert rev["verdict_rationale"][:40] in critic
    assert rev["load_bearing_reassessment"][0]["claim"] in critic
    assert rev["findings"]["epistemic_laundering"][0][:40] in critic
    assert "Gate transition" in critic
    assert "Before Critic" in critic
    assert rev["terminal_state"] in critic


# ---------------------------------------------------------------------------
# H9 LEVER conditional
# ---------------------------------------------------------------------------


def test_h9_lever_absent_is_honest(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    lever = text.split('id="lever"', 1)[1].split('id="economics"', 1)[0]
    assert "not present" in lever.lower() or "not reached" in lever.lower()
    assert "Cap meeting hours" not in lever


def test_h9_lever_present_is_full(tmp_path):
    run_dir = _minimal_run(tmp_path / "lever-run", lever=True)
    out = tmp_path / "run.html"
    res = run_html(run_dir, out, task="Synthetic lever task")
    assert res.returncode == 0, res.stderr
    text = out.read_text(encoding="utf-8")
    lever = text.split('id="lever"', 1)[1].split('id="economics"', 1)[0]
    assert "L1" in lever
    assert "Cap meeting hours" in lever
    assert "Coordination pressure" in lever
    assert "One team, two weeks" in lever
    assert "Batch size drops" in lever
    assert "Two cycles" in lever
    assert "ACCEPT" in lever


# ---------------------------------------------------------------------------
# H10 economics match manifest
# ---------------------------------------------------------------------------


def test_h10_economics_match_manifest_when_present(tmp_path):
    acc = {
        "host_inference_count": 4,
        "model_repair_count": 1,
        "checkpoint_retry_count": 2,
        "semantic_stage_count": 3,
        "candidate_bytes": 111,
        "development_bytes": 222,
    }
    run_dir = _minimal_run(tmp_path / "acc-run", accounting=acc)
    out = tmp_path / "run.html"
    assert run_html(run_dir, out, task="acc").returncode == 0
    text = out.read_text(encoding="utf-8")
    econ = text.split('id="economics"', 1)[1].split("</section>", 1)[0]
    assert "4" in econ
    assert ">1<" in econ or "1" in econ
    assert "111" in econ
    assert "222" in econ
    assert "unavailable" in econ


# ---------------------------------------------------------------------------
# H11 stage-wise
# ---------------------------------------------------------------------------


def test_h11_stage_wise_usage_authoritative_or_not_recorded(tmp_path):
    out = tmp_path / "named.html"
    assert run_html(RUN_H4, out).returncode == 0
    named = out.read_text(encoding="utf-8")
    assert "Stage-wise usage: not recorded" in named

    run_dir = _minimal_run(
        tmp_path / "sw-run",
        accounting={"host_inference_count": 1, "model_repair_count": 0, "checkpoint_retry_count": 0},
        stage_wise={"search": 9},
    )
    out2 = tmp_path / "sw.html"
    assert run_html(run_dir, out2, task="sw").returncode == 0
    text = out2.read_text(encoding="utf-8")
    assert "Stage-wise usage: not recorded" not in text.split('id="economics"', 1)[1]
    assert '"search": 9' in text or "&quot;search&quot;: 9" in text


# ---------------------------------------------------------------------------
# H12 missing optional usage does not fail
# ---------------------------------------------------------------------------


def test_h12_missing_optional_usage_does_not_fail(tmp_path):
    out = tmp_path / "run.html"
    res = run_html(RUN_H4, out)
    assert res.returncode == 0, res.stderr
    text = out.read_text(encoding="utf-8")
    assert "not recorded" in text

    run_dir = _minimal_run(
        tmp_path / "partial-acc",
        accounting={"host_inference_count": 2},
    )
    out2 = tmp_path / "partial.html"
    assert run_html(run_dir, out2, task="partial").returncode == 0
    text2 = out2.read_text(encoding="utf-8")
    assert "unavailable" in text2
    assert "Estimated cost" in text2

# ---------------------------------------------------------------------------
# H13 no provider/network in renderer source
# ---------------------------------------------------------------------------


def test_h13_renderer_source_has_no_provider_or_network_calls():
    source = HTML_RENDERER.read_text(encoding="utf-8").lower()
    for term in FORBIDDEN_SOURCE_TERMS:
        assert term not in source, f"forbidden provider/network term: {term}"
    cli = Path(BUNDLE_CLI).read_text(encoding="utf-8").lower()
    for term in FORBIDDEN_SOURCE_TERMS:
        assert term not in cli, f"forbidden provider/network term in CLI: {term}"


# ---------------------------------------------------------------------------
# H14 byte-stable
# ---------------------------------------------------------------------------


def test_h14_same_artifacts_produce_byte_stable_html(tmp_path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    assert run_html(RUN_H4, a).returncode == 0
    assert run_html(RUN_H4, b).returncode == 0
    assert a.read_bytes() == b.read_bytes()
    text = a.read_text(encoding="utf-8")
    assert re.search(r"datetime\.now|wall.clock", text, re.I) is None


# ---------------------------------------------------------------------------
# H15 escape untrusted text
# ---------------------------------------------------------------------------


def test_h15_escapes_untrusted_generated_text(tmp_path):
    run_dir = _minimal_run(tmp_path / "hostile", hostile=True)
    out = tmp_path / "run.html"
    res = run_html(run_dir, out, task="hostile <script>task</script>")
    assert res.returncode == 0, res.stderr
    raw = out.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in raw
    assert "<script>task</script>" not in raw
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in raw
    assert "&lt;script&gt;task&lt;/script&gt;" in raw
    assert "<img onerror=" not in raw
    assert "&lt;img onerror=" in raw
    assert 'href="javascript:' not in raw
    assert "javascript:alert(1)" in raw


# ---------------------------------------------------------------------------
# H16 no external network resources
# ---------------------------------------------------------------------------


def test_h16_no_external_network_resources(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "http://" not in lowered
    assert "https://" not in lowered
    assert "//cdn" not in lowered
    assert "<link rel=\"stylesheet\" href=\"http" not in lowered
    assert "<script src=" not in lowered
    src = HTML_RENDERER.read_text(encoding="utf-8").lower()
    assert "http://" not in src
    assert "https://" not in src
    assert "//cdn" not in src


def test_task_fallback_from_run_md(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assert "Ночь дрейфа: мама, Свят, nekto.me, 7 утра, самоупрёк «опять не собрался»" in text


def test_task_not_specified_without_run_md(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_INCOMPLETE, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assert "Not specified" in text


def test_js_off_titles_live_in_summary(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    script = text.split("<script>", 1)[1]
    body_wo_script = text.split("<script>", 1)[0]
    assessments = _load(RUN_H4 / "portfolio.json")["candidate_assessments"]
    cands = _load(RUN_H4 / "candidates.json")["candidates"]
    cand_by_id = {c["candidate_id"]: c for c in cands}
    kept_refs = [a["candidate_ref"] for a in assessments if a.get("disposition") == "KEEP"]
    for ref in kept_refs:
        c = cand_by_id.get(ref)
        if c and c.get("title"):
            assert c["title"] in body_wo_script
            assert c["title"] not in script
    assert "<details" in body_wo_script


# ---------------------------------------------------------------------------
# Style Addendum Contracts (2026-09-02)
# ---------------------------------------------------------------------------


def test_centered_desktop_reader_width_and_no_body_left_margin(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assert 'class="reader-shell"' in text
    assert "margin-inline: auto" in text
    assert "min(100% - 48px, 980px)" in text
    assert "body { margin-left:" not in text
    assert "margin-left: 18rem" not in text


def test_monospace_typography_and_ligatures_disabled(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assert "Iosevka" in text
    assert "JetBrains Mono" in text
    assert "font-variant-ligatures: none" in text
    assert 'font-feature-settings: "liga" 0, "calt" 0' in text
    assert "Georgia" not in text
    assert "Times New Roman" not in text


def test_near_monochrome_palette_and_no_semantic_stage_colors(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    for forbidden in (
        "--search:",
        "--portfolio:",
        "--perspective:",
        "--bundle:",
        "--deep:",
        "--critic:",
        "--lever:",
        "border-left: 6px solid",
    ):
        assert forbidden not in text


def test_hierarchy_task_then_summary_then_final_then_deep_then_perspectives_then_bundles(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    pos_task = text.index('id="task"')
    pos_summary = text.index('id="summary"')
    pos_final = text.index('id="final"')
    pos_deep = text.index('id="deep"')
    pos_persp = text.index('id="perspectives"')
    pos_bundles = text.index('id="bundles"')
    pos_critic = text.index('id="critic"')
    pos_lever = text.index('id="lever"')
    pos_econ = text.index('id="economics"')
    assert pos_task < pos_summary < pos_final < pos_deep < pos_persp < pos_bundles < pos_critic < pos_lever < pos_econ
    assert 'id="trace"' not in text
    assert 'id="search"' not in text
    assert 'id="portfolio"' not in text
    assert 'id="extra-stages"' not in text
    assert "Pipeline artifacts" not in text
    assert "Other stages" not in text


def test_perspectives_and_bundles_native_details_disclosure(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assert '<details open class="perspective"' in text
    assert '<details class="bundle"' in text
    assert 'id="perspective-P1"' in text
    assert 'id="bundle-B8"' in text
    assert '<summary><span class="pid">P1</span>' in text
    assert '<summary><span class="bid">B8</span>' in text


# ---------------------------------------------------------------------------
# R1–R10 Reader Order & Bundle Visibility Tests (2026-09-02)
# ---------------------------------------------------------------------------


def test_r1_developed_model_renders_before_perspectives(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    pos_deep = text.index('id="deep"')
    pos_persp = text.index('id="perspectives"')
    pos_bundles = text.index('id="bundles"')
    pos_critic = text.index('id="critic"')
    assert pos_deep < pos_persp < pos_bundles < pos_critic

    # Also verify in TOC navigation
    toc_deep = text.index('href="#deep"')
    toc_persp = text.index('href="#perspectives"')
    toc_bundles = text.index('href="#bundles"')
    toc_critic = text.index('href="#critic"')
    assert toc_deep < toc_persp < toc_bundles < toc_critic


def test_r2_every_perspective_renders_with_open_default_state(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    # All 13 perspectives in h4q9vn must render with <details open
    persp_section = text.split('id="perspectives"', 1)[1].split('</section>', 1)[0]
    for i in range(1, 14):
        assert f'<details open class="perspective" id="perspective-P{i}">' in persp_section
    # No closed perspective details tags in the perspectives section
    assert '<details class="perspective"' not in persp_section


def test_r3_collapse_expand_toolbar_targets_all_details(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assert 'id="js-toolbar"' in text
    assert 'id="expand-all"' in text
    assert 'id="collapse-all"' in text
    assert 'querySelectorAll("details")' in text
    assert 'nodes[i].open = v' in text


def _create_multi_bundle_run(root: Path, bundles: list, auto_target: dict | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    candidates = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "Cand 1",
                "semantic_core": {"claim": "Claim 1"},
                "epistemics": {},
            },
            {
                "candidate_id": "c02",
                "title": "Cand 2",
                "semantic_core": {"claim": "Claim 2"},
                "epistemics": {},
            },
            {
                "candidate_id": "c03",
                "title": "Cand 3",
                "semantic_core": {"claim": "Claim 3"},
                "epistemics": {},
            },
        ],
    }
    portfolio = {
        "schema_version": "pizm-portfolio-selection-v1",
        "stage": "portfolio",
        "route": "AUTO",
        "candidate_assessments": [
            {
                "candidate_ref": "pass01:c01",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "res1",
                "nearest_overlap": None,
                "reason": "keep1",
            },
            {
                "candidate_ref": "pass01:c02",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "res2",
                "nearest_overlap": None,
                "reason": "keep2",
            },
            {
                "candidate_ref": "pass01:c03",
                "disposition": "KEEP",
                "standalone_quality": "strong",
                "unique_residue": "res3",
                "nearest_overlap": None,
                "reason": "keep3",
            },
        ],
        "bundles": bundles,
        "auto_target": auto_target or {"target_type": "P", "target_id": "P1"},
    }
    (root / "candidates.json").write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (root / "portfolio.json").write_text(
        json.dumps(portfolio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return root


def test_r4_and_r5_and_r8_three_bundle_fixture_renders_all_bundles_and_selection(tmp_path):
    bundles = [
        {
            "bundle_id": "B1",
            "member_refs": ["pass01:c01", "pass01:c02"],
            "title": "First Bundle",
            "bundle_thesis": "Thesis B1",
            "composition_gain": "Gain B1",
            "member_roles": {"pass01:c01": "role1", "pass01:c02": "role2"},
            "member_ablation": {"pass01:c01": "abl1", "pass01:c02": "abl2"},
            "internal_tension": "tension1",
            "weakest_link": "weak1",
            "new_consequence_or_prediction": "pred1",
        },
        {
            "bundle_id": "B2",
            "member_refs": ["pass01:c02", "pass01:c03"],
            "title": "Second Bundle",
            "bundle_thesis": "Thesis B2",
            "composition_gain": "Gain B2",
            "member_roles": {"pass01:c02": "role2", "pass01:c03": "role3"},
            "member_ablation": {"pass01:c02": "abl2", "pass01:c03": "abl3"},
            "internal_tension": "tension2",
            "weakest_link": "weak2",
            "new_consequence_or_prediction": "pred2",
        },
        {
            "bundle_id": "B3",
            "member_refs": ["pass01:c01", "pass01:c03"],
            "title": "Third Bundle",
            "bundle_thesis": "Thesis B3",
            "composition_gain": "Gain B3",
            "member_roles": {"pass01:c01": "role1", "pass01:c03": "role3"},
            "member_ablation": {"pass01:c01": "abl1", "pass01:c03": "abl3"},
            "internal_tension": "tension3",
            "weakest_link": "weak3",
            "new_consequence_or_prediction": "pred3",
        },
    ]
    auto_target = {"target_type": "B", "target_id": "B2"}
    run_dir = _create_multi_bundle_run(tmp_path / "three-bundles", bundles=bundles, auto_target=auto_target)

    # Add development-v2 and deep-review-v2 targeting B2 for complete rendering
    dev = {
        "schema_version": "pizm-deep-model-v2",
        "stage": "deep",
        "target": {"target_type": "B", "target_id": "B2"},
        "identity_lock": {"bundle_id": "B2", "title": "Second Bundle", "core_claim": "Claim B2"},
        "developed_model": {"thesis": "Developed thesis B2"},
    }
    rev = {
        "schema_version": "pizm-deep-review-v2",
        "stage": "critic",
        "target": {"target_type": "B", "target_id": "B2"},
        "terminal_state": "MODEL_READY",
        "verdict_rationale": "Solid B2",
    }
    (run_dir / "development-v2.json").write_text(
        json.dumps(dev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (run_dir / "deep-review-v2.json").write_text(
        json.dumps(rev, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    out = tmp_path / "run.html"
    assert run_html(run_dir, out).returncode == 0
    text = out.read_text(encoding="utf-8")

    # R4 & R8: Every item in portfolio.bundles[] is rendered and visible
    assert 'id="bundle-B1"' in text
    assert 'id="bundle-B2"' in text
    assert 'id="bundle-B3"' in text
    assert '<span class="bid">B1</span> — First Bundle' in text
    assert '<span class="bid">B2</span> — Second Bundle' in text
    assert '<span class="bid">B3</span> — Third Bundle' in text

    # R5: Selection of B2 does NOT suppress B1 or B3
    bundles_sec = text.split('id="bundles"', 1)[1].split('</section>', 1)[0]
    assert 'id="bundle-B1"' in bundles_sec
    assert 'id="bundle-B2"' in bundles_sec
    assert 'id="bundle-B3"' in bundles_sec

    # B2 is identifiable as selected target across summary, final, and deep
    summary_sec = text.split('id="summary"', 1)[1].split('</section>', 1)[0]
    assert "B B2" in summary_sec
    final_sec = text.split('id="final"', 1)[1].split('</section>', 1)[0]
    assert "B2" in final_sec
    deep_sec = text.split('id="deep"', 1)[1].split('</section>', 1)[0]
    assert "Target B2" in deep_sec


def test_r6_zero_bundles_renders_cleanly(tmp_path):
    run_dir = _create_multi_bundle_run(tmp_path / "zero-bundles", bundles=[])
    out = tmp_path / "run.html"
    assert run_html(run_dir, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assert 'id="bundles"' in text
    bundles_sec = text.split('id="bundles"', 1)[1].split('</section>', 1)[0]
    assert "No bundles recorded." in bundles_sec
    # Perspectives still render cleanly
    assert 'id="perspective-P1"' in text


def test_r7_one_bundle_renders_cleanly(tmp_path):
    single_bundle = [
        {
            "bundle_id": "B1",
            "member_refs": ["pass01:c01", "pass01:c02"],
            "title": "Single Bundle",
            "bundle_thesis": "Thesis B1",
            "composition_gain": "Gain B1",
            "member_roles": {"pass01:c01": "role1", "pass01:c02": "role2"},
            "member_ablation": {"pass01:c01": "abl1", "pass01:c02": "abl2"},
            "internal_tension": "tension1",
            "weakest_link": "weak1",
            "new_consequence_or_prediction": "pred1",
        }
    ]
    run_dir = _create_multi_bundle_run(tmp_path / "one-bundle", bundles=single_bundle)
    out = tmp_path / "run.html"
    assert run_html(run_dir, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assert 'id="bundle-B1"' in text
    assert "Single Bundle" in text

def test_w1_post_critic_gap_notice_on_complete_run_without_final_artifact(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    final = text.split('id="final"', 1)[1].split("</section>", 1)[0]
    assert "W1 content notice" in final
    assert "No dedicated reader-facing post-Critic final synthesis is recorded in this frozen bundle" in final
    assert "W1 data/content gap" in final
    assert "See Developed Model" not in final
    assert "see Critic" not in final
    assert "see Deep" not in final
    assert "MODEL_READY" in final
    assert "B8" in final


def test_w1_post_critic_final_synthesis_rendered_when_present(tmp_path):
    run_dir = _minimal_run(tmp_path / "final-run", complete=True)
    final_payload = {
        "synthesis": "Here is the post-Critic actionable resolution for the team."
    }
    (run_dir / "final.json").write_text(json.dumps(final_payload), encoding="utf-8")
    out = tmp_path / "run.html"
    assert run_html(run_dir, out, task="Synthesis test").returncode == 0
    text = out.read_text(encoding="utf-8")
    final = text.split('id="final"', 1)[1].split("</section>", 1)[0]
    assert "Post-Critic synthesis:" in final
    assert "Here is the post-Critic actionable resolution for the team." in final
    assert "W1 content notice" not in final
    assert "gap-notice" not in final


def test_raw_provenance_and_hashes_suppressed_from_reader_html(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assert 'id="provenance"' not in text
    assert 'id="trace"' not in text
    assert 'id="search"' not in text
    assert 'id="portfolio"' not in text
    assert 'id="extra-stages"' not in text
    assert "Technical provenance" not in text
    assert "Schema versions / timestamps" not in text
    assert "Artifact paths" not in text
    assert "Pipeline artifacts" not in text
    assert "Other stages" not in text


def test_need_evidence_inquiry_program_rendered(tmp_path):
    """Critic NEED_EVIDENCE renders inquiry program details in HTML."""
    run_dir = tmp_path / "inquiry-run"
    run_dir.mkdir()
    cands = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "Model 1",
                "semantic_core": {"claim": "Claim 1", "structural_shift": "Shift 1", "mechanism": "Mech 1", "grounding_anchor": "Anchor 1", "what_becomes_visible": "Vis 1", "boundary": "Bound 1"},
                "epistemics": {"supported": ["Fact 1"], "inferred": [], "speculative": [], "unknown": []},
            }
        ],
    }
    c_bytes = json.dumps(cands).encode("utf-8")
    (run_dir / "candidates.json").write_bytes(c_bytes)
    (run_dir / "candidates.sha256").write_text(hashlib.sha256(c_bytes).hexdigest())

    port = {
        "schema_version": "pizm-portfolio-selection-v1",
        "stage": "portfolio",
        "route": "AUTO",
        "field_hash": hashlib.sha256(c_bytes).hexdigest(),
        "candidate_assessments": [{"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Res", "nearest_overlap": None, "reason": "Good"}],
        "bundles": [],
        "next_reasoning_move": "DEEP",
        "next_reasoning_rationale": "Deepen P1",
        "auto_target": {"target_type": "P", "target_id": "P1"},
        "information_request": None,
        "rival_shadow": None,
    }
    p_bytes = json.dumps(port).encode("utf-8")
    (run_dir / "portfolio.json").write_bytes(p_bytes)
    (run_dir / "portfolio.sha256").write_text(hashlib.sha256(p_bytes).hexdigest())

    dev = {
        "schema_version": "pizm-development-v2",
        "stage": "development-v2",
        "target": {"target_type": "P", "target_id": "P1"},
        "identity_lock": {"p_id": "P1", "title": "Model 1", "core_claim": "Claim 1", "structural_shift": "Shift 1", "mechanism": "Mech 1", "boundary": "Bound 1"},
        "developed_model": {
            "thesis": "Thesis 1",
            "synthesis": "Synthesis 1",
            "dynamics": "Dynamics 1",
            "implications": ["Imp 1"],
            "predictions_or_observables": ["Pred 1"],
            "break_conditions": ["Break 1"],
            "unresolved_tensions": [],
            "evidence_debt": ["Evidence debt item 1"],
            "load_bearing_claims": [{"claim": "Claim 1", "role_in_model": "core", "epistemic_status": "SPECULATIVE", "what_would_weaken_or_refute": "Refute 1"}],
            "comparative_standing": None,
            "development_delta": {"summary": "delta 1", "new_load_bearing_claims": [], "strengthened_claims": [], "new_causal_arrows_or_mechanisms": [], "material_imports": [], "scope_expansions": []},
        },
    }
    d_bytes = json.dumps(dev).encode("utf-8")
    (run_dir / "development-v2-P1.json").write_bytes(d_bytes)
    (run_dir / "development-v2-P1.sha256").write_text(hashlib.sha256(d_bytes).hexdigest())

    rev = {
        "schema_version": "pizm-deep-review-v2",
        "stage": "deep-review-v2",
        "frozen_hash": hashlib.sha256(d_bytes).hexdigest(),
        "target_type": "P",
        "target_id": "P1",
        "terminal_state": "NEED_EVIDENCE",
        "identity_verified": True,
        "independent_countermodel": "Countermodel 1",
        "cheapest_discriminating_test": "Test discriminating signal A vs B",
        "load_bearing_reassessment": [{"claim": "Claim 1", "critic_epistemic_status": "SPECULATIVE"}],
        "findings": {
            "identity_drift": None,
            "cross_field_contradictions": [],
            "unresolved_load_bearing_contradiction": False,
            "readiness_blockers": ["B1_SPECULATIVE_DEPENDENCY"],
            "readiness_blocker_details": {"B1_SPECULATIVE_DEPENDENCY": "Claim 1 is speculative"},
            "unsupported_specificity": [],
            "epistemic_laundering": [],
            "cost_relocation": None,
            "round_trip_skeleton": "Skeleton 1",
        },
        "evidence_debt": ["Missing metric telemetry"],
        "verdict_rationale": "Missing evidence required before acceptance",
        "inquiry_program": {
            "current_leading_models": ["Leading Model Alpha", "Leading Model Beta"],
            "unresolved_questions": ["What is the true failure rate under stress?"],
            "strongest_live_rival": "Rival Model Gamma",
            "result_that_would_change_model": "Failure rate exceeding 5%",
            "stop_rule": "100 benchmark trials executed",
        },
    }
    r_bytes = json.dumps(rev).encode("utf-8")
    (run_dir / "deep-review-v2-P1.json").write_bytes(r_bytes)
    (run_dir / "deep-review-v2-P1.sha256").write_text(hashlib.sha256(r_bytes).hexdigest())

    out = tmp_path / "run.html"
    assert run_html(run_dir, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assert "Inquiry program" in text
    assert "Leading Model Alpha" in text
    assert "What is the true failure rate under stress?" in text
    assert "Rival Model Gamma" in text
    assert "Failure rate exceeding 5%" in text
    assert "100 benchmark trials executed" in text
    assert "Readiness blocker" in text
    assert "B1_SPECULATIVE_DEPENDENCY" in text


def test_alias_and_target_artifacts_render_once(tmp_path):
    """When both target-suffixed and unsuffixed compatibility alias exist, target is rendered only once."""
    run_dir = tmp_path / "alias-dedup-run"
    run_dir.mkdir()
    cands = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "Model 1",
                "semantic_core": {"claim": "Claim 1", "structural_shift": "Shift 1", "mechanism": "Mech 1", "grounding_anchor": "Anchor 1", "what_becomes_visible": "Vis 1", "boundary": "Bound 1"},
                "epistemics": {"supported": ["Fact 1"], "inferred": [], "speculative": [], "unknown": []},
            }
        ],
    }
    c_bytes = json.dumps(cands).encode("utf-8")
    (run_dir / "candidates.json").write_bytes(c_bytes)
    (run_dir / "candidates.sha256").write_text(hashlib.sha256(c_bytes).hexdigest())

    port = {
        "schema_version": "pizm-portfolio-selection-v1",
        "stage": "portfolio",
        "route": "AUTO",
        "field_hash": hashlib.sha256(c_bytes).hexdigest(),
        "candidate_assessments": [{"candidate_ref": "pass01:c01", "disposition": "KEEP", "standalone_quality": "strong", "unique_residue": "Res", "nearest_overlap": None, "reason": "Good"}],
        "bundles": [],
        "next_reasoning_move": "DEEP",
        "next_reasoning_rationale": "Deepen P1",
        "auto_target": {"target_type": "P", "target_id": "P1"},
        "information_request": None,
        "rival_shadow": None,
    }
    p_bytes = json.dumps(port).encode("utf-8")
    (run_dir / "portfolio.json").write_bytes(p_bytes)
    (run_dir / "portfolio.sha256").write_text(hashlib.sha256(p_bytes).hexdigest())

    dev = {
        "schema_version": "pizm-development-v2",
        "stage": "development-v2",
        "target": {"target_type": "P", "target_id": "P1"},
        "identity_lock": {"p_id": "P1", "title": "Canonical P1 Model", "core_claim": "Claim 1", "structural_shift": "Shift 1", "mechanism": "Mech 1", "boundary": "Bound 1"},
        "developed_model": {
            "thesis": "Unique P1 Thesis",
            "synthesis": "Analytical prose synthesis.",
            "dynamics": "Dynamics",
            "implications": ["Imp 1"],
            "predictions_or_observables": ["Pred 1"],
            "break_conditions": ["Break 1"],
            "unresolved_tensions": [],
            "evidence_debt": [],
            "load_bearing_claims": [{"claim": "Claim 1", "role_in_model": "core", "epistemic_status": "SUPPORTED", "what_would_weaken_or_refute": "Refute"}],
            "comparative_standing": None,
            "development_delta": {"summary": "delta", "new_load_bearing_claims": [], "strengthened_claims": [], "new_causal_arrows_or_mechanisms": [], "material_imports": [], "scope_expansions": []},
        },
    }
    d_bytes = json.dumps(dev).encode("utf-8")
    (run_dir / "development-v2-P1.json").write_bytes(d_bytes)
    (run_dir / "development-v2-P1.sha256").write_text(hashlib.sha256(d_bytes).hexdigest())
    (run_dir / "development-v2.json").write_bytes(d_bytes)
    (run_dir / "development-v2.sha256").write_text(hashlib.sha256(d_bytes).hexdigest())

    rev = {
        "schema_version": "pizm-deep-review-v2",
        "stage": "deep-review-v2",
        "frozen_hash": hashlib.sha256(d_bytes).hexdigest(),
        "target_type": "P",
        "target_id": "P1",
        "terminal_state": "MODEL_READY",
        "identity_verified": True,
        "independent_countermodel": "Countermodel",
        "cheapest_discriminating_test": "Test",
        "load_bearing_reassessment": [{"claim": "Claim 1", "critic_epistemic_status": "SUPPORTED"}],
        "findings": {
            "identity_drift": None,
            "cross_field_contradictions": [],
            "unresolved_load_bearing_contradiction": False,
            "readiness_blockers": [],
            "readiness_blocker_details": {},
            "unsupported_specificity": [],
            "epistemic_laundering": [],
            "cost_relocation": None,
            "round_trip_skeleton": "Skeleton",
        },
        "evidence_debt": [],
        "verdict_rationale": "Ready",
        "inquiry_program": None,
    }
    r_bytes = json.dumps(rev).encode("utf-8")
    (run_dir / "deep-review-v2-P1.json").write_bytes(r_bytes)
    (run_dir / "deep-review-v2-P1.sha256").write_text(hashlib.sha256(r_bytes).hexdigest())
    (run_dir / "deep-review-v2.json").write_bytes(r_bytes)
    (run_dir / "deep-review-v2.sha256").write_text(hashlib.sha256(r_bytes).hexdigest())

    out = tmp_path / "run.html"
    assert run_html(run_dir, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assert text.count('<section id="deep"') == 1
    assert text.count('<section id="critic"') == 1
    assert text.count("Unique P1 Thesis") == 1


# ---------------------------------------------------------------------------
# V4 Slice 5 reader aids (plain_explanation, high_upside)
# ---------------------------------------------------------------------------


def test_h17_plain_explanation_and_spotlight_render(tmp_path):
    import shutil
    run = tmp_path / "run-h4-aided"
    shutil.copytree(RUN_H4, run)
    port_path = run / "portfolio.json"
    port = json.loads(port_path.read_text(encoding="utf-8"))
    keeper = next(a for a in port["candidate_assessments"] if a.get("disposition") == "KEEP")
    keeper["plain_explanation"] = "Plain words for the first kept perspective."
    port["high_upside"] = [
        {"ref": keeper["candidate_ref"], "why": "Big payoff.", "risk": "Thin evidence."}
    ]
    raw = json.dumps(port, indent=2, ensure_ascii=False).encode("utf-8")
    port_path.write_bytes(raw)
    (run / "portfolio.sha256").write_text(hashlib.sha256(raw).hexdigest(), encoding="utf-8")
    out = tmp_path / "run.html"
    assert run_html(run, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assert "<strong>Plain explanation.</strong>" in text
    assert "Plain words for the first kept perspective." in text
    assert "Start here — high-upside perspectives" in text
    assert "Big payoff." in text
    assert "Thin evidence." in text


def test_h17_legacy_run_omits_reader_aids(tmp_path):
    out = tmp_path / "run.html"
    assert run_html(RUN_H4, out).returncode == 0
    text = out.read_text(encoding="utf-8")
    assert 'class="spotlight"' not in text
    assert "<strong>Plain explanation.</strong>" not in text
