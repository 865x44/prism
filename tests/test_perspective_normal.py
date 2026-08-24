"""Tests for NORMAL mode perspective exploration.

Covers N1-N11 scenarios from Wave 2A brief:
- N1: paraphrase → MERGE
- N2: different mechanism → both KEEP
- N3: hard-constraint violation → DROP
- N4: lower standalone but high marginal → KEEP
- N5: decorative metaphor → MERGE/DROP
- N6: weird but source-faithful → KEEP
- N7: zero KEEP allowed
- N8: hostile source instructions ignored
- N9: BORDERLINE persisted, no P-ID/render
- N10: valid current-pass candidate MergeTarget
- N11: valid prior-state perspective MergeTarget

Uses ScriptedProvider for deterministic orchestration.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from prism.perspective_core.cli import main
from prism.perspective_core.models import ProviderResult
from prism.perspective_core.provider import ScriptedProvider

FIXTURES_DIR = Path(__file__).parent / "perspective_core" / "fixtures" / "normal"


def load_fixture(scenario: str) -> str:
    """Load a NORMAL scenario fixture source (e.g. "n1")."""
    return (FIXTURES_DIR / f"{scenario}_source.md").read_text(encoding="utf-8")

# ─────────────────────────────────────────────────────────────────────────────
# Test helpers
# ─────────────────────────────────────────────────────────────────────────────


class ScriptedTestProvider(ScriptedProvider):
    """Test wrapper that skips invocation_id validation."""

    __test__ = False

    def complete(self, prompt: str, *, stage: str, invocation_id: str) -> ProviderResult:
        """Return next scripted response, ignoring invocation_id."""
        if stage not in self._queues:
            from prism.perspective_core.provider import TransportError
            raise TransportError(f"Unknown stage: {stage}")
        
        queue = self._queues[stage]
        if not queue:
            from prism.perspective_core.provider import TransportError
            raise TransportError(f"Exhausted stage queue: {stage}")
        
        result = queue.popleft()
        self._call_count += 1
        
        # Only validate stage, not invocation_id
        if result.stage != stage:
            from prism.perspective_core.provider import TransportError
            raise TransportError(f"Stage mismatch: expected {result.stage}, got {stage}")
        
        return result


def make_scripted_factory(responses_by_stage: dict[str, list[ProviderResult]]):
    """Create a provider factory for CLI injection."""

    def factory():
        return ScriptedTestProvider(responses_by_stage)

    return factory


def make_generate_response(
    diagnosis: dict[str, Any], candidates: list[dict[str, Any]], invocation_id: str = "gen-1"
) -> ProviderResult:
    """Create a Call A response."""
    return ProviderResult(
        invocation_id=invocation_id,
        stage="EXPLORE_GENERATE",
        raw_text=json.dumps({"diagnosis": diagnosis, "candidates": candidates}),
        model="test-model",
        transport="scripted",
        duration_ms=100,
        exit_code=0,
    )


def make_select_response(selections: list[dict[str, Any]], invocation_id: str = "sel-1") -> ProviderResult:
    """Create a Call B response."""
    return ProviderResult(
        invocation_id=invocation_id,
        stage="EXPLORE_SELECT",
        raw_text=json.dumps(selections),
        model="test-model",
        transport="scripted",
        duration_ms=100,
        exit_code=0,
    )


def make_candidate(
    candidate_id: str = "C1",
    mechanism: str = "test mechanism",
    central_problem: str = "test problem",
    **overrides: Any,
) -> dict[str, Any]:
    """Create a minimal candidate structure."""
    base = {
        "semantic_core": {
            "central_problem": central_problem,
            "mechanism": mechanism,
            "load_bearing_claim": "test claim",
            "central_object": None,
            "unit_of_analysis": None,
            "system_boundary": None,
            "agency_model": None,
            "temporal_logic": None,
            "key_constraint": None,
            "downstream_consequences": ["consequence 1"],
        },
        "preserved": ["preserved element"],
        "default_frame": "default framing",
        "blind_spot": "blind spot",
        "operator_ids": [],
        "shift": "structural shift",
        "perspective": "perspective statement",
        "new_consequences": ["new consequence"],
        "return_path": {
            "dimension_changed": "mechanism",
            "consequence_chain": ["step 1", "step 2"],
            "why_it_matters": "matters because",
        },
        "epistemics": {
            "supported": ["supported fact"],
            "inferred": [],
            "speculative": [],
            "unknown": [],
            "break_condition": ["breaks when X"],
        },
    }
    base.update(overrides)
    return base


def make_selection(
    candidate_id: str,
    disposition: str = "KEEP",
    merge_target: dict[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    """Create a minimal selection structure."""
    base = {
        "candidate_id": candidate_id,
        "admissible": True,
        "constraint_failures": [],
        "structurally_distinct": True,
        "novelty_dimensions": ["mechanism"],
        "nearest_candidate_id": None,
        "nearest_existing_p_id": None,
        "standalone_quality": "strong",
        "marginal_contribution": "high",
        "disposition": disposition,
        "merge_target": merge_target,
        "reason": "test reason",
    }
    base.update(overrides)
    return base


def make_diagnosis() -> dict[str, Any]:
    """Create a minimal diagnosis."""
    return {
        "central_problem": "test central problem",
        "search_profile": "test search profile",
        "priority_dimensions": ["mechanism", "boundary"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# N1: Paraphrase → MERGE
# ─────────────────────────────────────────────────────────────────────────────


def test_n1_paraphrase_merge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """N1: Obvious paraphrase should be MERGE."""
    monkeypatch.chdir(tmp_path)

    source_text = load_fixture("n1")
    source_file = tmp_path / "source.md"
    source_file.write_text(source_text)

    # Two candidates: original and paraphrase
    candidates = [
        make_candidate("C1", mechanism="market competition", central_problem="resource allocation"),
        make_candidate(
            "C2",
            mechanism="competitive markets",  # Same mechanism, different words
            central_problem="allocating resources",
        ),
    ]

    selections = [
        make_selection("C1", disposition="KEEP"),
        make_selection(
            "C2",
            disposition="MERGE",
            merge_target={"kind": "candidate", "target_id": "C1"},
            structurally_distinct=False,
            reason="Paraphrase of C1, same mechanism",
        ),
    ]

    responses = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
        "EXPLORE_SELECT": [make_select_response(selections)],
    }

    factory = make_scripted_factory(responses)
    exit_code = main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Analyse economic systems",
            "--mode",
            "normal",
            "--session",
            "test-n1",
            "--trace-root",
            str(tmp_path / "traces"),
        ],
        provider_factory=factory,
    )

    assert exit_code == 0

    # Verify only C1 kept
    session_file = tmp_path / "prism-sessions" / "perspective-core" / "test-n1" / "session.json"
    assert session_file.exists()
    session_data = json.loads(session_file.read_text())

    assert len(session_data["perspectives"]) == 1
    assert "P1" in session_data["perspectives"]

    # Verify MERGE persisted in pass record
    assert len(session_data["passes"]) == 1
    pass_record = session_data["passes"][0]
    assert len(pass_record["selections"]) == 2
    merge_sel = next(s for s in pass_record["selections"] if s["candidate_id"] == "C2")
    assert merge_sel["disposition"] == "MERGE"
    assert merge_sel["merge_target"]["target_id"] == "C1"


# ─────────────────────────────────────────────────────────────────────────────
# N2: Different mechanism → both KEEP
# ─────────────────────────────────────────────────────────────────────────────


def test_n2_different_mechanism_both_keep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """N2: Same topic but different mechanism → both KEEP."""
    monkeypatch.chdir(tmp_path)

    source_text = load_fixture("n2")
    source_file = tmp_path / "source.md"
    source_file.write_text(source_text)

    candidates = [
        make_candidate("C1", mechanism="hierarchical authority", central_problem="decision coordination"),
        make_candidate("C2", mechanism="consensus deliberation", central_problem="decision coordination"),
    ]

    selections = [
        make_selection("C1", disposition="KEEP"),
        make_selection("C2", disposition="KEEP"),
    ]

    responses = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
        "EXPLORE_SELECT": [make_select_response(selections)],
    }

    factory = make_scripted_factory(responses)
    exit_code = main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Analyse decision-making",
            "--mode",
            "normal",
            "--session",
            "test-n2",
            "--trace-root",
            str(tmp_path / "traces"),
        ],
        provider_factory=factory,
    )

    assert exit_code == 0

    session_file = tmp_path / "prism-sessions" / "perspective-core" / "test-n2" / "session.json"
    session_data = json.loads(session_file.read_text())

    # Both kept with sequential P-IDs
    assert len(session_data["perspectives"]) == 2
    assert "P1" in session_data["perspectives"]
    assert "P2" in session_data["perspectives"]

    # Verify P-IDs assigned in candidate order
    p1_candidate = session_data["perspectives"]["P1"]["identity"]["candidate_id"]
    p2_candidate = session_data["perspectives"]["P2"]["identity"]["candidate_id"]
    assert p1_candidate == "C1"
    assert p2_candidate == "C2"


# ─────────────────────────────────────────────────────────────────────────────
# N3: Hard-constraint violation → DROP
# ─────────────────────────────────────────────────────────────────────────────


def test_n3_constraint_violation_drop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """N3: Hard-constraint violation → Call B DROP."""
    monkeypatch.chdir(tmp_path)

    source_text = load_fixture("n3")
    source_file = tmp_path / "source.md"
    source_file.write_text(source_text)

    candidates = [
        make_candidate("C1", mechanism="regulated banking"),
        make_candidate("C2", mechanism="unregulated shadow banking"),
    ]

    selections = [
        make_selection("C1", disposition="KEEP"),
        make_selection(
            "C2",
            disposition="DROP",
            admissible=False,
            constraint_failures=["violates no-unregulated-systems constraint"],
            reason="Violates hard constraint",
        ),
    ]

    responses = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
        "EXPLORE_SELECT": [make_select_response(selections)],
    }

    factory = make_scripted_factory(responses)

    # Pre-create session with hard constraint
    session_dir = tmp_path / "prism-sessions" / "perspective-core" / "test-n3"
    session_dir.mkdir(parents=True)
    session_data = {
        "session_id": "test-n3",
        "source_hash": None,  # Will be computed
        "objective": "Analyse financial systems",
        "constraint_ledger": {
            "entries": [
                {
                    "constraint_id": "no-unregulated",
                    "value": "No unregulated financial systems",
                    "kind": "hard",
                    "provenance_turn": None,
                    "status": "active",
                }
            ]
        },
        "next_p_number": 1,
        "perspectives": {},
        "passes": [],
        "deep_runs": [],
    }

    # Compute source hash from the exact fixture text handed to the CLI
    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    session_data["source_hash"] = source_hash

    (session_dir / "session.json").write_text(json.dumps(session_data))
    (session_dir / "source.md").write_text(source_text, encoding="utf-8")

    exit_code = main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Analyse financial systems",
            "--mode",
            "normal",
            "--session",
            "test-n3",
            "--trace-root",
            str(tmp_path / "traces"),
        ],
        provider_factory=factory,
    )

    assert exit_code == 0

    session_file = session_dir / "session.json"
    session_data = json.loads(session_file.read_text())

    # Only C1 kept
    assert len(session_data["perspectives"]) == 1
    assert "P1" in session_data["perspectives"]

    # DROP persisted
    pass_record = session_data["passes"][0]
    drop_sel = next(s for s in pass_record["selections"] if s["candidate_id"] == "C2")
    assert drop_sel["disposition"] == "DROP"
    assert drop_sel["admissible"] is False
    assert len(drop_sel["constraint_failures"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# N4: Lower standalone but high marginal → KEEP
# ─────────────────────────────────────────────────────────────────────────────


def test_n4_low_standalone_high_marginal_keep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """N4: Lower standalone quality but high marginal contribution → KEEP."""
    monkeypatch.chdir(tmp_path)

    source_text = load_fixture("n4")
    source_file = tmp_path / "source.md"
    source_file.write_text(source_text)

    candidates = [
        make_candidate("C1", mechanism="microservices"),
        make_candidate(
            "C2",
            mechanism="event-driven coupling",
            central_problem="service communication",
        ),
    ]

    selections = [
        make_selection("C1", disposition="KEEP"),
        make_selection(
            "C2",
            disposition="KEEP",
            standalone_quality="borderline",  # Lower standalone
            marginal_contribution="high",  # But high marginal
            reason="Adds unique coupling dimension despite weaker standalone",
        ),
    ]

    responses = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
        "EXPLORE_SELECT": [make_select_response(selections)],
    }

    factory = make_scripted_factory(responses)
    exit_code = main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Analyse architecture",
            "--mode",
            "normal",
            "--session",
            "test-n4",
            "--trace-root",
            str(tmp_path / "traces"),
        ],
        provider_factory=factory,
    )

    assert exit_code == 0

    session_file = tmp_path / "prism-sessions" / "perspective-core" / "test-n4" / "session.json"
    session_data = json.loads(session_file.read_text())

    # Both kept
    assert len(session_data["perspectives"]) == 2


# ─────────────────────────────────────────────────────────────────────────────
# N5: Decorative metaphor → MERGE/DROP
# ─────────────────────────────────────────────────────────────────────────────


def test_n5_decorative_metaphor_drop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """N5: Decorative metaphor (same mechanism, different words) → DROP."""
    monkeypatch.chdir(tmp_path)

    source_text = load_fixture("n5")
    source_file = tmp_path / "source.md"
    source_file.write_text(source_text)

    candidates = [
        make_candidate("C1", mechanism="hierarchical reporting"),
        make_candidate(
            "C2",
            mechanism="hierarchical reporting",  # Same mechanism
            central_problem="team coordination",
            shift="Metaphor: team as orchestra",  # Just different metaphor
        ),
    ]

    selections = [
        make_selection("C1", disposition="KEEP"),
        make_selection(
            "C2",
            disposition="DROP",
            structurally_distinct=False,
            marginal_contribution="none",
            reason="Decorative metaphor, same mechanism as C1",
        ),
    ]

    responses = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
        "EXPLORE_SELECT": [make_select_response(selections)],
    }

    factory = make_scripted_factory(responses)
    exit_code = main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Analyse management",
            "--mode",
            "normal",
            "--session",
            "test-n5",
            "--trace-root",
            str(tmp_path / "traces"),
        ],
        provider_factory=factory,
    )

    assert exit_code == 0

    session_file = tmp_path / "prism-sessions" / "perspective-core" / "test-n5" / "session.json"
    session_data = json.loads(session_file.read_text())

    # Only C1 kept
    assert len(session_data["perspectives"]) == 1


# ─────────────────────────────────────────────────────────────────────────────
# N6: Weird but source-faithful → KEEP
# ─────────────────────────────────────────────────────────────────────────────


def test_n6_weird_but_faithful_keep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """N6: Weird but source-faithful perspective → KEEP."""
    monkeypatch.chdir(tmp_path)

    source_text = load_fixture("n6")
    source_file = tmp_path / "source.md"
    source_file.write_text(source_text)

    candidates = [
        make_candidate(
            "C1",
            mechanism="induced demand feedback loop",
            central_problem="traffic congestion",
            shift="More roads create more traffic",
        ),
    ]

    selections = [
        make_selection(
            "C1",
            disposition="KEEP",
            reason="Counterintuitive but grounded in source data",
        ),
    ]

    responses = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
        "EXPLORE_SELECT": [make_select_response(selections)],
    }

    factory = make_scripted_factory(responses)
    exit_code = main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Analyse traffic",
            "--mode",
            "normal",
            "--session",
            "test-n6",
            "--trace-root",
            str(tmp_path / "traces"),
        ],
        provider_factory=factory,
    )

    assert exit_code == 0

    session_file = tmp_path / "prism-sessions" / "perspective-core" / "test-n6" / "session.json"
    session_data = json.loads(session_file.read_text())

    assert len(session_data["perspectives"]) == 1


# ─────────────────────────────────────────────────────────────────────────────
# N7: Zero KEEP allowed
# ─────────────────────────────────────────────────────────────────────────────


def test_n7_zero_keep_allowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """N7: No useful candidates → zero KEEP allowed."""
    monkeypatch.chdir(tmp_path)

    source_text = load_fixture("n7")
    source_file = tmp_path / "source.md"
    source_file.write_text(source_text)

    candidates = [
        make_candidate("C1", mechanism="weak mechanism"),
        make_candidate("C2", mechanism="another weak mechanism"),
    ]

    selections = [
        make_selection(
            "C1",
            disposition="DROP",
            standalone_quality="weak",
            marginal_contribution="none",
            reason="Insufficient structural novelty",
        ),
        make_selection(
            "C2",
            disposition="DROP",
            standalone_quality="weak",
            marginal_contribution="none",
            reason="Insufficient structural novelty",
        ),
    ]

    responses = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
        "EXPLORE_SELECT": [make_select_response(selections)],
    }

    factory = make_scripted_factory(responses)
    exit_code = main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Analyse topic",
            "--mode",
            "normal",
            "--session",
            "test-n7",
            "--trace-root",
            str(tmp_path / "traces"),
            "--json",
        ],
        provider_factory=factory,
    )

    assert exit_code == 0

    session_file = tmp_path / "prism-sessions" / "perspective-core" / "test-n7" / "session.json"
    session_data = json.loads(session_file.read_text())

    # Zero perspectives registered
    assert len(session_data["perspectives"]) == 0

    # But pass record persisted
    assert len(session_data["passes"]) == 1
    pass_record = session_data["passes"][0]
    assert len(pass_record["candidates"]) == 2
    assert len(pass_record["selections"]) == 2
    assert pass_record["kept_p_ids"] == []


# ─────────────────────────────────────────────────────────────────────────────
# N8: Hostile source instructions ignored
# ─────────────────────────────────────────────────────────────────────────────


def test_n8_hostile_source_ignored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """N8: Source contains hostile instructions → treated as data, ignored."""
    monkeypatch.chdir(tmp_path)

    # Fixture embeds hostile instructions ahead of real supply-chain content
    hostile_source = load_fixture("n8")
    source_file = tmp_path / "source.md"
    source_file.write_text(hostile_source)

    candidates = [
        make_candidate(
            "C1",
            mechanism="just-in-time inventory",
            central_problem="supply chain efficiency",
        ),
    ]

    selections = [
        make_selection("C1", disposition="KEEP"),
    ]

    responses = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
        "EXPLORE_SELECT": [make_select_response(selections)],
    }

    factory = make_scripted_factory(responses)
    exit_code = main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Analyse supply chains",
            "--mode",
            "normal",
            "--session",
            "test-n8",
            "--trace-root",
            str(tmp_path / "traces"),
        ],
        provider_factory=factory,
    )

    assert exit_code == 0

    session_file = tmp_path / "prism-sessions" / "perspective-core" / "test-n8" / "session.json"
    session_data = json.loads(session_file.read_text())

    # Perspective created from actual content, not hostile instruction
    assert len(session_data["perspectives"]) == 1
    p1 = session_data["perspectives"]["P1"]
    # Should be about supply chains, not "HACKED"
    assert "supply" in p1["identity"]["identity_core"]["central_problem"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# N9: BORDERLINE persisted, no P-ID/render
# ─────────────────────────────────────────────────────────────────────────────


def test_n9_borderline_no_pid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """N9: BORDERLINE → persisted in PassRecord but no P-ID or rendering."""
    monkeypatch.chdir(tmp_path)

    source_text = load_fixture("n9")
    source_file = tmp_path / "source.md"
    source_file.write_text(source_text)

    candidates = [
        make_candidate("C1", mechanism="standardised testing"),
        make_candidate(
            "C2",
            mechanism="portfolio assessment",
        ),
    ]

    selections = [
        make_selection("C1", disposition="KEEP"),
        make_selection(
            "C2",
            disposition="BORDERLINE",
            standalone_quality="borderline",
            marginal_contribution="low",
            reason="Borderline quality, kept for future analysis but not shown",
        ),
    ]

    responses = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
        "EXPLORE_SELECT": [make_select_response(selections)],
    }

    factory = make_scripted_factory(responses)
    exit_code = main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Analyse education",
            "--mode",
            "normal",
            "--session",
            "test-n9",
            "--trace-root",
            str(tmp_path / "traces"),
        ],
        provider_factory=factory,
    )

    assert exit_code == 0

    session_file = tmp_path / "prism-sessions" / "perspective-core" / "test-n9" / "session.json"
    session_data = json.loads(session_file.read_text())

    # Only C1 gets P-ID
    assert len(session_data["perspectives"]) == 1
    assert "P1" in session_data["perspectives"]

    # BORDERLINE persisted in pass record
    pass_record = session_data["passes"][0]
    borderline_sel = next(s for s in pass_record["selections"] if s["candidate_id"] == "C2")
    assert borderline_sel["disposition"] == "BORDERLINE"

    # No P-ID for BORDERLINE
    assert borderline_sel["candidate_id"] not in [
        p["identity"]["candidate_id"] for p in session_data["perspectives"].values()
    ]


# ─────────────────────────────────────────────────────────────────────────────
# N10: Valid current-pass candidate MergeTarget
# ─────────────────────────────────────────────────────────────────────────────


def test_n10_current_pass_merge_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """N10: MERGE target is valid current-pass candidate."""
    monkeypatch.chdir(tmp_path)

    source_text = load_fixture("n10")
    source_file = tmp_path / "source.md"
    source_file.write_text(source_text)

    candidates = [
        make_candidate("C1", mechanism="price signalling"),
        make_candidate("C2", mechanism="information asymmetry"),
        make_candidate("C3", mechanism="price signalling variant"),
    ]

    selections = [
        make_selection("C1", disposition="KEEP"),
        make_selection("C2", disposition="KEEP"),
        make_selection(
            "C3",
            disposition="MERGE",
            merge_target={"kind": "candidate", "target_id": "C1"},
            reason="Variant of C1 mechanism",
        ),
    ]

    responses = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
        "EXPLORE_SELECT": [make_select_response(selections)],
    }

    factory = make_scripted_factory(responses)
    exit_code = main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Analyse markets",
            "--mode",
            "normal",
            "--session",
            "test-n10",
            "--trace-root",
            str(tmp_path / "traces"),
        ],
        provider_factory=factory,
    )

    assert exit_code == 0

    session_file = tmp_path / "prism-sessions" / "perspective-core" / "test-n10" / "session.json"
    session_data = json.loads(session_file.read_text())

    # C1 and C2 kept
    assert len(session_data["perspectives"]) == 2

    # MERGE target validated
    pass_record = session_data["passes"][0]
    merge_sel = next(s for s in pass_record["selections"] if s["candidate_id"] == "C3")
    assert merge_sel["disposition"] == "MERGE"
    assert merge_sel["merge_target"]["kind"] == "candidate"
    assert merge_sel["merge_target"]["target_id"] == "C1"


# ─────────────────────────────────────────────────────────────────────────────
# N11: Valid prior-state perspective MergeTarget
# ─────────────────────────────────────────────────────────────────────────────


def test_n11_prior_perspective_merge_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """N11: MERGE target is valid prior-state perspective P-ID."""
    monkeypatch.chdir(tmp_path)

    source_text = load_fixture("n11")
    source_file = tmp_path / "source.md"
    source_file.write_text(source_text)

    # First pass: create P1
    candidates_pass1 = [
        make_candidate("C1", mechanism="explicit knowledge transfer"),
    ]
    selections_pass1 = [
        make_selection("C1", disposition="KEEP"),
    ]
    responses_pass1 = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates_pass1, "gen-1")],
        "EXPLORE_SELECT": [make_select_response(selections_pass1, "sel-1")],
    }

    factory_pass1 = make_scripted_factory(responses_pass1)
    exit_code = main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Analyse learning",
            "--mode",
            "normal",
            "--session",
            "test-n11",
            "--trace-root",
            str(tmp_path / "traces"),
        ],
        provider_factory=factory_pass1,
    )
    assert exit_code == 0

    # Second pass: C2 merges into P1
    candidates_pass2 = [
        make_candidate("C1", mechanism="tacit knowledge sharing"),
    ]
    selections_pass2 = [
        make_selection(
            "C1",
            disposition="MERGE",
            merge_target={"kind": "perspective", "target_id": "P1"},
            reason="Extends P1 with tacit dimension",
        ),
    ]
    responses_pass2 = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates_pass2, "gen-2")],
        "EXPLORE_SELECT": [make_select_response(selections_pass2, "sel-2")],
    }

    factory_pass2 = make_scripted_factory(responses_pass2)
    exit_code = main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Analyse learning",
            "--mode",
            "normal",
            "--session",
            "test-n11",
            "--trace-root",
            str(tmp_path / "traces"),
        ],
        provider_factory=factory_pass2,
    )
    assert exit_code == 0

    session_file = tmp_path / "prism-sessions" / "perspective-core" / "test-n11" / "session.json"
    session_data = json.loads(session_file.read_text())

    # Still only P1 (no new KEEP)
    assert len(session_data["perspectives"]) == 1
    assert "P1" in session_data["perspectives"]

    # Two passes recorded
    assert len(session_data["passes"]) == 2

    # Second pass MERGE target validated
    pass2 = session_data["passes"][1]
    merge_sel = pass2["selections"][0]
    assert merge_sel["disposition"] == "MERGE"
    assert merge_sel["merge_target"]["kind"] == "perspective"
    assert merge_sel["merge_target"]["target_id"] == "P1"


# ─────────────────────────────────────────────────────────────────────────────
# Schema repair tests
# ─────────────────────────────────────────────────────────────────────────────


def test_schema_repair_generate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Primary Call A fails, repair succeeds."""
    monkeypatch.chdir(tmp_path)

    source_file = tmp_path / "source.md"
    source_file.write_text("Source material.")

    # Malformed primary response
    bad_generate = ProviderResult(
        invocation_id="gen-1",
        stage="EXPLORE_GENERATE",
        raw_text='{"diagnosis": {"central_problem": "test"}}',  # Missing fields
        model="test-model",
        transport="scripted",
        duration_ms=100,
        exit_code=0,
    )

    # Valid repair response (every repair is a separate counted invocation stage)
    good_generate = ProviderResult(
        invocation_id="gen-repair-1",
        stage="SCHEMA_REPAIR:EXPLORE_GENERATE",
        raw_text=json.dumps({"diagnosis": make_diagnosis(), "candidates": [make_candidate()]}),
        model="test-model",
        transport="scripted",
        duration_ms=100,
        exit_code=0,
    )

    selections = [make_selection("C1", disposition="KEEP")]

    responses = {
        "EXPLORE_GENERATE": [bad_generate],
        "SCHEMA_REPAIR:EXPLORE_GENERATE": [good_generate],
        "EXPLORE_SELECT": [make_select_response(selections)],
    }

    factory = make_scripted_factory(responses)
    exit_code = main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Test repair",
            "--mode",
            "normal",
            "--session",
            "test-repair-gen",
            "--trace-root",
            str(tmp_path / "traces"),
        ],
        provider_factory=factory,
    )

    assert exit_code == 0

    # Verify repair was invoked
    trace_dir = tmp_path / "traces"
    run_dirs = list(trace_dir.glob("*"))
    assert len(run_dirs) == 1

    invocations_file = run_dirs[0] / "provider-invocations.json"
    invocations = json.loads(invocations_file.read_text())

    # Should have repair invocation
    repair_invocations = [i for i in invocations if i["stage"].startswith("SCHEMA_REPAIR:")]
    assert len(repair_invocations) == 1
    assert repair_invocations[0]["stage"] == "SCHEMA_REPAIR:EXPLORE_GENERATE"


