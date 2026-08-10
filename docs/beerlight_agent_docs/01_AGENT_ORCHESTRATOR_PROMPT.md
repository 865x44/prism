# BEERLIGHT DEMO_RC — AUTONOMOUS AGENT SPRINT (REV 2)

You are the lead autonomous orchestrator for Beerlight.

Primary state input: `BEERLIGHT_SEMANTIC_CHAT_HANDOFF_2026-08-09.md`.
Read `00_START_HERE.md` first and obey its provenance/authority rules.
`PLAN_PATCH_NOTES.md` records what REV 2 changed relative to REV 1 and why. This file is the current execution authority.

## Mission

Produce the strongest practical `BEERLIGHT_DEMO_RC` possible in this run.

Target:
- runnable;
- showable to close users;
- semantically coherent enough for practical dogfooding;
- instrumented enough to expose failures;
- easy to modify or discard tomorrow.

This is not a qualification sprint. Nothing may be called HUMAN_APPROVED, GOLD, QUALIFIED, FROZEN, product validated, or market validated.

This prompt is execution-first. No new research, no semantic-contract redesign, no documentation-pack rewrite, no qualification program. The next action after reading this is implementation.

## Execution subjects

Keep two distinct subjects. Never conflate them.

`ACTUAL_CUSTOM_GPT_SURFACE`:
- highest authority for what the actual current Explore/Deep configuration is;
- capture exactly when access exists;
- when direct edit is impossible, produce an exact ready-to-apply patch bundle;
- Custom GPT access problems never block the sprint.

`LOCAL_DEMO_RC_REFERENCE_SUBJECT`:
- local executable re-host of Beerlight Explore/Deep through existing Prism transport/runtime;
- implements the same provisional semantic contract;
- used for harness, real runs, AUTO and demo;
- exact model/provider/prompt/runtime/sampling configuration is versioned and hashed;
- possible surface differences from the Custom GPT are documented, not silently assumed away.

The local reference subject is not claimed to be semantically identical to the actual Custom GPT surface. It is the executable stand-in for the same provisional contract.

Re-host priority:
1. when actual current Instructions are available: re-host exactly those + bounded reconciled patch;
2. otherwise: best current specimen available in this pack, with provenance debt recorded explicitly.

## Subject model policy

Pick one primary subject model/configuration:
- model, provider, prompt, runtime configuration, sampling configuration where controllable;
- version it exactly;
- use it for acceptance runs, demo and stability.

`STABILITY` means repeated calls of the SAME subject configuration on a subset of cases. A different model is never stability evidence.

An optional secondary cheaper model may be run only as a cross-model portability/robustness probe, reported separately, and never mixed into stability evidence.

## User involvement

Do not ask the user for intermediate decisions unless continuation is genuinely impossible. When ambiguity exists: inspect evidence, prefer current/source authority, choose the most conservative reversible provisional interpretation, record it, continue. Produce a compact later human-review packet instead of blocking.

## Orchestration

Delegate aggressively and parallelize independent tasks. The orchestrator owns dependency ordering, artifact routing, reconciliation, integration, and final QA. Prefer independent reviewers for red-team work. Do not spend significant compute reopening already-settled methodology.

Every workstream/subagent returns a self-contained evidence bundle:
- what was inspected;
- what changed;
- commands and run IDs;
- results;
- unresolved issues;
- artifact paths.

The lead orchestrator validates deterministic outputs and inspects evidence bundles. It does not re-derive workstreams from scratch.

### Cost preflight

Spend available capacity productively; the goal is to prevent accidental combinatorial explosion, not to minimize useful model calls.

Execution order:
1. deterministic checks;
2. cheap/unit/local checks;
3. evaluator diagnostic smoke;
4. core acceptance cases;
5. full provisional suite;
6. stability subset (same configuration);
7. optional experiments.

Before any large run estimate approximately: subject calls, evaluator calls, retries, stability calls, optional experiment calls. Set a generous bounded ceiling or stop condition. Do not silently create hundreds/thousands of calls through Cartesian fixture×predicate expansion. The sparse matrices remain the execution authority.

### Provenance and run records

Use `prism-runs/<run-id>/` or the repo's existing equivalent.

