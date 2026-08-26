"""Deterministic Prism Humor to Forge seed adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from humor.ioyaml import dump, load

HUMOR_FIELDS: tuple[str, ...] = (
    "id",
    "collision",
    "shared_object",
    "comic_mechanism",
    "reality_anchor",
    "gameability",
    "core_premise",
    "causal_chain",
    "straight_faced_logic",
    "escalation_ladder",
    "reversal",
    "compression",
    "character_affordances",
    "institutional_consequences",
    "callback_potential",
    "failure_boundary",
    "title",
    "subtitle",
)

CANDIDATE_REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "collision",
    "shared_object",
    "comic_mechanism",
    "reality_anchor",
    "gameability",
)

DEVELOP_REQUIRED_FIELDS: tuple[str, ...] = (
    "bundle_id",
    "core_premise",
    "causal_chain",
    "straight_faced_logic",
    "escalation_ladder",
    "reversal",
    "compression",
    "character_affordances",
    "institutional_consequences",
    "callback_potential",
    "failure_boundary",
)


class AdapterError(ValueError):
    """Raised when candidate and develop inputs cannot be deterministically adapted."""


def _clean_str(val: object) -> str | None:
    if isinstance(val, str):
        s = val.strip()
        if s:
            return s
    return None


def derive_title(
    candidate: Mapping[str, object],
    develop: Mapping[str, object],
    override: str | None = None,
) -> str:
    cleaned_override = _clean_str(override)
    if cleaned_override is not None:
        return cleaned_override

    dev_title = _clean_str(develop.get("title"))
    if dev_title is not None:
        return dev_title

    cand_title = _clean_str(candidate.get("title"))
    if cand_title is not None:
        return cand_title

    cid = _clean_str(candidate.get("id")) or ""

    shared_object = _clean_str(candidate.get("shared_object"))
    if shared_object is not None:
        return f"Case {cid}: {shared_object}" if cid else shared_object

    collision = _clean_str(candidate.get("collision"))
    if collision is not None:
        return f"Case {cid}: {collision}" if cid else collision

    return f"Case {cid}" if cid else "Case"


def derive_subtitle(
    candidate: Mapping[str, object],
    develop: Mapping[str, object],
    override: str | None = None,
) -> str:
    cleaned_override = _clean_str(override)
    if cleaned_override is not None:
        return cleaned_override

    dev_subtitle = _clean_str(develop.get("subtitle"))
    if dev_subtitle is not None:
        return dev_subtitle

    cand_subtitle = _clean_str(candidate.get("subtitle"))
    if cand_subtitle is not None:
        return cand_subtitle

    core_premise = _clean_str(develop.get("core_premise"))
    if core_premise is not None:
        return core_premise

    collision = _clean_str(candidate.get("collision"))
    shared_object = _clean_str(candidate.get("shared_object"))
    if collision is not None and shared_object is not None:
        return f"Collision of {collision} around {shared_object}."

    cid = _clean_str(candidate.get("id")) or ""
    return f"Seed adaptation for {cid}."


def adapt_candidate_and_develop(
    candidate: Mapping[str, object],
    develop: Mapping[str, object],
    *,
    title: str | None = None,
    subtitle: str | None = None,
) -> dict[str, str]:
    if not isinstance(candidate, Mapping):
        raise AdapterError("candidate must be a mapping")
    if not isinstance(develop, Mapping):
        raise AdapterError("develop must be a mapping")

    for field in CANDIDATE_REQUIRED_FIELDS:
        val = candidate.get(field)
        if not isinstance(val, str) or not val.strip():
            raise AdapterError(f"candidate missing or empty required field: {field!r}")

    for field in DEVELOP_REQUIRED_FIELDS:
        val = develop.get(field)
        if not isinstance(val, str) or not val.strip():
            raise AdapterError(f"develop missing or empty required field: {field!r}")

    cid = str(candidate["id"]).strip()
    bundle_id = str(develop["bundle_id"]).strip()
    if cid != bundle_id:
        raise AdapterError(f"id mismatch: candidate id {cid!r} != develop bundle_id {bundle_id!r}")

    derived_title = derive_title(candidate, develop, override=title)
    if not derived_title:
        raise AdapterError("unable to derive non-empty title")

    derived_subtitle = derive_subtitle(candidate, develop, override=subtitle)
    if not derived_subtitle:
        raise AdapterError("unable to derive non-empty subtitle")

    seed: dict[str, str] = {
        "id": cid,
        "collision": str(candidate["collision"]).strip(),
        "shared_object": str(candidate["shared_object"]).strip(),
        "comic_mechanism": str(candidate["comic_mechanism"]).strip(),
        "reality_anchor": str(candidate["reality_anchor"]).strip(),
        "gameability": str(candidate["gameability"]).strip(),
        "core_premise": str(develop["core_premise"]).strip(),
        "causal_chain": str(develop["causal_chain"]).strip(),
        "straight_faced_logic": str(develop["straight_faced_logic"]).strip(),
        "escalation_ladder": str(develop["escalation_ladder"]).strip(),
        "reversal": str(develop["reversal"]).strip(),
        "compression": str(develop["compression"]).strip(),
        "character_affordances": str(develop["character_affordances"]).strip(),
        "institutional_consequences": str(develop["institutional_consequences"]).strip(),
        "callback_potential": str(develop["callback_potential"]).strip(),
        "failure_boundary": str(develop["failure_boundary"]).strip(),
        "title": derived_title,
        "subtitle": derived_subtitle,
    }

    for k in HUMOR_FIELDS:
        if k not in seed or not isinstance(seed[k], str) or not seed[k].strip():
            raise AdapterError(f"seed field {k!r} is missing or empty")

    return seed


def adapt_files(
    candidate_path: Path,
    develop_path: Path,
    out_path: Path | None = None,
    *,
    title: str | None = None,
    subtitle: str | None = None,
) -> str:
    try:
        cand_text = candidate_path.read_text(encoding="utf-8")
    except Exception as exc:
        raise AdapterError(f"unable to read candidate file {candidate_path}: {exc}") from exc

    try:
        cand_data = load(cand_text)
    except Exception as exc:
        raise AdapterError(f"unable to parse candidate YAML {candidate_path}: {exc}") from exc

    try:
        dev_text = develop_path.read_text(encoding="utf-8")
    except Exception as exc:
        raise AdapterError(f"unable to read develop file {develop_path}: {exc}") from exc

    try:
        dev_data = load(dev_text)
    except Exception as exc:
        raise AdapterError(f"unable to parse develop YAML {develop_path}: {exc}") from exc

    seed = adapt_candidate_and_develop(cand_data, dev_data, title=title, subtitle=subtitle)

    try:
        yaml_text = dump(seed)
    except Exception as exc:
        raise AdapterError(f"unable to dump seed YAML: {exc}") from exc

    if out_path is not None:
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(yaml_text, encoding="utf-8")
        except Exception as exc:
            raise AdapterError(f"unable to write output to {out_path}: {exc}") from exc

    return yaml_text
