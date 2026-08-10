from __future__ import annotations

import ast
from pathlib import Path

import pytest

from prism.beerlight_demo_rc.provider import DisabledProvider, ProviderCallsDisabled


def test_new_harness_has_no_legacy_runtime_or_slice_dependency():
    package = Path(__file__).parents[2] / "src/prism/beerlight_demo_rc"
    for source_path in package.glob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        assert not any(name.startswith("prism.runtime") or name.startswith("prism.slice") for name in imports)
        assert "MAX_CARDS" not in source


def test_default_provider_fails_closed_without_outbound_call():
    with pytest.raises(ProviderCallsDisabled):
        DisabledProvider().execute({"fixture_id": "E1"})
