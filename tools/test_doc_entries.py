#!/usr/bin/env python3
"""Knowledge-doc size caps: LOG.md / ISSUES.md newest entry, TASK.md ledger head.

`documentation`/`formats.md` states the caps -- a LOG entry is ~15 lines, an
ISSUES incident ~12, and TASK.md's injected head is <=6 one-row entries --
and gives the reason: these files (or their heads) are re-read by whoever
opens the repo, and TASK.md's head by every session, so length is a recurring
cost rather than a one-off. Nothing enforced it.
Measured 2026-08-12: LOG's median entry was 39 lines against a cap of 15, with
40 of 41 entries over; ISSUES ran 24 against 12, with 25 of 25 over. A cap that
every entry violates is not a cap, and the layer's own rule is to prefer a
deterministic mechanism over a written one.

**Only an UNCOMMITTED entry is checked, and that is the whole design.** Both
files are append-only -- `LOG.md` says "never rewritten", `ISSUES.md` "never
rewrite old ones" -- so a check that fired on history would demand exactly the
edit those files forbid. "Newest entry" was the first attempt and has the same
flaw one step removed: the newest entry is usually already committed, so the
check still asks for a rewrite, just of the most recent history instead of all
of it.

An entry is checkable exactly while it is still being written, which in this
repo means: `git diff HEAD` for that file is non-empty. A clean file passes,
because there is nothing in flight to cut.

The consequence is that this cannot clean up the backlog, and is not meant to.
It stops the backlog growing.

Run: python tools/test_doc_entries.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (file, cap, what the entry is) -- caps from documentation/formats.md.
# A little headroom over the stated number, because the caps are written as "~15
# lines" rather than as a hard limit, and a check that fires at 16 would be
# argued with rather than obeyed. 20 and 16 are still far below the medians that
# prompted this.
LIMITS = [("LOG.md", 20, "a LOG entry (~15 lines per formats.md)"),
          ("ISSUES.md", 16, "an ISSUES incident (~12 lines per formats.md)")]

ENTRY_RE = re.compile(r"(?m)^(?=## 20)")

SESSION_CONTEXT_RE = re.compile(
    r"(?ms)^<!--\s*session-context:start\s*-->\s*\n(.*?)\n^<!--\s*session-context:end\s*-->")
TABLE_SEP_RE = re.compile(r"\s*\|[\s|:-]+\|?\s*$")

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def being_written(filename: str) -> bool:
    """True when this file has uncommitted changes.

    Fails OPEN -- no git, no HEAD, or any error means "not in flight", so the
    check passes. A doc-length check that goes red because git is unavailable
    would be blocking work on a question it cannot actually answer.
    """
    try:
        proc = subprocess.run(  # noqa: S603
            ["git", "diff", "--quiet", "HEAD", "--", filename],
            cwd=str(ROOT), capture_output=True, timeout=30,
        )
    except Exception:  # noqa: BLE001
        return False
    return proc.returncode == 1  # 1 = differences, 0 = clean, other = error


def newest_entry(path: Path) -> list[str] | None:
    """Lines of the newest dated entry, or None when the file has none."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    parts = ENTRY_RE.split(text)
    if len(parts) < 2:
        return None
    return parts[1].strip().splitlines()


for filename, cap, what in LIMITS:
    path = ROOT / filename
    if not path.is_file():
        # Absent is not a failure: this layer installs into repos that have not
        # written one yet, and inventing a violation there would make the check
        # noise on every fresh install.
        check(f"{filename} has no entries yet -- nothing to cap", True)
        continue
    if not being_written(filename):
        check(f"{filename} is committed -- append-only, nothing in flight to cap",
              True)
        continue
    lines = newest_entry(path)
    if lines is None:
        check(f"{filename} has no dated entry yet -- nothing to cap", True)
        continue
    heading = lines[0] if lines else "(empty)"
    check(f"{filename}'s newest entry is within {cap} lines",
          len(lines) <= cap,
          f"{len(lines)} lines in `{heading}` -- {what}. Cut it to what a "
          f"future reader could not reconstruct from the diff, or split it.")


def check_task_head() -> None:
    """TASK.md's session-context region -- what 02-session-context.py injects
    every session -- is the <=6-row ledger, not an unbounded list. Soft on a
    file that has no markers yet (un-migrated install): the hook falls back
    gracefully there, so this layer does not go red in someone else's repo."""
    path = ROOT / "TASK.md"
    if not path.is_file():
        check("TASK.md absent -- nothing to cap", True)
        return
    match = SESSION_CONTEXT_RE.search(path.read_text(encoding="utf-8"))
    if match is None:
        check("TASK.md has no session-context markers yet -- row cap not enforced",
              True)
        return
    rows = [ln for ln in match.group(1).splitlines()
            if ln.lstrip().startswith("|") and not TABLE_SEP_RE.match(ln)]
    data_rows = rows[1:]  # first `| ... |` line is the header
    check("TASK.md ledger head is <=6 rows",
          len(data_rows) <= 6,
          f"{len(data_rows)} data rows in TASK.md's session-context region -- "
          f"evict the oldest Done row (its record stays in LOG.md + docs/plans/).")


check_task_head()

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All knowledge-doc entry checks passed")
