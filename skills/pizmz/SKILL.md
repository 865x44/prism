---
name: pizmz
description: Parallel Pizm PACK/AUTO fan-out with deterministic bundle and deep synthesis pair
---

# pizmz — parallel Pizm PACK/AUTO fan-out over OMP subagents

Run one Pizm PACK (or AUTO) task on 3-5 native OMP subagents in parallel, each owning its own full pipeline and freezing its own artifacts. Parent dispatches, tracks landings, assembles the portable bundle, writes deep synthesis — never runs Search/Portfolio itself.

## When to use

`/pizmz pack <task>`, `/pizmz auto <task>`, or parallel pizm on subagents. Default lanes: `task-agy`, `task-muse`, `task-ds`, `task-free` (user may override to 3-5 or swap, e.g. `task-astra`, `task-sol`).

## Preflight

1. Read `skill://pizm` for PACK/AUTO contracts (`references/pack.md`, `references/auto.md`, `references/explore.md`).
2. Run-id prefixes: `<slug>-<lane>-<timestamp>`, lowercase alnum-hyphens, UNIQUE per lane.
3. Fan-out slug `<slug>-<timestamp>` names output dir `.ai/pizm/pizmz-<slug>-<timestamp>/` for the bundle+synthesis pair.
4. Dispatch all lanes in ONE turn as parallel BLOCKING `task` calls; queueing is fine, blindness holds via distinct run-ids.

## Dispatch (per lane)

- `agent`: lane pin. `effort`: `med` pack, `hi` auto. `name`: CamelCase <=32.
- `solutionSpace`: one line on the open part.
- `task` body, self-contained: `# Target` (repo path + files); `# Change` (full PACK/AUTO pipeline per pack.md/auto.md ordering: never pre-read explore-selector.md before final search-field freeze; never load deep/lever for PACK; freeze passes via `$HOME/.local/bin/pizm-checkpoint`; portfolio route PACK/AUTO; AUTO adds Deep->Critic->optional LEVER; archive via `pizm-session-bundle create --accounting`); lane angle optional (distinct emphasis or verbatim duplicate marked PARALLEL); `# Acceptance` (packet path, run-id, counts, 5-8 line summary; file MUST exist).

## Landing

Per landing: `todo done` the lane, note packet path + counts. Lane fails: report + error, offer one retry (new prefix) or quorum proceed (>=2 packets).

## Bundle (deterministic, zero model calls)

When ALL lanes land (or quorum accepted), run `bin/pizmz-bundle` (installed: `$HOME/.local/bin/pizmz-bundle`):

```bash
pizmz-bundle --slug <slug-timestamp> --task "<verbatim task>" \
  --packet agy=<abs path>:<run-id> --packet muse=<abs path>:<run-id> [...] \
  [--missing lane:reason] --out-dir .ai/pizm/pizmz-<slug>-<timestamp>/
```

Writes `pizmz-<slug>-bundle.md` (manifest: task, lanes, run-ids, counts, sha256 per packet, missing lanes; then packets byte-verbatim between markers) + `pizmz-<slug>-synthesis.md` skeleton. Quorum: 2+ packets; `--allow-single` only for explicit single-lane bundle. Deterministic given `--created`. NEVER hand-assemble the bundle in chat.

## Deep synthesis (parent, five sections)

Read ONLY the bundle file (not dispatch memories). Overwrite the skeleton in place, same filename. All five sections mandatory:

1. Coverage map — theme x lane table, where all lanes are thin.
2. Agreements — evidence only: theme + lanes + P-IDs, minimum 2 lanes.
3. Conflicts — direct P-vs-P contradictions with adjudication; never average, keep dissent explicit.
4. Solo gems — strong single-lane insight others missed.
5. Short-list and next step — Deep targets / follow-up questions, each pointing to sections 2-4.

Reject rules: uncited claim (no `lane/P-ID`) = rewrite; missing Conflicts = rewrite; averaging a contradiction into mush = rewrite.

## Rules

- NEVER run Search/Deep/Portfolio freeze in parent; all pipelines live on subagents.
- NEVER reuse a run-id prefix; NEVER feed one lane output into another before all land.
- OMP-only lanes; NEVER Sol-Pi. Missing lanes reported, not hidden.
- Synthesis cites bundle only; chat reply is a compressed short-list, the file is the record.