def test_schema_repair_select(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Primary Call B fails, repair succeeds."""
    monkeypatch.chdir(tmp_path)

    source_file = tmp_path / "source.md"
    source_file.write_text("Source material.")

    candidates = [make_candidate()]

    # Malformed primary selection
    bad_select = ProviderResult(
        invocation_id="sel-1",
        stage="EXPLORE_SELECT",
        raw_text='[{"candidate_id": "C1"}]',  # Missing required fields
        model="test-model",
        transport="scripted",
        duration_ms=100,
        exit_code=0,
    )

    # Valid repair (repair is its own counted invocation stage)
    good_select = ProviderResult(
        invocation_id="sel-repair-1",
        stage="SCHEMA_REPAIR:EXPLORE_SELECT",
        raw_text=json.dumps([make_selection("C1", disposition="KEEP")]),
        model="test-model",
        transport="scripted",
        duration_ms=100,
        exit_code=0,
    )

    responses = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
        "EXPLORE_SELECT": [bad_select],
        "SCHEMA_REPAIR:EXPLORE_SELECT": [good_select],
    }

    factory = make_scripted_factory(responses)
    exit_code = main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Test repair",
            "--mode",
            "normal",
            "--session",
            "test-repair-sel",
            "--trace-root",
            str(tmp_path / "traces"),
        ],
        provider_factory=factory,
    )

    assert exit_code == 0

    # Verify repair was invoked
    trace_dir = tmp_path / "traces"
    run_dirs = list(trace_dir.glob("*"))
    assert len(run_dirs) == 1

    invocations_file = run_dirs[0] / "provider-invocations.json"
    invocations = json.loads(invocations_file.read_text())

    repair_invocations = [i for i in invocations if i["stage"].startswith("SCHEMA_REPAIR:")]
    assert len(repair_invocations) == 1
    assert repair_invocations[0]["stage"] == "SCHEMA_REPAIR:EXPLORE_SELECT"


# ─────────────────────────────────────────────────────────────────────────────
# Candidate budget enforcement
# ─────────────────────────────────────────────────────────────────────────────


def test_candidate_budget_enforced(tmp_path: Path):
    """Candidate budget is upper bound; excess candidates truncated before Call B."""
    from prism.perspective_core.explore import run_explore
    from prism.perspective_core.models import PerspectiveRequest
    from prism.perspective_core.session import SessionStore

    provider = ScriptedTestProvider(
        {
            "EXPLORE_GENERATE": [
                make_generate_response(
                    make_diagnosis(),
                    [make_candidate(f"C{i}") for i in range(1, 6)],
                )
            ],
            "EXPLORE_SELECT": [
                make_select_response(
                    [make_selection(f"C{i}", disposition="KEEP") for i in range(1, 4)]
                )
            ],
        }
    )

    run_explore(
        PerspectiveRequest(
            source="Source material.",
            objective="Test budget",
            mode="normal",
            session_id="test-budget",
            candidate_budget=3,
        ),
        session_store=SessionStore(tmp_path / "prism-sessions" / "perspective-core"),
        provider=provider,
        trace_root=tmp_path / "traces",
    )

    session_file = tmp_path / "prism-sessions" / "perspective-core" / "test-budget" / "session.json"
    session_data = json.loads(session_file.read_text())

    pass_record = session_data["passes"][0]
    assert len(pass_record["candidates"]) == 3
    assert [c["candidate_id"] for c in pass_record["candidates"]] == ["C1", "C2", "C3"]
    assert len(pass_record["selections"]) == 3
    assert pass_record["kept_p_ids"] == ["P1", "P2", "P3"]
    provider.assert_exhausted()


# ─────────────────────────────────────────────────────────────────────────────
# Trace persistence
# ─────────────────────────────────────────────────────────────────────────────


def test_trace_persistence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify all required trace files are written."""
    monkeypatch.chdir(tmp_path)

    source_file = tmp_path / "source.md"
    source_file.write_text("Source material.")

    candidates = [make_candidate()]
    selections = [make_selection("C1", disposition="KEEP")]

    responses = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
        "EXPLORE_SELECT": [make_select_response(selections)],
    }

    factory = make_scripted_factory(responses)
    main(
        [
            "run",
            "--source-file",
            str(source_file),
            "--task",
            "Test trace",
            "--mode",
            "normal",
            "--session",
            "test-trace",
            "--trace-root",
            str(tmp_path / "traces"),
        ],
        provider_factory=factory,
    )

    trace_dir = tmp_path / "traces"
    run_dirs = list(trace_dir.glob("*"))
    assert len(run_dirs) == 1

    run_dir = run_dirs[0]

    # Required trace files
    required_files = [
        "request.json",
        "constraints.json",
        "diagnosis.json",
        "candidates.json",
        "selection.json",
        "validation.json",
        "result.json",
        "session-before.json",
        "session-after.json",
        "provider-invocations.json",
        "explore_generate-response.json",
        "explore_select-response.json",
    ]

    for filename in required_files:
        assert (run_dir / filename).exists(), f"Missing trace file: {filename}"


