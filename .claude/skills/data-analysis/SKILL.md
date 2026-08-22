---
name: data-analysis
description: Answer a question about this layer's cost or behavior from real telemetry. Never an impression. Covers token/call/latency trends, duplicate-call rate, execution-level accuracy, local-repair ratio. Triggers include "how much are we spending on X", "is this actually faster now", "what does the telemetry say", "how often does X happen", "compare before and after", "what changed in cost", or "analyze the session data". Use this whenever a question could be answered with a real number instead of a guess. Do NOT use for a one-off shell command that answers it directly, or a downstream product's own data.
effort: medium
model: sonnet
disable-model-invocation: false
allowed-tools: Read Grep Glob Bash
---

# Data Analysis

Formalizes what `docs/research/*.md` has done ad hoc: turn this layer's own
real telemetry into a structured answer, grounded in numbers, not a
remembered impression. Built from real, existing usage — not a stub for an
unused Notion category. This repo ships no application code (`CLAUDE.md`),
so the "data" here is always the layer's own operational record, never a
downstream product's.

## Sources, in order of cost (cheapest first)

1. **`python tools/bench.py`** — the single command for session/turn cost:
   `CLAUDE.md`+rules chars, SessionStart output chars, skill/cmd/agent
   listing chars, shell-call counts and duplicate rate, skill-body-load
   totals, schema coverage, local-repair ratio. `--save` writes a baseline
   to compare a later run against; `--full` for the complete breakdown.
2. **`.claude/hooks/state/telemetry.jsonl`** — one append-only row per
   `Stop` event, session-cumulative (see `telemetry/09-telemetry.py`'s own
   docstring for exactly what "one run" means here). Read with `Read` or a
   short `jq`/Python one-liner; never edited, never truncated.
3. **`.claude/hooks/state/chain-ledger.jsonl`** — one row per turn, the
   derived state and the plan's ticked task count, plus `kind: "gate"` rows
   for each Gate 1/Gate 2 decision. `python tools/chain.py --ledger` reads
   it back formatted.
4. **The other `state/*.json` files** (`call-fingerprints.json`,
   `skill-cost.json`, `tool-cost.json`, `read-cost.json`, `agent-cost.json`,
   `human-cost.json`) — the raw counters `bench.py` and `telemetry.jsonl`
   already aggregate. Read these directly only when a question needs a
   field neither of those exposes.

All of `state/` is gitignored (`.gitignore:28`) — real, live, per-machine
data, never assumed present in a fresh clone or a downstream install.

## Procedure

1. **State the question precisely** — a comparison needs two points
   (before/after, this session/last), a rate needs a denominator, a trend
   needs a window. "Is this faster" is not answerable; "did the
   `PreToolUse` chain for a `Bash` call get faster after the
   `permission-security` consolidation" is.
2. **Reuse before retrieve.** Check whether `tools/bench.py --save` already
   recorded a baseline, or whether `docs/research/*.md`/`decisions/*.md`
   already measured this exact question — a stale measurement is still
   evidence of what was true then; re-measure only what the question
   actually needs fresh.
3. **Pick the cheapest source** from the list above that answers the
   question — `bench.py` for anything session-shaped, the ledger for
   anything turn-by-turn or gate-shaped.
4. **Compare like with like.** `tools/bench.py`'s own warning applies:
   wall-clock seconds drift ~2x across runs on the same unchanged tree
   depending on machine load. To compare two configurations, run them
   INTERLEAVED (a, b, a, b), never as two runs taken minutes apart.
   Character counts and call counts do not have this problem — they are
   exact.
5. **Report the number and the command that produced it**, not just the
   conclusion — the evidence contract this whole layer runs on
   (`AGENTS.md`: "test output for behavior"). A reader must be able to
   re-run the same command and get the same answer.
6. **Name what the data cannot show.** `telemetry/09-telemetry.py`'s own
   `unavailable` map lists every field this harness structurally cannot
   observe (token counts, the active model name, ...) — cite it rather
   than estimating a value nothing measures.

## Common questions and their instrument

| Question | Command |
|---|---|
| Session/turn character and call cost | `python tools/bench.py` |
| Duplicate-call rate | `tools/bench.py`'s `session_calls()` line, or `telemetry.jsonl`'s `duplicate_rate` field |
| Skill-body token load | `tools/bench.py`'s `skill_body_cost()` line |
| Predicted vs. actual execution level | `telemetry.jsonl`'s `execution_level.predicted`/`.actual` pair |
| Local-repair ratio (objective 24) | `tools/bench.py`'s `local_repair_ratio()`, over `telemetry.jsonl`'s `retries.rung` history |
| Schema coverage (objective 22) | `tools/bench.py`'s `schema_coverage()` |
| What happened in a given turn | `python tools/chain.py --ledger` |
| Gate 1/Gate 2 decision history | `chain-ledger.jsonl`'s `kind: "gate"` rows |

## Red Flags

- "It feels faster" without a number. Run the instrument.
- Comparing a number from an old session's transcript against a fresh
  `bench.py` run without accounting for the ~2x wall-clock drift — compare
  interleaved, or compare only exact counts.
- Reporting a field from `unavailable` as if it were measured.
- Re-deriving a number `docs/research/*.md` already measured this week
  without checking whether it's still current.

## Next step

State the answer with its command and number inline in the response. If the
finding is durable (a real before/after, a closed gap), hand it to
`documentation` for `LOG.md`/`decisions/`; a one-off answer to a question
needs no further handoff.

## Routing

- Mandatory validator: none — this reads and reports, it does not change
  code. `tools/bench.py`/the state files are read-only inputs.
- Entered directly when a cost/quality/behavior question is asked, or
  dispatched from `task-analysis`'s Stage A when a Constraint or Done
  Check turns on a measured number rather than an inspected one.
- Terminal handoff: back to the caller with the answer; `documentation` if
  the finding should be durable.

## Success

The question was answered with a real number and the command that produced
it, compared like-with-like against any baseline cited, and every field the
harness cannot observe was named rather than guessed.
