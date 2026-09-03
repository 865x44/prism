"""
Tests for Native Pizm installer (bin/install-pizm) and dynamic skill-root resolution.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALLER_SCRIPT = str(REPO_ROOT / "bin" / "install-pizm")
CHECKPOINT_SCRIPT = str(REPO_ROOT / "bin" / "pizm-checkpoint")


def test_install_claude_code(tmp_path, monkeypatch):
    """Test installing for Claude Code in an isolated temporary HOME."""
    monkeypatch.setenv("HOME", str(tmp_path))

    res = subprocess.run(
        [sys.executable, INSTALLER_SCRIPT, "--host", "claude-code"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"install failed: {res.stderr}"
    assert "INSTALL_COMPLETE" in res.stdout

    claude_skill = tmp_path / ".claude" / "skills" / "pizm"
    assert (claude_skill / "SKILL.md").is_file()
    assert (claude_skill / "references" / "explore.md").is_file()
    assert (claude_skill / "references" / "explore-selector.md").is_file()
    assert (claude_skill / "references" / "auto.md").is_file()
    assert (claude_skill / "references" / "deep.md").is_file()

    # OpenCode dir must NOT exist
    opencode_skill = tmp_path / ".config" / "opencode" / "skills" / "pizm"
    assert not opencode_skill.exists()

    # Helpers in ~/.local/bin
    local_bin = tmp_path / ".local" / "bin"
    assert (local_bin / "pizm-checkpoint").exists()
    assert (local_bin / "pizm-session-bundle").exists()
    assert (local_bin / "pizm-reader-server").exists()
    assert (local_bin / "pizm_render_html.py").exists()
    # Verify helpers are actual files, NOT symlinks (self-contained)
    for helper_name in ["pizm-checkpoint", "pizm-session-bundle", "pizm-reader-server", "pizm_render_html.py"]:
        h_path = local_bin / helper_name
        assert h_path.is_file(), f"{helper_name} is not a file"
        assert not h_path.is_symlink(), f"{helper_name} is unexpectedly a symlink"
        assert os.access(h_path, os.X_OK), f"{helper_name} is not executable"
    assert "TEST_CHECKPOINT_OK" in res.stdout


def test_install_opencode(tmp_path, monkeypatch):
    """Test installing for OpenCode in an isolated temporary HOME."""
    monkeypatch.setenv("HOME", str(tmp_path))

    res = subprocess.run(
        [sys.executable, INSTALLER_SCRIPT, "--host", "opencode"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"install failed: {res.stderr}"
    assert "INSTALL_COMPLETE" in res.stdout

    opencode_skill = tmp_path / ".config" / "opencode" / "skills" / "pizm"
    assert (opencode_skill / "SKILL.md").is_file()
    assert (opencode_skill / "references" / "explore.md").is_file()

    # Claude dir must NOT exist
    claude_skill = tmp_path / ".claude" / "skills" / "pizm"
    assert not claude_skill.exists()

    # Helpers in ~/.local/bin
    local_bin = tmp_path / ".local" / "bin"
    assert (local_bin / "pizm-checkpoint").exists()


def test_install_both(tmp_path, monkeypatch):
    """Test installing for both Claude Code and OpenCode."""
    monkeypatch.setenv("HOME", str(tmp_path))

    res = subprocess.run(
        [sys.executable, INSTALLER_SCRIPT, "--host", "both"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"install failed: {res.stderr}"
    assert "INSTALL_COMPLETE" in res.stdout

    assert (tmp_path / ".claude" / "skills" / "pizm" / "SKILL.md").is_file()
    assert (tmp_path / ".config" / "opencode" / "skills" / "pizm" / "SKILL.md").is_file()

    local_bin = tmp_path / ".local" / "bin"
    assert (local_bin / "pizm-checkpoint").exists()
    assert (local_bin / "pizm-session-bundle").exists()
    assert (local_bin / "pizm-reader-server").exists()
    assert (local_bin / "pizm_render_html.py").exists()


def test_checkpoint_dynamic_skill_root_claude_only(tmp_path, monkeypatch):
    """Test that pizm-checkpoint resolves skill root with no OpenCode directory present."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Install claude-code only
    res_inst = subprocess.run(
        [sys.executable, INSTALLER_SCRIPT, "--host", "claude-code"],
        capture_output=True,
        text=True,
    )
    assert res_inst.returncode == 0

    project = tmp_path / "test_project"
    project.mkdir(parents=True)

    cand_data = {
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [
            {
                "candidate_id": "c01",
                "title": "Seed 1",
                "semantic_core": {
                    "claim": "Claim 1",
                    "structural_shift": "Shift 1",
                    "mechanism": "Mechanism 1",
                    "grounding_anchor": "Anchor 1",
                    "what_becomes_visible": "Visible 1",
                    "boundary": "Boundary 1",
                },
                "epistemics": {
                    "supported": ["Fact 1"],
                    "inferred": [],
                    "speculative": [],
                    "unknown": [],
                },
            }
        ],
    }
    cand_file = project / "candidates.json"
    cand_file.write_text(json.dumps(cand_data), encoding="utf-8")

    # Freeze without --skill-root using the INSTALLED helper in ~/.local/bin:
    # should dynamically discover ~/.claude/skills/pizm with no repo sibling present.
    installed_checkpoint = str(tmp_path / ".local" / "bin" / "pizm-checkpoint")
    res_freeze = subprocess.run(
        [
            sys.executable,
            installed_checkpoint,
            "freeze",
            "--stage", "explore",
            "--run-id", "dyn-root-test",
            "--input", str(cand_file),
            "--project-root", str(project),
        ],
        capture_output=True,
        text=True,
    )
    assert res_freeze.returncode == 0, f"freeze failed: {res_freeze.stderr}"
    assert "FREEZE_OK" in res_freeze.stdout