# ─────────────────────────────────────────────────────────────────────────────
# ScriptedProvider queue exhaustion
# ─────────────────────────────────────────────────────────────────────────────


def test_scripted_provider_exhausted(tmp_path: Path):
    """All scripted responses must be consumed."""
    source_file = tmp_path / "source.md"
    source_file.write_text("Source material.")

    candidates = [make_candidate()]
    selections = [make_selection("C1", disposition="KEEP")]

    # Extra unused response
    extra_response = make_generate_response(make_diagnosis(), [], "unused")

    responses = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates), extra_response],
        "EXPLORE_SELECT": [make_select_response(selections)],
    }

    provider = ScriptedTestProvider(responses)

    # Run manually to check exhaustion
    from prism.perspective_core.explore import run_explore
    from prism.perspective_core.models import PerspectiveRequest
    from prism.perspective_core.session import SessionStore

    session_store = SessionStore(tmp_path / "prism-sessions" / "perspective-core")
    request = PerspectiveRequest(
        source="Source material.",
        objective="Test",
        mode="normal",
        session_id="test-exhaust",
    )

    run_explore(
        request,
        session_store=session_store,
        provider=provider,
        trace_root=tmp_path / "traces",
    )

    # Should raise because extra response was not consumed
    with pytest.raises(AssertionError, match="Unused scripted responses"):
        provider.assert_exhausted()


