# Prism public-alpha release and RIFT task

## Authorization and fixed decisions

The repository owner has explicitly authorized the following:

1. The repository should become **public** after all release gates pass.
2. The license is **MIT**.
3. The experimental **RIFT profile ships immediately** in the public alpha.
4. A full working-tree and Git-history secrets/privacy scan is mandatory before changing visibility.

Do not ask again about these four choices. If a release gate fails or sensitive material is found, stop before changing visibility and report the blocker.

## Repository and branch

- Repository: `865x44/prism`
- Continue the existing branch: `release/shareable-rift`
- The branch already contains:
  - a rewritten public-alpha `README.md`;
  - `LICENSE` with MIT terms;
  - `.github/workflows/ci.yml`;
  - this task.
- Do not discard these files. Correct them when implementation evidence requires it.
- Do not work directly on unrelated repositories or touch unrelated dirty state.

## Mission

Make Prism safe and credible enough to show friends and technical reviewers as a public alpha, then add the RIFT profile without changing the default practical behaviour.

The result must be installable, testable, honest about privacy and cost, and usable without repository archaeology.

Deliver two logical commits:

1. `release: make Prism shareable`
2. `feat: add experimental RIFT profile`

A small final repair commit is allowed only for defects found by verification.

---

# Part A. Public-alpha release polish

## A1. Preflight inventory

Before editing:

1. Record current branch, HEAD, status, and tracked/untracked changes.
2. Read the full repository, especially:
   - `README.md`;
   - `pyproject.toml`;
   - `src/prism/runtime/`;
   - `src/prism/slice/`;
   - tests and fixtures;
   - all prompt files;
   - trace/session/output path handling.
3. Search the entire working tree for:
   - `Beerlight` / `beerlight`;
   - placeholder URLs such as `<owner>` and `<этот репо>`;
   - absolute local paths;
   - API keys, tokens, emails, private source text, or committed traces.
4. Classify every remaining Beerlight reference:
   - public UX/documentation: rename to Prism;
   - internal compatibility/history: retain only when justified and document it;
   - stale copy-paste: remove.

Do not perform a blind global replacement.

## A2. Public naming and API cleanup

Make public-facing behaviour consistently Prism:

- public imports: `import prism.runtime`;
- module invocation: `python -m prism.runtime`;
- console script: `prism`;
- CLI descriptions and help text;
- package/project description;
- default run directory: `prism-runs/`;
- default session directory: `prism-sessions/`;
- error messages, docstrings, examples, handoff text, and inspect output.

Preserve read compatibility for legacy paths and traces when practical:

- existing `beerlight-runs/<run_id>` may remain a read-only inspect fallback;
- old trace schema v0/v1 readers must continue working;
- do not rewrite old traces in place.

Remove contradictions such as claiming that no console script exists while `pyproject.toml` defines `prism`.

## A3. README accuracy

Review the branch README against actual code and tests. Keep the concise public-alpha framing, but change any claim that is not implemented.

The final README must include:

- actual clone and install commands;
- Python requirement;
- configuration for HTTP and OpenCode transports;
- `prism doctor` and `prism demo` only after they exist;
- practical and RIFT examples;
- normal and 360 modes;
- honest call-count explanation:
  - normally two logical model calls;
  - up to one structured-output repair per generator/judge stage;
  - transport retries may duplicate failed requests;
- privacy and local trace storage warning;
- alpha limitations;
- feedback guidance;
- test/build commands;
- MIT license link.

Do not claim deterministic reproducibility or hidden-reasoning capture.

## A4. OpenCode transport privacy and robustness

Current implementation passes the full prompt as a process argument. Replace that behaviour.

1. Inspect the locally installed OpenCode CLI help and supported input methods.
2. Use a documented stdin or file-input mechanism.
3. Do not place the full source/prompt in argv or shell command strings.
4. Preserve:
   - timeout handling;
   - stdout/stderr capture;
   - return-code checks;
   - model selection;
   - one bounded transport retry.
5. Add tests using a fake executable or monkeypatched subprocess. Tests must prove that the prompt is not present in argv and is passed through the chosen safe channel.
6. If the installed OpenCode version has no safe non-argv input method, stop and report the exact supported CLI surface instead of inventing syntax.

## A5. Graceful judge failure

Resolve the current contradiction between documentation and implementation.

Preferred contract:

- generator succeeds;
- judge fails after bounded repair;
- preserve candidate pool and raw outputs;
- return `status: degraded` with no fabricated final cards;
- emit a clear warning and usable trace path;
- CLI exits with a documented non-zero or dedicated degraded code, chosen consistently across CLI and JSON contracts.

Do not silently present unjudged candidates as accepted cards.

If implementing `degraded` would break the accepted external contract too broadly, choose the smaller honest repair: keep explicit error behaviour and update every contradictory docstring/README claim. State the decision in the final report.

