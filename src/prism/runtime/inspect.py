"""Inspectability layer for Beerlight Runtime.
 
Provides inspection of run traces:
    beerlight inspect <run_id>
    beerlight inspect <run_id> --show-pool
    beerlight inspect <run_id> --show-judge
    beerlight inspect <run_id> --show-errors

The user must be able to recover:
    - all candidates
    - dropped candidates
    - judge decisions
    - rescue provenance
    - raw invalid output
    - repair attempt
    - abstention source

R1 semantics: inspect must distinguish three cardinality sets:
    1. Shown to user — cards actually in output.md (real shown, <=3)
    2. Kept by judge, hidden by cap — judge-kept cards beyond the cap
    3. Dropped — by judge judgments

Source of truth for "shown" is output.md / run result, not judge.json.
For legacy v0 traces: fallback — shown = output.md content if parseable,
otherwise empty shown.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import InspectResult
from .trace import read_trace_metadata, read_trace_judge, read_trace_candidates

MAX_CARDS = 3  # from plan invariant


def _parse_shown_from_output(output_path: Path) -> list[dict]:
    """Extract shown card titles from output.md.

    Parses `## Card Title` headings to identify which cards were
    actually shown to the user.  Returns list of {'title': ...} dicts.
    """
    if not output_path.exists():
        return []
    text = output_path.read_text(encoding="utf-8")
    # Match ## <title> lines that look like card headings
    # (exclude ## Run and other non-card sections)
    titles = re.findall(r'^## (.+)$', text, re.MULTILINE)
    # Filter out Run/Trace lines
    shown = []
    for t in titles:
        if t.startswith("Run:") or t.startswith("Trace:"):
            continue
        shown.append({"title": t})
    return shown


def inspect_run(run_dir: str, *, show_pool: bool = False,
                show_judge: bool = False,
                show_errors: bool = False) -> InspectResult:
    """Inspect a run trace directory.

    Returns a structured InspectResult with full provenance,
    distinguishing three cardinality sets per R1 semantics:
        shown_cards   — actually shown (source: output.md)
        kept_hidden   — judge-kept, hidden by cap
        dropped_candidates — dropped by judge

    For legacy v0 traces: shown is parsed from output.md if available;
    fallback behaviour is documented as per R1 acceptance.
    """
    trace_dir = Path(run_dir)
    result = InspectResult(run_id="", trace_dir=str(trace_dir))

    # Read metadata (handles v0 and v1)
    try:
        meta = read_trace_metadata(trace_dir)
        result.run_id = meta.run_id
        result.schema_version = meta.trace_schema_version
        result.metadata = meta.to_dict()
    except Exception as e:
        result.errors.append(f"metadata: {e}")
        result.schema_version = "unknown"

    # Read judge
    try:
        judge = read_trace_judge(trace_dir)
        result.judge_result = {
            "overall_decision": judge.overall_decision,
            "cards": [c.__dict__ for c in judge.cards],
            "judgments": [j.__dict__ for j in judge.judgments],
        }
        result.abstention_source = judge.abstention_source
    except Exception as e:
        result.errors.append(f"judge: {e}")

    # Read candidates
    try:
        result.candidates = read_trace_candidates(trace_dir)
    except Exception as e:
        result.errors.append(f"candidates: {e}")

    # --- R1: determine shown / kept-hidden / dropped ---
    # Source of truth for "shown": output.md (capped at MAX_CARDS)
    output_path = trace_dir / "output.md"
    result.shown_cards = _parse_shown_from_output(output_path)

    if result.judge_result:
        judgments = result.judge_result.get("judgments", [])
        # All judge-kept candidate IDs (keep, merge, rescue actions)
        kept_ids = {
            j["candidate_id"] for j in judgments
            if j.get("action") in ("keep", "merge", "rescue")
        }
        # Shown card titles (from output.md)
        shown_titles = {c.get("title", "") for c in result.shown_cards}

        # Kept by judge but hidden by cap: judge-kept cards NOT in output.md
        kept_hidden_candidates = [
            j for j in judgments
            if j.get("candidate_id") in kept_ids
            and j.get("action") in ("keep", "merge", "rescue")
            and j.get("candidate_id") not in [
                jj.get("candidate_id") for jj in judgments
                if jj.get("action") == "keep"
            ][:MAX_CARDS]  # first MAX_CARDS keep actions are "shown"
        ]
        # More accurate: match judge cards to shown cards by title
        judge_cards = result.judge_result.get("cards", [])
        kept_hidden_cards = []
        for jc in judge_cards:
            if jc.get("title") not in shown_titles:
                kept_hidden_cards.append(jc)
        result.kept_hidden = kept_hidden_cards

        # Dropped: judgments whose action != keep/merge/rescue
        # AND not already counted as kept_hidden
        hidden_ids = {c.get("card_id", "") for c in kept_hidden_cards}
        # Also exclude the shown cards
        result.dropped_candidates = [
            j for j in judgments
            if j.get("action") not in ("keep", "merge", "rescue")
        ]

    # Legacy alias: cards = shown_cards for backward compat
    if not result.cards:
        result.cards = result.shown_cards

    # Show pool (all candidates + judge analysis)
    if show_pool:
        pass  # Already populated in result.candidates

    # Show judge decisions
    if show_judge and result.judge_result is not None:
        pass  # Already populated

    # Show errors / raw invalid output
    if show_errors:
        raw_gen = trace_dir / "raw-generator.txt"
        if raw_gen.exists():
            result.raw_outputs["generator"] = raw_gen.read_text(encoding="utf-8")
        raw_judge = trace_dir / "raw-judge.txt"
        if raw_judge.exists():
            result.raw_outputs["judge"] = raw_judge.read_text(encoding="utf-8")

    # Rescue provenance
    if result.judge_result:
        for j in result.judge_result.get("judgments", []):
            if j.get("action") == "rescue":
                result.rescue_provenance.append(j)

    return result


def format_inspect_output(result: InspectResult) -> str:
    """Format inspection result as human-readable text.

    R1 semantics: sections distinguish Shown to user / Kept by judge,
    hidden by cap / Candidate Pool / Dropped.
    """
    lines = []
    lines.append(f"=== Beerlight Run Inspection ===")
    lines.append(f"Run ID:       {result.run_id}")
    lines.append(f"Trace dir:    {result.trace_dir}")
    lines.append(f"Schema:       {result.schema_version}")
    lines.append(f"Status:       {result.metadata.get('status', 'unknown')}")
    lines.append(f"Mode:         {result.metadata.get('mode', 'unknown')}")

    if result.abstention_source:
        lines.append(f"Abstention:   {result.abstention_source}")

    # --- Shown to user (from output.md, ≤MAX_CARDS) ---
    shown = result.shown_cards
    if shown:
        lines.append(f"\n--- Shown to user ({len(shown)}) ---")
        for card in shown:
            lines.append(f"  * {card.get('title', '(no title)')}")
    elif result.judge_result:
        lines.append(f"\n--- Shown to user (0) ---")

    # --- Kept by judge, hidden by cap ---
    if result.kept_hidden:
        lines.append(f"\n--- Kept by judge, hidden by cap ({len(result.kept_hidden)}) ---")
        for card in result.kept_hidden:
            lines.append(f"  * {card.get('title', '(no title)')}")

    # --- Candidate Pool (full) ---
    if result.candidates:
        lines.append(f"\n--- Candidate Pool ({len(result.candidates)}) ---")
        for c in result.candidates:
            cid = c.get("id", "?")
            title = c.get("title", "(no title)")
            lines.append(f"  [{cid}] {title}")

    # --- Judge Decisions ---
    judge = result.judge_result
    if judge:
        lines.append(f"\n--- Judge Decisions ---")
        lines.append(f"Overall: {judge.get('overall_decision', '?')}")
        for j in judge.get("judgments", []):
            cid = j.get("candidate_id", "?")
            action = j.get("action", "?")
            reason = j.get("reason", "")
            lines.append(f"  [{cid}] {action}: {reason}")

    # --- Dropped ---
    if result.dropped_candidates:
        lines.append(f"\n--- Dropped ({len(result.dropped_candidates)}) ---")
        for d in result.dropped_candidates:
            cid = d.get("candidate_id", "?")
            action = d.get("action", "?")
            lines.append(f"  [{cid}] {action}: {d.get('reason', '')}")

    # --- Rescue Provenance ---
    if result.rescue_provenance:
        lines.append(f"\n--- Rescue Provenance ---")
        for rp in result.rescue_provenance:
            lines.append(f"  [{rp.get('candidate_id', '?')}] rescinded")

    # --- Errors ---
    if result.errors:
        lines.append(f"\n--- Errors ---")
        for err in result.errors:
            lines.append(f"  {err}")

    # --- Raw Outputs ---
    if result.raw_outputs:
        lines.append(f"\n--- Raw Invalid Output ---")
        for key, val in result.raw_outputs.items():
            lines.append(f"  [{key}]:")
            lines.append(f"    {val[:500]}...")

    return "\n".join(lines)


def calibration_report(trace_dir: str) -> str:
    """Calibration: show 'strong dropped' candidates (potential false negatives).

    Finds candidates where:
        - Judge action is 'drop' or 'merge'
        - BUT judge marked novelty='real' AND fidelity='grounded'

    These are candidates that the judge considered genuinely novel AND
    well-grounded in the source text, yet still dropped — potential
    false negatives that may indicate over-aggressive judging.

    Works on both v0 and v1 traces.
    """
    from pathlib import Path

    td = Path(trace_dir)
    lines: list[str] = []
    lines.append(f"=== Judge Calibration: Strong Dropped ===")
    lines.append(f"Trace dir: {td}")
    lines.append(f"Rule: action in (drop, merge) AND novelty=real AND fidelity=grounded")
    lines.append("")

    # Read judge.json
    judge_path = td / "judge.json"
    if not judge_path.exists():
        lines.append("No judge.json found — nothing to calibrate against.")
        return "\n".join(lines)

    try:
        judge = json.loads(judge_path.read_text(encoding="utf-8"))
    except Exception as e:
        lines.append(f"Error reading judge.json: {e}")
        return "\n".join(lines)

    judgments = judge.get("judgments", [])
    if not judgments:
        lines.append("No judgments found in trace — nothing to calibrate against.")
        return "\n".join(lines)

    # Find strong dropped: drop|merge + novelty=real + fidelity=grounded
    strong_dropped = []
    for j in judgments:
        action = j.get("action", "")
        novelty = j.get("novelty", "")
        fidelity = j.get("fidelity", "")
        if action in ("drop", "merge") and novelty == "real" and fidelity == "grounded":
            strong_dropped.append(j)

    if not strong_dropped:
        lines.append("No strong dropped candidates found. (All drops were low-novelty or low-fidelity — judge is behaving as expected.)")
        return "\n".join(lines)

    lines.append(f"Found {len(strong_dropped)} potential false negative(s):")
    lines.append("")
    lines.append(f"{'CANDIDATE':<16} {'ACTION':<10} {'NOVELTY':<10} {'FIDELITY':<12} REASON")
    lines.append("-" * 90)
    for j in strong_dropped:
        cid = j.get("candidate_id", "?")[:14]
        action = j.get("action", "?")
        novelty = j.get("novelty", "?")
        fidelity = j.get("fidelity", "?")
        reason = j.get("reason", "")
        lines.append(f"{cid:<16} {action:<10} {novelty:<10} {fidelity:<12} {reason}")

    lines.append("")
    lines.append("NOTE: These are candidates the judge found genuinely novel and")
    lines.append("well-grounded yet still dropped. They may deserve manual review.")

    return "\n".join(lines)
