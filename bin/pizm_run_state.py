#!/usr/bin/env python3
"""
pizm_run_state: Deterministic route, artifact topology, completion, and outcome resolver.

Stdlib-only shared module providing a single authoritative state model for
downstream consumers (session bundling, markdown/HTML rendering, reader server,
completeness checks). Keeps route, artifact topology, execution completion,
and semantic outcome strictly distinct.
"""
from __future__ import annotations

import json
import random
import re
import string
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

ROUTES = ("MANUAL", "AUTO", "BONK")

ARTIFACT_SHAPES = (
    "SINGLE_DEEP_REVIEW",
    "COMPARISON_REVIEW",
    "PORTFOLIO_TERMINAL",
    "PARTIAL",
)

EXECUTION_COMPLETIONS = (
    "COMPLETE",
    "INCOMPLETE",
)

SEMANTIC_OUTCOMES = (
    "MODEL_READY",
    "NEED_EVIDENCE",
    "RETURN_TO_EXPLORE",
    "LEFT",
    "RIGHT",
    "CONDITIONAL",
    "UNRESOLVED",
    "GATHER_INFORMATION",
    "PRESERVE_ONLY",
)

_CYRILLIC_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}


def slugify_subject(text: Optional[str], default: str = "untitled") -> str:
    """Deterministic ASCII/transliteration rule for subject slugs.

    Transforms text to lowercase ASCII hyphen-separated slug.
    Transliterates Cyrillic characters (e.g. 'Комки' -> 'komki').
    Replaces non-alphanumeric chars with hyphens.
    Collapses repeated hyphens and strips leading/trailing hyphens.
    Falls back to `default` (or 'untitled') if result is empty.
    """
    if not text or not str(text).strip():
        return default
    s = str(text).strip().lower()
    res: List[str] = []
    for ch in s:
        if ch in _CYRILLIC_MAP:
            res.append(_CYRILLIC_MAP[ch])
        elif ch.isalnum() and ch.isascii():
            res.append(ch)
        else:
            res.append("-")
    slug = "".join(res)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug if slug else default


def generate_run_id(subject_slug: Optional[str] = None) -> str:
    """Generate run-id in format: <subject-slug>-<UTC timestamp>-<random4>"""
    slug = slugify_subject(subject_slug, default="untitled")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%Sz")
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{slug}-{ts}-{suffix}"


@dataclass(frozen=True)
class RunState:
    route: str  # MANUAL | AUTO | BONK
    artifact_shape: str  # SINGLE_DEEP_REVIEW | COMPARISON_REVIEW | PORTFOLIO_TERMINAL | PARTIAL
    execution_completion: str  # COMPLETE | INCOMPLETE
    semantic_outcome: Optional[str]  # e.g. MODEL_READY, LEFT, CONDITIONAL, UNRESOLVED, GATHER_INFORMATION, None
    missing_next: Optional[str] = None  # e.g. Search, Portfolio, Deep, Critic, Comparison, None
    auto_target: Optional[Dict[str, Any]] = None
    subject_slug: Optional[str] = None
    records: Optional[Dict[str, str]] = None  # e.g. {"markdown": "run-slug.md", "html": "run-slug.html"}

    @property
    def is_complete(self) -> bool:
        return self.execution_completion == "COMPLETE"

    @property
    def header_shape(self) -> str:
        if self.is_complete:
            return self.route
        return f"{self.route} · incomplete"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route": self.route,
            "artifact_shape": self.artifact_shape,
            "execution_completion": self.execution_completion,
            "semantic_outcome": self.semantic_outcome,
            "missing_next": self.missing_next,
            "auto_target": self.auto_target,
            "subject_slug": self.subject_slug,
            "records": self.records,
        }


def _unwrap_item(item: Any) -> Any:
    if isinstance(item, (tuple, list)) and len(item) == 2 and isinstance(item[0], str):
        return item[1]
    return item


