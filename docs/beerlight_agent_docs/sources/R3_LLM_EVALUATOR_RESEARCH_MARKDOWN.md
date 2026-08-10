# LLM Evaluator Research for Beerlight

## Executive decision and capability boundary

**Executive decision**

Beerlight can reasonably use an LLM judge as a **narrow semantic regression instrument**, but only if the claim being tested is operationalized as an observable relation between supplied texts: response vs source, response vs original claim, response vs prior turns, or response vs a criterion. The evaluator should not be treated as an oracle for “quality,” “novelty,” or causal truth.

The smallest defensible design is:

> **criterion-specific pointwise judging → structured `PASS | FAIL | BORDERLINE` → evidence spans → short observable justification → repeated-call stability check → human routing on ambiguity or instability.**

This recommendation is deliberately narrower than MT-Bench/G-Eval-style holistic scoring. Foundational work showed useful human agreement from strong judges, but adversarial meta-evaluation, self-preference work, multilingual studies, and 2025–2026 reliability studies all show that apparently strong aggregate agreement can coexist with serious case-level failures, prompt sensitivity, language degradation, or systematic bias. citeturn16view0turn16view2turn16view5turn15view8turn17search0

**Recommendation:** Use an LLM evaluator only for explicitly defined, externally observable semantic predicates. Treat its verdict as regression evidence, not ground truth.

**Evidence class:** **MIXED_EVIDENCE**

**Supporting evidence:** MT-Bench/Chatbot Arena in 2023 established that strong LLM judges can agree with human preferences at useful rates on general assistant outputs, while G-Eval showed improved human correlation for structured evaluation of summarization/dialogue. LLMBar then demonstrated that attractive-looking but instruction-violating alternatives could fool several judges below chance on its adversarial subset, with even the strongest GPT-4 setup materially below expert annotators. More recent work finds substantial task/model dependence. citeturn1search0turn16view8turn16view0turn20view1

**Important limitation:** None of those studies directly validates Beerlight's notions of “structural model,” “new territory,” “decorative metaphor,” or Russian multi-turn semantic continuity. Those concepts must be turned into local testable predicates and calibrated on Beerlight-specific **evaluator fixtures**.

### What an LLM judge can establish here

For Beerlight, the evidence is strongest when the judgment resembles **semantic entailment, contradiction, instruction adherence, or comparison against supplied context**, rather than unconstrained aesthetic preference.

| Beerlight property | Defensible interpretation | Evidence relationship |
|---|---|---|
| Grounding in supplied source | “Is this material claim supported, contradicted, or unsupported by the supplied text?” | Relatively strong analogue from factual-consistency/NLI and reference-based judging. citeturn15view6turn15view7turn20view3 |
| Preservation vs substitution | “Does the later formulation retain the specified proposition, or replace a material component?” | Strong semantic-relation analogue; local calibration still required. |
| Honest abstention | “Given only supplied evidence, does the response abstain when the rubric says evidence is insufficient?” | Instruction-following analogue; LLMBar supports adversarial testing of superficial compliance. citeturn16view0turn16view1 |
| Correct mode boundary | Semantic compliance with an explicit mode contract | Reasonable instruction-following analogue; exact mode tags should instead be deterministic. citeturn16view0 |
| Semantic continuity across turns | “Does this turn preserve/change specifically identified propositions from earlier turns?” | Plausible but less directly validated, especially for long Russian context. |
| Distinct structural/causal model vs paraphrase | “Do the two texts posit materially different variables, causal links, constraints, or mechanisms?” | Indirect evidence. Needs highly concrete anchors and adversarial fixtures. |
| Structural shift vs decorative metaphor | “Did explanatory structure change, or only terminology/analogy?” | Indirect evidence; close to LLMBar's superficial-similarity adversarial construction. citeturn16view1 |
| New vs recycled territory | Only defensible as “new relative to the supplied comparison set” | No basis for global novelty claims. |

The important reframing is that **“new territory” cannot mean objectively new in the world**. A judge can only assess novelty relative to the conversation, supplied model inventory, or an explicit comparison corpus. Similarly, source grounding means “supported by this source,” not “true in reality.”

**Recommendation:** Encode “distinct model,” “structural shift,” and “new territory” as changes in named semantic invariants—such as variables, causal arrows, mechanism, scope, prediction, or intervention—not as holistic impressions.

**Evidence class:** **INDIRECT_EVIDENCE**

**Supporting evidence:** LLMBar deliberately constructed adversarial cases where an incorrect candidate superficially resembled a correct answer or neighboring instruction; these exposed major evaluator weaknesses that ordinary preference sets did not. HD-Eval likewise found value in decomposing evaluation criteria rather than relying on an undifferentiated quality judgment. citeturn16view0turn16view1turn18search2

**Important limitation:** There is no published benchmark establishing that contemporary LLM judges reliably identify Beerlight-style “causal model novelty.” This is precisely what the local evaluator gold fixtures must test.

### What it cannot establish

The evaluator calibration described here cannot establish:

- that a Beerlight causal model is **actually causally correct** unless correctness follows from supplied evidence;
- that an idea is globally original rather than merely absent from supplied context;
- that the subject model's hidden reasoning was sound;
- that the evaluator's explanation faithfully exposes its own internal causal reasoning;
- that a PASS represents human consensus;
- that a judge from another vendor constitutes statistically independent evidence;
- that performance on roughly 15–20 fixtures generalizes to the full distribution of Russian/code-switched Beerlight outputs;
- that evaluator confidence is a calibrated probability;
- or that two evaluator versions are measurement-equivalent after a model/provider change.

Turpin et al. in NeurIPS 2023 showed that chain-of-thought explanations can rationalize answers influenced by hidden prompt biases without mentioning those influences. That makes visible judge reasoning useful as an **audit artifact**, not as proof that the judge reached its decision for the stated reason. citeturn13search3turn13search7