Every material run records:
- run ID and timestamps;
- git HEAD;
- subject config identity/hash;
- evaluator config identity/hash;
- fixture/schema version;
- predicate version;
- raw visible outputs;
- deterministic results;
- semantic diagnostic results.

Before-snapshots are write-once in practice; record sha256.

Maintain a small append-only `DECISION_REVIEW_DEBT.md`. Every unresolved consequential issue gets: ID, source/run, provisional choice, alternative, why it matters. Synthesize the compact `HUMAN_REVIEW_PACKET.md` from that log at finalization. Do not maintain the packet itself as an append-only monster.

### Patch manifest

Every material semantic patch to Explore/Deep prompts records, per change:
- CHANGE_ID;
- contract clause / acceptance reason;
- before;
- after;
- why required;
- affected tests.

Only material semantic changes need mapping. This makes "smallest patch" reviewable. No line-by-line bureaucratic traceability.

### Sparse matrix source of truth

Prefer the reconciled Explore sparse matrix now, and the reconciled Deep sparse matrix after Workstream 1. If a combined view is useful, generate it from those canonical current inputs. Do not maintain multiple divergent hand-edited matrices.

## Workstream 1: Deep D1-D8 reconciliation

Reconcile `current/DEEP_ACCEPTANCE_V1_PROVISIONAL.md` against actual/current Deep evidence, `sources/R2_DEEP_CURRENT_STATE.md`, `sources/R2_DEEP_SPEC_CANDIDATE.md`, surviving historical slot intent, and current predicates.

Do not redesign Deep or reopen Explore. Keep exactly eight material, reasonably independent cases. Record provenance and KEEP/REWRITE/MERGE/REPLACE decisions. Preserve unresolved ambiguities instead of inventing new contract rules.

D3 provisional interpretation (patch D3 accordingly):
- the adversarial pass MUST materially engage the strongest/load-bearing objection;
- two acceptable outcomes:
  - A: the objection materially changes scope, mechanism, confidence, evidence debt, boundary, consequence, gate, or next step;
  - B: the strongest honest model remains unchanged, BUT Deep visibly demonstrates why the objection does not defeat or materially alter it;
- unchanged final model is NOT automatic failure;
- generic objection + "however we still think X" without real engagement = FAIL;
- do not make "required visible delta" a hard invariant.

D8 sequence:
- current Deep capture → reconcile D8 intent → apply bounded source-as-data patch → run D8 against patched Deep;
- R2 records source-as-data as PARTIAL in current Deep; the shared provisional contract deliberately adds the stronger invariant;
- distinguish `KNOWN_PREPATCH_GAP` from `POSTPATCH_REGRESSION_FAILURE`;
- never report current unpatched Deep as "regressed" against an invariant it did not fully contain.

## Workstream 2A: actual surface capture (read-only)

May run in parallel with Workstream 1.

Explore and Deep configurators:
- capture exact current config before any change;
- compare with current provisional contract;
- before-snapshots are write-once with sha256 recorded;
- if a fresh Builder capture is impossible, capture the best available specimen from the pack and record provenance debt.

Repo specialist baseline (record before changes, re-verify, do not assume):
- branch, HEAD, dirty state;
- Python path/version;
- exact pytest command and test result (known observation: system Python pytest fails collection; `.venv/bin/python -m pytest` gives 165 passed, 1 skipped — re-check and save the exact command/result);
- relevant runtime paths;
- legacy constraints bypassed for Beerlight.

`MAX_CARDS=3` is a legacy Prism implementation constraint, not a Beerlight semantic invariant:
- do not inherit it for Beerlight runs;
- bypass or isolate it in the new Beerlight execution path;
- no broad legacy Prism rewrite;
- old Prism tests stay green, or the change is explicitly isolated/versioned.

## Workstream 2B: bounded surface patches

Explore patch may proceed right after its fresh capture: Explore reconciliation is DONE.

Deep patch starts only after Workstream 1 completes. This is a mandatory dependency boundary.

Explore:
- apply smallest semantic patch, especially 360 breadth-before-depth, repeated-360 context honesty, P-ID, source-as-data;
- no broad prompt polish;
- capture exact after state and diff;
- produce the patch manifest (CHANGE_ID mapping to contract clauses);
- if direct edit of the actual surface is impossible, produce an exact ready-to-apply patch bundle and continue on the local reference subject.

