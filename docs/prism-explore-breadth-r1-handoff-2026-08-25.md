# Release R1 Handoff: Explore Breadth
**Date:** 2026-08-25  
**Release:** R1 (Explore Breadth)  
**Status:** COMPLETE (offline implementation + test gates green)  
**Authoring source:** `docs/pizm-skill-staged-2026-08-24/`  
**Installed target:** `~/.config/opencode/skills/pizm/`  
**Plan reference:** `docs/prism-breadth-lever-single-auto-execution-plan-v4-2026-08-25.md` (§ R1)  
**Reconciliation reference:** `.ai/plans/prism-breadth-lever-auto-execution-reconciliation-2026-08-25.md`  

---

## 1. Executive Summary

Release R1 increases the structural recall of Pizm Explore by removing prompt-level self-filtering ("several strong", "small set is enough", "quota suppression") and replacing it with an explicit 12–16 candidate search-seed soft prior and ~20 soft safety ceiling. It introduces compact seed guidance (~1.0–1.5 KiB serialized), enforces deterministic fail-closed payload bounds in `bin/pizm-checkpoint`, adds post-hoc selector diagnostics to `bin/pizm-session-bundle`, verifies mirror synchronization across all 6 core skill files, and expands the test suite with 15 new deterministic regression tests.

---

## 2. Exact Breadth Contract Text Shipped

### 2.1 NORMAL Mode Breadth Contract (`references/explore.md`)
```markdown
### NORMAL

Candidate = compact search seed, not final Perspective.

Search broadly for materially different structural shifts.

When the material supports it:
aim roughly for 12–16 candidate seeds.

Around 20 is a soft safety ceiling, not a target.

Fewer is correct when further search mostly yields:
structural duplicates, decorative variants, weak noise.

Never pad to hit a number.

Preserve promising underdeveloped seeds for the selector.
Do not optimize toward the hidden selector rubric.

Prefer materially different mechanisms, incentives, constraints, causal structures, units of analysis, system boundaries, temporal dynamics, or agency distributions. Remove paraphrases and generic advice.
```

### 2.2 Compact Seed Guidance (`references/explore.md`)
```markdown
### Compact Seed Guidance

Raw candidates are search seeds, not final polished perspective cards:
- Each candidate should be compact (~1.0–1.5 KiB serialized). Do not make every candidate explain the entire universe or write presentation-ready essays.
- Focus on one semantic core and one load-bearing structural shift.
- Provide minimal grounding and epistemic status (`supported`, `inferred`, `speculative`, `unknown`).
- Highlight 1–2 key consequences (`what_becomes_visible`).
- Include optional `break_condition` (required for RIFT).
- Keep descriptions crisp and dense so the search pool can support 12–16 candidate seeds within payload safety bounds.
```

### 2.3 Product-Contract Manual Mode Invariant (`SKILL.md`)
```markdown
After Explore, do not force a next step or choose a perspective for the user; branch commit remains the user's. After Deep, do not automatically start another Explore pass.
```

---

## 3. Files Changed

| File Path | Scope | Description of Change |
|---|---|---|
| `docs/pizm-skill-staged-2026-08-24/references/explore.md` | Mutable | Replaced self-filtering with 12–16 soft prior; added compact seed guidance; rebalanced 360 phrasing |
| `docs/pizm-skill-staged-2026-08-24/SKILL.md` | Mutable | Added manual-mode invariant: branch commit remains the user's |
| `bin/pizm-checkpoint` | Mutable | Added payload safety bounds: candidate count 1..20, total bytes <= 192 KiB, single candidate <= 12 KiB; fail closed with `PAYLOAD_TOO_LARGE` |
| `bin/pizm-session-bundle` | Mutable | Added deterministic post-hoc selector diagnostics computation (`_compute_explore_diagnostics`) recorded in `manifest.json` and `diagnostics.json` |
| `tests/test_pizm_explore_contracts.py` | Mutable | Added `TestExploreBreadthContract` (10 assertions testing breadth framing, soft prior, absence of suppressive phrasing, compactness, invariant) |
| `tests/test_pizm_checkpoint.py` | Mutable | Added 4 payload bounds tests (pool 20 accepted, pool 21 rejected, single candidate >12 KiB rejected, total artifact >192 KiB rejected) |
| `tests/test_pizm_session_bundle.py` | Mutable | Added `TestSelectorDiagnostics` verifying diagnostics computation and artifact recording |
| `~/.config/opencode/skills/pizm/` (mirror) | Mirror | Synced `SKILL.md` and `references/explore.md`; verified 6/6 identical via `cmp -s` |
| `docs/prism-explore-breadth-r1-handoff-2026-08-25.md` | New | This handoff artifact |

