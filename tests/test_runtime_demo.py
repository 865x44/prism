import os
from pathlib import Path
from prism.runtime.demo import run_demo

def test_run_demo(tmp_path, monkeypatch):
    # change working directory so prism-runs is created in tmp_path
    monkeypatch.chdir(tmp_path)
    
    # We must mock the path to demo_fixtures since we changed cwd
    original_file = Path(__file__).parent.parent / "src" / "prism" / "runtime" / "demo.py"
    # Actually, demo.py uses Path(__file__) which is absolute and shouldn't be affected by chdir.
    
    assert run_demo() == 0
    assert (tmp_path / "prism-runs" / "prism-demo-1" / "output.md").exists()
    assert (tmp_path / "prism-runs" / "prism-demo-1" / "metadata.json").exists()