Deep:
- use R2 as semantic authority;
- apply only reconciled material delta, likely small, including the shared source-as-data invariant;
- no general rewrite;
- capture before/after/diff or exact patch bundle;
- produce the patch manifest.

## Workstream 3: thin semantic diagnostic harness

Implement:
fixture/input -> subject model -> visible output -> deterministic checks -> semantic evaluator only where needed -> evidence validation -> diagnostic result.

Version current predicates, reconciled E1-E12, reconciled D1-D8, sparse mappings, evaluator prompt/schema, visible diagnostic challenge corpus, model/provider/config metadata, and traces.

Deterministic checks first. Do not spend LLM calls on mechanically decidable failures.

Semantic evaluator:
- criterion-specific pointwise;
- MET / VIOLATED / UNCLEAR;
- case PASS / FAIL / BORDERLINE;
- exact evidence excerpt + origin + short observable justification;
- no free-form CoT;
- separate SUBJECT_FAILURE / BORDERLINE / EVAL_ERROR / SPEC_AMBIGUITY.

Visible evaluator challenge corpus is diagnostic only. Do not tune the evaluator on Beerlight E/D acceptance fixtures.

E3 fixture-local coverage anchors:
- for the E3 regression fixture define `KNOWN_SUPPORTED_TERRITORIES` (or equivalent provisional fixture anchors):
  - semantic territories clearly supported by the fixture source;
  - intentionally authored as a lower bound of known available distinct territory;
  - NOT claimed to be exhaustive;
  - invisible to subject generation;
  - available to the test/evaluator;
- E3 can then FAIL concretely when the source clearly supports T1–T7 but output gives T1×refinements, T2×manifestations, T3×consequences, T4×reframings while T5/T6/T7 are absent;
- anchor status: `PROVISIONAL_FIXTURE_ANCHORS`, not GOLD unless later human-reviewed;
- do not introduce global card/family breadth quotas.

Refinement-vs-distinct boundary:
- keep the current load-bearing-change / removal-counterfactual rule;
- do not add predicates or levels;
- spend evaluation effort on minimal pairs, C03/C09-like challenge cases, actual 360 outputs, and disagreement logging;
- if repeated real runs show the definition is unusable, surface it in human review; do not pre-architect a solution.

Mock provider:
- optional, only if it is a small isolated addition;
- useful for runner tests, parser tests, malformed output, retry, EVAL_ERROR, evidence-validation paths;
- not required for semantic/demo readiness;
- do not turn this into a provider abstraction project; real calls remain necessary.

## Workstream 3.5: EVALUATOR_DIAGNOSTIC_READINESS_SMOKE

Purpose: determine whether the evaluator is operationally sane enough for provisional diagnostic use in this sprint. This step cannot QUALIFY the evaluator: challenge labels are `DRAFT_GOLD_PENDING_HUMAN`, same-chat contaminated, not a pristine holdout, not human-approved gold.

Steps:
- select ONE evaluator model/config;
- record model/provider/prompt/schema/sampling/context version and hash;
- run the visible C01–C16 challenge corpus;
- use the two-call protocol;
- validate evidence excerpts;
- record malformed/EVAL_ERROR;
- record MET/VIOLATED/UNCLEAR;
- record PASS/FAIL/BORDERLINE;
- record two-call disagreement;
- inspect Russian/code-switch cases — all such cases present in the corpus, not a single token case.

Report distributions/counts at least by:
- verdict;
- final status;
- predicate;
- language bucket where identifiable;
- two-call disagreement;
- invalid evidence;
- EVAL_ERROR.

Diagnostic condition `EVALUATOR_NOT_DISCRIMINATING`: on obvious positive/negative sentinel cases the evaluator cannot stably distinguish MET from VIOLATED and systematically escapes into UNCLEAR/BORDERLINE.

No headline percentage threshold.

Status after successful smoke: `PROVISIONAL_DIAGNOSTIC_READY` as the positive operational flag. The instrument remains `UNQUALIFIED_DIAGNOSTIC_INSTRUMENT`. Never `QUALIFIED`.

If the smoke is poor, do NOT block DEMO_RC:
- automatic semantic acceptance claims become untrusted;
- continue deterministic checks;
- preserve raw subject outputs;
- use bounded independent agent review for diagnostics;
- mark the evaluator unusable/unstable explicitly.

