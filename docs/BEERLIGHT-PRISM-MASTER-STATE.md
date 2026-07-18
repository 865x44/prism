# Beerlight / Prism Master State

**Version:** 0.1-draft  
**Date:** 2026-07-18  
**Status:** master document for independent product and engineering review

## 0. Purpose

This document is the current project constitution. It separates the stable semantic core, accepted product decisions, experimental hypotheses, implemented surfaces, known contradictions, parked ideas, and the next falsifying tests.

Statuses used below:

- `implemented`: exists in working code or prompt behavior;
- `observed_once`: appeared in one real use;
- `repeatedly_useful`: survived several uses;
- `accepted`: current product decision;
- `experimental`: should be dogfooded before promotion;
- `parked`: potentially useful later;
- `rejected_now`: explicitly outside the current scope;
- `stale_artifact`: file exists but no longer represents the latest product decision.

No idea is promoted merely because it sounds elegant.

---

# 1. Executive state

## 1.1. Original product

Beerlight began as a compact semantic-shift module:

```text
source material
→ 2–3 non-obvious but applicable perspective shifts
→ next step in writing, research, planning, review, or creative work
```

Its core loop was:

```text
detect default frame
→ find a blind spot
→ apply a transferable thought operation
→ show the semantic diff
→ return a question, test, implication, or action
→ separate source support from speculation
```

It was explicitly not a persona simulator, style randomizer, debate framework, large workflow runtime, complete causal engine, or imitation of a specific author.

## 1.2. Current product hypothesis

The project now appears to contain a fuller lifecycle of a thought:

```text
source
→ explore perspective space
→ select a perspective
→ preserve it in a Perspective Capsule
→ deepen it into a causal model
→ find leverage points
→ intervene or test
→ observe the result
→ feed the observation back into exploration
```

Current product thesis:

> Beerlight is a family of source-grounded cognitive operations for discovering, preserving, deepening, testing, and acting on non-obvious perspectives.

Current implementation strategy:

> Dogfood conversational versions first. Transfer only repeatedly useful behavior into Prism Runtime in one later bounded implementation wave.

## 1.3. Accepted product split

### Beerlight Explore

Purpose: increase conceptual variety without losing the source.

Operations:

- NORMAL
- RIFT
- 360
- TRANSFER

### Beerlight Deep

Purpose: reduce ambiguity around a selected perspective, build a causal model, and find effective interventions.

Operations:

- DEEPEN
- LEVER
- hidden strengthened Pareto
- RETURN_TO_EXPLORE

### Boundary

```text
Explore offers branches
→ user explicitly selects one or more
→ Perspective Capsule preserves the chosen thought
→ Deep receives permission to develop it
```

## 1.4. Why two Custom GPTs

This is an accepted product decision.

Reasons:

1. different cognitive functions;
2. conflicting stopping rules;
3. different output contracts;
4. a practical Instructions budget of roughly 8k characters observed in the current UI;
5. independent prompt growth;
6. low UX friction through `@` invocation inside the same chat;
7. a useful psychological boundary between exploration and commitment.

This does not imply two repositories, two runtimes, automatic orchestration, automatic handoff, or shared persistent storage.

## 1.5. Current surfaces

### Chat Edition

Primary semantic dogfood surface:

```text
ordinary conversation
→ @Beerlight Explore
→ user selects
→ @Beerlight Deep
```

### Prism Runtime

Stable local surface for CLI, traces, sessions, inspect, and later eval work.

It should not be rewritten after every chat experiment.

### Artifact drift

The currently available Chat Edition pack still identifies itself as `0.1.0` and contains older contracts:

- visible INTERNAL POOL and judge decisions on every normal run;
- maximum three visible cards;
- an example where 360 returns only 1–3 directions;
- no accepted Explore / Deep split;
- no current RIFT, TRANSFER, DEEPEN, or LEVER contract.

These files are historical evidence and compatibility material, not the latest product source of truth.

---

# 2. How far the project moved

The product form moved far. The semantic core did not.

