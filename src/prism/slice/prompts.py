"""Prompt template loading for Prism (Beerlight Runtime v1).

Prompt files live in the `prompts/` directory next to this module and
contain a ```text fenced block with {placeholders}.
"""
from __future__ import annotations

import re
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt(name: str) -> str:
    """Load a prompt template from the prompts directory.

    The prompt files contain a ```text fenced block with {placeholders}.
    We extract the fenced block content.
    """
    path = _PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    content = path.read_text(encoding="utf-8")

    # Extract fenced text block
    m = re.search(r"```text\s*\n(.*?)```", content, re.DOTALL)
    if m:
        return m.group(1).strip()

    # Fallback: try any fenced block
    m = re.search(r"```\w*\s*\n(.*?)```", content, re.DOTALL)
    if m:
        return m.group(1).strip()

    return content.strip()