The 2026 large-scale study by Norman et al.—currently a **preprint**, so weaker evidence than the peer-reviewed 2023–2025 work—makes the distinction between reliability and validity especially explicit: highly reproducible judges can still exhibit substantial systematic bias, and the ranking of judge models changed materially across benchmarks. citeturn17search0turn20view1

## Failure modes, model-family effects, and Russian

**Relevant failure modes and biases**

The following risks should not all be treated as equally established.

| Failure mode | Evidence status | Engineering implication |
|---|---|---|
| Position/order bias | Strong, repeated evidence | Avoid pairwise unless needed; if used, swap AB/BA. |
| Verbosity/style bias | Real but heterogeneous and protocol-dependent | Include controlled length/style perturbation fixtures; do not assume a fixed direction. |
| Self-preference | Strong evidence in tested settings | Same-model judging should not be assumed neutral. |
| Same-family preference | Emerging evidence; less mature | Cross-family is preferable as a heuristic, not proof of independence. |
| Reference-answer effects | Strong evidence that references change verdicts; often improve factual judging | Supply references when the construct is explicitly reference-relative; treat the reference as part of the measurement definition. |
| Rubric/prompt sensitivity | Strong evidence | Prompt/rubric/examples constitute evaluator versioned code. |
| Repeated-call instability | Strong current evidence | Measure test-retest locally and route disagreements. |
| Language effects | Strong multilingual evidence; some Russian evidence | Russian fixtures are mandatory. |
| Agreement/sycophancy bias | Adjacent evidence, limited direct Beerlight-judge evidence | Probe rather than assume. |
| Correlated judge errors | Increasing 2026 evidence, mostly preprint | Ensembles/cross-family judges do not provide independent votes automatically. |

**Position bias.** Pairwise assessment can outperform absolute scoring in some NLG settings, but the same literature reports strong positional effects. Liusie et al. found pairwise comparative assessment effective while explicitly identifying positional bias. Panickssery et al. observed pairwise preference reversals under order swapping at rates of 25%, 58%, and 89% for the three evaluators in their summarization experiments. A systematic 2025 study found position behavior depends substantially on both task and judge. citeturn18search1turn16view3turn20view2

The current 2026 large-scale preprint reinforces the heterogeneity rather than establishing a universal magnitude: on its MT-Bench audit, position-bias measures ranged from 0.002 to 0.192 across judges, and even models from the same provider family differed dramatically. citeturn20view1

**Verbosity/style bias.** The original MT-Bench work identified verbosity as a judge bias. However, it would now be incorrect to turn this into the rule “LLM judges always strongly prefer longer responses.” The 2026 Norman et al. audit measured very small length/verdict correlations under its particular pairwise MT-Bench protocol, while another 2026 controlled preprint found heterogeneous behavior across models, including positive, neutral, and reversed length tendencies. Therefore **verbosity bias is an empirical probe, not a universal correction coefficient**. citeturn1search0turn20view1turn19search7

**Self-preference.** Panickssery et al., NeurIPS 2024, found GPT-3.5, GPT-4, and Llama 2 evaluators disproportionately favored their own summaries in their studied tasks and linked stronger self-recognition with stronger self-preference. The authors themselves caution that controlling perfectly for true generation quality is difficult, so the evidence does not imply every self-judgment is biased. citeturn16view2turn16view4

**Reference effects.** References should not be viewed as harmless additional context. A July 2026 multilingual study found that adding reference information materially changed verdicts and generally improved agreement with human correctness judgments, especially where reference-free judges over-credited incorrect answers. It also found that the same extracted answer could be judged differently once a reference was visible. citeturn20view3

For Beerlight this is mostly desirable: when judging **preservation**, **grounding**, or **continuity**, the original/source/prior text is not an optional hint; it defines the construct. The mistake would be calling such a result “reference-free semantic quality.”

**Rubric and prompt sensitivity.** LLMBar's best prompting strategy improved GPT-4 performance on its adversarial set by about ten percentage points, directly demonstrating that the evaluator prompt is part of the instrument rather than incidental wording. Liu et al.'s 2024 calibration work similarly calibrates evaluator criteria from human labels, while HD-Eval decomposes criteria to improve alignment. citeturn16view0turn15view0turn18search2

**Agreement bias.** There is extensive broader evidence that contemporary LLMs can become sycophantic—favoring agreement with a user's asserted position over independent reasoning—but direct evidence that this manifests as a distinct, stable **Beerlight semantic-judge** bias is weaker. A 2025 sycophancy study found the effect across GPT-4o, Claude Sonnet, and Gemini on its tested tasks, but that is not the same construct as evaluator acquiescence. citeturn19search3

Therefore the correct classification here is **INDIRECT_EVIDENCE**: add one or two fixtures where the candidate confidently asserts “this preserves the original model” while actually substituting it, but do not invent an “agreement-bias correction.”

### Same-model vs different-model judge

**Recommendation:** Prefer a judge from a different model/provider family than the subject model when a comparably qualified judge is available, but select the judge primarily on the local evaluator gold/holdout—not on family separation alone.

**Evidence class:** **MIXED_EVIDENCE**

**Supporting evidence:** Self-model bias is empirically supported by Panickssery et al. 2024. More recent studies report family-level preference effects, but this evidence base is less established. Meanwhile, the 2026 cross-model literature increasingly finds correlated errors across nominally different judges; a panel of different models should therefore not be modeled as independent voters. citeturn16view2turn19search16turn14search3

**Important limitation:** “Different family” is a **risk-reduction heuristic**, not independent replication. Models may share training data, preference conventions, benchmark contamination, stylistic priors, or common failure heuristics. The 2026 panel work on correlated errors is currently preprint evidence and should not be overstated. citeturn14search3turn14search19

A useful selection rule is thus:

> qualified cross-family judge > equally qualified same-family judge  
> but  
> locally validated same-family judge > unvalidated cross-family judge.

There is no evidence-based reason for Beerlight V1 to use a panel of three or more families. That increases cost and apparent sophistication without solving shared-bias validity.

