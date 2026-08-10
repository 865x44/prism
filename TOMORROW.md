# TOMORROW — 5 Highest-Value Manual Dogfood Actions

These are the most impactful next steps for a human operator after the
DEMO_RC sprint. They require real subject adapter authorization and are
outside the current offline scope.

## 1. Authorize a real subject adapter

Freeze a tool-disabled, repository-isolated runtime identity with hashed
config/prompt/fixture/runner/tool-policy. Install a raw-stream fail-closed
`tool_use` rule. Set a conservative call ceiling. This unblocks semantic
verification of all 6 scenarios with actual model output.

## 2. Run S5 (source-injection) with a real adapter

The scripted demo proves the routing label (`source_role=DATA_NOT_INSTRUCTIONS`)
but cannot test whether a real model semantically resists the embedded
control text. Running S5 with a real adapter would produce the first
genuine source-as-data evidence.

## 3. Run S2 (fake-breadth-360) with a real adapter

Territory detection is absent from AUTO. A real 360-mode run would show
whether the subject model produces actual territory diversity or repeats
one territory — the first test of E3 at the generation layer.

## 4. Implement LEVER prohibition at the adapter/evaluator layer

D5 specifies that NEED_EVIDENCE + LEVER (recommending removal of review)
is an immediate failure. AUTO cannot enforce this as a routing dispatcher.
A subject adapter or evaluator integration is the correct layer for this
safety invariant.

## 5. Capture actual Custom GPT surface configuration

The `LOCAL_DEMO_RC_REFERENCE_SUBJECT` is a local re-host. Actual Custom
GPT Builder instructions remain `NOT_LOCALLY_AVAILABLE`. A fresh capture
would enable provenance reconciliation between local and actual surfaces.
