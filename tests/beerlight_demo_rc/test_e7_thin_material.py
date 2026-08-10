from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROMPT = ROOT / "src/prism/beerlight_demo_rc/prompts/explore/LOCAL_DEMO_RC_REFERENCE_SUBJECT_P2.md"


def test_e7_thin_material_guard_requires_honest_grounded_limit_without_quota():
    prompt = PROMPT.read_text(encoding="utf-8")

    assert "## Thin-material grounding" in prompt
    assert "cannot support materially distinct grounded models" in prompt
    assert "do not manufacture breadth" in prompt
    assert "Honestly limit or abstain, or request the context" in prompt
    assert "Exact wording is not a contract." in prompt
    assert "There is no minimum\ncard or family count" in prompt
