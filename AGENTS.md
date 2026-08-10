# Agent Instructions

## Source of Truth

- `.ai/STATE.md` is the live session cursor and operational source of truth.
- `.ai/plans/` contains plans and briefs; it is not a task database.
- Existing project artifacts and git state are evidence; do not overwrite or
  normalize unrelated dirty files.

## Failure Journal

- `.ai/failure-log.md` is Prism's canonical Markdown journal of investigated
  failures.
- `~/.ai/logs/agent-failures.jsonl` is a separate, global harness log.
- Do not create `.ai/failures/` or `FL-*.md`.

## Failure Capture (FLS Candidates)

When a genuine workflow failure or recurring papercut is observed, follow
`contracts/failure-capture.md` and include an `FLS_CANDIDATE` block in the
final report.

- Agents are sensors, not storage writers: never invoke
  `bin/failure-log-record` or `tools.failure_log.append_event`.
- The foreground primary may review and consolidate candidates, then present
  them for explicit human acceptance; it must not assign IDs or timestamps or
  write FLS storage.
- The dedicated accepted-event recorder is not implemented here. Do not add
  automatic recording, hooks, transcript mining, or background collectors.
- Do not emit a candidate for expected test failures or ordinary mistakes.

## Papercuts

Record meaningful workflow friction with the installed `papercuts` CLI when it
caused delay, needed a non-obvious workaround, or is likely to affect another
agent. Do not record ordinary coding mistakes, expected failing tests, or
secrets/sensitive data.

The session-closing primary triages each new papercut as exactly one of:
resolve, keep open, promote to `.ai/failure-log.md`, or create a concrete task.
For data loss, unsafe writes, authority violations, corruption, or
unverifiable results, stop and escalate instead of merely logging it.
