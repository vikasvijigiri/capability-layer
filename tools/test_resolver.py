#!/usr/bin/env python3
"""Simple test runner for the resolver CLI."""
import subprocess
import sys

PY = sys.executable

cases = [
    ('oauth', 'backend'),
    ('rag', 'ai'),
    ('accessibility', 'frontend'),
    ('deploy', 'deployment'),
    ('logs', 'debugging'),
    ('docs', 'documentation'),
]

fail = False
for query, expected in cases:
    p = subprocess.run([PY, 'tools/resolve_capability.py', query], capture_output=True, text=True)
    out = p.stdout.strip().splitlines()
    if p.returncode != 0:
        print(f'ERROR running resolver for {query}:', p.stderr)
        fail = True
        continue
    name = out[0] if out else ''
    if name != expected:
        print(f'FAIL: query={query} expected={expected} got={name}')
        fail = True
    else:
        print(f'OK: {query} -> {name}')

if fail:
    sys.exit(1)
print('All tests passed')
