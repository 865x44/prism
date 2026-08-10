# PLAN_PATCH_NOTES — REV 2 execution corrections

Date: 2026-08-09
Scope: execution corrections to `01_AGENT_ORCHESTRATOR_PROMPT.md` only, after an external red-team of REV 1. Goal: remove real execution holes before build start, keep the sprint execution-first.

## Changed

- **Two execution subjects.** `ACTUAL_CUSTOM_GPT_SURFACE` (highest authority for actual config; capture or ready-to-apply patch bundle) vs `LOCAL_DEMO_RC_REFERENCE_SUBJECT` (local re-host through Prism transport/runtime; used for harness/runs/AUTO/demo; exact config versioned; surface differences documented). Local re-host is NOT claimed semantically identical to the Custom GPT. Custom GPT access never blocks the sprint.
- **Subject model policy.** One primary subject config, versioned exactly. STABILITY = same-config reruns only. A secondary cheaper model is at most an optional cross-model portability probe, never stability evidence.
- **Repo baseline + MAX_CARDS.** Phase 0 records branch/HEAD/dirty, Python path/version, exact pytest command/result (re-verified: system pytest fails collection; `.venv/bin/python -m pytest` = 165 passed, 1 skipped), relevant runtime paths, legacy constraints bypassed. `MAX_CARDS=3` treated as legacy implementation constraint: bypassed/isolated for Beerlight runs, no broad rewrite, old Prism tests stay green.
- **WS3.5 `EVALUATOR_DIAGNOSTIC_READINESS_SMOKE`** (not "qualification": corpus is DRAFT_GOLD_PENDING_HUMAN, same-chat contaminated, not a holdout). One frozen evaluator config; run C01–C16 with two-call; validate evidence; distribution counts by verdict/status/predicate/language bucket/disagreement/invalid evidence/EVAL_ERROR; all RU/code-switch cases inspected; new condition `EVALUATOR_NOT_DISCRIMINATING`; no percentage threshold. Success = `PROVISIONAL_DIAGNOSTIC_READY` (instrument remains `UNQUALIFIED_DIAGNOSTIC_INSTRUMENT`). Poor smoke does not block DEMO_RC: semantic claims become untrusted, deterministic checks continue.
- **WS2 split.** WS2A capture (read-only, parallel with WS1); WS2B patch — Explore patch right after its capture, Deep patch only after WS1 (mandatory dependency boundary).
- **D3 interpretation.** Adversarial pass must materially engage the strongest objection; unchanged-but-demonstrated model is acceptable; generic objection + "however we still think X" = FAIL; no hard "required delta" invariant.
- **D8 sequence.** capture → reconcile → bounded source-as-data patch → run D8 against patched Deep; `KNOWN_PREPATCH_GAP` vs `POSTPATCH_REGRESSION_FAILURE` distinguished.
- **G3 gate before AUTO.** No unresolved BLOCKER in minimum primitive behaviors AUTO depends on (grounded divergence, 360 breadth, Explore/Deep boundary, P-ID continuity; selected-model preservation, NEED_EVIDENCE, RETURN_TO_EXPLORE; source-as-data where relevant). Candidate IDs E1/E3/E8/E12(/E11), D1/D5/D6(/D8) are implementation mapping, not gate ontology. No "qualified evaluator PASS" requirement.
- **Cost preflight.** Staged order (deterministic → cheap/local → evaluator smoke → core acceptance → full suite → stability → optional); approximate call estimates + generous ceiling before large runs; sparse matrices remain authority. Purpose is explosion prevention, not call minimization.
- **Shift-left adversarial smoke** in WS4 (fake breadth, paraphrase pack, source-as-data, P-ID rebinding, hidden Deep substitution); independent post-build red-team unchanged.
- **Provenance.** `prism-runs/<run-id>/`; run records (run ID, git HEAD, subject/evaluator config hashes, fixture/schema/predicate versions, timestamps, raw outputs, results); before-snapshots write-once + sha256. Small append-only `DECISION_REVIEW_DEBT.md` (ID, source/run, provisional choice, alternative, why it matters) → compact `HUMAN_REVIEW_PACKET.md` synthesized at finalization.
- **Patch manifest.** Per material change: CHANGE_ID, contract clause/acceptance reason, before, after, why required, affected tests. No line-by-line bureaucracy.
- **E3 operability.** Fixture-local `KNOWN_SUPPORTED_TERRITORIES` anchors (`PROVISIONAL_FIXTURE_ANCHORS`): authored lower bound of known supported territory, invisible to subject, available to test/evaluator; lets E3 FAIL on concrete omission without global breadth quotas.
- **Toolkit.** Default SKIP until core is runnable/red-teamable; bounded 360 A/B on at most 1–2 rich tasks if surplus.
- **Demo scripts.** Per scenario: exact input, mode/path, expected observable properties, caveats, exact command; demo expectations, not GOLD.
- **Versioning per report/run** and self-contained evidence bundles from every workstream; lead validates deterministic outputs, does not re-derive.
- **Sparse matrix source of truth:** reconciled Explore matrix now, reconciled Deep matrix after WS1; combined views generated, not hand-maintained.
- Mock provider optional cheap infra only.

## Explicitly NOT changed

- Semantic contract (`CONTRACT_DECISIONS_PROVISIONAL.md`), predicates, reconciled E1–E12 bodies, evaluator spec, and all source documents — untouched.
- No new research, no new methodology layer, no qualification program.

## Next action

Implementation (Codex start), not another audit.