| Original concept | Current descendant |
|---|---|
| `distance: far` | RIFT |
| several PerspectiveDiffs | NORMAL and broad 360 |
| operator routing | independent causal families |
| cross-domain operator | TRANSFER |
| PerspectiveDiff | Perspective Capsule |
| return path | LEVER |
| supported / speculative | observation / inference / assumption |
| break condition | falsifier and RETURN_TO_EXPLORE |
| human selection | explicit user commit |
| `no_useful_shift` | abstention and refusal to rescue weak models |

The main conceptual expansion is:

```text
perspective ≠ causal model ≠ intervention
```

The original PerspectiveDiff was not necessarily the final answer. It was often the first stable object in a longer thought lifecycle.

---

# 3. What the original scope got right

1. **One clear JTBD.** Escape the default frame and return an applicable shift.
2. **Strong non-goals.** No persona theater, debate, universal framework, or decorative metaphor engine.
3. **A falsifiable hypothesis.** Transferable operations had to beat a generic perspective prompt.
4. **Mandatory return to use.** A result needed a question, test, decision, or next-step change.
5. **Epistemic separation.** Source, transformation, addition, and boundary were visible.
6. **A small experiment.** One strong prompt, several candidates, and manual selection were enough to meet reality.

The original mistake was not the core. It was treating some NORMAL choices as universal product laws.

The clearest example is the top-three cap. It is correct for NORMAL and usually RIFT. It is destructive for 360, whose purpose is broad coverage.

Stable invariants:

- source grounding;
- meaningful semantic difference;
- source/addition separation;
- boundary;
- abstention;
- return to use.

Non-invariants:

- exactly three cards;
- one schema;
- one judge;
- one GPT;
- one output format;
- two LLM calls.

---

# 4. Stable constitution

1. Source before novelty.
2. Mechanism before voice, persona, or moral repaint.
3. Show the semantic diff.
4. Separate observation, inference, assumption, prediction, and boundary.
5. Return to practical use.
6. Allow abstention and rollback.
7. Leave the perspective commit visible and human-selected.
8. Dogfood before infrastructure.
9. Every new component must beat a simple baseline, prevent an observed failure, or replace meaningful labor.
10. Self-analysis creates proposals, not automatic production patches.

---

# 5. Conversation, commit, and Capsule

## 5.1. Chat as a temporary bus

The existing conversation already contains source, discussion history, previous cards, and user choices.

Advantages:

- no new interface;
- no orchestrator;
- no repeated context entry;
- user-controlled routing.

Limits:

- long context can be compressed;
- references such as `P2` can become ambiguous;
- new chats need a portable handoff;
- the invoked GPT may not reliably receive every earlier detail.

The chat is convenient but not authoritative.

## 5.2. User commit

Deep does not start without a focus by default.

```text
Углуби P2.
```

Advanced case:

```text
Сравни P2 и P7 как конкурирующие модели.
```

A single focus remains the default, but two rival models may be appropriate when the uncertainty itself matters.

## 5.3. Minimal Perspective Capsule

```text
ID + title
Claim
Source anchors
Mechanism seed
Added assumptions
Boundary
Open questions
Unresolved ambiguity / compression risk
```

The Capsule must remain screen-sized and human-readable.

It is the mandatory handoff protocol, not a universal JSON schema for all runs.

---

# 6. Explore contracts

## 6.1. NORMAL

Purpose: 1–3 strongest applicable alternative perspectives.

Objective:

```text
quality × applicability × source fidelity
```

Stop when strong structurally different perspectives exist and further candidates become duplicates or require distortion.

**Status:** accepted; earlier implementations exist.

## 6.2. RIFT

Purpose: distant, strange, original shifts that preserve the source mechanism.

Objective:

```text
conceptual distance × originality × mechanism fidelity × creative return
```

Minimum fields:

```text
Source anchor
Mechanism
Strange shift
Creative or practical return
Assumption
Break point
Evidence debt
```

`Evidence debt` records which added assumptions make the angle compelling and what must be checked before Deep treats it as a model.

