"""
Contract tests for bin/pizmz-bundle.

Covers:
- B1: verbatim embedding (packet bytes preserved byte-for-byte inside bundle)
- B2: quorum enforcement (1 packet refused; --allow-single passes)
- B3: run-id/lane validation (bad lane names, bad run-ids, duplicates fail closed)
- B4: final-packet basename gate (non-packet .md refused)
- B5: missing lanes reported in manifest, not hidden
- B6: determinism (same inputs + --created => byte-identical bundle)
- B7: no-overwrite of existing bundle/synthesis
- B8: synthesis skeleton carries all five mandatory sections
- B9: installer deploys the helper
- B10: managed skill documents the bundle+synthesis pair
"""
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_CLI = str(REPO_ROOT / "bin" / "pizmz-bundle")


def run_pizmz_bundle(*args, cwd=None):
    return subprocess.run(
        [sys.executable, BUNDLE_CLI, *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def _sample_packet(tmp_path, name, keep=3, merge=1, borderline=1, drop=0, bundles=1):
    text = (
        "# Pizm Research Pack\n\n"
        "## Curated Perspectives\n\n"
        "### P1 — sample (`pass01:c01`)\n- Core claim: sample claim.\n\n"
        "## Curation summary\n"
        f"- Raw candidate refs: {keep + merge + borderline + drop}\n"
        f"- KEEP: {keep}\n"
        f"- MERGE: {merge}\n"
        f"- BORDERLINE: {borderline}\n"
        f"- DROP: {drop}\n"
        f"- Bundles: {bundles}\n"
    )
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def two_packets(tmp_path):
    a = _sample_packet(tmp_path, "research-pack-alpha.md", keep=4)
    b = _sample_packet(tmp_path, "research-pack-beta.md", keep=2, bundles=2)
    return a, b


# ---------------------------------------------------------------------------
# B1: verbatim embedding
# ---------------------------------------------------------------------------


def test_packets_embedded_byte_verbatim(tmp_path, two_packets):
    a, b = two_packets
    out = tmp_path / "out"
    r = run_pizmz_bundle(
        "--slug", "demo-20261019t000000z",
        "--task", "verbatim check",
        "--packet", f"agy={a}:alpha-20261019t000000z-aaaa",
        "--packet", f"muse={b}",
        "--out-dir", str(out),
        "--created", "20261019t000000z",
    )
    assert r.returncode == 0, r.stderr
    bundle = out / "pizmz-demo-20261019t000000z-bundle.md"
    raw_a, raw_b = a.read_bytes(), b.read_bytes()
    body = bundle.read_bytes()
    assert raw_a.decode("utf-8").rstrip("\n").encode("utf-8") in body
    assert raw_b.decode("utf-8").rstrip("\n").encode("utf-8") in body
    assert hashlib.sha256(raw_a).hexdigest() in bundle.read_text(encoding="utf-8")
    assert hashlib.sha256(raw_b).hexdigest() in bundle.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# B2: quorum
# ---------------------------------------------------------------------------


def test_single_packet_refused_without_allow_single(tmp_path, two_packets):
    a, _ = two_packets
    r = run_pizmz_bundle(
        "--slug", "solo-x",
        "--task", "t",
        "--packet", f"agy={a}",
        "--out-dir", str(tmp_path / "out"),
    )
    assert r.returncode != 0
    assert "quorum" in r.stderr.lower()


def test_single_packet_allowed_with_flag(tmp_path, two_packets):
    a, _ = two_packets
    r = run_pizmz_bundle(
        "--slug", "solo-x",
        "--task", "t",
        "--packet", f"agy={a}",
        "--allow-single",
        "--out-dir", str(tmp_path / "out"),
    )
    assert r.returncode == 0, r.stderr


# ---------------------------------------------------------------------------
# B3: validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "spec",
    [
        "bad lane!=/tmp/x.md",
        "agy=/tmp/x.md:BAD_UPPER",
        "agy=/tmp/x.md:",
    ],
)
def test_bad_specs_fail_closed(tmp_path, spec):
    r = run_pizmz_bundle(
        "--slug", "ok-slug",
        "--task", "t",
        "--packet", spec,
        "--packet", "muse=/tmp/y.md",
        "--out-dir", str(tmp_path / "out"),
    )
    assert r.returncode != 0


def test_duplicate_lanes_fail_closed(tmp_path, two_packets):
    a, b = two_packets
    r = run_pizmz_bundle(
        "--slug", "dup-x",
        "--task", "t",
        "--packet", f"agy={a}",
        "--packet", f"agy={b}",
        "--out-dir", str(tmp_path / "out"),
    )
    assert r.returncode != 0


def test_missing_lane_also_landed_fails(tmp_path, two_packets):
    a, b = two_packets
    r = run_pizmz_bundle(
        "--slug", "dup-x",
        "--task", "t",
        "--packet", f"agy={a}",
        "--packet", f"muse={b}",
        "--missing", "agy:crashed",
        "--out-dir", str(tmp_path / "out"),
    )
    assert r.returncode != 0


# ---------------------------------------------------------------------------
# B4: basename gate
# ---------------------------------------------------------------------------


def test_non_packet_basename_refused(tmp_path):
    p = tmp_path / "notes.md"
    p.write_text("# notes\nnot a packet\n", encoding="utf-8")
    q = _sample_packet(tmp_path, "research-pack-ok.md")
    r = run_pizmz_bundle(
        "--slug", "gate-x",
        "--task", "t",
        "--packet", f"agy={p}",
        "--packet", f"muse={q}",
        "--out-dir", str(tmp_path / "out"),
    )
    assert r.returncode != 0
    assert "final packet" in r.stderr.lower()


# ---------------------------------------------------------------------------
# B5: missing lanes
# ---------------------------------------------------------------------------


def test_missing_lanes_reported_not_hidden(tmp_path, two_packets):
    a, b = two_packets
    r = run_pizmz_bundle(
        "--slug", "miss-x",
        "--task", "t",
        "--packet", f"agy={a}",
        "--packet", f"muse={b}",
        "--missing", "free:crashed on pass02 freeze",
        "--out-dir", str(tmp_path / "out"),
        "--created", "20261019t000000z",
    )
    assert r.returncode == 0, r.stderr
    text = (tmp_path / "out" / "pizmz-miss-x-bundle.md").read_text(encoding="utf-8")
    assert "Missing lanes" in text
    assert "free" in text and "crashed on pass02 freeze" in text


# ---------------------------------------------------------------------------
# B6: determinism
# ---------------------------------------------------------------------------


def test_same_inputs_same_bytes(tmp_path, two_packets):
    a, b = two_packets
    outs = []
    for i in (1, 2):
        out = tmp_path / f"out{i}"
        r = run_pizmz_bundle(
            "--slug", "det-x",
            "--task", "same task",
            "--packet", f"agy={a}",
            "--packet", f"muse={b}",
            "--out-dir", str(out),
            "--created", "20261019t000000z",
        )
        assert r.returncode == 0, r.stderr
        outs.append((out / "pizmz-det-x-bundle.md").read_bytes())
    assert outs[0] == outs[1]


# ---------------------------------------------------------------------------
# B7: no overwrite
# ---------------------------------------------------------------------------


def test_refuses_to_overwrite(tmp_path, two_packets):
    a, b = two_packets
    out = tmp_path / "out"
    args = [
        "--slug", "once-x",
        "--task", "t",
        "--packet", f"agy={a}",
        "--packet", f"muse={b}",
        "--out-dir", str(out),
        "--created", "20261019t000000z",
    ]
    assert run_pizmz_bundle(*args).returncode == 0
    r = run_pizmz_bundle(*args)
    assert r.returncode != 0
    assert "overwrite" in r.stderr.lower()


# ---------------------------------------------------------------------------
# B8: synthesis skeleton
# ---------------------------------------------------------------------------


def test_synthesis_skeleton_sections(tmp_path, two_packets):
    a, b = two_packets
    out = tmp_path / "out"
    r = run_pizmz_bundle(
        "--slug", "skel-x",
        "--task", "t",
        "--packet", f"agy={a}",
        "--packet", f"muse={b}",
        "--out-dir", str(out),
        "--created", "20261019t000000z",
    )
    assert r.returncode == 0, r.stderr
    skel = (out / "pizmz-skel-x-synthesis.md").read_text(encoding="utf-8")
    for section in (
        "Coverage map",
        "Agreements",
        "Conflicts",
        "Solo gems",
        "Short-list and next step",
    ):
        assert section in skel


def test_no_synthesis_skel_flag(tmp_path, two_packets):
    a, b = two_packets
    out = tmp_path / "out"
    r = run_pizmz_bundle(
        "--slug", "noskel-x",
        "--task", "t",
        "--packet", f"agy={a}",
        "--packet", f"muse={b}",
        "--no-synthesis-skel",
        "--out-dir", str(out),
    )
    assert r.returncode == 0, r.stderr
    assert not (out / "pizmz-noskel-x-synthesis.md").exists()


# ---------------------------------------------------------------------------
# B9/B10: installer + skill wiring
# ---------------------------------------------------------------------------


def test_installer_lists_helper():
    text = (REPO_ROOT / "bin" / "install-pizm").read_text(encoding="utf-8")
    assert '"pizmz-bundle"' in text


def test_installer_helper_file_exists_and_executable():
    helper = REPO_ROOT / "bin" / "pizmz-bundle"
    assert helper.is_file()
    import os
    assert os.access(helper, os.X_OK)

REPO_SKILL = REPO_ROOT / "skills" / "pizmz" / "SKILL.md"


def test_skill_canonical_in_repo():
    assert REPO_SKILL.is_file(), "canonical skill skills/pizmz/SKILL.md must exist in repo"


def test_skill_documents_bundle_and_synthesis():
    text = REPO_SKILL.read_text(encoding="utf-8")
    assert "pizmz-bundle" in text
    assert "Coverage map" in text
    assert "Conflicts" in text
    assert "Solo gems" in text