### Russian and multilingual considerations

**NO_DIRECT_EVIDENCE**

I found no direct study establishing reliable LLM-as-judge performance for the specific task:

> Russian/code-switched, multi-turn semantic regression involving causal-model distinction, structural novelty, claim preservation, and mode continuity.

The nearest evidence is materially weaker than that target.

Fu and Liu, Findings of EMNLP 2025, evaluated five model families across five tasks and 25 languages. They found low cross-language judgment consistency overall, with average Fleiss' κ around 0.3, worse performance in lower-resource languages, and no simple guarantee that greater model size or multilingual training solved the problem. This measures multilingual consistency, not Beerlight correctness. citeturn16view5

REPA, a 2025 Russian-specific preprint, is closer. It contains 1,003 Russian queries, 2,000 generated responses, ten human-annotated error dimensions, and eight LLM judges. The authors report a noticeable Russian-vs-English judge-performance gap and only partial alignment of LLM- and human-derived rankings. Its dimensions include request following, factuality, repetition, contradiction, refusal and code-switching. citeturn16view6turn16view7

But REPA's “code-switching” criterion treats less switching as preferable, whereas Beerlight explicitly expects Russian with English technical vocabulary. It therefore does **not** validate Beerlight's desired code-switching behavior. citeturn16view7

**Nearest analogue:** Russian fine-grained response judging in REPA plus multilingual consistency evaluation from Fu & Liu.

**Extrapolation distance:** **medium-to-high**. Beerlight adds discourse-level structural semantics, expected code-switching, multi-turn state, and project-specific conceptual distinctions.

**Recommendation:** A judge is not qualified for Beerlight merely because it performs well in English. At least a majority of evaluator fixtures should reflect the actual Russian/code-switched surface distribution, including Russian paraphrases whose semantic distinction is intentionally subtle.

**Evidence class:** **MIXED_EVIDENCE**

**Supporting evidence:** Direct evidence exists that language changes judge reliability and that Russian fine-grained judgment is harder than English in at least one dedicated study. citeturn16view5turn16view6

**Important limitation:** No publication gives a defensible Russian fixture count or Russian/English ratio for Beerlight. The “majority” recommendation is an engineering choice justified by deployment distribution, not a statistically validated threshold.

Do **not** automatically translate Russian cases into English for judging. That changes the tested object and may erase precisely the lexical ambiguity, terminology, discourse continuity, or code-switching behavior that the regression test is intended to detect.

## Rubric, verdict, evidence, thresholds, and confidence

### Rubric and verdict design

For this harness, four common designs have different failure surfaces.

| Design | Advantage | Main problem for Beerlight | Verdict |
|---|---|---|---|
| Binary PASS/FAIL | Minimal | Forces ambiguous partial cases into a gate | Too brittle alone |
| Ordinal 1–5/etc. | Expresses degree | Introduces poorly anchored distances and multiple thresholds | Unnecessary |
| Criterion-by-criterion pointwise | Directly tests a semantic invariant; auditable | Requires explicit rubric | **Recommended** |
| Pairwise | Human-intuitive for “which answer is better?”; can outperform scoring in some NLG tasks | Position bias; requires a comparator; asks a different question from invariant satisfaction | Use only for genuine preference comparisons |

Pairwise evaluation is not generally “better.” Liusie et al. 2024 found advantages over absolute scoring for moderate-sized NLG judges, but pairwise evaluation also introduces a well-documented position problem. A 2025 model-ranking study further found cases where more costly pairwise evaluation did not outperform pointwise ranking. The relevant conclusion is task dependence, not a universal hierarchy. citeturn18search1turn14search1turn20view2

Beerlight is fundamentally asking:

> Does this output satisfy semantic invariant X?

not:

> Is response A generally better than response B?

That makes criterion-specific pointwise classification a closer construct match.

**Recommendation:** For each acceptance case, evaluate only the criterion or small set of criteria that case is designed to test. For each criterion return `MET | VIOLATED | UNCLEAR`; derive the externally visible `PASS | FAIL | BORDERLINE` deterministically.

**Evidence class:** **MIXED_EVIDENCE**

**Supporting evidence:** Fine-grained/decomposed criteria have repeatedly been used to improve evaluator alignment and auditability, including HD-Eval and evaluator-calibration work. Pairwise studies demonstrate useful comparative behavior but also substantial position bias. citeturn18search2turn15view0turn18search1

**Important limitation:** The exact three-way label set is an engineering design, not a result established by those papers. Its purpose is safe routing, not claiming a statistically calibrated third class.

A minimal deterministic aggregation is:

```text
any required criterion = VIOLATED
    => FAIL

all required criteria = MET
    => PASS

otherwise
    => BORDERLINE
```

`BORDERLINE` should mean **“the evaluator cannot safely map the observed case to PASS or FAIL under the rubric”**, not “50% confidence” and not “moderately good.”

### Evidence returned by the evaluator

A verdict alone is insufficient for diagnosing regressions. Conversely, generated step-by-step reasoning creates a misleading appearance of observability.

**Recommendation:** Return:

```text
criterion_id
verdict
evidence excerpts
concise observable justification
```

Do not require or store free-form step-by-step chain-of-thought.

**Evidence class:** **MIXED_EVIDENCE**

**Supporting evidence:** G-Eval 2023 showed that a CoT/form-filling judging procedure could improve correlation with human ratings on its tested summarization/dialogue tasks, so it would be wrong to claim that reasoning scaffolds are inherently useless. But Turpin et al. 2023 showed that visible CoT can rationalize decisions driven by unreported biases. More recent work on judge reasoning likewise does not show that generated explanations are faithful introspective traces. citeturn16view8turn13search3turn13search7

**Important limitation:** Evidence excerpts and a concise rationale make the decision **inspectable**, not necessarily causally faithful. They are primarily debugging/audit artifacts.

The distinction should be explicit:

