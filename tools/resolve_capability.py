#!/usr/bin/env python3
"""Resolve a capability for a simple query by scanning `.claude/routing/capabilities.md`.

Usage:
    python tools/resolve_capability.py "oauth"   # prints matched capability + routing path

Manual counterpart to `.claude/hooks/pre-run/02-capability-router.py`, which does
the same match automatically on every prompt. Both read the same file, so a
keyword added there changes both.

Scanned nine `.claude/capabilities/*/index.md` files until 2026-07-31.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTING = ROOT / '.claude' / 'routing' / 'capabilities.md'


def load_capabilities() -> list[tuple[str, list[str]]]:
    """[(domain, [keyword, ...])] parsed from the routing file's `## ` sections."""
    if not ROUTING.is_file():
        return []
    text = ROUTING.read_text(encoding='utf-8', errors='ignore')
    caps = []
    for block in re.split(r'^## +', text, flags=re.M)[1:]:
        lines = block.splitlines()
        if not lines:
            continue
        domain = lines[0].strip().lower()
        m = re.search(r'^Keywords:\s*(.+)$', block, re.M | re.I)
        keys = [k.strip().lower() for k in m.group(1).split(',') if k.strip()] if m else []
        if domain:
            caps.append((domain, keys))
    return caps


def find_capability(query: str) -> tuple[str, int] | None:
    """Best-matching capability and its hit count, or None.

    Ranks by number of distinct keyword hits rather than returning the first
    match in file order. The previous version returned whichever capability
    sorted first alphabetically, so "ai" beat a stronger "testing" match purely
    on name order.
    """
    q = query.lower()
    scored = []
    for domain, keys in load_capabilities():
        hits = sum(1 for k in keys if k and k in q)
        if domain in q:
            hits += 2  # naming the capability outright is a strong signal
        if hits:
            scored.append((hits, domain))
    if not scored:
        return None
    scored.sort(key=lambda row: (-row[0], row[1]))
    hits, domain = scored[0]
    return domain, hits


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: resolve_capability.py <query>')
        return 2
    query = ' '.join(sys.argv[1:])
    res = find_capability(query)
    if not res:
        print('No capability matched for query:', query)
        return 1
    name, hits = res

    # Emit the pre-run hook with query + resolved capability.
    #
    # `json` was used here without being imported until 2026-07-31 and the bare
    # `except Exception` swallowed the resulting NameError, so this branch had
    # never once run. Failures now go to stderr instead of vanishing.
    #
    # The hook's stdout is captured rather than inherited: this script's stdout
    # is a two-line contract (capability name, then source) that
    # test_resolver.py parses positionally, and hook chatter would make line 0
    # the hook's JSON instead of the answer.
    try:
        payload = json.dumps({'query': query, 'capability': name})
        runner = Path(__file__).resolve().parent / 'run_hook.py'
        if runner.exists():
            proc = subprocess.run(
                [sys.executable, str(runner), 'pre-run', payload],
                capture_output=True, text=True, check=False,
            )
            if proc.returncode != 0:
                print(f'warning: pre-run hook exited {proc.returncode}: '
                      f'{proc.stderr.strip()}', file=sys.stderr)
    except Exception as exc:  # never fail the lookup because the hook failed
        print(f'warning: pre-run hook not emitted: {exc}', file=sys.stderr)

    print(name)
    print(f'{ROUTING.relative_to(ROOT).as_posix()} ({hits} hit{"s" if hits != 1 else ""})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
