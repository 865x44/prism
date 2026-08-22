FROZEN LEGACY COPY — intentionally not synced to workflow FLS v1. Workflow closure commit 9690d5098c43de8d9677c263861f8353bbcc7e44 (2026-08-22) is canonical; future semantics live in /home/alx/projects/workflow/contracts/failure-capture.md and .ai/analysis/fls-v1-closure-2026-08-22.md. No parity is asserted; do not evolve this copy independently.

# Failure Capture — FLS Candidate Contract

## Purpose

One shared, report-only contract for Claude, Codex, and Kimi when they observe
a genuine workflow failure or recurring papercut. Models are **sensors, not
storage writers**: they may emit a structured `FLS_CANDIDATE` block in their
final report and must never write to FLS storage.

This wave does **not** implement automatic recording, hooks, transcript mining,
lifecycle management, or canonical-store synchronization.

## One-Way Flow

```text
Claude / Codex / Kimi
→ detect a genuine failure or recurring papercut
→ include FLS_CANDIDATE in final report
→ no storage mutation

foreground primary
→ reviews and consolidates candidates
→ presents them for explicit human acceptance
→ no storage mutation

future dedicated recorder (not implemented in this wave)
→ invoked only after explicit human acceptance
→ assigns id and timestamp
→ invokes the existing FLS writer once
```

The eventual single writer assigns `id` and `timestamp` only **after** explicit
human acceptance. No agent, worker, subagent, or foreground primary assigns
them. The foreground primary may emit, review, consolidate, and present
candidates for human acceptance, but must not assign accepted-event
`id`/`timestamp`, invoke `bin/failure-log-record`, or write FLS storage.
Only a future, separately implemented dedicated recorder — invoked after
explicit human acceptance — may assign metadata and call the writer; no such
recorder is implemented by this integration wave.

## Candidate Shape

An `FLS_CANDIDATE` block has exactly these six fields:

```text
FLS_CANDIDATE

kind: failure | papercut
severity: minor | major | blocker
recurrence_key: stable-short-key
source: bounded source identifier
summary: one bounded sentence
evidence: concrete command, report path, commit, test result, or reproducible observation
```

Do **not** include: `id`, `timestamp`, lifecycle status, owner, resolution,
remediation task, dedupe key, or arbitrary metadata.

## Candidate Semantics

### failure

A concrete event where expected workflow behavior or an explicit system
invariant was violated.

Examples:

- a successful writer operation produces storage that its own doctor marks
  unhealthy;
- a skill contract promises automatic fallback while the live launcher
  explicitly stops without fallback;
- a worktree operation unexpectedly mutates the main checkout;

### papercut

A recurring or meaningfully repeatable friction point that does not fully break
the workflow but wastes time, creates confusion, or increases error probability.

Examples:

- repeated manual reconstruction of the same invocation;
- inconsistent command or path conventions across harnesses;
- repeated misleading diagnostics;
- a recurring extra confirmation caused by a narrow configuration defect.

## Do Not Capture

Do **not** emit candidates for:

- ordinary command typos;
- expected negative tests;
- intentionally triggered validation failures;
- normal quota exhaustion by itself;
- a single harmless failed attempt immediately corrected;
- an ordinary command exits nonzero, times out, is interrupted, or fails for
  a routine local reason, when the event does not expose a recurring workflow
  defect, violated invariant, broken contract, or systemic papercut;
- stylistic preferences;
- speculative risks without observed evidence;
- every reviewer comment as an independent event;
- defects already represented by the same candidate in the current report;
- normal task failure caused by incorrect user input.

## Quality Threshold

Emit an `FLS_CANDIDATE` only when **all** are true:

1. Something concrete was observed.
2. The event is relevant to workflow reliability or recurring friction.
3. Evidence is available.
4. The summary is understandable without the full transcript.
5. The recurrence key can plausibly group the same class of event later.

When uncertain, report the observation normally and do not manufacture an FLS
candidate.

## Severity

- `minor`: limited inconvenience, low risk, easy workaround;
- `major`: blocks or materially disrupts a workflow path, causes repeated
  rework, or risks incorrect results;
- `blocker`: stops a critical workflow path or creates a credible risk of
  destructive or unrecoverable mutation.

Do not classify every failed task as major or blocker.

## Recurrence Key

`recurrence_key` must:

- be lowercase;
- use stable hyphen-separated words;
- identify the failure class, not the specific session;
- exclude dates, random IDs, commit hashes, and usernames.

Good: `worktree-hook-main-mutation`, `skill-launcher-contract-drift`.

Bad: `failure-2026-07-17`, `commit-abc123`, `claude-problem-7`.

## Source

Use a bounded source such as:

- `claude:<task-or-session-role>`
- `codex:<task-or-session-role>`
- `kimi:<task-or-session-role>`
- `workflow-run:<transaction-name>`
- `review:<artifact-name>`

Do not include secrets, giant paths, full prompts, or whole transcripts.

## Evidence

Evidence must be concise and concrete. Preferred forms:

- command plus exit code;
- test name and result;
- report path;
- candidate commit;
- exact observed contradiction;
- bounded reproduction.

Do not paste full logs, credentials, secrets, entire source files, large stack
traces, or private user conversation content.

## Subagents and Workers

- Subagents and workers may propose an `FLS_CANDIDATE` in their report.
- They must never append directly to shared FLS storage.
- The primary agent may consolidate duplicate candidate reports.
- Only one candidate should represent one observed incident class per task
  report.
- No nested agent receives permission to record directly.

## Canonical Storage Separation

```text
FLS JSONL
→ machine-readable event stream written only by the accepted writer

Markdown reports, handoffs, and agent outputs
→ candidate sources or derived human-readable views

Beads
→ remediation and task tracking, not the canonical failure-event stream
```

- The accepted FLS Core v0 writer (`bin/failure-log-record`, API
  `tools.failure_log.append_event`) appends to an **explicit** output path
  (`-o`); it has no default path and defines no canonical operational location.
- The final canonical operational JSONL path is **not yet defined** by the
  repository; it remains an integration decision. This does not block
  report-only candidate emission, because this wave performs no writes.
- `.ai/failure-log.md` remains the canonical repository-level Markdown journal
  of investigated failures. It is **not** an FLS JSONL store and must not be
  converted into a second writable event store.

## No Automation

This contract does not authorize or implement:

- Claude Stop hooks, Codex completion hooks, Kimi completion hooks;
- automatic transcript parsing;
- automatic candidate acceptance;
- automatic IDs or timestamps;
- direct calls to the FLS writer by agents;
- writes during `/handoff`;
- cron jobs, background collectors;
- locking or concurrency support;
- Markdown-to-JSONL or JSONL-to-Markdown synchronization;
- lifecycle or triage fields.

## Dogfood Examples

Valid failure candidate:

```text
FLS_CANDIDATE

kind: failure
severity: major
recurrence_key: skill-launcher-contract-drift
source: review:cross-harness-diagnostic
summary: The /ds skill promised automatic agy-scout to ds-scout fallback, but the live agy-scout launcher explicitly stopped without fallback.
evidence: ds/SKILL.md documented automatic fallback; agy-scout-run reported no fallback and instructed manual rerun
```

Valid papercut candidate:

```text
FLS_CANDIDATE

kind: papercut
severity: minor
recurrence_key: repeated-manual-brief-path-fix
source: kimi:workflow-repair
summary: The same brief path required manual correction in multiple consecutive runs.
evidence: two task reports referenced an invalid generated brief path
```

Must **not** become a candidate:

```text
A negative test intentionally supplied an unknown field and received ValidationError.
```