def resolve_run_state(
    portfolio: Optional[Dict[str, Any]] = None,
    developments: Optional[Sequence[Any]] = None,
    reviews: Optional[Sequence[Any]] = None,
    comparison: Optional[Any] = None,
    lever_design: Optional[Dict[str, Any]] = None,
    lever_review: Optional[Dict[str, Any]] = None,
    passes: Optional[Sequence[Any]] = None,
    manifest: Optional[Dict[str, Any]] = None,
    subject: Optional[str] = None,
) -> RunState:
    """Deterministically resolve the route, artifact topology, execution completion, and semantic outcome."""
    # Normalize inputs
    port_data = portfolio if isinstance(portfolio, dict) else None
    dev_items = [_unwrap_item(d) for d in (developments or []) if _unwrap_item(d) is not None]
    rev_items = [_unwrap_item(r) for r in (reviews or []) if _unwrap_item(r) is not None]
    comp_data = _unwrap_item(comparison) if comparison is not None else None
    if not isinstance(comp_data, dict):
        comp_data = None
    passes_list = list(passes or [])
    manifest_data = manifest if isinstance(manifest, dict) else None

    # Determine records and subject slug
    subject_slug = None
    records = None
    if manifest_data:
        subject_slug = manifest_data.get("subject_slug") or manifest_data.get("subject")
        if isinstance(manifest_data.get("records"), dict):
            records = dict(manifest_data["records"])
    if not subject_slug and subject:
        subject_slug = slugify_subject(subject)

    # 1. Determine Route
    route = "AUTO"
    if port_data is not None:
        raw_route = port_data.get("route")
        if isinstance(raw_route, str) and raw_route.strip():
            raw_upper = raw_route.strip().upper()
            if raw_upper in ("FORGE", "BONK"):
                route = "BONK"
            elif raw_upper == "MANUAL":
                route = "MANUAL"
            else:
                route = "AUTO"
        elif port_data.get("competition_status") in ("TWO_DEFENSIBLE_BUNDLES", "NO_SECOND_DEFENSIBLE_BUNDLE"):
            route = "BONK"
        elif port_data.get("schema_version") in ("pizm-portfolio-selection-v1", "pizm-portfolio-selection-v2"):
            route = "AUTO"
    elif comp_data is not None:
        route = "BONK"
    elif manifest_data is not None and manifest_data.get("route"):
        m_route = str(manifest_data["route"]).strip().upper()
        route = "BONK" if m_route in ("FORGE", "BONK") else m_route
    elif not port_data and (dev_items or rev_items or passes_list):
        route = "MANUAL"

    # 2. Check Portfolio Terminal
    if port_data is not None:
        next_move = port_data.get("next_reasoning_move")
        if route == "AUTO" and next_move in ("GATHER_INFORMATION", "PRESERVE_ONLY"):
            return RunState(
                route="AUTO",
                artifact_shape="PORTFOLIO_TERMINAL",
                execution_completion="COMPLETE",
                semantic_outcome=next_move,
                missing_next=None,
                auto_target=None,
                subject_slug=subject_slug,
                records=records,
            )

    # 3. Check BONK Route (Comparison Review or Single Fallback)
    if route == "BONK":
        comp_status = port_data.get("competition_status") if port_data else None

        if comp_status == "NO_SECOND_DEFENSIBLE_BUNDLE":
            # Single Deep path under BONK
            single_target = port_data.get("single_target") if port_data else None
            if dev_items and rev_items:
                term = rev_items[0].get("terminal_state") if isinstance(rev_items[0], dict) else None
                return RunState(
                    route="BONK",
                    artifact_shape="SINGLE_DEEP_REVIEW",
                    execution_completion="COMPLETE",
                    semantic_outcome=term,
                    missing_next=None,
                    auto_target=single_target,
                    subject_slug=subject_slug,
                    records=records,
                )
            elif dev_items:
                return RunState(
                    route="BONK",
                    artifact_shape="PARTIAL",
                    execution_completion="INCOMPLETE",
                    semantic_outcome=None,
                    missing_next="Critic",
                    auto_target=single_target,
                    subject_slug=subject_slug,
                    records=records,
                )
            else:
                return RunState(
                    route="BONK",
                    artifact_shape="PARTIAL",
                    execution_completion="INCOMPLETE",
                    semantic_outcome=None,
                    missing_next="Deep",
                    auto_target=single_target,
                    subject_slug=subject_slug,
                    records=records,
                )
        else:
            # TWO_DEFENSIBLE_BUNDLES or comparison stage
            if comp_data is not None:
                comp_sub = comp_data.get("comparison") if isinstance(comp_data.get("comparison"), dict) else comp_data
                pref = comp_sub.get("current_preference") if isinstance(comp_sub, dict) else None
                outcome = pref if pref in ("LEFT", "RIGHT", "CONDITIONAL", "UNRESOLVED") else (pref or "UNRESOLVED")
                return RunState(
                    route="BONK",
                    artifact_shape="COMPARISON_REVIEW",
                    execution_completion="COMPLETE",
                    semantic_outcome=outcome,
                    missing_next=None,
                    auto_target=None,
                    subject_slug=subject_slug,
                    records=records,
                )
            elif len(dev_items) >= 2:
                return RunState(
                    route="BONK",
                    artifact_shape="PARTIAL",
                    execution_completion="INCOMPLETE",
                    semantic_outcome=None,
                    missing_next="Critic",
                    auto_target=None,
                    subject_slug=subject_slug,
                    records=records,
                )
            elif len(dev_items) == 1:
                return RunState(
                    route="BONK",
                    artifact_shape="PARTIAL",
                    execution_completion="INCOMPLETE",
                    semantic_outcome=None,
                    missing_next="Deep",
                    auto_target=None,
                    subject_slug=subject_slug,
                    records=records,
                )
            elif port_data is not None:
                return RunState(
                    route="BONK",
                    artifact_shape="PARTIAL",
                    execution_completion="INCOMPLETE",
                    semantic_outcome=None,
                    missing_next="Deep",
                    auto_target=None,
                    subject_slug=subject_slug,
                    records=records,
                )

    # 4. Check AUTO / MANUAL Single Deep Review
    auto_target = None
    if port_data:
        raw_t = port_data.get("auto_target")
        if isinstance(raw_t, dict) and raw_t.get("target_id"):
            auto_target = raw_t

    if rev_items:
        term = rev_items[0].get("terminal_state") if isinstance(rev_items[0], dict) else None
        return RunState(
            route=route,
            artifact_shape="SINGLE_DEEP_REVIEW",
            execution_completion="COMPLETE",
            semantic_outcome=term,
            missing_next=None,
            auto_target=auto_target,
            subject_slug=subject_slug,
            records=records,
        )
    elif dev_items:
        return RunState(
            route=route,
            artifact_shape="PARTIAL",
            execution_completion="INCOMPLETE",
            semantic_outcome=None,
            missing_next="Critic",
            auto_target=auto_target,
            subject_slug=subject_slug,
            records=records,
        )
    elif port_data is not None:
        return RunState(
            route=route,
            artifact_shape="PARTIAL",
            execution_completion="INCOMPLETE",
            semantic_outcome=None,
            missing_next="Deep",
            auto_target=auto_target,
            subject_slug=subject_slug,
            records=records,
        )
    elif passes_list:
        return RunState(
            route=route,
            artifact_shape="PARTIAL",
            execution_completion="INCOMPLETE",
            semantic_outcome=None,
            missing_next="Portfolio",
            auto_target=auto_target,
            subject_slug=subject_slug,
            records=records,
        )
    else:
        return RunState(
            route=route,
            artifact_shape="PARTIAL",
            execution_completion="INCOMPLETE",
            semantic_outcome=None,
            missing_next="Search",
            auto_target=None,
            subject_slug=subject_slug,
            records=records,
        )