---

## 4. Test Results Verbatim

### 4.1 Focused Test Suite Execution
```bash
PYTHONPATH=src python3 -m pytest tests/test_pizm_explore_contracts.py tests/test_pizm_checkpoint.py tests/test_pizm_session_bundle.py -v
```
**Output:**
```text
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
pytest: 181 passed in 6.74s
```

### 4.2 Full Repository Test Suite Execution
```bash
PYTHONPATH=src python3 -m pytest tests -q
```
**Output:**
```text
........................................................................ [  9%]
........................................................................ [ 18%]
........................................................................ [ 27%]
........................................................................ [ 36%]
........................................................................ [ 45%]
........................................................................ [ 54%]
........................................................................ [ 63%]
........................................................................ [ 72%]
........................................................................ [ 82%]
........................................................................ [ 91%]
..........................................s...........................   [100%]
789 passed, 1 skipped in 11.55s
```
*(Baseline was 774 passed, 1 skipped; delta is +15 passed tests covering all R1 features).*

---

## 5. Mirror Gate Verification

Command run:
```bash
for f in SKILL.md agents/openai.yaml references/deep.md references/deep-reviewer.md references/explore.md references/explore-selector.md; do
    cmp -s "docs/pizm-skill-staged-2026-08-24/$f" "$HOME/.config/opencode/skills/pizm/$f" || { echo "MISMATCH: $f"; exit 1; }
done
echo "MIRROR_GATE_PASS"
```
**Output:**
```text
MIRROR_GATE_PASS
```
All 6 files in `MIRRORED_FILES` are verified byte-identical between `docs/pizm-skill-staged-2026-08-24/` and `~/.config/opencode/skills/pizm/`.

---

## 6. Selector Diagnostics Format Sample

Sample generated by `bin/pizm-session-bundle` when bundling an Explore stage containing `candidates.json` and `selection.json`:

```json
{
  "candidate_count": 4,
  "keep_count": 1,
  "merge_count": 1,
  "drop_count": 1,
  "borderline_count": 1,
  "disposition_distribution": {
    "KEEP": 1,
    "BORDERLINE": 1,
    "MERGE": 1,
    "DROP": 1
  },
  "duplicate_or_merge_count": 1,
  "serialized_candidates_bytes": 3506,
  "serialized_selection_bytes": 850
}
```

This record is stored in `manifest.json` under `manifest["diagnostics"]["<stage-label>"]` and as `<stage-label>/diagnostics.json` inside the archive.

---

## 7. Deterministic Fail-Closed Payload Safety Proof

`bin/pizm-checkpoint` enforces:
1. `len(candidates) > 20`: raises `PAYLOAD_TOO_LARGE: candidate count <n> exceeds maximum 20`.
2. `len(raw_bytes) > 196608` (192 KiB): raises `PAYLOAD_TOO_LARGE: total candidates artifact size <n> bytes exceeds maximum 196608 bytes (192 KiB)`.
3. `len(json.dumps(c)) > 12288` (12 KiB): raises `PAYLOAD_TOO_LARGE: candidate[<i>] (<cid>) serialized size <n> bytes exceeds maximum 12288 bytes (12 KiB)`.

**Fail-Closed Behavior:**
- Exit code != 0
- Error message printed to stderr with `PAYLOAD_TOO_LARGE`
- Zero artifacts or directories created in `.ai/pizm/run-<id>`
- Next-stage contract (`explore-selector.md`) is NEVER read or printed to stdout.

---

## 8. Known Limitations & Dogfood Boundaries

1. **Cross-Pass Blindness:** Multi-pass flows (NORMAL → 360, repeated 360) remain blocked for semantic live calls because the selector rubric revealed in Pass 1 remains in the conversation history for Pass 2.
2. **Offline Implementation:** All R1 changes are purely local prompt contracts, CLI tools, and deterministic tests. Zero semantic live provider calls were executed.
3. **Manual Mode Invariant:** Explore provides candidate perspectives and survivor cards; it never automatically selects a winning branch or forces a next step.

---

## 9. Rollback Strategy

If a regression or kill criterion is identified:
1. Primary reverts only the R1 commit:
   ```bash
   git revert <R1-commit-sha>
   ```
2. Resync mirror from baseline staged skill:
   ```bash
   for f in SKILL.md agents/openai.yaml references/deep.md references/deep-reviewer.md references/explore.md references/explore-selector.md; do
       cp "docs/pizm-skill-staged-2026-08-24/$f" "$HOME/.config/opencode/skills/pizm/$f"
   done
   ```
3. Re-run test gate:
   ```bash
   PYTHONPATH=src python3 -m pytest tests -q
   ```
