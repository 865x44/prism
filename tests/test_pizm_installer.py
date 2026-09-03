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

    # Freeze without --skill-root: should dynamically discover ~/.claude/skills/pizm
    res_freeze = subprocess.run(
        [
            sys.executable,
            CHECKPOINT_SCRIPT,
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