- **Private/internal judge reasoning:** whatever computation the model/provider uses internally. Beerlight need not control it.
- **User-visible justification:** a short statement mapping quoted observable evidence to one rubric condition.
- **Evidence:** exact text fragments from source, prior turn, original claim, or candidate response—not an evaluator-generated paraphrase presented as evidence.

A suitable schema concept is:

```json
{
  "criterion_id": "claim_preservation",
  "verdict": "PASS",
  "evidence": [
    {
      "origin": "original",
      "excerpt": "..."
    },
    {
      "origin": "candidate",
      "excerpt": "..."
    }
  ],
  "justification": "The candidate retains X and Y; no material replacement of Z is present."
}
```

For a grounding criterion, evidence should come from both the source and candidate where possible. For a mode criterion, the relevant response span may suffice.

Evidence excerpts also permit cheap deterministic validation: Beerlight can verify that every quoted excerpt actually occurs in the referenced supplied text.

### PASS / FAIL / BORDERLINE anchors

Do not calibrate an opaque global numerical threshold.

The rubric should define observable anchors such as:

**PASS**
: All material components specified by the criterion are present/preserved; no material contradictory substitution appears.

**FAIL**
: At least one named material component is contradicted, removed, replaced, or unsupported in a way the criterion explicitly defines as substantive.

**BORDERLINE**
: The supplied texts genuinely underdetermine the criterion, or the candidate mixes preservation and material change such that the rubric does not settle the classification.

For “distinct causal model,” an anchor could define material distinction as change in at least one of:

> causal direction, operative mechanism, relevant state variable, constraint, intervention, or distinct observable prediction.

A terminology change without such a difference would be FAIL for “new structural model.” This exact ontology is a Beerlight domain definition, not something the literature can supply.

Examples/few-shot cases can materially alter judge behavior; LLMBar showed approximately ten percentage points of improvement from prompt strategy on its adversarial set, and calibration research explicitly uses human-labeled examples to align criteria. That is evidence for **testing examples empirically**, not blindly adding many few-shots. citeturn16view0turn15view0

**Recommendation:** Begin with explicit anchors and at most a small number of evaluator-gold examples only where development-set evidence shows that they repair a recurring error. Freeze examples as part of the evaluator prompt version.

**Evidence class:** **INDIRECT_EVIDENCE**

**Supporting evidence:** Evaluator performance is demonstrably prompt- and criterion-sensitive. citeturn16view0turn15view0turn18search2

**Important limitation:** There is no evidence-based universal optimal number of few-shot examples. Adding examples can itself create anchoring, lexical imitation, or fixture overfitting.

### Test-retest stability

Current evidence rejects an assumption that an identical judge prompt reliably produces the same judgment.

Haldar and Hockenmaier's 2025 Rating Roulette study found low intra-rater reliability across repeated LLM-judge runs on several NLG settings, with performance varying across models and tasks. Their SummaC experiment also found that three-run majority voting could improve human-label accuracy for the tested judges. citeturn15view8turn16view9

But a crucial counterpoint is that **stability is not correctness**. The 2026 Norman et al. preprint found examples with test-retest reliability above 0.98 while position bias remained substantial; deterministic repetition can consistently reproduce the same systematic mistake. citeturn17search1

Sampling policy is also not settled. Rating Roulette found that disabling sampling reduced variance but slightly degraded accuracy for its tested models, whereas other studies report that higher temperature increases variance. Thus the literature does **not** justify a universal “temperature 0 is always optimal” rule. citeturn16view9turn20view0

**Recommendation:** Fix one sampling configuration and qualify that exact configuration. For Beerlight's low-volume semantic gates, use two independent evaluations of each acceptance case and require verdict concurrence for automatic PASS/FAIL. Any disagreement becomes BORDERLINE/human review rather than being hidden by majority vote.

**Evidence class:** **INDIRECT_EVIDENCE**

**Supporting evidence:** Repeated-call instability is directly documented; repeated sampling can improve some judge results, while reliability can coexist with systematic bias. citeturn15view8turn16view9turn17search1

**Important limitation:** **Two calls is a conservative engineering default, not a literature-derived optimum.** Three-call majority vote has empirical support in particular benchmarks, but would suppress an important diagnostic signal here: disagreement. For a regression gate, preserving that signal is more useful than manufacturing a majority.

### Confidence handling

Do not ask the judge for a `0–100% confidence` field in V1.

A 2025 preprint focused specifically on LLM-as-judge confidence reports systematic overconfidence, with stated confidence exceeding observed correctness. Broader uncertainty research similarly finds that verbal confidence is not automatically calibrated. citeturn15view9

With only 15–20 local gold fixtures, Beerlight also lacks enough data to calibrate a useful continuous probability.

**Recommendation:** Do not route based on verbalized judge confidence. Route on observable evaluator signals: `BORDERLINE`, repeated-call disagreement, missing evidence, invalid evidence, insufficient supplied context, malformed output, or unqualified evaluator version.

**Evidence class:** **DIRECT_EVIDENCE** for rejecting uncalibrated confidence as a probability; **INDIRECT_EVIDENCE** for the exact routing scheme.

**Supporting evidence:** Empirical LLM-judge confidence studies identify overconfidence. citeturn15view9

**Important limitation:** Properly calibrated confidence could eventually help routing, but that would require a materially larger held-out calibration corpus. Nothing in the current 15–20-case regime supports it.

## Calibration, holdout discipline, small-N limits, and drift

### Calibration methodology

The evaluator fixture corpus and Beerlight acceptance corpus must remain separate not merely in name, but by **content lineage**.

A minimal lifecycle is:

```text
author evaluator fixtures
        ↓
split development / untouched holdout
        ↓
iterate judge + rubric + prompt on development only
        ↓
freeze evaluator configuration
        ↓
run untouched holdout
        ↓
qualify or reject evaluator version
        ↓
use frozen evaluator on Beerlight acceptance cases
```

