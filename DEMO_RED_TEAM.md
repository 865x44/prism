# DEMO_RED_TEAM — Beerlight DEMO_RC P5-A Summary

**Source:** `prism-runs/beerlight-demo-rc-p5-redteam-20260810-01/REVIEW.md`
**Findings:** 8 total (0 BLOCKER, 1 EMBARRASSING, 4 TOLERABLE, 3 DEFERRED)
**Post-fix:** F4 (EMBARRASSING) resolved in P5-B. Remaining: 0/1/4/3.

## Post-fix disposition

| # | Vector | Pre-fix | Post-fix | Notes |
|---|--------|---------|----------|-------|
| F1 | E3 fake breadth | TOLERABLE | TOLERABLE | Demo shows fake breadth; AUTO doesn't detect it (correct for scripted adapter) |
| F2 | E9 paraphrase | DEFERRED | DEFERRED | Needs subject adapter or evaluator |
| F3 | E11+D8 source-as-data | TOLERABLE | TOLERABLE | Routing boundary solid; semantic test needs real adapter |
| F4 | E8+D6 RETURN_TO_EXPLORE | EMBARRASSING | **FIXED** | S6 added, tests pass |
| F5 | E12+D1/D7 P-ID continuity | TOLERABLE | TOLERABLE | Well-covered |
| F6 | D2/D3/D5 LEVER/objection | DEFERRED | DEFERRED | Needs subject adapter layer |
| F7 | E6/E7 grounding | DEFERRED | DEFERRED | Needs real adapter |
| F8 | Malformed/fail-closed | TOLERABLE | TOLERABLE | Comprehensive |

## Infrastructure facts

- Offline scripted adapters only; zero real provider/model/transport calls
- Protocol: `beerlight-demo-rc-auto-v1`
- 6 demo scenarios, 47 focused tests, 281 full suite tests
- Evaluator not imported or invoked

## Honest narration guidance

When presenting the demo:
- S2 demonstrates fake breadth **appearance**, not detection
- S5 demonstrates source-as-data **routing label**, not prompt-injection resistance
- F2/F6/F7 are architectural gaps requiring a real subject adapter, not bugs
