"""Diagnostic tool for Prism Runtime."""
import importlib.metadata
import os
import shutil
import subprocess
import sys
from pathlib import Path

from prism.slice.provider import (
    _resolve_transport,
    get_generator_model,
    get_judge_model,
    call_llm,
    TransportError,
    TRANSPORT_HTTP,
    TRANSPORT_OPENCODE,
)

def run_doctor(smoke: bool = False) -> int:
    """Run diagnostic checks and optionally a smoke test.
    Returns 0 on full PASS, 1 on FAIL.
    """
    print("=== Prism Diagnostic ===")
    
    issues = 0
    warnings = 0

    def ok(msg): print(f"[PASS] {msg}")
    def warn(msg):
        nonlocal warnings
        warnings += 1
        print(f"[WARN] {msg}")
    def fail(msg):
        nonlocal issues
        issues += 1
        print(f"[FAIL] {msg}")

    # Version
    try:
        version = importlib.metadata.version("prism")
        ok(f"Prism version: {version}")
    except importlib.metadata.PackageNotFoundError:
        warn("Prism version: unknown (not installed as package)")

    # Python version
    py_ver = sys.version_info
    py_str = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"
    if py_ver >= (3, 11):
        ok(f"Python version: {py_str} (supported)")
    else:
        fail(f"Python version: {py_str} (unsupported, need >= 3.11)")

    # Package health
    try:
        import prism.runtime
        import prism.slice
        ok("Package imports: healthy")
    except Exception as e:
        fail(f"Package imports: failed ({e})")

    # API Key presence
    key_env = "PRISM_API_KEY" if os.environ.get("PRISM_API_KEY") else ("OPENAI_API_KEY" if os.environ.get("OPENAI_API_KEY") else None)
    if key_env:
        ok(f"API Key: present in {key_env} (value redacted)")
    else:
        ok("API Key: not found")

    # Transport
    try:
        transport = _resolve_transport()
        explicit = os.environ.get("PRISM_TRANSPORT")
        if explicit:
            ok(f"Transport: {transport} (explicit via PRISM_TRANSPORT)")
        else:
            ok(f"Transport: {transport} (auto-detected)")
            
        if transport == TRANSPORT_OPENCODE:
            opencode_path = shutil.which("opencode")
            if opencode_path:
                try:
                    res = subprocess.run(["opencode", "--version"], capture_output=True, text=True, timeout=2)
                    ok(f"OpenCode executable: found ({res.stdout.strip()})")
                except Exception as e:
                    warn(f"OpenCode executable: found but failed to run ({e})")
            else:
                fail("OpenCode executable: not found on PATH")
    except TransportError as e:
        fail(f"Transport: invalid ({e})")
        transport = "unknown"

    # Models
    try:
        gen_model = get_generator_model()
        ok(f"Generator model: {gen_model}")
    except Exception as e:
        fail(f"Generator model: error ({e})")

    try:
        judge_model = get_judge_model()
        ok(f"Judge model: {judge_model}")
    except Exception as e:
        fail(f"Judge model: error ({e})")

    # Directories
    def check_dir(dname: str):
        p = Path(dname)
        try:
            p.mkdir(parents=True, exist_ok=True)
            test_file = p / ".doctor_test"
            test_file.write_text("test")
            test_file.unlink()
            ok(f"Directory {dname}: writable")
        except Exception as e:
            fail(f"Directory {dname}: not writable ({e})")

    check_dir("prism-runs")
    check_dir("prism-sessions")

    # Smoke Test
    if smoke:
        print("\n--- Smoke Test ---")
        if transport == "unknown":
            fail("Smoke test skipped due to invalid transport.")
        else:
            print(f"Executing minimal call to {get_generator_model()} via {transport}...")
            try:
                # Use a deterministic/minimal prompt
                res = call_llm("Respond with exactly the word 'OK'.", get_generator_model())
                ok("Smoke test: succeeded")
            except Exception as e:
                fail(f"Smoke test: failed ({e})")

    print("\n--- Summary ---")
    if issues == 0 and warnings == 0:
        print("PASS")
        return 0
    elif issues == 0:
        print(f"WARN (0 failures, {warnings} warnings)")
        return 0
    else:
        print(f"FAIL ({issues} failures, {warnings} warnings)")
        return 1
