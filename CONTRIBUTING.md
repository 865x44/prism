# Contributing to Prism

Prism is a public alpha. The most valuable contribution is evidence about whether an angle changed what someone wrote, investigated, or decided.

## Useful bug reports

Please include:

- Prism version or commit;
- Python version;
- transport and model names;
- the exact command;
- a sanitized source excerpt;
- expected and actual behaviour;
- relevant trace files after reviewing them for private data.

Never include API keys, unreviewed private documents, or full traces containing sensitive material.

## Useful semantic feedback

Especially valuable:

- two or three cards that are actually the same causal model;
- a strong candidate dropped by the judge;
- an output that should have been `NO_USEFUL_OUTPUT`;
- a RIFT result that is distant but genuinely useful;
- a RIFT result that is only decorative strangeness;
- a 360 pass that repeats an already explored direction;
- an angle that survived editing and remained in the final text or decision.

## Development setup

```bash
git clone https://github.com/865x44/prism.git
cd prism
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Before opening a pull request:

```bash
python -m pytest
python -m build
prism --help
python -m prism.runtime --help
```

Keep generated runs, sessions, credentials, and private source texts out of commits.

## Scope discipline

Prefer small changes with explicit evidence. Avoid combining a prompt redesign, trace migration, CLI rewrite, and provider architecture change in one pull request.

The practical profile is the compatibility baseline. Experimental RIFT changes should remain clearly versioned and should not silently alter practical output.