# ─────────────────────────────────────────────────────────────────────────────
# Outcome determination
# ─────────────────────────────────────────────────────────────────────────────


def test_outcome_no_territory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """No KEEP → NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS."""
    monkeypatch.chdir(tmp_path)

    source_file = tmp_path / "source.md"
    source_file.write_text("Source material.")

    candidates = [make_candidate()]
    selections = [
        make_selection(
            "C1",
            disposition="DROP",
            standalone_quality="weak",
            marginal_contribution="none",
        )
    ]

    responses = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
        "EXPLORE_SELECT": [make_select_response(selections)],
    }

    factory = make_scripted_factory(responses)

    # Capture JSON output
    import io
    import sys

    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    try:
        exit_code = main(
            [
                "run",
                "--source-file",
                str(source_file),
                "--task",
                "Test outcome",
                "--mode",
                "normal",
                "--session",
                "test-outcome",
                "--trace-root",
                str(tmp_path / "traces"),
                "--json",
            ],
            provider_factory=factory,
        )
    finally:
        sys.stdout = old_stdout

    assert exit_code == 0

    result = json.loads(captured.getvalue())
    assert result["outcome"] == "NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS"
    assert result["kept"] == []


def test_outcome_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """At least one KEEP → OK."""
    monkeypatch.chdir(tmp_path)

    source_file = tmp_path / "source.md"
    source_file.write_text("Source material.")

    candidates = [make_candidate()]
    selections = [make_selection("C1", disposition="KEEP")]

    responses = {
        "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
        "EXPLORE_SELECT": [make_select_response(selections)],
    }

    factory = make_scripted_factory(responses)

    import io
    import sys

    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    try:
        exit_code = main(
            [
                "run",
                "--source-file",
                str(source_file),
                "--task",
                "Test outcome",
                "--mode",
                "normal",
                "--session",
                "test-outcome-ok",
                "--trace-root",
                str(tmp_path / "traces"),
                "--json",
            ],
            provider_factory=factory,
        )
    finally:
        sys.stdout = old_stdout

    assert exit_code == 0

    result = json.loads(captured.getvalue())
    assert result["outcome"] == "OK"
    assert len(result["kept"]) == 1