This follows the general meta-evaluation logic used in LLMBar and evaluator-calibration research: the judge itself is evaluated against independent labeled cases before downstream use. citeturn16view0turn15view0

**Recommendation:** Treat the entire following tuple as the evaluator version:

```text
provider
exact model/snapshot
system/evaluator prompt
rubric text
few-shot examples
output schema
sampling parameters
context construction
aggregation/stability rule
```

**Evidence class:** **DIRECT_EVIDENCE** that models and prompts affect outcomes; **INDIRECT_EVIDENCE** for this exact configuration tuple.

**Supporting evidence:** Prompt strategies materially change judge accuracy; current providers explicitly document behavioral differences across model snapshots. citeturn16view0turn15view10turn15view11turn15view12

**Important limitation:** Some provider-side implementation details may change without being fully exposed, so logging cannot guarantee perfect reproducibility.

### Fixture authorship

The evaluator development set should contain three kinds of examples:

1. **Obvious synthetic cases** that test whether the rubric works at all.
2. **Subtle/adversarial synthetic cases** designed so surface similarity, polish, metaphor, length, or terminology points toward the wrong verdict.
3. **Real failure patterns discovered later**, converted into new evaluator diagnostics without copying Beerlight acceptance cases into evaluator training/calibration.

LLMBar provides particularly strong support for the second category: its adversarial set intentionally contains outputs that superficially look suitable while failing the actual instruction, and these cases separated strong from weak judging much better than natural examples. citeturn16view0turn16view1

Recommended synthetic perturbations include:

| Target criterion | Useful paired construction |
|---|---|
| Paraphrase vs new model | Same mechanism, completely different terminology |
| Structural shift | Same nouns/metaphor, one changed causal arrow |
| Claim preservation | Fluent rewrite replacing one material quantifier/condition |
| Grounding | Plausible unsupported inference inserted among supported claims |
| New territory | New label applied to previously stated mechanism |
| Abstention | One source insufficient; one source minimally sufficient |
| Mode boundary | Stylistically correct response that performs wrong semantic operation |
| Continuity | Long turn that preserves most context but silently reverses one prior commitment |

These are **evaluator fixtures**, not Beerlight product tests.

A practical leakage invariant is:

```text
evaluator_fixture_lineage ∩ beerlight_acceptance_lineage = ∅
```

If an acceptance case exposes a judge weakness, do **not** tune the evaluator directly on that case and continue reporting it as independent acceptance evidence. Either leave the case human-routed under the existing evaluator, or create a genuinely new diagnostic fixture representing the failure mechanism and obtain a fresh holdout before qualifying the modified evaluator.

### Development vs holdout discipline

**Recommendation:** Development fixtures may be repeatedly inspected and used for prompt/rubric iteration. Holdout fixtures remain unseen until the evaluator candidate is frozen.

**Evidence class:** **INDIRECT_EVIDENCE**

**Supporting evidence:** This is standard measurement/ML holdout logic, and evaluator-calibration studies explicitly separate calibration information from evaluation. The 2026 reference-sensitivity paper likewise argues for a small calibration sample before larger judge use. citeturn15view0turn20view3

**Important limitation:** With such a tiny corpus, calling this “validation” in a statistical sense would exaggerate what it provides.

The holdout may be inspected when deciding whether the frozen evaluator qualifies. Once an item-level failure has been inspected **and used to change the prompt, rubric, examples, model choice, or decision logic**, the relevant holdout has entered the development information channel.

At that point:

> the evaluator may be improved, but it requires a fresh untouched holdout before the next independent qualification claim.

A previously exposed holdout can remain as a permanent regression suite, but it is no longer an untouched holdout.

There is one useful nuance for provider model upgrades: the same hidden holdout can be rerun on a new snapshot for direct old-vs-new comparison **provided its item content has not been used to modify the new evaluator**. Once failures are inspected and drive changes, retire the affected cases from holdout status and replace them.

### Small-N limitations

With roughly 15–20 cases and one human gold rater, this process is an **engineering sanity check**, not statistical validation.

A simple binomial illustration shows why. Even 20/20 observed successes give a 95% Wilson interval whose lower bound is only about **0.84** for the underlying per-case success probability under IID assumptions; 19/20 gives approximately **0.76–0.99**. Those IID assumptions themselves are dubious because fixture failures are correlated by semantic type.

Therefore a result such as “19/20 = 95% evaluator accuracy” should **not** be presented as evidence that the judge is 95%-accurate in production.

One human rater creates another limitation: there is no estimate of inter-rater agreement. The “gold” establishes compatibility with **one operational interpretation of the rubric**, not human consensus.

What 15–20 fixtures can reasonably establish:

- the evaluator understands the intended label schema;
- it handles a selected set of critical positive and negative examples;
- obvious permissiveness or over-strictness is detectable;
- known superficial traps can be probed;
- malformed-output frequency can be observed;
- repeated-call disagreement can be measured descriptively;
- candidate prompts/models can be rejected when they fail badly.

What they cannot establish:

- general accuracy with useful confidence bounds;
- stable rates for rare failure modes;
- construct validity;
- calibrated confidence;
- Russian population-level reliability;
- human consensus;
- evaluator independence from the subject model;
- robustness to all future Beerlight outputs;
- measurement equivalence after model updates.

**Recommendation:** Do not qualify an evaluator using a percentage target such as “≥90% accuracy.” With tiny N, use **specified-case conformance**: critical sentinel cases must behave correctly; observed ambiguities and disagreements must match the routing policy; report the complete confusion/disagreement table rather than a headline accuracy number.

**Evidence class:** **INDIRECT_EVIDENCE**

**Supporting evidence:** Modern judge audits show that aggregate agreement can hide chance agreement, benchmark dependence and bias. Norman et al. 2026 report large differences between exact match and chance-corrected agreement on MT-Bench, although that result is currently preprint evidence. citeturn20view0turn20view1

