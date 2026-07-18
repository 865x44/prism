import os
import shutil
import subprocess
from unittest import mock

import pytest
from prism.runtime.doctor import run_doctor

@pytest.fixture
def clean_env(monkeypatch):
    """Isolate env vars."""
    for var in ("PRISM_API_KEY", "OPENAI_API_KEY", "PRISM_TRANSPORT"):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch

def test_doctor_http_no_key(clean_env, capsys):
    """If no key is set, explicit transport http is still resolved, but key is missing."""
    clean_env.setenv("PRISM_TRANSPORT", "http")
    run_doctor(smoke=False)
    out = capsys.readouterr().out
    assert "Transport: http" in out
    assert "API Key: not found" in out

def test_doctor_secret_redaction(clean_env, capsys):
    """If key is set, it is not printed."""
    clean_env.setenv("PRISM_API_KEY", "sk-secret-do-not-leak")
    run_doctor(smoke=False)
    out = capsys.readouterr().out
    assert "sk-secret-do-not-leak" not in out
    assert "present in PRISM_API_KEY" in out

def test_doctor_invalid_transport(clean_env, capsys):
    """Handles invalid explicit transport."""
    clean_env.setenv("PRISM_TRANSPORT", "magic")
    run_doctor(smoke=False)
    out = capsys.readouterr().out
    assert "Transport: invalid" in out
    assert "magic" in out

def test_doctor_opencode_found(clean_env, capsys, monkeypatch):
    """Tests opencode found logic."""
    clean_env.setenv("PRISM_TRANSPORT", "opencode")
    
    def fake_which(cmd):
        if cmd == "opencode": return "/fake/bin/opencode"
        return None
    
    monkeypatch.setattr(shutil, "which", fake_which)
    
    def fake_run(*args, **kwargs):
        class Result:
            stdout = "opencode fake version 1.18.3"
        return Result()
    
    monkeypatch.setattr(subprocess, "run", fake_run)
    
    run_doctor(smoke=False)
    out = capsys.readouterr().out
    assert "OpenCode executable: found (opencode fake version 1.18.3)" in out

def test_doctor_opencode_missing(clean_env, capsys, monkeypatch):
    """Tests opencode missing logic."""
    clean_env.setenv("PRISM_TRANSPORT", "opencode")
    monkeypatch.setattr(shutil, "which", lambda cmd: None)
    
    run_doctor(smoke=False)
    out = capsys.readouterr().out
    assert "OpenCode executable: not found on PATH" in out