RIFT is not random metaphor, style transfer, author imitation, or permission to ignore the source.

**Status:** accepted; requires repeated dogfood.

## 6.3. 360

Purpose: map still-unexplored perspective space relative to the entire available conversation.

Objective:

```text
coverage × causal diversity × non-repetition
```

Critical correction:

- 360 is not a top-three selection mode;
- target 12–20 directions in a rich long conversation;
- up to 24 is acceptable when genuinely distinct;
- fewer is valid for poor or already exhausted material.

Output is a compact grouped map with stable local IDs:

```text
## Time and trajectory

L1.1. Angle title
New angle: ...
What it changes: ...
```

A final block may nominate 2–4 promising directions without deleting the rest.

Judge or self-critique acts only as a collision filter:

- remove duplicates;
- remove paraphrases of explored directions;
- merge one causal model expressed several ways;
- remove decorative variants;
- remove unsupported fantasy.

360 should distinguish:

```text
unexplored but supported
unsupported / dead zone
```

**Status:** accepted product correction. Older artifacts still contradict it.

## 6.4. TRANSFER

Purpose: import a working mechanism from another domain.

Required output:

```text
Donor mechanism
Source mechanism
Mapping
New perspective
Boundary
Test
```

Without explicit mapping, the result is a metaphor rather than TRANSFER.

**Status:** accepted for Explore; experimental until dogfood proves distinction from RIFT.

---

# 7. Deep contracts

## 7.1. DEEPEN

Purpose: turn a selected perspective into a dynamic causal model without silently replacing it.

Required distinctions:

```text
Source observation
Inference
Added assumption
Prediction
Falsifier
Nearest rival model
Discriminating observation
Boundary
```

A rival model matters because almost any coherent story can be given a performative falsifier. Deep should identify what observation distinguishes the chosen model from its nearest plausible alternative.

Stop when the mechanism is coherent enough to make predictions, assumptions and boundaries are explicit, and the next step requires data or action rather than another paragraph.

**Status:** accepted for the first Deep MVP; prompt-only today.

## 7.2. RETURN_TO_EXPLORE

Deep must reject a chosen perspective when it discovers:

- weak grounding;
- mechanism substitution;
- an oversized assumption;
- indistinguishable predictions;
- a good metaphor but bad model;
- contradiction with the source.

**Status:** accepted mandatory Deep behavior.

## 7.3. LEVER

Purpose: find the most effective intervention points across short, medium, and long horizons.

Before ranking leverage points, state:

```text
Objective
Beneficiary
Protected constraints
Affected actors
System-maintaining mechanisms
```

LEVER is not a cautious small-experiment mode.

Horizons:

- near: bottlenecks, rules, sequence, information, local coordination;
- medium: incentives, feedback, measurement, interfaces, capabilities, responsibility;
- long: standards, infrastructure, legitimacy, path dependence, institutions, norm formation, learning capacity.

Normally return 3–6 leverage candidates. For each:

```text
Type
Horizon
Point of intervention
Mechanism
Direct effect
Secondary effects
System response
Capture path
Adaptation path
Countermove
Cost and risk
Reversibility
Success signal
Error signal
Stop condition
```

The strongest answer may be a sequence:

```text
entry lever
→ transition condition
→ structural lever
→ long-term lock-in or protection
```

A cheap reversible experiment may be the entry or evidence step, but it must not replace long-term leverage analysis.

**Status:** accepted mandatory component of the first Deep MVP.

## 7.4. Strengthened hidden Pareto

Natural trigger:

```text
Ебани Парето.
```

It searches for the minimum closed working loop, not literal 20 percent task selection.

Categories:

- Keep now
- Required support
- Do not cut
- Freeze
- Delete

LEVER changes causal structure. Pareto cuts implementation scope after the intervention is chosen.

**Status:** accepted hidden operator.

---

# 8. Output objects

