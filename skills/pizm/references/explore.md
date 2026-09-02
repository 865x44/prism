# Pizm Search (Explore)

Search is the divergence primitive (invoked as Search or Explore). Expand the space of materially distinct, grounded models of the situation, then stop before fully developing one branch.

In staged execution, Search operates as a generator: it produces a structured candidate pool, writes the candidate JSON to a temporary file, and freezes the artifact via the checkpoint tool.

## Generator Workflow

**Pre-freeze future-contract prohibition:** Until the checkpoint returns `FREEZE_OK`, do not read, open, search, list, inspect, or otherwise access any future-stage contract or reference asset. Use only this loaded pre-freeze contract and the visible conversation context. If a future-stage contract is exposed prematurely, stop the pass and report the separation failure.

1. Analyze the task, source materials, any accumulated search field, and any prior visible Pizm territory.
2. Generate candidate perspective seeds according to the requested search policy (initial, residual, or rift; see Search Policies below).
3. Format candidate perspectives according to the `pizm-candidates-v1` schema.
4. **Tool-only pre-freeze turn**: The assistant turn that writes candidates and invokes checkpoint must contain ONLY tool calls (write the pending JSON file, then invoke the freeze command via bash). Emit ZERO visible prose in this turn — no summaries, no "candidates saved", no commentary. The `<slug>` used as `--run-id` must be a timestamp or random lowercase alphanumeric slug (e.g., `20260824t153000`, `a3f7b2`), never derived from session identity or user-visible state.
   ```bash
   $HOME/.local/bin/pizm-checkpoint freeze --stage explore --run-id <slug> --input <path>
   ```
5. Do not output raw candidate pools or intermediate JSON directly to user chat.

### Bounded Retry and Failure Handling (A2)

- Normal path: write candidate JSON and invoke the checkpoint command once.
- If the checkpoint execution fails (e.g., schema validation error or write failure), perform ONE bounded regeneration attempt: correct the candidate artifact, re-write the JSON file, and invoke the checkpoint command a second time.
- If the second checkpoint attempt fails, output a visible error explaining the failure, append a `FOLLOW_UP_CANDIDATE` note, and stop execution without further retries.

### Generator Output Hygiene (A1)

- Do not perform self-assessment or self-evaluation of generated candidates.
- Do not predict downstream filtering, inclusion, or exclusion decisions.
- Do not provide ranking hints, confidence percentages, or probabilities.
- Do not use "weakest/strongest candidate" language.
- Maintain objective, descriptive generation of candidate models without editorializing.

## Search Policies

Every Search pass runs exactly one deliberate search policy: `initial`, `residual`, or `rift`. The policy names how this pass searches; it is not a quality grade. Candidate count is never a quality metric, and no policy has a fixed quota.

Legacy mode strings remain parseable on read for compatibility: `NORMAL` = initial policy, `360` = residual policy (deprecated alias retained for one release), `RIFT` = rift policy. "Breadth" is superseded terminology and is not a user mode.
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

For each candidate perspective, populate the semantic core:
- `candidate_id` and short title;
- core claim or structural shift;
- concrete anchor in the task/source (`grounding_anchor`);
- what becomes visible under this model (`what_becomes_visible`);
- mechanism seed (`mechanism`);
- load-bearing assumption or limit (`boundary`);
- epistemics arrays (`supported`, `inferred`, `speculative`, `unknown`).

### residual policy

The residual policy inspects the accumulated search field (see Search Field below), reconstructs the semantic territory already covered, and searches genuinely uncovered structural territory. Soft target: 6–10 candidate seeds when the material supports it.

Coverage-first semantics:

- Distinguish seen from closed: territory can be seen without being closed; only a genuinely exhausted outer shell justifies moving on.
- Reconstruct prior semantic cores before claiming novelty, then seek the next outer shell: blind spots, missing variables, countermodels, alternative units of analysis, boundary shifts, new causal families.
- Avoid attractor repetition: do not regenerate previous territory under new names, and do not keep returning to a favored mechanism, actor swap, example swap, family heading, or stylistic reframing as if it were new breadth.
- Seek genuinely distinct logics: mechanisms, system boundaries, agency distributions, time horizons, constraints, assumptions, failure logics, intervention logics.
- Honest exhaustion is allowed: when no genuinely uncovered structural territory remains, return a short honest limit rather than forcing novelty.
- Borderline-open territories may stay open: an inconclusive shell may remain explicitly open instead of being forced shut.
- If prior context is materially incomplete enough to make novelty uncertain, say so rather than pretending continuity.

There is no fixed candidate quota. A map of genuinely independent territories is better than a large fake-breadth map of decorative variations.

For each residual candidate, populate `difference_from_prior` along with the semantic core.

### 360

Deprecated compatibility alias. Retained for one release solely as a compatibility alias. A request for 360 executes the residual search policy (`Search(residual)`) above; the mode string stays accepted on read. Removal is deferred to a later plan. A 360 request never runs implicitly, is not a distinct semantic pipeline, and never means "a larger NORMAL".
### RIFT

Rift is MANUAL-ONLY. It starts solely from an explicit `/pizm rift` user request. AUTO and BONK never auto-trigger a rift pass, and there is no hidden auto-trigger.

