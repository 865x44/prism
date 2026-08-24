# Pizm Explore

Explore is the divergence primitive. Expand the space of materially distinct, grounded models of the situation, then stop before fully developing one branch.

In staged execution, Explore operates as a generator: it produces a structured candidate pool, writes the candidate JSON to a temporary file, and freezes the artifact via the checkpoint tool.

## Generator Workflow

**Pre-freeze future-contract prohibition:** Until the checkpoint returns `FREEZE_OK`, do not read, open, search, list, inspect, or otherwise access any future-stage contract or reference asset. Use only this loaded pre-freeze contract and the visible conversation context. If a future-stage contract is exposed prematurely, stop the pass and report the separation failure.

1. Analyze the task, source materials, and any prior visible Pizm territory.
2. Generate candidate perspective seeds according to the requested mode (NORMAL, 360, or RIFT).
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

## Modes

### NORMAL
Find several strong, practically useful perspectives the user is not already considering.

Prefer materially different mechanisms, incentives, constraints, causal structures, units of analysis, system boundaries, temporal dynamics, or agency distributions. Remove paraphrases and generic advice.

Usually a small set is enough. There is no card quota. Generate fewer perspectives when the material is thin and more only when they are genuinely independent.

For each candidate perspective, populate the semantic core:
- `candidate_id` and short title;
- core claim or structural shift;
- concrete anchor in the task/source (`grounding_anchor`);
- what becomes visible under this model (`what_becomes_visible`);
- mechanism seed (`mechanism`);
- load-bearing assumption or limit (`boundary`);
- epistemics arrays (`supported`, `inferred`, `speculative`, `unknown`).

### RIFT
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

### 360
360 is explicit-only and coverage-first. It is not a larger NORMAL and not a ranking pass.

Before local elaboration, seek materially distinct grounded semantic territories. Do not count refinements, actor swaps, example swaps, family headings, stylistic reframings, or candidate count as independent breadth.

Use prior accessible Pizm territory. Reconstruct its semantic cores before claiming novelty and seek the next outer shell: blind spots, missing variables, countermodels, alternative units of analysis, new causal families, boundary shifts, or otherwise genuinely distinct territories.

Do not regenerate previous territory under new names. If prior context is materially incomplete enough to make novelty uncertain, say so rather than pretending continuity.

There is no minimum candidate or family count. A smaller map of genuinely independent territories is better than a large fake-breadth map.

For each candidate perspective, populate `difference_from_prior` along with the semantic core.

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
      "difference_from_prior": "string (360 only)",
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

Ensure seeds remain compact — no presentation-ready essays.

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
-->