| Object | Produced by | Purpose |
|---|---|---|
| Perspective Card | NORMAL / RIFT | one meaningful semantic shift |
| 360 Map | 360 | broad cartography of unexplored directions |
| Perspective Capsule | after selection | preserve thought through handoff |
| Causal Model | DEEPEN | explain dynamics and produce discriminating predictions |
| Lever Portfolio | LEVER | compare intervention points and sequences |

These objects should not be forced into one universal schema.

---

# 9. Operations may be different axes

Experimental interpretation:

| Operation | Primary dimension |
|---|---|
| NORMAL | selection policy |
| RIFT | conceptual distance |
| 360 | coverage width |
| TRANSFER | mechanism source |
| DEEPEN | commitment and model construction |
| LEVER | intervention target |
| Pareto | implementation scope |

This is useful for prompt design. It does not justify a combinatorial mode framework, public sliders, or Runtime redesign today.

---

# 10. Evidence ledger

## Operators beat generic baseline

**Status:** repeatedly_useful / accepted.

Evidence:

- blind comparison 7:2:3 in Beerlight’s favor;
- 8/8 initial operators produced usable effects;
- failures were classifiable rather than random.

Known limits: theoretical inflation, quota filling, weak abstention, same-family blind spots.

## Chat Edition is the best current semantic lab

**Status:** accepted.

Strengths: rapid iteration, broad quota, real conversations, immediate UX feedback.

Limits: nondeterminism, context truncation, model drift, weaker artifact guarantees.

## 360 must be broad

**Status:** observed_once, high-confidence correction.

Evidence: raw prompt produced roughly 15–20 useful directions; wrapper inherited normal selection and reduced them to three.

Next test: three long-chat runs after the broad-map hotfix.

## RIFT needs a separate objective

**Status:** accepted, not yet repeatedly validated.

Next test: NORMAL vs RIFT on five real materials, checking causal difference rather than style.

## Capsule is the handoff protocol

**Status:** accepted, minimum shape not stabilized.

Next test: five end-to-end chains and removal of fields that prove unnecessary.

## Beerlight can produce useful self-improvement proposals

**Status:** observed_once.

Boundary: self-analysis creates proposals but cannot auto-promote them into production prompts.

## LEVER is required for the user’s actual JTBD

**Status:** accepted by explicit user need.

Next test: the first Deep prototype includes LEVER and is compared with ordinary advice.

---

# 11. Known failure modes

1. False novelty: a new voice or judgment over the same mechanism.
2. Decorative distance: RIFT produces compelling emptiness.
3. Economic monoculture: different labels over incentives, scarcity, and shifted labor.
4. Quota filling.
5. Premature selection that removes strange but valuable candidates.
6. Causal laundering: Deep turns a weak hypothesis into a coherent story.
7. Capsule mutation: the handoff summary replaces the thought.
8. Advice disguised as leverage.
9. Safety amputation: only small reversible steps survive.
10. Chat context illusion.
11. Self-improvement runaway.

---

# 12. Idea register

## Accepted now

- Explore / Deep split;
- two Custom GPTs;
- explicit user commit;
- minimal Capsule;
- mode-specific success criteria and stopping rules;
- NORMAL 1–3;
- RIFT as a separate objective;
- 360 as a broad map;
- TRANSFER in Explore;
- DEEPEN and LEVER in the first Deep MVP;
- hidden strengthened Pareto;
- RETURN_TO_EXPLORE;
- epistemic labeling;
- chat as MVP bus;
- common technical core;
- five frozen end-to-end chains;
- mode-leakage checklist;
- no Runtime redesign before dogfood.

## Experimental near-term

- thought compiler as a design metaphor, not framework;
- Explore raises entropy, Deep lowers it;
- two competing Capsules in Deep;
- RIFT evidence debt;
- nearest rival model and discriminating observation;
- Capsule compression risk;
- stable 360 IDs;
- supported vs dead zones;
- 360 revisit / discard conditions;
- actor-relative leverage;
- capture and adaptation paths;
- leverage sequence;
- cognitive transfer metric;
- operations as independent axes;
- context-confidence marker;
- master document as executable constitution.

