"""
Tests for pizm-reader-server: Safe local loopback-only HTTP reader server.
"""
from __future__ import annotations

import http.client
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
READER_SCRIPT = str(REPO_ROOT / "bin" / "pizm-reader-server")


@pytest.fixture
def run_workspace(tmp_path):
    """Create a mock .ai/pizm root with sample runs."""
    root = tmp_path / "pizm_root"
    root.mkdir()

    # Run 1: run-slug1
    run1 = root / "run-slug1"
    run1.mkdir()
    (run1 / "run.html").write_text("<html><body><h1>Run Slug 1</h1></body></html>", encoding="utf-8")

    # Run 2: bare-slug2
    run2 = root / "bare2"
    run2.mkdir()
    (run2 / "run.html").write_text("<html><body><h1>Bare 2</h1></body></html>", encoding="utf-8")

    return root


@pytest.fixture
def running_reader(run_workspace):
    """Start reader server in foreground on ephemeral port (0) and yield (proc, port, root)."""
    cmd = [
        sys.executable,
        READER_SCRIPT,
        "start",
        "--port", "0",
        "--root", str(run_workspace),
        "--foreground",
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Read the first line of stdout to find actual allocated port
    line = proc.stdout.readline()
    # Expect: READER_SERVER_RUNNING http://127.0.0.1:<port>/ (pid=...)
    import re
    m = re.search(r"127\.0\.0\.1:(\d+)", line)
    assert m is not None, f"Failed to parse port from line: {line!r} (stderr: {proc.stderr.read()})"
    port = int(m.group(1))

    # Wait briefly for server ready
    deadline = time.time() + 3.0
    ready = False
    while time.time() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=0.2)
            conn.request("GET", "/health", headers={"Host": f"127.0.0.1:{port}"})
            r = conn.getresponse()
            if r.status == 200:
                ready = True
                conn.close()
                break
        except Exception:
            time.sleep(0.05)

    assert ready, "Reader server failed to respond on /health"

    try:
        yield proc, port, run_workspace
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def test_health_endpoint(running_reader):
    proc, port, root = running_reader
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1.0)
    conn.request("GET", "/health", headers={"Host": f"127.0.0.1:{port}"})
    resp = conn.getresponse()
    assert resp.status == 200
    assert resp.getheader("Content-Type") == "application/json; charset=utf-8"
    assert resp.getheader("Cache-Control") == "no-store"
    data = json.loads(resp.read().decode("utf-8"))
    assert data["status"] == "ok"
    assert data["served_root"] == str(root.resolve())
    assert data["version"] == "pizm-reader-v1"
    assert data["pid"] == proc.pid
    conn.close()


def test_head_health_endpoint(running_reader):
    _, port, _ = running_reader
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1.0)
    conn.request("HEAD", "/health", headers={"Host": f"127.0.0.1:{port}"})
    resp = conn.getresponse()
    assert resp.status == 200
    assert resp.read() == b""
    conn.close()


def test_run_endpoint_canonical_and_normalized(running_reader):
    _, port, _ = running_reader
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1.0)

    # 1. Access with 'run-slug1'
    conn.request("GET", "/run/run-slug1/", headers={"Host": f"127.0.0.1:{port}"})
    r1 = conn.getresponse()
    assert r1.status == 200
    assert r1.getheader("Content-Type") == "text/html; charset=utf-8"
    assert r1.getheader("Cache-Control") == "no-store"
    body1 = r1.read().decode("utf-8")
    assert "<h1>Run Slug 1</h1>" in body1

    # 2. Access normalized with bare 'slug1' (maps to run-slug1)
    conn.request("GET", "/run/slug1/", headers={"Host": f"127.0.0.1:{port}"})
    r2 = conn.getresponse()
    assert r2.status == 200
    body2 = r2.read().decode("utf-8")
    assert "<h1>Run Slug 1</h1>" in body2

    # 3. Access bare folder 'bare2'
    conn.request("GET", "/run/bare2/", headers={"Host": f"127.0.0.1:{port}"})
    r3 = conn.getresponse()
    assert r3.status == 200
    body3 = r3.read().decode("utf-8")
    assert "<h1>Bare 2</h1>" in body3

    # 4. Access bare folder with 'run-bare2'
    conn.request("GET", "/run/run-bare2/", headers={"Host": f"127.0.0.1:{port}"})
    r4 = conn.getresponse()
    assert r4.status == 200
    body4 = r4.read().decode("utf-8")
    assert "<h1>Bare 2</h1>" in body4

    conn.close()


def test_head_run_endpoint(running_reader):
    _, port, _ = running_reader
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1.0)
    conn.request("HEAD", "/run/slug1/", headers={"Host": f"127.0.0.1:{port}"})
    resp = conn.getresponse()
    assert resp.status == 200
    assert resp.getheader("Content-Type") == "text/html; charset=utf-8"
    assert resp.read() == b""
    conn.close()


def test_nonexistent_run_returns_404(running_reader):
    _, port, _ = running_reader
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1.0)
    conn.request("GET", "/run/nonexistent-slug/", headers={"Host": f"127.0.0.1:{port}"})
    resp = conn.getresponse()
    assert resp.status == 404
    conn.close()


def test_path_traversal_blocked(running_reader):
    _, port, _ = running_reader
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1.0)

    # Traversal in slug
    conn.request("GET", "/run/..%2F..%2Fetc/", headers={"Host": f"127.0.0.1:{port}"})
    resp = conn.getresponse()
    assert resp.status in (400, 403, 404)

    # Directory listing root
    conn.request("GET", "/", headers={"Host": f"127.0.0.1:{port}"})
    resp2 = conn.getresponse()
    assert resp2.status == 404

    conn.close()


