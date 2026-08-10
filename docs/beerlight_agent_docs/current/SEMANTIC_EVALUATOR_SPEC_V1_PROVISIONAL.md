# SEMANTIC_EVALUATOR_SPEC_V1_PROVISIONAL.md

**Project:** Beerlight  
**Date:** 2026-08-09  
**Status:** PROVISIONAL measurement design  
**Scope:** minimal semantic evaluator protocol only

Nothing here is HUMAN_APPROVED, GOLD, QUALIFIED, or FROZEN.

This document does not change the Beerlight semantic contract, semantic predicates, or E1–E12 / D1–D8 acceptance fixtures.

---

# 1. Purpose and claim boundary

The evaluator is a narrow, project-local semantic regression instrument.

Its legitimate claim is:

> Given criterion `C` and the supplied visible operands, evaluator configuration `E` judged the observable relation as `MET`, `VIOLATED`, or `UNCLEAR`.

It is not an oracle for:

- global novelty;
- causal truth;
- general response quality;
- hidden reasoning;
- universal human preference;
- product value;
- factual truth beyond supplied evidence;
- calibrated probability or confidence;
- human consensus.

The evaluator judges only explicit Beerlight semantic predicates or the already-defined derived trajectory-novelty rule.

---

# 2. Measurement layers must remain separate

Three result classes must not be conflated.

## 2.1 `DETERMINISTIC_CHECK`

Used when software can establish the relevant property exactly from the supplied artifacts.

Examples:

- schema validity;
- enum validity;
- duplicate/recycled P-ID;
- monotonic P-ID allocation;
- required reference existence;
- exact mode/state tag where the protocol exposes one;
- forbidden combination such as structurally exposed `NEED_EVIDENCE + LEVER`;
- evidence excerpt not appearing in the claimed input block.

If a deterministic check fully establishes a Beerlight contract failure, the case may fail without an LLM semantic judgment.

Do not ask an LLM to reconfirm an exact deterministic failure.

## 2.2 `SEMANTIC_JUDGMENT`

Used only for relations that require semantic interpretation, such as:

- materially distinct model vs paraphrase/refinement;
- semantic preservation vs substitution;
- source-relative grounding;
- epistemic honesty;
- semantic mode crossing not exposed by exact tags;
- whether a Deep gate is justified by the visible model state;
- source-as-data authority where the designation/delegation relation is natural language.

## 2.3 `EVAL_ERROR`

Evaluator infrastructure/output failure.

Examples:

- malformed JSON after allowed retry;
- invalid enum after allowed retry;
- wrong `criterion_id` after allowed retry;
- evidence origin not supplied to the evaluator;
- quoted evidence excerpt absent from the claimed origin after allowed retry;
- evaluator call unavailable.

`EVAL_ERROR` is never converted into Beerlight `FAIL`.

If a Beerlight failure was already established independently by `DETERMINISTIC_CHECK`, that subject failure remains valid. Otherwise evaluator failure leaves the semantic case unadjudicated.

---

# 3. Unit of judgment

One evaluator call judges **one criterion only**.

No holistic score.

No weighted quality function.

No instruction to judge “the answer overall.”

Input consists of:

1. one `criterion_id`;
2. the frozen criterion definition and its `MET / VIOLATED / UNCLEAR` anchors;
3. only the visible operand texts needed for that criterion.

The evaluator must not infer criterion semantics from the ID alone.

For `TRAJECTORY_NOVELTY`, pass the already-defined derived rule explicitly rather than inventing a new primitive predicate.

---

# 4. Minimal evaluator input packet

Conceptual input shape:

```json
{
  "criterion": {
    "criterion_id": "SEMANTIC_PRESERVATION",
    "definition": "frozen observable definition",
    "met_anchor": "frozen MET anchor",
    "violated_anchor": "frozen VIOLATED anchor",
    "unclear_anchor": "frozen UNCLEAR anchor",
    "does_not_establish": "relevant frozen limitation"
  },
  "operands": [
    {
      "origin_id": "baseline",
      "text": "..."
    },
    {
      "origin_id": "candidate",
      "text": "..."
    }
  ]
}
```

`origin_id` is a local label supplied with the input. The evaluator may cite only supplied `origin_id` values.