## Parked

- global source hashes;
- branching tree;
- Landscape / Dossier memory split;
- independent release cycles;
- mode-specific inspect;
- persistent cross-chat storage;
- model routing;
- large eval framework;
- automatic routing;
- taste retrieval and embeddings.

## Rejected now

- two repositories;
- universal cognitive framework;
- separate public Pareto or TRAJECTORY modes;
- AUDIT as central UX;
- persona and debate modes;
- embeddings without proven need;
- automatic orchestrator;
- full Runtime rewrite before dogfood;
- graph database;
- universal causal ontology;
- automatic promotion of self-generated changes.

---

# 13. Implementation gap matrix

| Component | Product status | Implementation status |
|---|---|---|
| NORMAL | accepted | earlier Runtime and Chat implementations exist |
| RIFT | accepted | exact current behavior requires verification |
| broad 360 | accepted correction | stale artifacts still contradict it |
| TRANSFER | accepted experimental | no stable implementation |
| user commit | accepted | natural-language/manual |
| Capsule | accepted | not stabilized |
| DEEPEN | accepted | prompt concept only |
| RETURN_TO_EXPLORE | accepted | prompt concept only |
| LEVER | accepted mandatory | not implemented |
| hidden Pareto | accepted | natural-language behavior |
| Explore GPT | accepted | current Beerlight is a prototype; rebuild needed |
| Deep GPT | accepted | not built |
| Prism public alpha | accepted | release work proceeds separately |
| full Runtime lifecycle | deferred | intentionally not started |

---

# 14. Immediate dogfood plan

Run five real chains.

## Chain 1: NORMAL

```text
conversation → NORMAL → selection → Capsule → DEEPEN → LEVER
```

## Chain 2: RIFT

```text
conversation → RIFT → Capsule + evidence debt → DEEPEN → model or RETURN_TO_EXPLORE
```

## Chain 3: broad 360

```text
long conversation → 12–20 item map → selection by stable ID → Capsule → DEEPEN
```

## Chain 4: TRANSFER

```text
source → donor mechanism → mapping → boundary → Capsule → DEEPEN
```

## Chain 5: competing models

```text
two Capsules → rival-model comparison → discriminating observation → LEVER → Pareto
```

Record:

- did the claim survive handoff;
- did Deep add a real mechanism;
- did assumptions become facts;
- did RETURN_TO_EXPLORE fire when needed;
- did LEVER identify a real intervention point;
- were short and long horizons preserved;
- did it beat ordinary ChatGPT;
- which Capsule fields were useful;
- where mode leakage occurred.

Outcome events:

```text
shown
selected
developed
applied
retained
survived evidence
reverted
unrated
```

Do not optimize only for `selected`.

---

# 15. Promotion gates

Promote Explore / Deep prompts after at least five completed chains with low mode leakage, stable handoff, at least three testable causal models, and at least two LEVER outputs better than generic advice.

Transfer to Prism only after output formats, Capsule, broad 360, recurring failure modes, and LEVER portfolio stabilize.

Then perform one bounded implementation wave:

- prompt bundles;
- simple dispatch;
- Capsule input/output;
- mode-specific formatters;
- trace metadata;
- frozen-chain fixtures.

No plugin framework.

---

# 16. Decision log

## D1. Two Custom GPTs

**Status:** accepted.

**Revision condition:** handoff remains unreliable even with Capsule, or switching creates persistent friction.

## D2. LEVER in the first Deep MVP

**Status:** accepted.

Must not collapse into generic tasks, only cheap experiments, only reversible actions, or Pareto scope cutting.

## D3. 360 is a broad map

**Status:** accepted correction.

Contract: 12–20 directions in rich contexts, compact grouped output, shortlist only on explicit follow-up.

## D4. Chat Edition remains the semantic lab

**Status:** accepted.

Runtime remains the reproducible surface.

## D5. Runtime does not follow every chat experiment

**Status:** accepted.

Reason: avoid duplicate work and schema churn.

---

# 17. Review mission for Fable