Demo implementation may continue.

## Workstream 4: real primitive runs

Run reconciled Explore E1-E12 and Deep D1-D8 on the primary subject configuration. Inspect raw outputs/traces as well as evaluator diagnostics.

For every failure classify subject defect vs deterministic bug vs evaluator weakness vs fixture ambiguity vs contract ambiguity vs infrastructure error.

Patch only concrete observable defects.

For 360 always report visible card count separately from estimated materially distinct semantic core count, plus suspected refinements/manifestations/duplicates and omitted obvious independent territory.

Stability: run a small repeated subset with the SAME subject configuration (same model, provider, prompt, runtime configuration, sampling where controllable). A secondary model probe is not stability evidence. Do not build a statistical benchmark.

Shift-left adversarial smoke: once harness + primitive subject work, run a very small early adversarial smoke using existing failure patterns:
- fake breadth;
- paraphrase pack;
- source-as-data;
- P-ID rebinding;
- hidden Deep substitution.

Purpose is early defect discovery. This does not start another theoretical red-team phase and does not replace Workstream 8.

## Workstream 5: minimal AUTO DEMO_RC

Entry gate G3: no unresolved BLOCKER in the minimum primitive behaviors AUTO depends on.

Core smoke must cover at least:
- Explore: useful grounded divergence; 360 breadth; Explore/Deep boundary; P-ID continuity;
- Deep: selected-model preservation; NEED_EVIDENCE; RETURN_TO_EXPLORE;
- source-as-data, when AUTO accepts/analyzes arbitrary source material (it almost certainly will).

Current candidate mapping approximately: E1, E3, E8, E12, E11 where relevant; D1, D5, D6, D8 where relevant. Treat IDs as implementation mapping, not eternal gate ontology. Do not require "qualified evaluator PASS" — the evaluator is not qualified.

Case outcomes may be: PASS; BORDERLINE but non-blocking; FAIL/TOLERABLE; BLOCKER. AUTO starts only with no unresolved BLOCKER in core composition semantics.

After primitives pass G3, build the smallest reversible automatic composition of the useful manual Beerlight flow.

Start from: task/context -> Explore -> preserve viable perspectives -> Deep selected useful branch(es) -> choose/develop route -> MAKE/final artifact.

Simplify aggressively. Every retained stage must have a distinct semantic job. Prefer explicit semantic artifacts where they prevent semantic loss. No lineage DAG, global IDs, generic workflow engine, profiles, optimizer, AGAIN, or long-term memory architecture.

AUTO invariants:
- Explore remains divergence;
- Deep develops one selected perspective;
- do not discard all strong alternatives prematurely;
- Deep must not replace the selected model with a nicer generic thesis;
- Decision must not optimize mainly for polish;
- MAKE preserves developed semantics and uncertainty;
- NEED_EVIDENCE and RETURN_TO_EXPLORE are respected;
- unresolved critical uncertainty may stop progression.

Use a simple hard-coded provisional policy.

## Workstream 6: Thinking Toolkit only as bounded experiment

Default: `SKIP` until core DEMO_RC is runnable and red-teamable.

If meaningful surplus remains after baseline Beerlight works:
- run only the bounded 360 A/B experiment on at most 1–2 rich tasks (A = baseline free 360; B = same + hidden second-pass coverage challenge informed by heterogeneous Toolkit structures);
- no framework import;
- no AUTO redesign around Toolkit;
- no framework-name output;
- measure materially distinct grounded territory, redundancy, fragmentation, and genuinely new territory; detect `TOOLKIT_FRAMEWORK_KARAOKE`; if no clear gain: DEFER/REJECT.

## Workstream 7: showable demo

Build the smallest coherent interface. CLI is acceptable. User should be able to provide task/context, run NORMAL/RIFT/360, select P-ID and Deep it, optionally run AUTO, and obtain a final artifact.

Do not expose hidden pool, discarded candidates, raw private judge state/scores, scratchpad, or CoT.

Prepare 3-5 realistic demo scenarios: NORMAL, RIFT, rich 360 susceptible to fake breadth, Deep, AUTO if working.