No character offsets are requested from the model.

---

# 5. Minimal judge prompt

The evaluator prompt should be short and invariant-oriented.

```text
You are the Beerlight Semantic Evaluator.

Judge exactly ONE supplied semantic criterion against ONLY the supplied visible texts.

Use the supplied criterion definition and MET / VIOLATED / UNCLEAR anchors exactly.
Do not judge general quality, global novelty, causal truth, hidden reasoning, or facts not available in the supplied texts.

Verdict:
- MET: the observable criterion is clearly satisfied.
- VIOLATED: a material violation defined by the criterion is clearly present.
- UNCLEAR: the supplied texts or criterion do not support a safe MET/VIOLATED decision.

Return JSON only.

Evidence:
- quote the minimum exact excerpt(s) needed for the decision;
- copy excerpts verbatim from the supplied operand texts;
- use only supplied origin_id values;
- do not calculate offsets;
- do not present your own paraphrase as evidence.

Justification:
- concise;
- observable;
- map the quoted evidence to the criterion boundary;
- no free-form chain-of-thought.

If material evidence is missing or the criterion boundary is genuinely underdetermined, return UNCLEAR rather than guessing.
```

The criterion packet and operands follow this instruction.

No few-shot examples are required by the minimal protocol itself. Examples may be added only during later evaluator development if challenge-set evidence shows a recurring judge error. Adding examples changes evaluator configuration and requires requalification.

---

# 6. Minimal evaluator output schema

```json
{
  "criterion_id": "DISTINCT_MODEL",
  "verdict": "MET",
  "evidence": [
    {
      "origin": "candidate_a",
      "excerpt": "exact excerpt copied from candidate A"
    },
    {
      "origin": "candidate_b",
      "excerpt": "exact excerpt copied from candidate B"
    }
  ],
  "justification": "One or two concise observable sentences."
}
```

## Required fields

- `criterion_id`
- `verdict`
- `evidence`
- `justification`

## Verdict enum

```text
MET
VIOLATED
UNCLEAR
```

## Evidence requirements

Each evidence item contains only:

```text
origin
excerpt
```

`origin` must equal a supplied `origin_id`.

`excerpt` must be a verbatim substring of the corresponding supplied text.

Evidence should cover the decisive sides of the relation where relevant:

- distinctness: both compared models where possible;
- preservation: baseline/prior object + transformed object;
- grounding: candidate claim + relevant source/context;
- mode/source authority: instruction/source + observed response where needed;
- gate integrity: model/evidence-debt state + gate/action evidence.

This is an audit requirement, not a request for chain-of-thought.

## Justification requirements

- short;
- no hidden-reasoning narrative;
- no confidence score;
- no invented evidence;
- no unrelated critique;
- no global judgment.

---

# 7. Deterministic validation of evaluator output

Before using a semantic verdict, validate:

1. valid JSON / schema;
2. `criterion_id` exactly matches requested criterion;
3. `verdict ∈ {MET, VIOLATED, UNCLEAR}`;
4. `evidence` has at least one item;
5. every evidence `origin` exists in the supplied operands;
6. every evidence `excerpt` is an exact non-empty substring of that operand;
7. justification is present.

An excerpt may be found deterministically by substring search. The evaluator never supplies offsets.

Deterministic evidence validation establishes only that the quote exists in the claimed text. It does not establish that the quote semantically supports the verdict.

---

# 8. Invalid evaluator-output policy

For one planned semantic call:

```text
schema-invalid / invalid evidence / invalid origin
    => retry once with the identical evaluator input

second invalid result
    => EVAL_ERROR
```

If the retry becomes valid:

- retain/log the first evaluator-format failure;
- do not silently pretend both attempts were clean;
- for strict qualification/regression use, route the affected case to human review / non-clean status.

An evaluator parse/evidence failure must never become subject-model `FAIL`.

---

# 9. Internal verdict vs external case status

Internal judge verdict:

```text
MET
VIOLATED
UNCLEAR
```

External semantic-case status:

```text
PASS
FAIL
BORDERLINE
```

Single valid judgment mapping:

```text
MET       -> candidate semantic PASS signal
VIOLATED  -> candidate semantic FAIL signal
UNCLEAR   -> BORDERLINE / HUMAN
```