def test_symlink_escape_blocked(running_reader, tmp_path):
    _, port, root = running_reader
    outside_file = tmp_path / "outside.html"
    outside_file.write_text("<h1>Secret Outside</h1>", encoding="utf-8")

    # Create symlink inside run directory pointing outside
    escaped_run = root / "run-escaped"
    escaped_run.mkdir()
    (escaped_run / "run.html").symlink_to(outside_file)

    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1.0)
    conn.request("GET", "/run/escaped/", headers={"Host": f"127.0.0.1:{port}"})
    resp = conn.getresponse()
    # Must reject symlink escape outside root
    assert resp.status in (403, 404)
    body = resp.read().decode("utf-8")
    assert "Secret Outside" not in body
    conn.close()


def test_mutating_methods_rejected_405(running_reader):
    _, port, _ = running_reader
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1.0)

    for method in ("POST", "PUT", "DELETE", "PATCH"):
        conn.request(method, "/run/slug1/", headers={"Host": f"127.0.0.1:{port}"}, body=b"data")
        resp = conn.getresponse()
        assert resp.status == 405, f"Method {method} should return 405, got {resp.status}"

    conn.close()


def test_host_header_validation(running_reader):
    _, port, _ = running_reader
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1.0)

    # Valid Host headers
    conn.request("GET", "/health", headers={"Host": f"127.0.0.1:{port}"})
    r1 = conn.getresponse()
    assert r1.status == 200

    conn.request("GET", "/health", headers={"Host": f"localhost:{port}"})
    r2 = conn.getresponse()
    assert r2.status == 200

    # Hostile Host header
    conn.request("GET", "/health", headers={"Host": "attacker.com"})
    r3 = conn.getresponse()
    assert r3.status == 400

    conn.close()


def test_ensure_command_lifecycle(run_workspace):
    """Test CLI ensure command starts server, reuses healthy server, and stops cleanly."""
    # Find free port
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    try:
        # 1. ensure starts server
        res_ensure = subprocess.run(
            [sys.executable, READER_SCRIPT, "ensure", "--port", str(port), "--root", str(run_workspace)],
            capture_output=True,
            text=True,
            timeout=10.0,
        )
        assert res_ensure.returncode == 0, f"ensure failed: {res_ensure.stderr}"
        assert f"http://127.0.0.1:{port}/" in res_ensure.stdout

        # 2. ensure again reuses running instance
        res_ensure2 = subprocess.run(
            [sys.executable, READER_SCRIPT, "ensure", "--port", str(port), "--root", str(run_workspace)],
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        assert res_ensure2.returncode == 0
        assert f"http://127.0.0.1:{port}/" in res_ensure2.stdout

        # 3. status confirms running
        res_status = subprocess.run(
            [sys.executable, READER_SCRIPT, "status", "--port", str(port), "--root", str(run_workspace)],
            capture_output=True,
            text=True,
        )
        assert res_status.returncode == 0
        status_data = json.loads(res_status.stdout)
        assert status_data["status"] == "ok"
        assert status_data["served_root"] == str(run_workspace.resolve())

        # 4. ensure with different root fails cleanly (port collision without killing)
        other_dir = run_workspace.parent / "other_root"
        other_dir.mkdir(exist_ok=True)
        res_coll = subprocess.run(
            [sys.executable, READER_SCRIPT, "ensure", "--port", str(port), "--root", str(other_dir)],
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        assert res_coll.returncode != 0
        assert "READER_PORT_COLLISION" in res_coll.stderr

        # 5. server still healthy for original root
        res_status2 = subprocess.run(
            [sys.executable, READER_SCRIPT, "status", "--port", str(port), "--root", str(run_workspace)],
            capture_output=True,
            text=True,
        )
        assert res_status2.returncode == 0
    finally:
        # 6. stop server
        subprocess.run(
            [sys.executable, READER_SCRIPT, "stop", "--port", str(port), "--root", str(run_workspace)],
            capture_output=True,
            text=True,
        )

def test_status_root_mismatch(running_reader, tmp_path):
    """Status check against a foreign root fails with READER_ROOT_MISMATCH."""
    _, port, _ = running_reader
    foreign_root = tmp_path / "foreign_root"
    foreign_root.mkdir(exist_ok=True)

    res = subprocess.run(
        [sys.executable, READER_SCRIPT, "status", "--port", str(port), "--root", str(foreign_root)],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "READER_ROOT_MISMATCH" in res.stderr


def test_stop_safe_foreign_root(running_reader, tmp_path):
    """Stop command with foreign root skips kill to prevent killing wrong server."""
    proc, port, _ = running_reader
    foreign_root = tmp_path / "foreign_root"
    foreign_root.mkdir(exist_ok=True)

    res = subprocess.run(
        [sys.executable, READER_SCRIPT, "stop", "--port", str(port), "--root", str(foreign_root)],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "READER_STOP_SKIPPED" in res.stderr
    # Server process is still running
    assert proc.poll() is None


def test_stop_safe_pid_mismatch(running_reader):
    """Stop command skips kill when state PID does not match health PID."""
    proc, port, root = running_reader
    state_file = root / f".reader-server-{port}.json"
    # Intentionally corrupt state file with a different PID (current test runner pid)
    state_file.write_text(
        json.dumps({
            "pid": os.getpid(),
            "port": port,
            "served_root": str(root.resolve()),
            "version": "pizm-reader-v1",
        }),
        encoding="utf-8",
    )

    res = subprocess.run(
        [sys.executable, READER_SCRIPT, "stop", "--port", str(port), "--root", str(root)],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "READER_STOP_SKIPPED" in res.stderr
    assert "PID mismatch" in res.stderr
    # Neither reader process nor current process was killed
    assert proc.poll() is None