# ─────────────────────────────────────────────────────────────────────────────
# Focused acceptance tests: session validation, trace refs, invocation IDs
# ─────────────────────────────────────────────────────────────────────────────


def test_existing_session_source_mismatch_fails_closed(tmp_path: Path):
    """Existing session fails closed when request.source hash differs, before provider use."""
    from prism.perspective_core.explore import run_explore
    from prism.perspective_core.models import PerspectiveRequest
    from prism.perspective_core.session import SessionStore

    session_store = SessionStore(tmp_path / "prism-sessions" / "perspective-core")
    session_store.create(
        session_id="test-source-mismatch",
        source="Original source content",
        objective="Original objective",
    )

    # Provider should never be called
    provider = ScriptedTestProvider(
        {
            "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), [make_candidate()])],
        }
    )

    request = PerspectiveRequest(
        source="Different source content that does not match original",
        objective="Original objective",
        mode="normal",
        session_id="test-source-mismatch",
    )

    with pytest.raises(ValueError, match="Request source hash.*does not match"):
        run_explore(
            request,
            session_store=session_store,
            provider=provider,
            trace_root=tmp_path / "traces",
        )

    # Zero provider calls
    assert provider._call_count == 0


def test_existing_session_objective_mismatch_fails_closed(tmp_path: Path):
    """Existing session rejects request.objective different from immutable session.objective before provider use."""
    from prism.perspective_core.explore import run_explore
    from prism.perspective_core.models import PerspectiveRequest
    from prism.perspective_core.session import SessionStore

    session_store = SessionStore(tmp_path / "prism-sessions" / "perspective-core")
    session_store.create(
        session_id="test-obj-mismatch",
        source="Original source content",
        objective="Original objective",
    )

    # Provider should never be called
    provider = ScriptedTestProvider(
        {
            "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), [make_candidate()])],
        }
    )

    request = PerspectiveRequest(
        source="Original source content",
        objective="Materially different objective",
        mode="normal",
        session_id="test-obj-mismatch",
    )

    with pytest.raises(ValueError, match="Request objective.*does not match immutable session objective"):
        run_explore(
            request,
            session_store=session_store,
            provider=provider,
            trace_root=tmp_path / "traces",
        )

    # Zero provider calls
    assert provider._call_count == 0


