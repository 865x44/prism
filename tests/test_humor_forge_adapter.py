"""Tests for deterministic Prism Humor -> Forge seed adapter."""

from pathlib import Path

import pytest

import humor.__main__
from humor.forge_adapter import (
    HUMOR_FIELDS,
    AdapterError,
    adapt_candidate_and_develop,
    adapt_files,
    derive_subtitle,
    derive_title,
)
from humor.ioyaml import dump, load

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "prism-runs" / "pipeline" / "fixtures" / "synthetic-v0"


def test_adapt_synthetic_v0_h1() -> None:
    cand_path = FIXTURE / "candidates" / "H1.yaml"
    dev_path = FIXTURE / "develop-H1.yaml"

    cand_data = load(cand_path.read_text(encoding="utf-8"))
    dev_data = load(dev_path.read_text(encoding="utf-8"))

    seed = adapt_candidate_and_develop(cand_data, dev_data)

    assert set(seed.keys()) == set(HUMOR_FIELDS)
    assert len(seed) == 18

    for k in HUMOR_FIELDS:
        assert isinstance(seed[k], str)
        assert len(seed[k].strip()) > 0

    assert seed["id"] == "H1"
    assert seed["title"] == "Case H1: vault-born rats"
    assert seed["subtitle"] == "vault births create new money and new property"
    assert seed["collision"] == "money-animal"
    assert seed["shared_object"] == "vault-born rats"
    assert seed["core_premise"] == "vault births create new money and new property"

    dumped = dump(seed)
    loaded = load(dumped)
    assert loaded == seed


def test_adapt_synthetic_v0_h2() -> None:
    cand_path = FIXTURE / "candidates" / "H2.yaml"
    dev_path = FIXTURE / "develop-H2.yaml"

    cand_data = load(cand_path.read_text(encoding="utf-8"))
    dev_data = load(dev_path.read_text(encoding="utf-8"))

    seed = adapt_candidate_and_develop(cand_data, dev_data)

    assert set(seed.keys()) == set(HUMOR_FIELDS)
    assert len(seed) == 18
    assert seed["id"] == "H2"
    assert seed["title"] == "Case H2: escaping currency"
    assert seed["subtitle"] == "reserves walk out as a liquidity event"


def test_id_mismatch_raises_adapter_error() -> None:
    cand_path = FIXTURE / "candidates" / "H1.yaml"
    dev_path = FIXTURE / "develop-H2.yaml"

    cand_data = load(cand_path.read_text(encoding="utf-8"))
    dev_data = load(dev_path.read_text(encoding="utf-8"))

    with pytest.raises(AdapterError, match="id mismatch"):
        adapt_candidate_and_develop(cand_data, dev_data)


def test_cli_forge_seed(tmp_path: Path) -> None:
    cand_path = FIXTURE / "candidates" / "H1.yaml"
    dev_path = FIXTURE / "develop-H1.yaml"
    out_path = tmp_path / "seed-H1.yaml"

    code = humor.__main__.main(
        [
            "forge-seed",
            "--candidate",
            str(cand_path),
            "--develop",
            str(dev_path),
            "--out",
            str(out_path),
        ]
    )

    assert code == 0
    assert out_path.is_file()

    seed = load(out_path.read_text(encoding="utf-8"))
    assert set(seed.keys()) == set(HUMOR_FIELDS)
    assert seed["id"] == "H1"
    assert seed["title"] == "Case H1: vault-born rats"


def test_cli_forge_seed_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    cand_path = FIXTURE / "candidates" / "H1.yaml"
    dev_path = FIXTURE / "develop-H1.yaml"

    code = humor.__main__.main(
        [
            "forge-seed",
            "--candidate",
            str(cand_path),
            "--develop",
            str(dev_path),
        ]
    )

    assert code == 0
    captured = capsys.readouterr()
    seed = load(captured.out)
    assert set(seed.keys()) == set(HUMOR_FIELDS)
    assert seed["id"] == "H1"


