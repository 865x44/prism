# Contributing to Prism

Thank you for contributing to Prism. This document outlines development setup, testing requirements, safety rules, and workflow expectations.

---

## 1. Development Setup & Testing

Requirements: Python 3.11 or newer.

```bash
git clone https://github.com/865x44/prism.git
cd prism
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Running Tests

Always run the full test suite before proposing changes:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

Before committing, verify whitespace and diff formatting:

```bash
git diff --check
```

---

## 2. Canonical Skill & Mirror Synchronization

The repository's canonical skill authority is located at:

```text
skills/pizm/
```

1. Always edit the canonical files under `skills/pizm/`.
2. Sync changes to the installed deployment mirrors (Claude Code and OpenCode) using the installer:
   ```bash
   ./bin/install-pizm --host both
   ```
   (Run `./bin/install-pizm --help` for options).
3. Verify mirror integrity and contract compliance:
   ```bash
   PYTHONPATH=src python3 -m pytest tests/test_pizm_installer.py tests/test_pizm_forge.py -q
   ```

---

## 3. Strict Safety & Invariant Rules

### Frozen Perspective Core

```text
DO NOT MODIFY:
src/prism/perspective_core/**
```

The Perspective Core implementation under `src/prism/perspective_core/` is permanently frozen byte-for-byte in this repository. Immutability is maintained by policy and code review, not by automated tests.

### Dirty-Work & Explicit Staging Protection

- **Explicit Staging Only**: Never use `git add .` or `git add -A`. Stage only files directly touched by your scoped task.
- **Never Destroy User Dirt**: Never run `git reset --hard`, `git clean -fd`, or `git stash` on working directories containing unrelated user material.
- **Current HEAD is Authority**: Always verify the current git status (`git status --short`) before and after changes.

---

## 4. Contract-Change Expectations

- All stages enforce fail-closed payload bounds, hash verification sidecars (`.sha256`), and deterministic output structures.
- Semantic changes to schemas or checkpoint behaviors require matching updates in `tests/test_pizm_*_contracts.py` and `bin/`.
- For detailed technical design and stage boundaries, consult `docs/architecture.md`.
