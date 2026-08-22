## Decision

Keep `.claude/project-checks.json`'s `test` array sorted alphabetically and
`docs/objectives.md`'s instrument table sorted by objective number. New
entries go in sorted position, not appended at the end.

## Why

Three clusters (D, A, B — objectives 11-30's missing instruments) landed as
separate PRs off the same base within one evening, each adding rows/entries
to these two files plus `LOG.md` and `README.md`'s suite count. Every pair
that both appended at the literal end conflicted on the same lines — real
conflicts, resolved twice by hand (`4fc5420`'s follow-up merges), purely
because two branches' "new line at the tail" landed on the identical
insertion point.

Sorting removes this specific class of conflict for a common, checkable
reason: two branches adding *different* keys (different test filenames,
different objective numbers) sort to *different* positions in the file, so
git's line-based diff sees non-overlapping hunks and merges automatically.
It doesn't eliminate every possible conflict (two branches touching the
*same* objective's row, or an adjacent one, can still collide — that is a
real conflict worth seeing, not noise) but it removes the guaranteed,
content-free "we both added something at the end" case that fired three
times in one evening.

## Alternatives considered

- **Leave it as append-only and accept the conflicts.** Cheap, and the
  conflicts were fast to resolve (both sides are always correct, resolution
  is a union) — but "fast to resolve" still means a human or agent stops
  and does it every time two parallel units touch these files, which this
  session did three times in a row. Rejected once the pattern repeated.
- **Split into per-unit files** (e.g. one JSON fragment per cluster, merged
  at read time). Would eliminate the conflict entirely, but changes the
  runtime contract `_projectchecks.py` and every reader of
  `project-checks.json` already depends on — a bigger, riskier change than
  the problem justifies. Not adopted.
- **Restructure `LOG.md` similarly** (e.g. one file per entry). Rejected:
  `LOG.md`'s append-at-top format is deliberate and documented
  (`.claude/skills/documentation/formats.md`), conflicts there are cheap
  (a two-entry reorder, not a rewrite), and restructuring an established,
  widely-read convention to save an occasional trivial resolution is not
  worth the churn.
- **Remove the numeric README.md suite count entirely** to avoid the
  single-line conflict it causes. Rejected: the count exists specifically
  so `tools/test_referenced_paths.py` can catch a stale claim — this repo's
  own README previously said "the thirteen skills" while there were
  fourteen, undetected for months, which is exactly the failure the count
  exists to prevent. The occasional one-line conflict is a cheap price for
  keeping that property; removing it would trade a rare, trivial conflict
  for a real, silent-drift risk.