```text
Read the master document completely.

Do not improve the architecture by default. Test whether the product theory is true.

1. Where did the project discover a genuinely new product, and where did it merely rename ordinary LLM operations?
2. Which ideas create new user value, and which only organize prompts elegantly?
3. Are Explore and Deep two products, or two phases of one conversation?
4. Is Perspective Capsule sufficient to preserve an unusual thought?
5. Where does the system risk formalizing living thought to death?
6. Which three major claims are most likely wrong?
7. What is the smallest dogfood test that could falsify each?
8. What should be removed?
9. What unexpected product may be hiding here?
10. Classify ideas: preserve, test immediately, park, delete.

Pay special attention to two GPTs, broad 360, RIFT evidence debt, causal laundering, multi-horizon LEVER, and operations as independent axes.

Do not recommend a universal framework, multi-agent debate, persistent memory, or a large eval lab without demonstrated product need.

Cite exact sections.
```

---

# 18. Review mission for Kimi

```text
Read the master document and compare it against the actual Prism repository and current Chat Edition pack.

Build a claim-to-code matrix with statuses: documented, implemented, partially implemented, prompt-only, not implemented, contradicted.

Check:

1. NORMAL, RIFT, and 360 objectives, cardinalities, and stopping rules.
2. Every place that can still apply top-3 to 360.
3. How operator families enter generator context.
4. Trace/schema assumptions blocking RIFT, broad 360, Capsule, or Deep.
5. Whether Capsule can be added without migrating the whole Runtime schema.
6. Whether Explore / Deep requires two GPTs, two prompt bundles, or orchestration.
7. Runtime components reusable for Deep.
8. README or prompt claims that exceed implementation.
9. Compatibility and migration risks.
10. The smallest safe implementation delta after five successful chains.

Audit stale Chat Edition 0.1.0 artifacts against current accepted decisions.

Do not implement changes. Do not build a plugin framework. Do not begin broad research.

Return: claim-to-code matrix, blocking inconsistencies, smallest safe implementation slice, required tests, and what not to touch.
```

---

# 19. Questions reviewers must attack

1. Does the two-GPT split justify the handoff?
2. Is Capsule a protocol or a prettier summary?
3. Can broad 360 avoid quota filling?
4. Is RIFT a different causal search or a distance style?
5. Is TRANSFER distinct from RIFT?
6. Does DEEPEN create discriminating models or coherent stories?
7. Can RETURN_TO_EXPLORE resist the model’s helpfulness?
8. Does LEVER find system-changing points or generic advice?
9. Does multi-horizon analysis preserve strategy or create bloat?
10. Which ideas are artifacts of Beerlight analyzing itself too enthusiastically?
11. Are operations better represented as independent axes?
12. What must remain human-selected?

---

# 20. What not to do next

Do not immediately:

- rebuild Prism around Explore / Deep;
- add all new output fields to one universal schema;
- build a mode registry;
- build persistent memory or branching;
- add embeddings;
- build a large eval harness;
- create two repositories;
- automatically promote self-generated ideas into production prompts.

The next action is independent review plus conversational dogfood.

---

# 21. One-paragraph handoff

Beerlight began as a small source-grounded semantic-shift tool and has grown into a proposed lifecycle for working with non-obvious thoughts. Explore discovers perspectives through NORMAL, RIFT, broad 360, and TRANSFER. The user explicitly selects one or more perspectives and preserves them in a minimal Perspective Capsule. Deep develops the chosen perspective into a causal model, distinguishes observation from inference and assumption, compares it with a rival model, and either returns it to Explore or passes it to LEVER. LEVER searches for effective intervention points across short, medium, and long horizons and may assemble them into a sequence. Two Custom GPTs are accepted because their cognitive functions, stopping rules, output contracts, and instruction budgets differ. Chat Edition remains the rapid semantic lab; Prism remains the stable reproducible runtime. The immediate task is not infrastructure expansion but five real end-to-end chains, followed by independent product falsification from Fable and claim-to-code auditing from Kimi.
