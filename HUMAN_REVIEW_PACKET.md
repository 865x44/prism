# HUMAN_REVIEW_PACKET — Compact Summary for Human Reviewer

**Verdict:** `BEERLIGHT_DEMO_RC_SHOWABLE_WITH_KNOWN_ISSUES`

## What you need to know

1. **The demo works offline.** Six scenarios run with a fake adapter.
   No network, no provider, no evaluator, no external service. Run with:
   ```bash
   .venv/bin/python docs/beerlight_demo_rc/demo_runner.py --all
   ```

2. **All tests pass.** 47 focused, 281 full, pack 24/24, diff clean.

3. **No BLOCKER findings.** Red-team found 0 blockers. One embarrassing
   gap (RETURN_TO_EXPLORE missing from demo) was fixed in P5-B.

4. **Three deferred gaps require a real adapter:**
   - Paraphrase detection (F2)
   - LEVER prohibition (F6)
   - Material grounding (F7)
   These are architectural boundaries, not bugs.

5. **This is LOCAL_DEMO_RC_ONLY.** Not qualified, validated, or equivalent
   to any actual Custom GPT surface.

## What to review

| Document | Why |
|----------|-----|
| `BEERLIGHT_DEMO_RC_FINAL.md` | Full verdict, baseline, known issues |
| `docs/beerlight_demo_rc/README.md` | Demo commands, prohibited claims |
| `prism-runs/beerlight-demo-rc-p5-redteam-20260810-01/REVIEW.md` | 8 findings with evidence |
| `prism-runs/beerlight-demo-rc-p5-fix-20260810-01/FIX_MANIFEST.md` | F4 fix with before/after hashes |
| `TOMORROW.md` | 5 next actions for real-adapter dogfood |

## Decisions for you

1. Is `SHOWABLE_WITH_KNOWN_ISSUES` the right verdict, or should it be
   `SHOWABLE` (stricter) or `BLOCKED` (more conservative)?
2. Should any DEFERRED finding be promoted to EMBARRASSING before demo?
3. Is the demo narration guidance in `DEMO_RED_TEAM.md` honest enough?
4. Ready to authorize a real subject adapter for dogfood runs?
