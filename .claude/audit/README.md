# `.claude/audit/` — a pointer, not a trail

**The audit trail is `.claude/hooks/state/chain-ledger.jsonl`.** This directory
holds no records and must not start holding any.

`GOAL_CHECKLIST.md` §0 asks for an append-only log of what the system actually
did. That log already exists, has a suite behind it (`tools/test_chain.py`), and
is written by one hook. A second trail here would drift from it within a week,
and two audit logs that disagree are worse than one — the reader has no way to
tell which lied.

## What the ledger holds

One row per turn: timestamp, derived state, slug, and the plan's ticked-task
count. Plus `kind: "gate"` rows carrying each gate's decision and the user's
reason **verbatim**.

    python tools/chain.py --ledger

## What it does not hold

Not every tool call, and not every file write. The checklist asks for both; this
records neither, and calling the ledger a complete audit trail would be the kind
of overclaim this layer keeps having to walk back. Per-call totals — count,
input characters, repeats — are kept separately by
`.claude/hooks/post-tool/01-context-cost.py` and read by `tools/bench.py`, and
they reset per session.

## Append-only by convention

The file is gitignored, so it is not tamper-evident and does not survive a clean
checkout. It is honest bookkeeping, not a compliance artefact. If it ever needs
to be either, that is a decision with its own plan — do not quietly upgrade the
claim by writing a stronger sentence here.
