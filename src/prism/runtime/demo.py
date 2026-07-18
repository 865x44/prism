import shutil
import sys
from pathlib import Path

def run_demo() -> int:
    print("=== Prism Recorded Demo ===")
    print("Notice: This is a static fixture, not a live provider call.\n")
    
    # Locate demo_fixtures
    base_dir = Path(__file__).parent.parent / "demo_fixtures" / "demo_run"
    if not base_dir.exists():
        print(f"Error: Demo fixture not found at {base_dir}", file=sys.stderr)
        return 1
        
    # Destination
    dest_dir = Path("prism-runs") / "prism-demo-1"
    
    try:
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        shutil.copytree(base_dir, dest_dir)
        
        # Display output
        output_md = (dest_dir / "output.md").read_text(encoding="utf-8")
        print("Source: (synthetic draft about writing speed vs review time)")
        print(f"Task: Find non-obvious angles for this post\n")
        print("--- Output ---")
        print(output_md)
        print("\n--- Inspectability ---")
        print("The full candidate pool and judge decisions have been saved.")
        print(f"You can inspect them now by running: prism inspect prism-demo-1")
    except Exception as e:
        print(f"Error running demo: {e}", file=sys.stderr)
        return 1
        
    return 0