def test_zero_candidate_pass_record_invocation_ids_and_relative_trace_ref(tmp_path: Path):
    """Zero-candidate PassRecord collects provider invocation IDs and relative trace_ref."""
    from prism.perspective_core.explore import run_explore
    from prism.perspective_core.models import PerspectiveRequest
    from prism.perspective_core.session import SessionStore

    session_store = SessionStore(tmp_path / "prism-sessions" / "perspective-core")
    trace_root = tmp_path / "traces"

    provider = ScriptedTestProvider(
        {
            "EXPLORE_GENERATE": [
                make_generate_response(make_diagnosis(), [], invocation_id="inv-gen-zero-1")
            ],
        }
    )

    result = run_explore(
        PerspectiveRequest(
            source="Source material.",
            objective="Test zero candidate invocation ids",
            mode="normal",
            session_id="test-zero-cand-inv",
        ),
        session_store=session_store,
        provider=provider,
        trace_root=trace_root,
    )

    assert result.outcome == "NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS"
    assert result.kept == []

    session = session_store.load("test-zero-cand-inv")
    assert len(session.passes) == 1
    pass_record = session.passes[0]
    assert pass_record.candidates == []
    assert pass_record.selections == []
    assert pass_record.kept_p_ids == []
    assert pass_record.provider_invocation_ids == ["inv-gen-zero-1"]
    assert pass_record.trace_ref == result.run_id
    assert not Path(pass_record.trace_ref).is_absolute()


