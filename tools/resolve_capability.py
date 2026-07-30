#!/usr/bin/env python3
"""Resolve capability for a simple query by scanning `.claude/capabilities/*/index.md`.

Usage:
    python tools/resolve_capability.py "oauth"    # prints matched capability and index path
"""
import sys
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CAP_DIR = ROOT / '.claude' / 'capabilities'


def load_index(cap_path: Path) -> str:
    idx = cap_path / 'index.md'
    if not idx.exists():
        return ''
    return idx.read_text(encoding='utf-8')


def find_capability(query: str):
    q = query.lower()
    matches = []
    for cap in sorted(CAP_DIR.iterdir()):
        if not cap.is_dir():
            continue
        content = load_index(cap)
        # try matching capability name
        if cap.name.lower() in q:
            matches.append((cap.name, cap))
            continue
        # look for Keywords: line
        m = re.search(r"^Keywords:\s*(.+)$", content, re.M | re.I)
        if m:
            keys = [k.strip().lower() for k in m.group(1).split(',')]
            for k in keys:
                if k and k in q:
                    matches.append((cap.name, cap))
                    break
        # fallback: search index content for query tokens
        if q in content.lower():
            matches.append((cap.name, cap))

    # rank: exact name matches first, then keyword/content matches
    if not matches:
        return None
    # deduplicate preserving order
    seen = set()
    uniq = []
    for name, path in matches:
        if name not in seen:
            seen.add(name)
            uniq.append((name, path))
    return uniq[0]


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: resolve_capability.py <query>')
        sys.exit(2)
    query = ' '.join(sys.argv[1:])
    res = find_capability(query)
    if not res:
        print('No capability matched for query:', query)
        sys.exit(1)
    name, path = res
    # Emit pre-run hook with query + resolved capability
    try:
        payload = json.dumps({'query': query, 'capability': name})
        runner = Path(__file__).resolve().parents[0] / 'run_hook.py'
        if runner.exists():
            subprocess.run([sys.executable, str(runner), 'pre-run', payload])
    except Exception:
        pass
    print(name)
    print(path / 'index.md')