**Important limitation:** Cohen's κ is not a solution here either: with 15–20 cases and deliberately controlled class prevalence, κ will itself be unstable. Report it only diagnostically, if at all.

### Model drift and requalification

This requires explicit engineering treatment because model aliases differ by provider.

OpenAI's current API documentation states that prompting behavior can differ between snapshots and recommends pinned model versions plus application evals. Anthropic states that its current 4.6-generation dateless IDs correspond to fixed snapshots rather than moving aliases. Google's Gemini documentation distinguishes stable identifiers from `latest`, with `latest` explicitly hot-swapped as new releases appear. citeturn15view10turn15view11turn15view12

**Recommendation:** Record exact provider/model identifier and use a pinned/stable snapshot where supported. Avoid moving `latest` aliases for a regression judge.

**Evidence class:** **DIRECT_EVIDENCE**

**Supporting evidence:** Current official provider documentation explicitly describes snapshot/version behavior. citeturn15view10turn15view11turn15view12

**Important limitation:** Pinning reduces one source of drift but cannot guarantee bit-for-bit reproducibility of hosted systems.

Trigger full requalification when any of these changes:

```text
judge model/snapshot
provider
evaluator prompt
rubric anchors
few-shot fixtures in the prompt
context construction
sampling/reasoning settings
schema in a semantically relevant way
verdict aggregation rule
```

A pure logging or serialization change that provably leaves the model input and decision function unchanged need not consume a new holdout.

Old PASS results should be interpreted as:

> PASS under evaluator configuration E_v1

not:

> PASS under all subsequent evaluators.

After moving to `E_v2`, historical V1 and new V2 results are not automatically measurement-equivalent. Re-running a representative frozen regression corpus under both versions is the cheapest way to expose incompatibility; it does not prove equivalence.

## Hybrid checks, human routing, minimal architecture, and evidence gaps

### Deterministic and non-LLM adjuncts

Do not spend semantic-judge capacity on properties that software can determine exactly.

**Recommendation:** Keep these deterministic:

- schema validity and enum values;
- presence of required fields;
- exact mode/tag markers where Beerlight controls the protocol;
- source/citation identifiers referring to an allowed supplied source;
- evidence excerpt actually appearing in the claimed source/response;
- duplicate identifiers;
- required turn/reference IDs;
- exact abstention marker, when abstention is protocol-level rather than semantic;
- length/count constraints where they are literal requirements.

**Evidence class:** **DIRECT_EVIDENCE by construction**, not an empirical LLM claim.

**Important limitation:** Do not convert semantically fuzzy requirements into brittle lexical checks merely to make them deterministic.

For cheap semantic adjuncts, two classes have legitimate but limited value.

**NLI/factual alignment.** SummaC, TACL 2022, showed that sentence-level NLI aggregation could detect summarization inconsistencies with balanced accuracy of 74.4% across its six-dataset benchmark. AlignScore, ACL 2023, generalized text-to-text factual alignment across contradiction and hallucination settings. citeturn15view6turn15view7

That supports using an NLI/alignment score to **flag suspicious grounding or contradiction cases**, but not to replace the final semantic judge—especially because those results do not establish Russian Beerlight performance.

**Embeddings.** Embedding similarity can cheaply identify obvious near-duplicates and likely paraphrases, which can be useful for fixture triage or detecting that two proposed “new perspectives” are nearly identical. But embedding proximity is not sufficient to distinguish, for example:

```text
A causes B
B causes A
A prevents B
A correlates with B
```

when their lexical/semantic neighborhoods remain highly similar. It should therefore be a retrieval/alert signal, not a gate.

**Recommendation:** V1 does not need embeddings or NLI unless profiling shows an actual cost or diagnostic bottleneck. If added, use them only as secondary flags or fixture-generation aids.

**Evidence class:** **MIXED_EVIDENCE**

**Supporting evidence:** NLI/alignment metrics have real factual-consistency utility, but their benchmark accuracy is far below a level that would justify replacing human/LLM semantic adjudication, and the cited evidence is not Russian-specific. citeturn15view6turn15view7

**Important limitation:** Adding adjunct metrics before they solve a demonstrated problem would expand the harness without increasing the validity of its central semantic verdict.

### Human-review triggers

Human review should remain mandatory when:

| Trigger | Why |
|---|---|
| Either repeated run returns BORDERLINE | Rubric does not support safe automatic classification |
| Two repeated runs disagree | Observable judge instability |
| Evidence excerpt is absent, fabricated, or cannot be located | Verdict is not auditable |
| Persistent malformed evaluator output | Evaluator failed, not subject model |
| Required information is absent from supplied context | Judge would have to hallucinate an evidential basis |
| Criterion requires world truth rather than supplied-text semantics | Outside qualified construct |
| Case introduces a semantic failure mode absent from evaluator fixtures | Out-of-distribution diagnostic |
| Russian/code-switching pattern is substantially unlike qualified fixtures | Multilingual extrapolation |
| Evaluator version has changed without requalification | Measurement instrument changed |
| “Novelty” would have to be inferred beyond supplied comparison space | Unobservable construct |

A subject-model result must **not** be marked FAIL simply because the evaluator infrastructure failed. Maintain an internal `EVAL_ERROR` status separate from `FAIL`.

### Minimal recommended evaluator architecture

The entire architecture can remain small:

```text
Beerlight acceptance case
        │
        ├── deterministic checks
        │
        ▼
build criterion-specific evaluator input
        │
        ├── supplied source / prior turns / original claim
        ├── candidate response
        ├── exactly relevant criterion
        └── PASS / FAIL / BORDERLINE anchors
        │
        ▼
qualified frozen judge × 2
        │
        ├── structured verdict
        ├── evidence excerpts
        └── concise justification
        │
        ▼
deterministic output validation
        │
        ├── same valid PASS => PASS
        ├── same valid FAIL => FAIL
        └── otherwise => BORDERLINE / HUMAN
```