def _load_json_safe(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def resolve_run_state_from_dir(run_dir: Union[str, Path]) -> RunState:
    """Scan a run directory and resolve its RunState."""
    rd = Path(run_dir)
    if not rd.is_dir():
        return RunState(
            route="AUTO",
            artifact_shape="PARTIAL",
            execution_completion="INCOMPLETE",
            semantic_outcome=None,
            missing_next="Search",
        )

    # Passes
    passes = []
    for p in sorted(rd.glob("candidates*.json")):
        if not p.name.endswith(".meta.json"):
            data = _load_json_safe(p)
            if data:
                passes.append((p.name, data))

    # Portfolio
    portfolio = _load_json_safe(rd / "portfolio.json")
    if portfolio is None and (rd / "selection.json").is_file():
        portfolio = _load_json_safe(rd / "selection.json")

    # Developments
    developments = []
    for p in sorted(rd.glob("development*.json")):
        if not p.name.endswith(".meta.json"):
            data = _load_json_safe(p)
            if data:
                developments.append((p.name, data))

    # Reviews
    reviews = []
    for p in sorted(rd.glob("deep-review*.json")):
        if not p.name.endswith(".meta.json"):
            data = _load_json_safe(p)
            if data:
                reviews.append((p.name, data))
    if not reviews and (rd / "review.json").is_file():
        data = _load_json_safe(rd / "review.json")
        if data:
            reviews.append(("review.json", data))

    # Comparison
    comparison = None
    for c_name in ("comparison-review-v1.json", "comparison-review.json"):
        if (rd / c_name).is_file():
            data = _load_json_safe(rd / c_name)
            if data:
                comparison = (c_name, data)
                break

    # Lever
    lever_design = _load_json_safe(rd / "design.json") or _load_json_safe(rd / "lever-design.json")
    lever_review = _load_json_safe(rd / "lever-review.json")

    # Manifest
    manifest = _load_json_safe(rd / "manifest.json")

    return resolve_run_state(
        portfolio=portfolio,
        developments=developments,
        reviews=reviews,
        comparison=comparison,
        lever_design=lever_design,
        lever_review=lever_review,
        passes=passes,
        manifest=manifest,
    )


def resolve_html_record(run_dir: Union[str, Path], subject_slug: Optional[str] = None) -> Optional[Path]:
    """Resolve authoritative rendered HTML file for reader server according to plan section 4.5:
    1. manifest records.html
    2. named run-<subject>.html, if subject known or matching run-*.html
    3. legacy run.html
    """
    rd = Path(run_dir)
    manifest_path = rd / "manifest.json"
    if manifest_path.is_file():
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(m, dict) and "records" in m and isinstance(m["records"], dict):
                rec_html = m["records"].get("html")
                if rec_html:
                    p = rd / rec_html
                    if p.is_file():
                        return p
        except Exception:
            pass

    if subject_slug:
        named = rd / f"run-{subject_slug}.html"
        if named.is_file():
            return named

    for p in sorted(rd.glob("run-*.html")):
        if p.name != "run.html" and p.is_file():
            return p

    legacy = rd / "run.html"
    if legacy.is_file():
        return legacy

    return None


def resolve_markdown_record(run_dir: Union[str, Path], subject_slug: Optional[str] = None) -> Optional[Path]:
    """Resolve authoritative rendered Markdown file according to plan section 4.4:
    1. manifest records.markdown
    2. named run-<subject>.md, if subject known or matching run-*.md
    3. legacy run.md
    """
    rd = Path(run_dir)
    manifest_path = rd / "manifest.json"
    if manifest_path.is_file():
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(m, dict) and "records" in m and isinstance(m["records"], dict):
                rec_md = m["records"].get("markdown")
                if rec_md:
                    p = rd / rec_md
                    if p.is_file():
                        return p
        except Exception:
            pass

    if subject_slug:
        named = rd / f"run-{subject_slug}.md"
        if named.is_file():
            return named

    for p in sorted(rd.glob("run-*.md")):
        if p.name != "run.md" and p.is_file():
            return p

    legacy = rd / "run.md"
    if legacy.is_file():
        return legacy

    return None