def test_cli_forge_seed_error_returns_one(capsys: pytest.CaptureFixture[str]) -> None:
    cand_path = FIXTURE / "candidates" / "H1.yaml"
    dev_path = FIXTURE / "develop-H2.yaml"

    code = humor.__main__.main(
        [
            "forge-seed",
            "--candidate",
            str(cand_path),
            "--develop",
            str(dev_path),
        ]
    )

    assert code == 1
    captured = capsys.readouterr()
    assert "forge-seed error" in captured.err


def test_missing_or_empty_field_raises_adapter_error() -> None:
    cand_path = FIXTURE / "candidates" / "H1.yaml"
    dev_path = FIXTURE / "develop-H1.yaml"

    cand_data = load(cand_path.read_text(encoding="utf-8"))
    dev_data = load(dev_path.read_text(encoding="utf-8"))

    # Missing field in candidate
    bad_cand = dict(cand_data)
    del bad_cand["comic_mechanism"]
    with pytest.raises(AdapterError, match="comic_mechanism"):
        adapt_candidate_and_develop(bad_cand, dev_data)

    # Empty field in candidate
    empty_cand = dict(cand_data)
    empty_cand["comic_mechanism"] = "   "
    with pytest.raises(AdapterError, match="comic_mechanism"):
        adapt_candidate_and_develop(empty_cand, dev_data)

    # Missing field in develop
    bad_dev = dict(dev_data)
    del bad_dev["causal_chain"]
    with pytest.raises(AdapterError, match="causal_chain"):
        adapt_candidate_and_develop(cand_data, bad_dev)

    # Empty field in develop
    empty_dev = dict(dev_data)
    empty_dev["causal_chain"] = ""
    with pytest.raises(AdapterError, match="causal_chain"):
        adapt_candidate_and_develop(cand_data, empty_dev)


def test_derive_title_and_subtitle_precedence() -> None:
    cand = {"id": "X1", "collision": "c_val", "shared_object": "s_val"}
    dev = {"bundle_id": "X1", "core_premise": "p_val"}

    # Overrides have highest precedence
    assert derive_title(cand, dev, override="Custom Title") == "Custom Title"
    assert derive_subtitle(cand, dev, override="Custom Subtitle") == "Custom Subtitle"

    # develop title / subtitle
    cand_with_titles = {"id": "X1", "collision": "c_val", "shared_object": "s_val", "title": "Cand Title", "subtitle": "Cand Sub"}
    dev_with_titles = {"bundle_id": "X1", "core_premise": "p_val", "title": "Dev Title", "subtitle": "Dev Sub"}

    assert derive_title(cand_with_titles, dev_with_titles) == "Dev Title"
    assert derive_subtitle(cand_with_titles, dev_with_titles) == "Dev Sub"

    # candidate title / subtitle when develop has none
    dev_no_titles = {"bundle_id": "X1", "core_premise": "p_val"}
    assert derive_title(cand_with_titles, dev_no_titles) == "Cand Title"
    assert derive_subtitle(cand_with_titles, dev_no_titles) == "Cand Sub"

    # Fallback to collision / shared_object / core_premise
    assert derive_title(cand, dev) == "Case X1: s_val"
    assert derive_subtitle(cand, dev) == "p_val"

    # Fallback when shared_object is missing
    cand_no_shared = {"id": "X1", "collision": "c_val"}
    assert derive_title(cand_no_shared, dev) == "Case X1: c_val"

    # Fallback when collision and shared_object are missing
    cand_bare = {"id": "X1"}
    assert derive_title(cand_bare, dev) == "Case X1"

    # Subtitle fallback when core_premise is missing
    dev_no_premise = {"bundle_id": "X1"}
    assert derive_subtitle(cand, dev_no_premise) == "Collision of c_val around s_val."
    assert derive_subtitle(cand_bare, dev_no_premise) == "Seed adaptation for X1."
