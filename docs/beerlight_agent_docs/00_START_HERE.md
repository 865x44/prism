# Beerlight DEMO_RC Agent Documentation Pack

Date: 2026-08-09
Status: PROVISIONAL / DEMO_RC input pack

## Purpose

This archive is the self-contained documentation bundle for an autonomous agent/orchestrator tasked with moving Beerlight from semantic-design paperwork into a runnable, showable `BEERLIGHT_DEMO_RC`.

Nothing in this pack is HUMAN_APPROVED, GOLD, QUALIFIED, FROZEN, product validated, or market validated.

## Read first

1. `BEERLIGHT_SEMANTIC_CHAT_HANDOFF_2026-08-09.md`
2. `01_AGENT_ORCHESTRATOR_PROMPT.md`
3. `current/CONTRACT_DECISIONS_PROVISIONAL.md`
4. `current/SEMANTIC_PREDICATES_V1_PROVISIONAL.md`
5. `current/EXPLORE_ACCEPTANCE_CURRENT_STATE.md`
6. `current/EXPLORE_ACCEPTANCE_V1_PROVISIONAL_RECONCILED.md`
7. `current/EXPLORE_ACCEPTANCE_SPARSE_MATRIX_PROVISIONAL.md`
8. `sources/R2_DEEP_CURRENT_STATE.md`
9. `sources/R2_DEEP_SPEC_CANDIDATE.md`
10. `current/DEEP_ACCEPTANCE_V1_PROVISIONAL.md`
11. `current/SEMANTIC_EVALUATOR_SPEC_V1_PROVISIONAL.md`
12. `current/EVALUATOR_CHALLENGE_V1_PROVISIONAL.md`
13. `sources/R1_REPO_AUDIT.md`
14. `sources/PROTOCOL_V1_CANDIDATE.md`
15. `sources/R3_LLM_EVALUATOR_RESEARCH_MARKDOWN.md` (and full JSON only if needed)

Note: `01_AGENT_ORCHESTRATOR_PROMPT.md` is REV 2 (2026-08-09). `PLAN_PATCH_NOTES.md` records the execution corrections; the sprint prompt is the current execution authority.

## Authority / provenance rules

- Actual current Explore/Deep configuration, when freshly captured by the implementation agents, outranks copies in handoffs.
- `CONTRACT_DECISIONS_PROVISIONAL.md` is the current provisional semantic contract target for DEMO_RC.
- `SEMANTIC_PREDICATES_V1_PROVISIONAL.md` is the current provisional semantic vocabulary.
- For Explore E1-E12, prefer the RECONCILED artifacts. The earlier greenfield Explore acceptance file is intentionally not bundled as current authority.
- `DEEP_ACCEPTANCE_V1_PROVISIONAL.md` is only a candidate. Deep D1-D8 still require a bounded reconciliation against R2/current Deep evidence before stronger claims.
- `EVALUATOR_CHALLENGE_V1_PROVISIONAL.md` is a development/diagnostic corpus. It is not a pristine holdout and its labels are `DRAFT_GOLD_PENDING_HUMAN`.
- R1 is implementation/substrate evidence, not semantic authority.
- R3 is evaluator-method evidence, not Beerlight semantic authority.
- R4 is bounded protocol/identity design evidence.
- `historical/beerlight-master-agent-execution-plan-v1-2026-08-09.DO_NOT_EXECUTE_BLINDLY.md` is historical/planning material only.

## Important completed work

- Minimal provisional semantic contract: DONE.
- Semantic predicates: DONE provisionally.
- Explore E1-E12 archaeology/reconciliation: DONE provisionally.
- Evaluator protocol + visible challenge corpus: DONE provisionally.
- Deep D1-D8 reconciliation: NOT DONE.
- Actual current Explore/Deep configuration capture + patch: NOT DONE.
- Repo implementation + real E/D runs: NOT DONE.
- AUTO semantic/runtime demo: NOT DONE.
- Post-build red-team + bounded fixes: NOT DONE.

## Do not research again unless real execution contradicts existing evidence

- 360 breadth is not card count.
- Actor/style/metaphor variation alone is not semantic novelty.
- P-ID is provisionally conversation/reference-scoped and monotonic, not global.
- No lineage DAG/global UUID is required for current Explore V1 semantics.
- Repeated-360 novelty is relative to supplied prior semantic territory.
- Source grounding is not world truth.
- Source-as-data is a semantic authority boundary, not a security proof.
- Evaluator should be criterion-specific/evidence-based rather than holistic score.
- Evaluator infrastructure failure is not subject FAIL.
- Tiny corpora do not justify population accuracy percentages.

## Repository / implementation note

R1 indicates Prism should be treated as reusable low-level substrate rather than semantic authority. Reuse transport, structured extraction/validation/repair, traces and version metadata where appropriate. Do not blindly inherit legacy generator/judge semantics or `MAX_CARDS=3` behavior.

## Thinking Toolkit

Thinking Toolkit (`https://github.com/ponomr/thinking-toolkit`) is NOT a required semantic authority and is intentionally not vendored into this archive. It is only an optional design donor / bounded experiment for AUTO routing or a hidden 360 coverage challenge. Do not block Beerlight DEMO_RC on it and do not import its 30 named frameworks into Explore.

## Archive layout

- root: start/handoff/orchestrator instructions (REV 2) + plan patch notes + Codex orchestrator start prompt
- `current/`: current provisional Beerlight semantic/eval artifacts
- `sources/`: R1-R4 and source specimens/research
- `historical/`: superseded/planning-only material
- `external/`: reserved for optional external snapshots; may be empty

## Valid near-term claim

A valid near-term claim after implementation is bounded to something like:

> A provisional Beerlight DEMO_RC implementing the current locally defined semantic contract and acceptance candidates, with unresolved qualification/human-review debt explicitly tracked.