This architecture intentionally does not contain another judge, voting panel, judge-of-judge, learned calibration layer, agent loop, evaluator memory, prompt optimizer, or semantic database.

### Explicitly rejected overengineering

**Learned/fine-tuned judge:** unnecessary for 15–20 fixtures and explicitly outside the goal. The local dataset is much too small to justify a learned measurement model.

**Multi-model panels:** not justified for V1. Current 2026 evidence indicates that judge errors can remain correlated across models, undermining the naive assumption that three judges provide three independent observations. citeturn14search3turn14search19

**Majority voting to erase every disagreement:** rejected. Repeated-call disagreement is valuable evidence that a case sits in an unstable region. Reliability studies show that voting can improve benchmark accuracy, but stable consensus can still be systematically wrong. citeturn16view9turn17search1

**Numeric confidence calibration:** rejected until substantially more labeled data exists. Current evidence shows overconfidence, and 15–20 labels cannot calibrate a useful probability model. citeturn15view9

**Long generated judge chain-of-thought:** rejected as a stored evaluation artifact. CoT can improve task performance in some settings, but its faithfulness is not guaranteed. citeturn16view8turn13search3

**Global 1–10 semantic score:** rejected. It collapses distinct failure mechanisms and introduces arbitrary thresholds Beerlight does not need.

**Pairwise ranking/Elo/Bradley–Terry:** rejected because Beerlight is testing invariants, not ranking candidate systems.

**Embedding/NLI ensemble as final verdict:** rejected. They can cheaply flag particular relations but do not establish Beerlight's structural-semantic predicates. citeturn15view6turn15view7

**Large academic benchmark:** rejected. The goal is local regression detection, not estimating a population leaderboard metric.

**Automatic evaluator prompt optimization:** rejected. With tiny gold data it would make overfitting easier while making the resulting instrument harder to interpret.

### Open evidence gaps

The important gaps are not cosmetic.

**NO_DIRECT_EVIDENCE:** Russian/code-switched judgment of distinct causal/structural models.

**NO_DIRECT_EVIDENCE:** reliable detection of “decorative metaphor vs genuine structural shift.”

**NO_DIRECT_EVIDENCE:** global “new intellectual territory” detection. Only relative novelty can be operationalized.

**NO_DIRECT_EVIDENCE:** statistically justified PASS/FAIL/BORDERLINE thresholds for a 15–20-item semantic-regression corpus.

**NO_DIRECT_EVIDENCE:** optimal number of evaluator reruns for a small regression harness. Two-call concurrence is a conservative engineering choice, not a published optimum.

**NO_DIRECT_EVIDENCE:** that cross-provider judging supplies independent evidence. Existing evidence actually cautions against that inference. citeturn14search3

**MIXED_EVIDENCE:** optimal sampling configuration. Lower temperature often increases stability, but at least one peer-reviewed 2025 study found that completely disabling sampling slightly reduced judge accuracy in its tested settings. citeturn16view9turn20view0

**MIXED_EVIDENCE:** verbosity bias magnitude in modern judges. Foundational 2023 work identified it, but current audits show strong model/protocol heterogeneity. citeturn1search0turn20view1turn19search7

The unresolved empirical question for Beerlight is therefore not “Are LLM judges generally good enough?” It is much narrower:

> **Does one frozen evaluator configuration reliably distinguish Beerlight's locally important semantic perturbations, in Russian/code-switched text, without false PASSes on the specific failure patterns the harness is intended to catch?**

Fifteen to twenty fixtures can cheaply falsify a bad configuration. They cannot strongly validate a good one.

## RECOMMENDED_EVALUATOR_PROTOCOL_V1

**Purpose**

Use the evaluator solely as a project-specific semantic regression instrument. Its qualified claim is:

> Under evaluator configuration `E`, this response satisfied/violated/was ambiguous with respect to criterion `C`, according to a locally calibrated judge protocol.

It does not measure general intelligence, global response quality, truth beyond supplied evidence, or Beerlight product value.

**Judge selection policy**

**Recommendation:** Evaluate candidate judge models on the **evaluator development fixtures** and select based primarily on local errors, especially false PASSes on critical negative cases and Russian/code-switched cases. Prefer a different provider/model family from the subject model when performance is otherwise comparable.

**Evidence class:** **MIXED_EVIDENCE**

**Supporting evidence:** Same-model self-preference is documented; judge quality is strongly task-dependent; cross-family independence is not established. citeturn16view2turn20view1turn14search3

**Important limitation:** Do not infer that different-family = unbiased or independent.

**Model/version recording**

Record at minimum:

```text
evaluator_version
provider
exact model ID / snapshot
prompt version or content hash
rubric version
few-shot fixture IDs/version
schema version
sampling/reasoning parameters
context-construction version
execution timestamp
```

Pin an exact/stable model snapshot where the provider supports it. Do not use moving `latest` aliases for qualification-sensitive runs. citeturn15view10turn15view11turn15view12

**Sampling/stability policy**

No universal temperature value is justified by the literature.

Choose one fixed generation configuration during development and qualify that exact configuration. Favor settings with low observed instability, but do not assume zero sampling maximizes correctness. citeturn16view9turn20view0

For V1 semantic acceptance cases:

```text
run judge twice independently

same valid PASS + PASS
    => PASS

same valid FAIL + FAIL
    => FAIL

anything involving BORDERLINE
    => BORDERLINE / human review

PASS + FAIL
PASS + BORDERLINE
FAIL + BORDERLINE
    => unstable => BORDERLINE / human review
```

Do **not** automatically majority-vote a third call. The disagreement itself is the regression-harness signal.

The exact two-call setting is **INDIRECT_EVIDENCE / engineering default**, not an empirically optimal sample count.

**Evaluator prompt versioning**

The prompt is executable measurement logic.

Freeze and version:

```text
system instructions
criterion definition
PASS anchor
FAIL anchor
BORDERLINE anchor
evidence instructions
examples
output schema
```

