# Beerlight DEMO_RC — Offline Demo Package

**Status:** `PROVISIONAL_LOCAL_DEMO_RC_ONLY`

## Prerequisites

- Python 3.14+ (project `.venv` only — system Python fails collection)
- No network, no provider, no evaluator, no external service

## Setup

```bash
cd /home/alx/projects/prism
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'   # editable install; tests import prism.*
```

Note: plain `pytest` after installing only `pytest` fails collection
(`ModuleNotFoundError: No module named 'prism'`). The editable install (or
`PYTHONPATH=src`) is required.

## Exact demo command

```bash
cd /home/alx/projects/prism

# Run all 6 scenarios
.venv/bin/python docs/beerlight_demo_rc/demo_runner.py --all

# Run one scenario
.venv/bin/python docs/beerlight_demo_rc/demo_runner.py S1

# Run focused tests
.venv/bin/python -m pytest tests/beerlight_demo_rc -q
```

## Scenarios

| ID | Name | Mode | Gate | Demonstrates |
|----|------|------|------|-------------|
| S1 | normal-grounded | NORMAL | MODEL_READY | Full EXPLORE→DEEP→MAKE pipeline; lowest-numeric-viable P-ID selection |
| S2 | fake-breadth-360 | 360 | MODEL_READY | Volume without territory coverage (E3 fake-breadth resistance) |
| S3 | deep-handoff | NORMAL | MODEL_READY | P-ID continuity across EXPLORE→DEEP→MAKE |
| S4 | need-evidence | NORMAL | NEED_EVIDENCE | Terminal uncertainty gate; MAKE never invoked |
| S5 | source-injection | NORMAL | MODEL_READY | Embedded adversarial text treated as DATA_NOT_INSTRUCTIONS |
| S6 | return-to-explore | NORMAL | RETURN_TO_EXPLORE | Terminal gate; selected mechanism fails, branch stop with named break point |

## Expected observable fields

Every scenario output (JSON to stdout) contains:

- `scenario_id`, `scenario_name`, `protocol_version`
- `result.gate` — one of `MODEL_READY`, `NEED_EVIDENCE`, `RETURN_TO_EXPLORE`
- `result.selected_p_id` — the P-ID selected by lowest-numeric-viable policy
- `result.alternative_p_ids` — all perspective P-IDs from EXPLORE
- `result.final_artifact` — non-null only when gate is `MODEL_READY`
- `visible_outputs.EXPLORE` / `DEEP` / `MAKE` — visible text per stage
- `call_ledger` — every adapter call with stage, payload hash, and full payload
- `call_counts` — fake_adapter count and zero counts for all other call types

## Subject identity and provenance disclaimer

This demo runs with an **in-process scripted adapter** (`OFFLINE_SCRIPTED_ADAPTER_P4_B`).
No real subject model, provider, or transport is invoked.

The subject identity is `LOCAL_DEMO_RC_REFERENCE_SUBJECT` — a local
re-host of the Beerlight Explore/Deep provisional semantic contract.
It is **not** the actual Custom GPT Builder surface, and no semantic
equivalence or parity is claimed.

The documentation pack in `docs/beerlight_agent_docs/` is the provisional
semantic authority (read-only immutable pack, 24 files, SHA-256 verified).

## Prohibited claims

The following claims are **explicitly forbidden** for this demo:

- That this is a qualified, validated, or production-ready system
- That results demonstrate parity with any actual Custom GPT surface
- That the evaluator has acceptance authority (it is
  `UNQUALIFIED_DIAGNOSTIC_INSTRUMENT` with zero acceptance authority)
- That hidden judge state, private pool, scratchpad, chain-of-thought,
  internal reasoning, or model_lock is exposed or available
- That any result is `GOLD`, `FROZEN`, `HUMAN_APPROVED`, `QUALIFIED`,
  product-validated, or market-validated
- That `MAX_CARDS=3` or any global breadth quota governs the output
- That source text containing adversarial instructions changed the
  system's behavior (source_role is always `DATA_NOT_INSTRUCTIONS`)

## Honest vocabulary

All accepted labels:
`PROVISIONAL`, `LOCAL_DEMO_RC_ONLY`, `UNQUALIFIED_DIAGNOSTIC_INSTRUMENT`,
`PROVISIONAL_FIXTURE_ANCHORS`, `PROVISIONAL_DIRECT_SUBAGENT_EVIDENCE`,
`KNOWN_PREPATCH_GAP`, `DEMO` (never `GOLD`).

## Architecture

AUTO (`src/prism/beerlight_demo_rc/auto.py`) is a minimal, provider-free,
hard-coded dispatcher. It imports no provider, has no default route, and
fails closed on: private fields, stage/mode mismatch, P-ID substitution,
invalid gates, malformed records, and missing adapter.

Protocol version: `beerlight-demo-rc-auto-v1`

## Run evidence

Full run packet: `prism-runs/beerlight-demo-rc-p4-b-20260810-01/`

## Upstream gates

- G3: `G3_ACCEPTED` (LOCAL_DEMO_RC only) — `prism-runs/beerlight-demo-rc-g3-20260810-02/`
- P4-A: `P4_A_ACCEPTED` — `prism-runs/beerlight-demo-rc-p4-auto-20260810-01/`