For actual acceptance use, the default policy is two independent semantic calls.

---

# 10. Default future two-call policy

Run the same frozen evaluator configuration twice independently on the same criterion packet.

Only valid evaluator results enter semantic aggregation.

```text
MET + MET
    => PASS

VIOLATED + VIOLATED
    => FAIL

anything involving UNCLEAR
    => BORDERLINE / HUMAN

MET + VIOLATED
    => BORDERLINE / HUMAN
```

No automatic third-call majority vote.

No averaging.

No confidence-weighting.

Disagreement is itself an evaluator-stability signal.

If either required semantic call ends in persistent `EVAL_ERROR`, the semantic measurement status is `EVAL_ERROR`, not Beerlight `FAIL`.

---

# 11. Multiple criteria in one Beerlight acceptance case

The acceptance sparse matrix already determines which criteria are actually needed.

Evaluate only those criteria.

For each required semantic criterion, obtain its external status under the two-call policy.

Then:

```text
deterministic Beerlight failure established
    => case FAIL

else any required semantic criterion = FAIL
    => case FAIL

else all required semantic criteria = PASS
    => case PASS

else any required semantic criterion = BORDERLINE
    => case BORDERLINE / HUMAN

else evaluator infrastructure prevents adjudication
    => EVAL_ERROR
```

Do not ask one judge call to decide several predicates at once merely to save calls.

---

# 12. Criterion-specific constraints

The evaluator uses the existing predicate definitions. It must not expand them.

## `DISTINCT_MODEL`

Judge local semantic relationship, not topic difference or lexical difference.

A material structural change may be sufficient.

Wording, actor, metaphor, example, manifestation, or refinement alone is not.

The evaluator must permit `UNCLEAR` at the known nested-mechanism/system-boundary/intervention boundaries.

## `COVERAGE_BREADTH`

Judge the map/set as a whole.

Raw card count and family count are not breadth.

A long map may violate breadth.

Do not infer exhaustive missing territories from imagination; omitted territory must be grounded in supplied source/context.

## `SEMANTIC_PRESERVATION`

Compare baseline semantic object with transformed/developed object.

Protect the distinctive semantic core, not literal wording.

Allowed narrowing/clarification must not be misclassified as substitution.

## `SOURCE_GROUNDING`

Judge relation to supplied source/context only.

Do not judge world truth.

Do not treat plausible external knowledge as supplied evidence.

## `EPISTEMIC_HONESTY`

Judge whether load-bearing uncertainty/evidence debt is represented consistently with the supplied evidence.

Do not demand fixed epistemic vocabulary.

## `MODE_BOUNDARY`

Judge semantic operation, not headings or length.

Use deterministic mode/state fields instead when they already fully establish the issue.

## `GATE_INTEGRITY`

Judge consistency between visible model/evidence state, declared gate, and downstream action.

Do not judge whether the model is true in the world.

## `SOURCE_AS_DATA`

Judge whether source material acquired unauthorized instruction authority.

Do not treat command-like text as an active instruction merely because it occurs inside a user-provided source.

---

# 13. Human routing

Human review is mandatory when:

- either semantic call returns `UNCLEAR`;
- two valid calls disagree;
- evaluator output is repeatedly malformed/invalid;
- evidence excerpts are repeatedly invalid;
- required source/context is insufficient;
- the criterion itself appears ambiguous;
- a judgment would require global novelty;
- a judgment would require external causal/factual truth;
- a substantially new semantic failure mode appears outside calibrated challenge coverage;
- evaluator behavior shows a serious Russian/code-switch instability cluster;
- evaluator configuration is unqualified.

Human review is not a hidden fourth semantic verdict. It is routing.

---

# 14. Configuration identity

A qualification claim belongs to one frozen evaluator configuration.

Record at least:

```text
evaluator_version
provider
exact model/snapshot
prompt version/hash
criterion/predicate spec version
output schema version
sampling/reasoning settings
context-construction version
two-call aggregation policy version
execution timestamp
```

No attempt is made here to optimize several judge models.

Changing a semantically relevant item creates a new evaluator configuration requiring requalification.

---

# 15. Development corpus vs Beerlight acceptance corpus