def test_relative_trace_ref_in_pass_record(tmp_path: Path):
    """PassRecord stores trace_ref relative to trace_root (run_id), not an absolute host path."""
    from prism.perspective_core.explore import run_explore
    from prism.perspective_core.models import PerspectiveRequest
    from prism.perspective_core.session import SessionStore

    session_store = SessionStore(tmp_path / "prism-sessions" / "perspective-core")
    trace_root = tmp_path / "traces"

    provider = ScriptedTestProvider(
        {
            "EXPLORE_GENERATE": [
                make_generate_response(make_diagnosis(), [make_candidate("C1")], invocation_id="inv-gen-1")
            ],
            "EXPLORE_SELECT": [
                make_select_response([make_selection("C1", disposition="KEEP")], invocation_id="inv-sel-1")
            ],
        }
    )

    result = run_explore(
        PerspectiveRequest(
            source="Source material.",
            objective="Test relative trace ref",
            mode="normal",
            session_id="test-relative-trace",
        ),
        session_store=session_store,
        provider=provider,
        trace_root=trace_root,
    )

    assert result.outcome == "OK"
    session = session_store.load("test-relative-trace")
    pass_record = session.passes[0]
    assert pass_record.trace_ref == result.run_id
    assert not Path(pass_record.trace_ref).is_absolute()
    assert pass_record.provider_invocation_ids == ["inv-gen-1", "inv-sel-1"]