def test_invalid_host_fails(tmp_path, monkeypatch):
    """Invalid host argument fails with error code 2."""
    monkeypatch.setenv("HOME", str(tmp_path))
    res = subprocess.run(
        [sys.executable, INSTALLER_SCRIPT, "--host", "unknown-host"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 2


def test_install_rejects_divergent_skill_roots(tmp_path, monkeypatch):
    """If both Claude Code and OpenCode skill roots exist but diverge, install fails unless --host both."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Install claude-code first
    res1 = subprocess.run([sys.executable, INSTALLER_SCRIPT, "--host", "claude-code"], capture_output=True, text=True)
    assert res1.returncode == 0

    # Create divergent OpenCode skill root
    opencode_skill = tmp_path / ".config" / "opencode" / "skills" / "pizm"
    opencode_skill.mkdir(parents=True)
    (opencode_skill / "SKILL.md").write_text("Divergent content", encoding="utf-8")

    # Installing only claude-code must detect divergence and fail
    res2 = subprocess.run([sys.executable, INSTALLER_SCRIPT, "--host", "claude-code"], capture_output=True, text=True)
    assert res2.returncode != 0
    assert "Divergent skill roots detected" in res2.stderr

    # Installing both synchronizes them and must succeed
    res3 = subprocess.run([sys.executable, INSTALLER_SCRIPT, "--host", "both"], capture_output=True, text=True)
    assert res3.returncode == 0
    assert "INSTALL_COMPLETE" in res3.stdout


def test_checkpoint_rejects_divergent_skill_roots(tmp_path, monkeypatch):
    """pizm-checkpoint dynamic skill root resolution raises error if both roots exist and diverge."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Set up divergent Claude and OpenCode skill roots
    claude_skill = tmp_path / ".claude" / "skills" / "pizm"
    claude_skill.mkdir(parents=True)
    (claude_skill / "SKILL.md").write_text("Claude version", encoding="utf-8")

    opencode_skill = tmp_path / ".config" / "opencode" / "skills" / "pizm"
    opencode_skill.mkdir(parents=True)
    (opencode_skill / "SKILL.md").write_text("OpenCode version", encoding="utf-8")

    # Copy checkpoint to standalone dir (no local repo skills/pizm sibling)
    standalone_bin = tmp_path / "custom_bin"
    standalone_bin.mkdir()
    standalone_ck = standalone_bin / "pizm-checkpoint"
    standalone_ck.write_bytes(Path(CHECKPOINT_SCRIPT).read_bytes())
    standalone_ck.chmod(0o755)

    project = tmp_path / "proj"
    project.mkdir()
    cand_file = project / "candidates.json"
    cand_file.write_text(json.dumps({
        "schema_version": "pizm-candidates-v1",
        "stage": "explore",
        "mode": "NORMAL",
        "candidates": [{"candidate_id": "c01", "title": "T", "semantic_core": {"claim": "C", "structural_shift": "S", "mechanism": "M", "grounding_anchor": "A", "what_becomes_visible": "V", "boundary": "B"}, "epistemics": {"supported": ["S"], "inferred": [], "speculative": [], "unknown": []}}],
    }), encoding="utf-8")

    res = subprocess.run(
        [sys.executable, str(standalone_ck), "freeze", "--stage", "explore", "--run-id", "div-test", "--input", str(cand_file), "--project-root", str(project)],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "Divergent skill roots detected" in res.stderr
