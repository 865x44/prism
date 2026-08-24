"""Prompt package for Perspective Core v0.

Prompt markdown files are declared as package data in pyproject.toml:
    "prism.perspective_core" = ["prompts/*.md"]

Prompt files are owned by their respective waves:
    - Explore prompts: Wave 2A
    - 360 prompts: Wave 3
    - Deep prompts: Wave 2B
    - RIFT prompts: Wave 4
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path


def prompt_path(name: str) -> Path:
    """Resolve a prompt file path within the prompts package.

    Args:
        name: Filename (e.g., "explore_generate.md")

    Returns:
        Path to the prompt file
    """
    pkg = resources.files("prism.perspective_core.prompts")
    return Path(pkg.joinpath(name))