## A6. `prism doctor`

Add a tool-free diagnostic command:

```bash
prism doctor
```

It should report without exposing secrets:

- Prism version;
- Python version and supported/unsupported status;
- selected transport and how it was resolved;
- whether an API key is present, never its value;
- generator and judge model names;
- OpenCode executable availability/version when relevant;
- writable run/session directories;
- package/import health;
- concise PASS/WARN/FAIL summary.

Optional:

```bash
prism doctor --smoke
```

This may perform one explicitly announced minimal provider call. It must never run by default.

Add deterministic tests for no-key HTTP, OpenCode found/missing, invalid transport, and secret redaction.

## A7. `prism demo`

Add a recorded, key-free demo:

```bash
prism demo
```

Requirements:

- no provider call;
- synthetic/shareable source only;
- demonstrate source, candidate pool, judge decisions, final cards, and inspectability;
- clearly label output as a recorded fixture, not a live run;
- use repository fixtures committed under a clear demo path;
- no personal texts, absolute local paths, or provider credentials;
- deterministic test coverage.

## A8. Packaging and CI

Verify and repair `.github/workflows/ci.yml` as needed.

Required matrix:

- Python 3.11;
- Python 3.12;
- Python 3.13.

Required gates:

- install dev dependencies;
- full pytest suite;
- `prism --help`;
- `python -m prism.runtime --help`;
- wheel and sdist build;
- install built wheel in a clean environment;
- post-install CLI smoke.

Locally run the same checks before relying on CI.

## A9. Public repository hygiene

Add or verify:

- MIT `LICENSE`;
- `.gitignore` covers run/session outputs, build outputs, virtualenvs, caches, coverage files, and local environment files;
- no generated private traces are tracked;
- no secret-bearing `.env` files are tracked;
- optional lightweight `CONTRIBUTING.md` or issue guidance, only if it adds real value.

Do not add badges until the referenced workflow and branch actually exist.

---

# Part B. Experimental RIFT profile

## B1. Separate profile from mode

Do not add RIFT as a third run mode.

Use orthogonal dimensions:

```text
mode: normal | 360
profile: practical | rift
```

Supported CLI:

```bash
prism run text.md --task "..." --profile practical --mode normal
prism run text.md --task "..." --profile rift --mode normal
prism run text.md --task "..." --profile rift --mode 360
prism session run session-dir --task "..." --profile rift --mode 360
```

Default profile remains `practical`.

Backward compatibility:

- omitted profile means `practical`;
- old `run-json` requests remain valid;
- old public Python calls remain valid;
- practical prompt behaviour must remain unchanged unless a bug fix is explicitly justified.

## B2. RIFT semantics

RIFT optimizes for:

- conceptual distance;
- originality;
- mechanism preservation;
- creative or practical return.

RIFT must reject:

- random metaphor;
- style imitation;
- decorative surrealism;
- surface-level analogy;
- unsupported catastrophic extrapolation;
- strangeness that cannot identify a source anchor and preserved mechanism.

Create versioned prompt assets, for example:

- `rift-v0.md` or `generator-rift-v0.md`;
- `judge-rift-v0.md` or a clearly versioned judge overlay;
- `operator-families-v0.md`.

Do not overwrite the validated practical `generator-v1.md`, `judge-v1.md`, or `360-v1.md`.

## B3. Independent operator families

Include independent search families such as:

1. incentives and redistribution;
2. measurement and comparison;
3. time and irreversibility;
4. coordination and interfaces;
5. identity and legitimacy;
6. contradiction and contingency;
7. category mutation;
8. scale inversion;
9. agency displacement;
10. cross-domain mechanism transfer.

Rules:

- families are lenses, not a quota checklist;
- do not generate one weak candidate per family;
- candidate diversity is judged by causal structure, not labels;
- record `operator_family` as optional candidate metadata;
- optional distance metadata may be `near | far | extreme` for RIFT;
- existing candidate/card readers must tolerate missing new optional fields.

## B4. Prompt routing and trace metadata

The prompt builder must route by both mode and profile.

Examples:

- practical + normal: existing generator v1;
- practical + 360: existing 360 v1;
- rift + normal: RIFT generator profile;
- rift + 360: 360 context plus RIFT search constraints.

Trace/request metadata must record:

- profile;
- effective generator prompt version;
- effective judge prompt version;
- operator family when provided;
- RIFT distance when provided.

Do not lie by labelling a RIFT run `generator-v1`.

Preserve read compatibility for older traces lacking profile by normalizing them to `practical` on read.

## B5. Judge behaviour

The practical judge may remain the default for practical runs.

RIFT judging must not discard a strong distant transfer merely because immediate office-style usefulness is lower. It must still enforce:

