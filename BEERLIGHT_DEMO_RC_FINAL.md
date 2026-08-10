# BEERLIGHT DEMO_RC — Final Verdict

**Verdict:** `BEERLIGHT_DEMO_RC_SHOWABLE_WITH_KNOWN_ISSUES`
**Date:** 2026-08-10
**Authority:** Orchestrator primary (qwen3.7-max session)

## What is showable

The Beerlight DEMO_RC package is a runnable, offline, provider-free
demonstration of the AUTO routing protocol (`beerlight-demo-rc-auto-v1`).
It exercises six scenarios covering all three terminal gates
(MODEL_READY, NEED_EVIDENCE, RETURN_TO_EXPLORE), fake-breadth detection
(E3), P-ID continuity, and source-as-data injection resistance.

### Exact demo command

```bash
cd /home/alx/projects/prism
.venv/bin/python docs/beerlight_demo_rc/demo_runner.py --all
.venv/bin/python -m pytest tests/beerlight_demo_rc -q
```

### Baseline record (2026-08-10)

| Check | Result |
|-------|--------|
| Focused suite | 47 passed |
| Full suite | 281 passed, 1 skipped |
| Demo runner --all | 6/6 scenarios, exit 0 |
| Immutable pack | 24/24 SHA-256 |
| Deep suite validator | OK, immutable_pack_files_verified=25, provider_calls=0 |
| git diff --check | clean |
| Provider/evaluator/fallback calls | 0 |

## Known issues

### Tolerable for demo (no fix needed)

- **F1 (E3):** AUTO has no territory detection. S2 demonstrates what fake
  breadth looks like but does not flag it at the routing layer. Territory
  detection is implicitly delegated to the subject adapter.
- **F3 (E11+D8):** Source-as-data routing boundary verified
  (source_role=DATA_NOT_INSTRUCTIONS). Semantic non-compliance is untestable
  with a scripted adapter.
- **F5 (E12+D1/D7):** P-ID continuity well-covered. No gap.
- **F8 (Malformed):** Fail-closed comprehensive across all documented paths.

### Deferred (outside current contract)

- **F2 (E9):** Paraphrase/actor/style detection — zero coverage. Requires
  subject adapter or evaluator integration.
- **F6 (D2/D3/D5):** LEVER prohibition and strongest-objection engagement —
  absent from AUTO (routing dispatcher, not semantic analyzer). Requires
  subject adapter layer.
- **F7 (E6/E7):** Material grounding — untestable with scripted adapter.
  Requires real subject generation.

## Gate summary

| Gate | Status | Run dir |
|------|--------|---------|
| P0 | DONE | `beerlight-demo-rc-p0-20260810-01` |
| G1 | PASS | `beerlight-demo-rc-g1-20260810-01` |
| G2 | PASS (reduced trust) | `beerlight-demo-rc-g2-20260810-01` |
| G3 | ACCEPTED (LOCAL_DEMO_RC) | `beerlight-demo-rc-g3-20260810-02` |
| P4-A | ACCEPTED | `beerlight-demo-rc-p4-auto-20260810-01` |
| P4-B | ACCEPTED | `beerlight-demo-rc-p4-b-20260810-01` |
| Luna | PASS | `beerlight-demo-rc-p4-b-luna-check-20260810-01` |
| P5-A | ACCEPTED | `beerlight-demo-rc-p5-redteam-20260810-01` |
| P5-B | ACCEPTED | `beerlight-demo-rc-p5-fix-20260810-01` |

## What this is NOT

- Not HUMAN_APPROVED, GOLD, QUALIFIED, FROZEN, product-validated, or
  market-validated.
- Not a claim of parity with any actual Custom GPT surface.
- Not evidence of semantic correctness, prompt-injection resistance, or
  grounding — only of deterministic routing invariants.
- Evaluator remains UNQUALIFIED_DIAGNOSTIC_INSTRUMENT with zero acceptance
  authority.

## AUTO preview

Protocol `beerlight-demo-rc-auto-v1`:
- Three stages: EXPLORE → DEEP → gated MAKE
- Selection policy: lowest numeric viable P-ID
- Terminal gates: NEED_EVIDENCE and RETURN_TO_EXPLORE (MAKE never invoked)
- Fail-closed: private fields, stage/mode mismatch, P-ID substitution,
  invalid gates, malformed records, missing adapter
- Provider-free: no import, no default route, injected adapter only

Sample transcripts: `prism-runs/beerlight-demo-rc-p4-b-20260810-01/demo-output.json`
(5 scenarios, full call ledgers with payload hashes — captured pre-F4-fix;
the current package runs 6 scenarios S1-S6, see the demo runner)

## Files

| Artifact | Location |
|----------|----------|
| Demo README | `docs/beerlight_demo_rc/README.md` |
| Scenarios | `docs/beerlight_demo_rc/scenarios.json` |
| Demo runner | `docs/beerlight_demo_rc/demo_runner.py` |
| Demo tests | `tests/beerlight_demo_rc/test_demo_scenarios.py` |
| Red-team review | `prism-runs/beerlight-demo-rc-p5-redteam-20260810-01/REVIEW.md` |
| Fix manifest | `prism-runs/beerlight-demo-rc-p5-fix-20260810-01/FIX_MANIFEST.md` |
| P4-B run packet | `prism-runs/beerlight-demo-rc-p4-b-20260810-01/` |
| Luna check | `prism-runs/beerlight-demo-rc-p4-b-luna-check-20260810-01/REVIEW.md` |
