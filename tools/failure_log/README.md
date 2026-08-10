# Failure Log System Core v0

Isolated test-stand engine for recording immutable friction/failure/papercut
observations. This is **not** connected to live workflow hooks, operational
logs, or the canonical `.ai/failure-log.md`.

## Scope

- Immutable JSONL intake stream for `failure` and `papercut` events.
- Append-only writes to an explicit output path.
- Public `append_event` API validates every new event before touching storage.
- Writer validates existing storage before every append.
- Idempotent retry for identical events.
- Conflict detection for same id with different payload.
- Dry-run validation and display.
- Read-only `doctor` checks for malformed/invalid records and duplicate ids.
- Deterministic serialization and documented exit codes.

## Storage contract

Core v0 is an **immutable intake stream**, not a lifecycle ledger. Each line is
one unchangeable observation.

- `id` — unique idempotency key.
- `recurrence_key` — grouping key for similar observations; may repeat.
- Status lifecycle, triage, mitigation and prevention are intentionally outside
  this wave.

## Event schema

```json
{
  "id": "event-2026-001",
  "timestamp": "2026-07-16T19:59:08Z",
  "kind": "failure",
  "source": "bounded-worker",
  "summary": "concise one-line summary",
  "evidence": "path/to/evidence or inline description",
  "severity": "major",
  "recurrence_key": "scope/recurring-symptom"
}
```

### Allowed values

- `kind`: `failure`, `papercut`
- `severity`: `minor`, `major`, `blocker`

All listed fields are required. `evidence` is a plain string in this wave.

### Timestamp contract

Timestamps must be a **restricted RFC 3339 profile** with an explicit timezone:

- `2026-07-16T20:00:00Z`
- `2026-07-16T20:00:00+05:00`
- `2026-07-16T20:00:00.123456Z`

Rejected forms include: space instead of `T`; compact dates/times; ISO week
dates; timezone offsets containing seconds; timestamps without seconds;
timestamps without a timezone.

## Writer invariants

A successful `append_event` cannot produce storage that `doctor` considers
unhealthy.

Before append:

1. If the output file is missing or empty, continue.
2. If the output file exists:
   - read it completely;
   - validate every existing record;
   - reject duplicate ids in existing storage with a storage-domain error;
   - reject malformed or invalid storage with a domain error and write nothing.

### Retry semantics

- Same `id` + identical normalized event → idempotent no-op, exit `0`, file
  unchanged.
- Same `id` + different payload → conflict, exit `1`, file unchanged.
- Repeated `recurrence_key` → allowed, not a doctor finding.

### Terminal newline handling

An existing record without a trailing newline is separated from the new record
by a newline written as part of the same append payload.

### Retry-safe automation

Automation that needs retry-safe behavior must generate and persist **both**
the `id` and the `timestamp`. Reusing only the `id` while letting the CLI
re-generate a fresh timestamp will produce a different payload and therefore a
conflict.

## Public Python API

```python
from pathlib import Path
from tools.failure_log import append_event

written, record = append_event(
    Path("/tmp/fls-events.jsonl"),
    {
        "id": "fl-001",
        "timestamp": "2026-07-16T20:00:00Z",
        "kind": "failure",
        "source": "bounded-worker",
        "summary": "demo failure",
        "evidence": "tests/failure_log/fixtures/evidence.txt",
        "severity": "major",
        "recurrence_key": "demo/recurrence",
    },
)
```

`append_event` raises `ValidationError` for invalid new events and never
creates or mutates the output file.

### CLI/API asymmetry

The CLI may be stricter than the Python API because argparse validates
`--kind`/`--severity` choices and timestamp spelling before domain
normalization. The Python API performs the documented value normalization
first and then runs domain validation.

## CLI usage

Record an event:

```bash
bin/failure-log-record record \
  -o /tmp/fls-events.jsonl \
  --id fl-001 \
  --kind failure \
  --source bounded-worker \
  --summary "demo failure" \
  --evidence "tests/failure_log/fixtures/evidence.txt" \
  --severity major \
  --recurrence-key demo/recurrence
```

Dry-run (validate and print, no write):

```bash
bin/failure-log-record record --dry-run -o /tmp/fls-events.jsonl ...
```

Inspect an existing log:

```bash
bin/failure-log-record doctor -o /tmp/fls-events.jsonl
```

### Stdout contract

- `--dry-run` prints the normalized candidate and does not mutate storage.
- Successful append prints the canonical committed record.
- Idempotent retry prints the canonical existing record.
- Conflict, validation error, unhealthy storage, I/O error, or internal error
  leave stdout empty and report through stderr with the documented exit code.

## Exit-code contract

- `0` — success, healthy log, or idempotent retry
- `1` — domain validation error, conflict, or doctor findings
- `2` — CLI usage error from argparse
- `3` — unexpected I/O or internal error

## Deferred limitations

- Single-writer only.
- Locking is not implemented.
- Concurrent writers are not supported.
- Full crash recovery is not guaranteed.
- Live hooks and operational integration are absent.
- This is a laboratory intake core, not the canonical FLS store.

## Tests

```bash
pytest tests/failure_log/
```

All tests use temporary directories and fixtures; no live project files are
touched.