def test_formal_validation_inadmissible_keep_blocks_registration(tmp_path: Path):
    """Formal validation error INADMISSIBLE_KEEP blocks P-ID registration and preserves validation trace."""
    from prism.perspective_core.explore import run_explore
    from prism.perspective_core.models import PerspectiveRequest
    from prism.perspective_core.session import SessionStore

    session_store = SessionStore(tmp_path / "prism-sessions" / "perspective-core")
    trace_root = tmp_path / "traces"

    candidates = [make_candidate("C1")]
    bad_selection = make_selection("C1", disposition="KEEP", admissible=False)

    provider = ScriptedTestProvider(
        {
            "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
            "EXPLORE_SELECT": [make_select_response([bad_selection])],
        }
    )

    with pytest.raises(ValueError, match="INADMISSIBLE_KEEP"):
        run_explore(
            PerspectiveRequest(
                source="Source material.",
                objective="Test validation failure",
                mode="normal",
                session_id="test-val-inadmissible",
            ),
            session_store=session_store,
            provider=provider,
            trace_root=trace_root,
        )

    # Verify session has no perspectives registered and no passes saved
    session = session_store.load("test-val-inadmissible")
    assert len(session.perspectives) == 0
    assert len(session.passes) == 0

    # Verify validation.json was preserved in trace
    run_dirs = list(trace_root.glob("*"))
    assert len(run_dirs) == 1
    val_file = run_dirs[0] / "validation.json"
    assert val_file.exists()
    val_data = json.loads(val_file.read_text(encoding="utf-8"))
    assert "C1" in val_data
    assert any(issue["code"] == "INADMISSIBLE_KEEP" for issue in val_data["C1"])


def test_formal_validation_keep_with_constraint_failures_blocks_registration(tmp_path: Path):
    """Formal validation error KEEP_WITH_CONSTRAINT_FAILURES blocks P-ID registration."""
    from prism.perspective_core.explore import run_explore
    from prism.perspective_core.models import PerspectiveRequest
    from prism.perspective_core.session import SessionStore

    session_store = SessionStore(tmp_path / "prism-sessions" / "perspective-core")
    trace_root = tmp_path / "traces"

    candidates = [make_candidate("C1")]
    bad_selection = make_selection(
        "C1",
        disposition="KEEP",
        admissible=True,
        constraint_failures=["violates constraint c1"],
    )

    provider = ScriptedTestProvider(
        {
            "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
            "EXPLORE_SELECT": [make_select_response([bad_selection])],
        }
    )

    with pytest.raises(ValueError, match="KEEP_WITH_CONSTRAINT_FAILURES"):
        run_explore(
            PerspectiveRequest(
                source="Source material.",
                objective="Test validation failure",
                mode="normal",
                session_id="test-val-constraint-fail",
            ),
            session_store=session_store,
            provider=provider,
            trace_root=trace_root,
        )

    session = session_store.load("test-val-constraint-fail")
    assert len(session.perspectives) == 0
    assert len(session.passes) == 0

    run_dirs = list(trace_root.glob("*"))
    assert len(run_dirs) == 1
    val_file = run_dirs[0] / "validation.json"
    assert val_file.exists()
    val_data = json.loads(val_file.read_text(encoding="utf-8"))
    assert "C1" in val_data
    assert any(issue["code"] == "KEEP_WITH_CONSTRAINT_FAILURES" for issue in val_data["C1"])


def test_formal_validation_unexpected_merge_target_blocks_registration(tmp_path: Path):
    """Formal validation error UNEXPECTED_MERGE_TARGET blocks P-ID registration."""
    from prism.perspective_core.explore import run_explore
    from prism.perspective_core.models import PerspectiveRequest
    from prism.perspective_core.session import SessionStore

    session_store = SessionStore(tmp_path / "prism-sessions" / "perspective-core")
    trace_root = tmp_path / "traces"

    candidates = [make_candidate("C1")]
    bad_selection = make_selection(
        "C1",
        disposition="DROP",
        merge_target={"kind": "candidate", "target_id": "C1"},
    )

    provider = ScriptedTestProvider(
        {
            "EXPLORE_GENERATE": [make_generate_response(make_diagnosis(), candidates)],
            "EXPLORE_SELECT": [make_select_response([bad_selection])],
        }
    )

    with pytest.raises(ValueError, match="UNEXPECTED_MERGE_TARGET"):
        run_explore(
            PerspectiveRequest(
                source="Source material.",
                objective="Test validation failure",
                mode="normal",
                session_id="test-val-merge-target",
            ),
            session_store=session_store,
            provider=provider,
            trace_root=trace_root,
        )

    session = session_store.load("test-val-merge-target")
    assert len(session.perspectives) == 0
    assert len(session.passes) == 0

    run_dirs = list(trace_root.glob("*"))
    assert len(run_dirs) == 1
    val_file = run_dirs[0] / "validation.json"
    assert val_file.exists()
    val_data = json.loads(val_file.read_text(encoding="utf-8"))
    assert "C1" in val_data
    assert any(issue["code"] == "UNEXPECTED_MERGE_TARGET" for issue in val_data["C1"])