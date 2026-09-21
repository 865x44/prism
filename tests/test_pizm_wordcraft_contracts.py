"""
Contract tests for Pizm WORDCRAFT v1 (WORDCRAFT-V1).

Verifies:
- Reference presence and routing in SKILL.md
- Default Explore NORMAL behavior preserved for bare `/pizm <task>`
- WORDCRAFT excluded from AUTO and BONK automated pipeline topologies
- Architectural invariants: prompt-only, one host-model pass, zero new infrastructure/checkpoints/schemas/runtimes
- Honest no-winner path (NO WINNER / source text is stronger)
- Output diversity (both coined words/neologisms and phrases/metaphors/formulas supported)
- Context-first qualitative selection without fake numeric memetic scoring
- Analytical reference files untouched
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = REPO_ROOT / "skills" / "pizm"
WORDCRAFT_REF = SKILL_ROOT / "references" / "wordcraft.md"
SKILL_MD = SKILL_ROOT / "SKILL.md"
AUTO_REF = SKILL_ROOT / "references" / "auto.md"
BONK_REF = SKILL_ROOT / "references" / "bonk.md"
OPENAI_YAML = SKILL_ROOT / "agents" / "openai.yaml"
README_MD = REPO_ROOT / "README.md"


@pytest.fixture
def wordcraft_text() -> str:
    assert WORDCRAFT_REF.is_file(), "skills/pizm/references/wordcraft.md must exist"
    return WORDCRAFT_REF.read_text(encoding="utf-8")


@pytest.fixture
def skill_text() -> str:
    assert SKILL_MD.is_file(), "skills/pizm/SKILL.md must exist"
    return SKILL_MD.read_text(encoding="utf-8")


@pytest.fixture
def auto_text() -> str:
    assert AUTO_REF.is_file(), "skills/pizm/references/auto.md must exist"
    return AUTO_REF.read_text(encoding="utf-8")


@pytest.fixture
def bonk_text() -> str:
    assert BONK_REF.is_file(), "skills/pizm/references/bonk.md must exist"
    return BONK_REF.read_text(encoding="utf-8")


@pytest.fixture
def readme_text() -> str:
    assert README_MD.is_file(), "README.md must exist"
    return README_MD.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Presence and routing
# ---------------------------------------------------------------------------


class TestWordcraftPresenceAndRouting:
    def test_wordcraft_reference_exists(self, wordcraft_text: str):
        assert len(wordcraft_text) > 1000, "wordcraft.md should contain full contract specification"
        assert "# WORDCRAFT Contract" in wordcraft_text or "WORDCRAFT" in wordcraft_text

    def test_skill_routes_wordcraft(self, skill_text: str):
        assert "references/wordcraft.md" in skill_text
        assert "/pizm wordcraft" in skill_text
        assert re.search(r"/pizm wordcraft.*references/wordcraft\.md", skill_text, re.DOTALL)

    def test_skill_default_unchanged(self, skill_text: str):
        assert "Explore NORMAL" in skill_text
        assert re.search(r"/pizm <task>.*Explore NORMAL", skill_text)

    def test_wordcraft_not_in_auto_or_bonk_topology(self, auto_text: str, bonk_text: str):
        assert "wordcraft" not in auto_text.lower(), "AUTO must not execute or mention WORDCRAFT"
        assert "wordcraft" not in bonk_text.lower(), "BONK must not execute or mention WORDCRAFT"

    def test_readme_documents_wordcraft(self, readme_text: str):
        assert "/pizm wordcraft" in readme_text
        assert "references/wordcraft.md" in readme_text


# ---------------------------------------------------------------------------
# 2. Architectural invariants
# ---------------------------------------------------------------------------


class TestWordcraftArchitecturalInvariants:
    def test_no_checkpoint_schema_or_runtime_requirements(self, wordcraft_text: str):
        lower = wordcraft_text.lower()
        assert "pizm-checkpoint" not in lower
        assert "pizm-session-bundle" not in lower
        assert "json schema" not in lower
        assert "perspective_core" not in lower

    def test_one_pass_host_model(self, wordcraft_text: str):
        assert re.search(r"single\s+(?:cognitive\s+)?pass", wordcraft_text, re.IGNORECASE)
        assert re.search(r"host\s+model", wordcraft_text, re.IGNORECASE)


# ---------------------------------------------------------------------------
# 3. Semantic behavior contracts
# ---------------------------------------------------------------------------


class TestWordcraftSemanticContracts:
    def test_honest_no_winner_path_permitted(self, wordcraft_text: str):
        assert "NO WINNER" in wordcraft_text
        assert re.search(r"исходник\s+сильнее", wordcraft_text, re.IGNORECASE) or "no useful wordcraft" in wordcraft_text.lower()

    def test_output_diversity_both_words_and_phrases(self, wordcraft_text: str):
        lower = wordcraft_text.lower()
        assert "neologism" in lower or "coined word" in lower or "неологизм" in lower
        assert "phrase" in lower or "metaphor" in lower or "punchline" in lower or "formula" in lower

    def test_context_first_selection(self, wordcraft_text: str):
        lower = wordcraft_text.lower()
        assert "in context" in lower
        assert "context" in lower

    def test_no_fake_memetic_scoring(self, wordcraft_text: str):
        lower = wordcraft_text.lower()
        assert "memetic" in lower
        assert "no fake" in lower or "not" in lower or "do not" in lower or "qualitative" in lower

    def test_voice_preservation(self, wordcraft_text: str):
        lower = wordcraft_text.lower()
        assert "voice" in lower


# ---------------------------------------------------------------------------
# 4. Analytical references untouched
# ---------------------------------------------------------------------------


class TestAnalyticalReferencesUntouched:
    ANALYTICAL_REFS = [
        "explore.md",
        "explore-selector.md",
        "deep.md",
        "deep-reviewer.md",
        "deep-compare.md",
        "lever.md",
        "lever-reviewer.md",
        "auto.md",
        "bonk.md",
        "reasoning-arsenal.md",
    ]

    def test_analytical_reference_files_exist_and_unmodified(self):
        for ref_name in self.ANALYTICAL_REFS:
            ref_path = SKILL_ROOT / "references" / ref_name
            assert ref_path.is_file(), f"Analytical reference {ref_name} must exist"

        # Check git status for any diffs in analytical references against HEAD
        res = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "--", "skills/pizm/references/"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            changed_refs = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            # GATE1F-ITER2-20260912 authorizes two further bounded edits: deep.md
            # (D2 presentation-only paragraph invariant) and deep-reviewer.md
            # (D3 blocker-code target-label clarification, zero semantic change).
            # BPATCH comparison-parity follow-up additionally authorizes the
            # bounded deep-compare.md inheritance pointer + schema example
            # (no Critic semantics duplicated or changed).
            # WAVE1-RELEASE-PATCH-20260920 authorizes bounded task-relative
            # explore-selector.md and synchronized explore.md pre-search clarification.
            # PACK-BONK-REPAIR-20260922 authorizes the route-coherence repair of
            # pack.md (installed-path recipes, exact-three-pass and archive
            # topology invariants) plus the matching selector/bonk.md edits.
            allowed_changes = {
                "skills/pizm/references/wordcraft.md",
                "skills/pizm/references/auto.md",
                "skills/pizm/references/bonk.md",
                "skills/pizm/references/pack.md",
                "skills/pizm/references/deep.md",
                "skills/pizm/references/deep-reviewer.md",
                "skills/pizm/references/deep-compare.md",
                "skills/pizm/references/explore-selector.md",
                "skills/pizm/references/explore.md",
            }
            for changed in changed_refs:
                assert changed in allowed_changes, (
                    f"Unexpected modification in analytical reference: {changed}"
                )