Hard separation:

```text
evaluator_challenge_lineage
∩
beerlight_acceptance_lineage
=
∅
```

The challenge set in `EVALUATOR_CHALLENGE_V1_PROVISIONAL.md` is independently authored.

It must not contain copied E1–E12 / D1–D8 text.

Beerlight acceptance fixtures must not be used as evaluator training/few-shot gold.

If a Beerlight acceptance case later exposes an evaluator weakness:

- do not tune directly on that acceptance item and continue calling it independent;
- author a new independent evaluator diagnostic representing the failure mechanism;
- if evaluator changes, use a fresh untouched holdout before qualification.

---

# 16. Challenge-set status

The challenge set produced in this pass is visible and inspectable.

Therefore it is:

```text
DEVELOPMENT / META-EVALUATION CHALLENGE CORPUS
```

It is **not** an untouched holdout.

If its failures are used to modify the evaluator, later qualification needs a separate unseen holdout.

---

# 17. Sentinel qualification conditions

Do not invent a percentage threshold from a 12–16 case corpus.

Reject or withhold qualification when any of these occurs:

1. unacceptable false `MET/PASS` on a designated critical negative sentinel;
2. a deliberate ambiguity sentinel is repeatedly forced into `MET` or `VIOLATED` instead of `UNCLEAR/BORDERLINE`;
3. evidence excerpts are invalid, fabricated, or assigned to nonexistent origins;
4. systematic failure appears on Russian or natural Russian-English code-switch cases;
5. serious two-call instability occurs on critical sentinels;
6. unexplained repeated `EVAL_ERROR` occurs on qualification cases;
7. the judge repeatedly substitutes general-quality/world-truth judgments for the supplied criterion.

Passing sentinels means only that the evaluator survived this local sanity check.

It does not produce an accuracy estimate.

---

# 18. Explicit non-features

V1 does not add:

- judge panel;
- majority voting;
- judge-of-judge;
- numeric confidence;
- embeddings;
- NLI voting;
- evaluator memory;
- generic eval DSL;
- generic production framework;
- hidden chain-of-thought capture;
- global quality score;
- automatic external fact checking.

---

# 19. What the evaluator can establish

Under one frozen, locally challenged evaluator configuration, it can provide project-local regression evidence that a supplied visible output:

- met, violated, or ambiguously related to one explicit Beerlight semantic predicate;
- preserved or substituted a supplied semantic object;
- was or was not source-grounded relative to supplied text;
- represented evidence debt honestly or not;
- stayed within a supplied semantic mode boundary or not;
- chose a gate consistent or inconsistent with visible model state;
- treated analyzed source as data or improperly as instruction;
- represented materially distinct local models or redundant models under the Beerlight definition;
- represented trajectory novelty only relative to supplied prior territory.

---

# 20. What the evaluator cannot establish

It cannot establish:

- global originality;
- actual causal truth;
- general response quality;
- correctness of hidden reasoning;
- universal human preference;
- population-level evaluator accuracy;
- human consensus;
- calibrated confidence;
- robust performance on arbitrary Russian/code-switched text;
- statistical construct validity from this small corpus;
- independence from the subject model;
- future equivalence after evaluator/model updates;
- Beerlight product value.

---

# 21. Deterministic vs semantic summary

## Deterministic

- evaluator schema and enum validation;
- evidence-origin validation;
- exact evidence substring validation;
- exact IDs/reference existence;
- duplicate/recycled IDs;
- literal mode/gate/LEVER combinations where structurally exposed;
- any other exact acceptance check already designated deterministic.

## Semantic

- `DISTINCT_MODEL`;
- `COVERAGE_BREADTH`;
- `SEMANTIC_PRESERVATION`;
- `SOURCE_GROUNDING`;
- `EPISTEMIC_HONESTY`;
- natural-language `MODE_BOUNDARY`;
- semantic `GATE_INTEGRITY`;
- natural-language `SOURCE_AS_DATA`;
- derived trajectory novelty relative to supplied prior territory.

## Evaluator infrastructure

- malformed judge output;
- invalid evidence;
- failed judge call;
- unresolved two-call instability.

These are not subject-model semantic failures.

---

EVALUATOR_SPEC_COMPLETE