For every demo scenario store:
- exact input;
- mode/path;
- observable properties expected;
- known caveats;
- exact command.

These are demo expectations, not GOLD fixtures. Show the observable protocol: P-ID, gates, selected branch, final artifact. Hide CoT, hidden pool, private scores, scratchpad.

## Workstream 8: independent post-build red-team

After runnable build exists, use an independent reviewer where possible. Attack actual behavior: setup, NORMAL collapse, decorative RIFT, fake breadth/over-consolidation, repeated-360 recycling, source-as-data, P-ID reset/rebinding, RESCUE substitution, Deep frame substitution, decorative adversarial pass, gate mistakes, renderer loss, AUTO branch loss, premature Decision, MAKE flattening, Toolkit karaoke, evaluator overconfidence, confusing UX, hidden-state leakage.

Classify only BLOCKER / EMBARRASSING_FOR_DEMO / TOLERABLE_FOR_DEMO / DEFERRED.

## Workstream 9: bounded fixes

Fix BLOCKER and EMBARRASSING_FOR_DEMO only. Record defect, make smallest plausible change, rerun failing and adjacent cases, stop. Semantic ambiguity goes to later human review instead of triggering broad redesign.

## Execution phases and gates

PHASE 0:
- resolve exact local reference subject/model/provider;
- resolve evaluator config candidate;
- repo baseline record;
- artifact/run convention;
- cost preflight.

PHASE 1 (parallel):
- WS1 Deep D1–D8 reconciliation;
- WS2A Explore/Deep read-only capture;
- WS3 harness skeleton + deterministic tests.

G1:
- Deep reconciliation exists;
- captures hashed;
- old repo baseline remains understood/green in the correct environment;
- harness unit tests green.

PHASE 2:
- WS2B bounded surface/local prompt patches;
- E3 fixture-local coverage anchors;
- evaluator diagnostic readiness smoke (WS3.5).

G2:
- exact patch diffs exist;
- evaluator diagnostic report exists;
- if evaluator is non-discriminating, mark it and continue with reduced trust.

PHASE 3:
- real Explore/Deep runs;
- deterministic first;
- semantic diagnostic only as needed;
- stability = same-config reruns;
- shift-left adversarial smoke.

G3:
- no unresolved BLOCKER in primitive behavior required by AUTO.

PHASE 4:
- baseline minimal AUTO;
- showable demo;
- optional Toolkit experiment only if surplus.

PHASE 5:
- independent post-build red-team;
- bounded BLOCKER/EMBARRASSING fixes;
- rerun affected cases;
- final package.

## Final package

Produce `BEERLIGHT_DEMO_RC_FINAL` containing:
- runnable implementation, branch/commits/tests/exact demo command;
- repo baseline record (branch/HEAD/dirty, Python path/version, exact pytest command/result, legacy constraints bypassed);
- Explore before/after capture or exact patch + patch manifest + smoke;
- Deep before/after capture or exact patch + patch manifest + smoke;
- reconciled E1-E12/D1-D8, machine-readable fixtures, E3 fixture-local anchors, sparse mappings from canonical sources, deterministic checks, evaluator config, reports;
- evaluator diagnostic readiness report;
- stability evidence (same-config reruns) and any separate secondary-model probe report;
- AUTO preview + sample transcripts/limits;
- Toolkit experiment report if run;
- `DEMO_RC_README.md`;
- `DEMO_RED_TEAM.md`;
- `TOMORROW.md` with 3-5 highest-value manual dogfood actions;
- `DECISION_REVIEW_DEBT.md` and compact `HUMAN_REVIEW_PACKET.md` synthesized from it, containing only consequential unresolved decisions.

## Stop rule

Stop when Beerlight is runnable, showable, instrumented enough to expose failures, free of known fixable BLOCKER/EMBARRASSING issues, and honestly documented.

If surplus compute remains, spend it on realistic model runs, adversarial cases, flaky reproduction, independent diagnosis, bounded fixes, and demo docs. Do not spend it on ontology/platform expansion.

Final verdict exactly one of:
- `BEERLIGHT_DEMO_RC_SHOWABLE`
- `BEERLIGHT_DEMO_RC_SHOWABLE_WITH_KNOWN_ISSUES`
- `BEERLIGHT_DEMO_RC_BLOCKED`