Field handling:

- If an accumulated field exists, rift receives it as negative context: territory to move away from, not territory to refine.
- With no accumulated field, rift works directly from the source/task.

Find far-but-grounded structural shifts, not merely unusual wording or decorative analogy.

A RIFT may change the unit of analysis, allocation of agency, mechanism, system boundary, time horizon, type of causality, or transfer a genuinely relevant functional structure from another domain.

For each candidate RIFT, provide:
- source/task anchor;
- structural shift;
- mechanism seed;
- why the analogy/shift is warranted (`functional_mapping`);
- what it reveals (`what_becomes_visible`);
- added assumption or limit (`boundary`);
- break point where the model stops working (`break_condition`, required for RIFT);
- `rift_extras` (`source_structure`, `functional_mapping`, `return_path`, `break_condition`).

If the material cannot support a meaningful RIFT, return a short honest limit rather than forcing novelty.

## Search Field (accumulated candidates across passes)

Explore passes accumulate into a persistent search field:

- Every pass's frozen candidates stay available. Later passes append to the field; they never overwrite, prune, or rewrite earlier raw candidates.
- Candidates are addressed by composite ref `passNN:cMM`: the pass index (`pass01`, `pass02`, ... monotonic within the active conversation) plus the candidate id local to that pass. Two passes may reuse the same local ids (each may have its own `c01`) without collision because composite refs stay distinct.
- After each pass the host maintains a tiny search-field manifest conforming to `pizm-search-field-v1`: per-pass entries referencing each frozen candidates artifact by location plus its hash, plus accumulated composite refs. The manifest references artifacts; it never duplicates candidate contents.
- The manifest itself freezes through the checkpoint tool with stage `search-field` and is append-only across passes: earlier passes' rows are never rewritten, and payload bounds fail closed.
- Across multiple passes, ~28 candidates is the accumulated soft ceiling for the search field; avoid padding beyond honest exhaustion.
## Candidate Schema (pizm-candidates-v1)

Candidate JSON must conform to the following schema:

```json
{
  "schema_version": "pizm-candidates-v1",
  "stage": "explore",
  "mode": "NORMAL|360|RIFT",
  "candidates": [
    {
      "candidate_id": "string (unique within pool)",
      "title": "string",
      "semantic_core": {
        "claim": "string — core claim or structural shift",
        "structural_shift": "string — what changes in the model",
        "mechanism": "string — mechanism seed",
        "grounding_anchor": "string — anchor in source/task",
        "what_becomes_visible": "string — what this model reveals",
        "boundary": "string — load-bearing assumption or limit"
      },
      "epistemics": {
        "supported": ["string"],
        "inferred": ["string"],
        "speculative": ["string"],
        "unknown": ["string"]
      },
      "break_condition": "string (optional, RIFT-required)",
      "difference_from_prior": "string (residual policy; includes deprecated 360 alias)",
      "rift_extras": {
        "source_structure": "string",
        "functional_mapping": "string",
        "return_path": "string",
        "break_condition": "string"
      }
    }
  ]
}
```

### Compact Seed Guidance

Raw candidates are search seeds, not final polished perspective cards:
- Each candidate should be compact (~1.0–1.5 KiB serialized). Do not make every candidate explain the entire universe or write presentation-ready essays.
- Focus on one semantic core and one load-bearing structural shift.
- Provide minimal grounding and epistemic status (`supported`, `inferred`, `speculative`, `unknown`).
- Highlight 1–2 key consequences (`what_becomes_visible`).
- Include optional `break_condition` (required for RIFT).
- Keep descriptions crisp and dense so the search pool can support 12–16 candidate seeds within payload safety bounds.

## P-ID continuity

Within the active referenceable conversation/context:
- allocate visible P-IDs monotonically: P1, P2, P3, ... across modes and Explore passes;
- preserve a P-ID when the same semantic perspective is merely clarified, re-rendered, narrowed without substitution, or genuinely rescued with its central mechanism intact;
- allocate a fresh higher P-ID for a semantic fork, substituted central claim, or genuinely new model;
- never recycle or silently rebind an old P-ID;
- P-IDs are human-facing context-scoped aliases, not global identifiers.

## Grounding and abstention

If supplied material cannot support materially distinct grounded models, do not manufacture breadth. Limit, abstain, or request only the critical context required for grounded analysis.

Separate what is supported by the source/task from inference and added assumptions. Do not imply completeness that the material cannot support.

## Boundary

Do not select the winning perspective for the user. Do not silently switch into Deep. Do not generate a final article, plan, recommendation, or polished downstream artifact unless the user explicitly changes the task.

Do not reveal hidden candidate pools, private reasoning, chain-of-thought, internal scores, or hidden selection machinery.

<!-- migration-notes
epistemics: kept (supported/inferred/speculative/unknown arrays)
break_condition: kept, RIFT-required
return_path: RIFT-only via rift_extras
default_frame: derived from visible framing + structural_shift (not stored)
blind_spot: represented by what_becomes_visible + difference_from_prior
operator provenance: represented by mode + rift_extras.source_structure (no invented IDs)
search-policy naming: initial|residual|rift; legacy mode strings NORMAL|360|RIFT stay parseable on read (360 = deprecated alias of residual)
-->
