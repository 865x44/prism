# Prism

**Prism is an experimental thinking amplifier for text and ideas.** Give it a draft, post, argument, plan, or research note. It returns up to three non-obvious perspectives grounded in the source, then preserves the full candidate pool and judge decisions for inspection.

> Status: public alpha. The core works, but the CLI, prompts, and output contracts are still evolving. Please report surprising successes, boring failures, and cases where several angles are secretly the same idea.

## Why Prism

Most idea generators optimize for quantity and fluent phrasing. Prism instead tries to produce a small portfolio of structurally different perspectives and is allowed to return `NO_USEFUL_OUTPUT` when the source does not support a useful shift.

A normal run uses two model roles:

1. **Generator** creates a candidate pool.
2. **Judge** evaluates novelty, fidelity, duplication, and practical return.

The user sees no more than three cards:

- **Shift**: what becomes visible;
- **Basis**: concrete support in the source;
- **Action**: a useful next move;
- **Boundary**: what the card does not establish.

The full pool, dropped candidates, and judge decisions remain available through `inspect`.

## Profiles and modes

Prism separates the relationship to prior work from the style of search.

### Profiles

- `practical`: grounded perspectives with clear writing, research, or decision value;
- `rift`: distant, strange, and original reframings that must preserve the source mechanism. RIFT rejects decorative absurdity, random metaphor, and surface-level analogy.

### Modes

- `normal`: find the strongest next perspectives;
- `360`: search outside the directions already explored in a session trajectory.

This allows combinations such as a practical normal run or a RIFT-flavoured 360 pass.

## Installation

Requirements: Python 3.11 or newer.

```bash
git clone https://github.com/865x44/prism.git
cd prism
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
pytest
```

You can also install directly from GitHub:

```bash
pip install "git+https://github.com/865x44/prism.git"
```

## Configure an LLM

Prism supports an OpenAI-compatible HTTP endpoint and an OpenCode CLI transport.

```bash
export PRISM_API_KEY="sk-..."                       # or OPENAI_API_KEY
export PRISM_BASE_URL="https://api.openai.com/v1" # optional
export PRISM_GENERATOR_MODEL="gpt-4o-mini"        # optional
export PRISM_JUDGE_MODEL="gpt-4o-mini"            # optional
```

| Variable | Default | Purpose |
|---|---|---|
| `PRISM_API_KEY` | fallback `OPENAI_API_KEY` | HTTP transport key |
| `PRISM_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible endpoint |
| `PRISM_GENERATOR_MODEL` | transport default | generator model |
| `PRISM_JUDGE_MODEL` | transport default | judge model, which may be stronger or from another family |
| `PRISM_TRANSPORT` | `auto` | `auto`, `http`, or `opencode` |

With no API key, `auto` tries the `opencode` transport. OpenCode must be installed and authenticated.

Check the local setup without running a full analysis:

```bash
prism doctor
```

Try a recorded, key-free walkthrough:

```bash
prism demo
```

## Quick start

Practical analysis:

```bash
prism run draft.md \
  --task "find non-obvious angles for this post" \
  --profile practical
```

RIFT profile:

```bash
prism run draft.md \
  --task "find distant, strange, but defensible reframings" \
  --profile rift
```

A run normally makes two logical model calls, one for generation and one for judging. Invalid structured output can trigger one bounded repair call per stage, so a run may make up to four logical model calls. Transport retries can repeat a failed request.

Results are written to stdout. Traces are stored under `prism-runs/<run_id>/`.

## Example output

```markdown
## Review work became the product

**Shift**
The tool does not remove writing work. It moves the scarce work from drafting to deciding what can be trusted.

**Basis**
The source claims faster production while repeatedly adding review and approval stages.

**Action**
Measure reviewer time and correction rate separately from raw generation speed.

**Boundary**
This does not establish that the tool reduces total output quality.
```

## Commands

```text
prism doctor [--smoke]
prism demo
prism run <file> --task "..." [--profile practical|rift] [--mode normal|360]
prism run-json <request.json>
prism inspect <run_id> [--show-pool] [--show-judge] [--calibrate]
prism session create <file> [dir]
prism session run <dir> --task "..." [--profile practical|rift] [--mode normal|360]
prism session update <dir> "new text" | --file f.md
prism session event <dir> <run_id> <candidate_id> selected|applied|retained|reverted
prism session outcomes <dir>
prism session show <dir>
prism trajectory show <dir>
prism handoff <dir> --output <dir>
```

## Sessions and 360

A session stores the original text, current revision, runs, explicit outcome events, and a compact trajectory.

```bash
prism session create draft.md my-session
prism session run my-session --task "angles for the post"
prism session event my-session <run_id> c2 selected
prism session update my-session --file draft-v2.md
prism session run my-session --task "find untouched layers" --mode 360
prism session outcomes my-session
```

Use 360 after at least one substantive pass. It should search outside previous cards and developed directions rather than paraphrasing them.

## Privacy and cost

Prism sends the source text, task, and relevant trajectory to the configured model endpoint. It also stores the source and structured run artifacts locally. The `privacy` field in trace metadata is a classification label, not encryption or access control.

Do not process secrets or sensitive personal material unless you trust both the configured provider and the machine running Prism. Review traces before sharing or committing them.

Model usage is billed by the provider or consumed through the configured local/CLI harness. Repairs and transport retries can increase usage beyond the usual two calls.

## Honest limitations

- Results are non-deterministic.
- Generator and judge may share the same model and blind spots.
- A different operator-family label does not prove that two candidates use different causal models.
- RIFT can become decorative unless its source anchor and mechanism are enforced.
- 360 depends on the quality of the stored trajectory.
- Prism finds perspectives. It does not automatically rewrite the source or verify external factual claims.
- A trace records the declared pipeline output, not private model reasoning.

## Feedback

Useful feedback includes:

- a card you actually developed, applied, or retained;
- a strong candidate the judge dropped;
- several cards that were secretly the same mechanism;
- a RIFT result that was strange but useful;
- a RIFT result that was merely decorative;
- a source where `NO_USEFUL_OUTPUT` should have been returned.

Open an issue with a sanitized source excerpt, command, model names, and the relevant trace files. Never upload API keys, private documents, or unreviewed full traces.

## Development

```bash
pip install -e ".[dev]"
pytest
python -m prism.runtime --help
prism --help
```

Before a public release, the repository must pass tests, package build/install smoke, history and secret scans, and a clean CLI demonstration.

## License

MIT. See [LICENSE](LICENSE).