Any semantically relevant prompt/rubric/example change creates a new evaluator version and triggers requalification. Prompt sensitivity is empirically established. citeturn16view0turn15view0

**Development-set use**

Use evaluator development fixtures freely for:

```text
rubric clarification
prompt iteration
judge comparison
sampling-setting comparison
schema repair
bias probes
failure diagnosis
```

Include a mixture of:

```text
obvious synthetic cases
subtle/adversarial synthetic cases
Russian/code-switched cases
surface-style/verbosity perturbations
semantic-preservation perturbations
real failure mechanisms discovered later
```

Real Beerlight **acceptance cases must not be copied into evaluator development gold**.

Maintain content/lineage IDs so the two corpora cannot silently overlap.

**Holdout use**

Keep an untouched evaluator holdout separate from development.

Use it only after:

```text
judge fixed
prompt fixed
rubric fixed
examples fixed
sampling fixed
schema fixed
decision policy fixed
```

The holdout is a **qualification smoke test**, not an accuracy estimator.

If a holdout item's content is inspected and that inspection informs an evaluator change, retire it from untouched-holdout status before the next qualification.

A previously exposed holdout may remain as a normal evaluator regression fixture.

Do not tune the evaluator on Beerlight acceptance cases.

**Output schema concept**

Minimum semantic result:

```json
{
  "criterion_id": "string",
  "verdict": "PASS | FAIL | BORDERLINE",
  "evidence": [
    {
      "origin": "source | candidate | prior_turn | original_claim",
      "excerpt": "short exact excerpt"
    }
  ],
  "justification": "short observable rubric-to-evidence mapping"
}
```

Do not include a numeric confidence field in V1.

Do not request persistent free-form chain-of-thought.

Evidence excerpts must be exact enough for deterministic substring/span validation.

**PASS / FAIL / BORDERLINE policy**

`PASS` means the observable criterion is satisfied under its explicit anchor.

`FAIL` means a material violation specified by the rubric is present.

`BORDERLINE` means supplied evidence/rubric is insufficient for a safe binary decision.

`BORDERLINE` is **not** a probability bucket.

For multiple required subcriteria:

```text
any VIOLATED => FAIL
all MET       => PASS
otherwise     => BORDERLINE
```

Prefer one semantic criterion per acceptance case where practical. Do not produce a global weighted quality score.

**Handling malformed judge output**

Treat malformed output as **evaluator failure**, never subject-model FAIL.

Policy:

```text
malformed / schema-invalid
    => one identical retry

second malformed
    => EVAL_ERROR + human/infrastructure review
```

If the first call is malformed and the retry succeeds, log the parse failure. For a strict regression gate, treat the case as evaluator-unstable rather than silently pretending the first call did not happen.

`EVAL_ERROR` is an infrastructure status outside `PASS | FAIL | BORDERLINE`.

**Handling unstable verdicts**

Any repeated-call semantic disagreement routes to human review.

Do not average or reinterpret contradictory categorical verdicts.

Track instability by:

```text
criterion
language pattern
judge version
subject-model family
fixture lineage
```

A recurring instability cluster is evidence that the evaluator rubric/judge is unqualified for that region.

**Evidence excerpt policy**

Require short excerpts supporting the material judgment.

For grounding:

```text
source excerpt
+
candidate claim excerpt
```

For preservation/continuity:

```text
original/prior-turn excerpt
+
candidate excerpt
```

For distinct-model judgments:

```text
excerpt expressing old mechanism
+
excerpt expressing proposed new mechanism
+
short statement naming the structural difference
```

Verify excerpts deterministically against the supplied inputs.

Generated paraphrases may appear in `justification`; they must not masquerade as quoted evidence.

**Human-review triggers**

Route to human when:

```text
BORDERLINE
two-call disagreement
persistent malformed output
invalid/nonexistent evidence excerpt
source/context insufficient
criterion requires external factual truth
global novelty would need to be inferred
new semantic failure mode
substantially novel Russian/code-switch pattern
evaluator version is not qualified
```

Human review should also override any case where the rubric itself is revealed to be ambiguous; that is a specification defect, not merely a judge defect.

**Model-change requalification trigger**

Requalify after any change to:

```text
model/provider/snapshot
rubric
prompt
few-shot examples
context construction
sampling/reasoning configuration
semantic output schema
aggregation/routing logic
```

Run development fixtures first, then an untouched/replacement holdout after the new evaluator is frozen.

Provider documentation directly supports pinning and re-evaluation across model versions. citeturn15view10turn15view11turn15view12

Historical PASS results remain:

```text
PASS under E_v1
```

They must not be silently interpreted as:

```text
PASS under E_v2
```

without a comparability study.

**Qualification criterion**

Do not use a pseudo-statistical rule such as:

```text
accuracy >= 90%
```

with 15–20 fixtures.

Instead require specified-case conformance:

```text
no unacceptable false PASS on designated critical negative holdout fixtures
valid evidence on required cases
expected handling of deliberately ambiguous cases
acceptable observed test-retest stability
no unresolved Russian-specific systematic failure
no evaluator infrastructure failure on qualification cases
```

Report raw fixture outcomes and disagreements.

Passing this gate means only that the evaluator survived the selected sanity checks.

**What must NOT be inferred from this calibration**

A qualified V1 evaluator does **not** establish:

```text
95% or any other population accuracy
general LLM judging reliability
human consensus
global semantic validity
global novelty
causal correctness
faithful hidden reasoning
calibrated confidence
cross-family independence
robustness to arbitrary Russian/code-switched text
future equivalence after provider/model updates
Beerlight product quality
Beerlight market validity
Beerlight general intelligence
```

The strongest defensible claim is narrower:

> **Beerlight has a frozen, locally sanity-checked semantic regression judge that has been shown to reproduce one human operational rubric on a small set of representative and adversarial evaluator fixtures, with explicit abstention, stability checks, evidence traces, holdout discipline, and human routing for cases outside that demonstrated region.**