- source anchor;
- preserved mechanism;
- explicit assumption;
- break point;
- non-duplication;
- non-decorative distance;
- useful creative, analytical, research, or writing return.

Do not weaken fidelity into “anything interesting goes”.

## B6. Output compatibility

Do not perform a full card-schema migration in this release.

Map RIFT output into the existing card fields:

- `shift`: strange but defensible reframing;
- `basis`: source anchor plus preserved mechanism;
- `action`: creative/practical return and possible exploration;
- `boundary`: assumption and break point.

Keep the maximum of three cards.

Store richer RIFT candidate metadata in traces for future evaluation.

## B7. Tests and bounded live smoke

Deterministic tests must cover:

- profile defaulting to practical;
- CLI and JSON profile parsing;
- session-run profile parsing;
- practical prompt byte/semantic preservation;
- all four mode/profile routing combinations;
- operator-family optional fields;
- old trace normalization to practical;
- RIFT prompt version in metadata;
- RIFT card cap;
- RIFT abstention;
- malformed RIFT output repair;
- README commands.

Live smoke budget:

- one practical normal run as regression control;
- one RIFT normal run on the same source;
- one RIFT 360 only if session/trajectory routing changed;
- no repeated calls merely to obtain prettier examples.

Compare practical and RIFT for:

- actual causal-family difference;
- source fidelity;
- decorative failure;
- usefulness or creative return;
- hidden duplication.

Save only sanitized, explicitly shareable smoke evidence. Do not commit private source texts or absolute paths.

---

# Part C. Secret, privacy, and history gate

This gate is mandatory because the repository is authorized to become public.

## C1. Working tree scan

Check all tracked and untracked files for:

- API keys and tokens;
- `.env` files;
- credentials;
- private email addresses;
- absolute home paths;
- personal source texts;
- private traces;
- generated prompts containing private context;
- archives or binaries that have not been reviewed.

Use an established scanner when available, plus targeted repository searches.

## C2. Full Git history scan

Scan all refs and complete Git history, not only HEAD.

Preferred tools:

- `gitleaks git` or equivalent history-aware scan;
- a second targeted grep/log review for known provider-key patterns and private path prefixes.

Also inspect:

- branches;
- tags;
- deleted files still present in history;
- large blobs;
- commit patches containing source text or credentials.

If a secret or private text is found:

1. Do not make the repository public.
2. Report exact affected commits/paths without echoing secret values.
3. Rotate any credential first.
4. Propose history rewrite/removal separately.

A clean HEAD is not sufficient when old commits contain sensitive material.

## C3. Visibility change

The owner has authorized public visibility, but change visibility only after:

- all tests pass;
- package build/install smoke passes;
- CI is green or has an explained platform-only issue;
- README matches implementation;
- working-tree and full-history scans are clean;
- branch is merged to `main` or `main` otherwise contains the verified release commits;
- `main` is clean and points at the reviewed release state.

Then, when authenticated with sufficient rights, use an explicit command such as:

```bash
gh repo edit 865x44/prism --visibility public --accept-visibility-change-consequences
```

Verify afterward that anonymous repository metadata and README are accessible.

If the local environment cannot change visibility, report the exact final manual command instead of claiming success.

---

# Verification commands

Adapt to repository conventions, but final evidence must include equivalents of:

```bash
git status --short
python -m pytest
python -m build
python -m venv /tmp/prism-release-venv
/tmp/prism-release-venv/bin/pip install dist/*.whl
/tmp/prism-release-venv/bin/prism --help
python -m prism.runtime --help
prism doctor
prism demo
```

Also run:

- full branding/reference search;
- placeholder URL search;
- secrets scan for working tree and full history;
- inspection of tracked files and large blobs;
- a clean clone install smoke if practical.

Do not use paid inference in deterministic tests.

---

# Final report

Return:

```markdown
# Prism Public Alpha Release Report

## Verdict
READY / BLOCKED

## Baseline
- branch:
- starting commit:
- final commits:

## Release polish
- public naming:
- paths and compatibility:
- README:
- OpenCode transport:
- judge failure contract:
- doctor:
- demo:
- CI/package:

## RIFT
- CLI/API profile:
- prompt versions:
- families:
- trace metadata:
- practical compatibility:
- smoke comparison:

## Tests
- exact commands:
- results:

## Security and privacy gate
- working-tree scanner:
- history scanner:
- targeted searches:
- large blobs:
- verdict:

## Public visibility
- changed: yes/no
- verification:
- if not changed, exact remaining command:

## Commits
- release:
- RIFT:
- optional repair:

## Unrelated state
- confirmed untouched:
```

Stop after the report. Do not begin a larger schema rewrite, Chat Edition synchronization, Lab work, provider routing architecture, personalization, or repository-wide semantic v2 migration.
