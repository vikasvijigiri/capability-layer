#!/usr/bin/env python3
"""Test suite for the hooks subsystem (tools/run_hook.py).

Verifies each implemented event runs its subscriber(s) successfully, and that
pre-commit correctly fails (non-zero exit) when a secret pattern is present.

Usage:
    python tools/test_hooks.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PY = sys.executable
ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'tools' / 'run_hook.py'

fail = False


def run_hook(event, payload_obj):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(payload_obj, f)
        path = f.name
    try:
        p = subprocess.run([PY, str(RUNNER), event, '--file', path], capture_output=True, text=True, cwd=ROOT)
    finally:
        Path(path).unlink(missing_ok=True)
    return p


# 1. Each implemented event with a benign payload should exit 0.
BENIGN_EVENTS = [
    ('pre-run', {'workflow': 'oauth-workflow'}),
    ('post-run', {'workflow': 'oauth-workflow', 'status': 'success'}),
    ('on-validate-fail', {'validator': 'smoke-test', 'failures': ['x']}),
    ('on-blueprint-promote', {'blueprint': {'name': 'test-blueprint'}}),
    ('on-human-approval-request', {'workflow': 'deploy-pipeline'}),
    ('on-deploy-failure', {'workflow': 'deploy-pipeline', 'status': 'failed'}),
    ('on-artifact-create', {'event': 'test', 'capabilities_written': 7}),
    ('on-error', {'error': 'ValueError: test'}),
    ('session-start', {}),
]

for event, payload in BENIGN_EVENTS:
    p = run_hook(event, payload)
    if p.returncode != 0:
        print(f'FAIL: {event} exited {p.returncode}\n{p.stdout}\n{p.stderr}')
        fail = True
    else:
        print(f'OK: {event}')

# 2. pre-commit with a clean file should pass.
p = run_hook('pre-commit', {'files': ['requirements.txt']})
if p.returncode != 0:
    print(f'FAIL: pre-commit (clean) exited {p.returncode}\n{p.stdout}')
    fail = True
else:
    print('OK: pre-commit (clean file)')

# 3. pre-commit with a planted secret should fail (non-zero exit).
# The fake key is assembled at runtime rather than written as one literal:
# 01-secret-scan.py scans this file too, and a literal `AKIA` + 16 chars here
# makes the repo permanently uncommittable. The bytes written to the temp file
# are identical either way, so the hook under test still sees a full key and
# must still reject it -- this weakens the fixture's realism not at all.
PLANTED_KEY = 'AKIA' + 'ABCDEFGHIJKLMNOP'
with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8', dir=ROOT) as f:
    f.write(f'aws_key = "{PLANTED_KEY}"\n')
    secret_file = Path(f.name)
try:
    rel = secret_file.relative_to(ROOT).as_posix()
    p = run_hook('pre-commit', {'files': [rel]})
    if p.returncode == 0:
        print('FAIL: pre-commit did not detect planted secret')
        fail = True
    else:
        print('OK: pre-commit detected planted secret (exit', p.returncode, ')')
finally:
    secret_file.unlink(missing_ok=True)

# 4. Review gate: which commands it classifies as a delivery, and which it must
# leave alone.
#
# The read-only PR verbs matter as much as the gated ones. A gate that fires on
# `gh pr view` teaches people to approve without reading, which costs more than it
# protects.
#
# This imports the module and asks it to classify the command, rather than running
# the hook and reading its decision. An end-to-end decision also depends on receipt
# state, so the first draft of this test passed or failed depending on whether an
# earlier test had recorded a receipt -- it asserted "the regex matches" while
# actually measuring "the regex matches AND no valid receipt exists". Classification
# is the part that belongs in a regex test.
import importlib.util  # noqa: E402

GATE = ROOT / '.claude' / 'hooks' / 'pre-commit' / '03-review-gate.py'
_spec = importlib.util.spec_from_file_location('review_gate', GATE)
_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gate)


def gate_decision(command):
    """The action the gate would gate on, or None when it ignores the command."""
    if _gate.DRY_RUN_RE.search(command):
        return None
    if _gate.PR_RE.search(command):
        return 'ask'
    if _gate.COMMIT_RE.search(command) or _gate.PUSH_RE.search(command):
        return 'ask'
    return None


GATED = ['git commit -m x', 'git push', 'gh pr create --fill',
         'gh pr merge 12', 'gh pr ready']
UNGATED = ['gh pr view 12', 'gh pr list', 'gh pr diff', 'gh pr checks',
           'git status', 'git log --oneline', 'git commit --dry-run',
           'gh issue create']

# The verb is matched anywhere in the command, not anchored to its start, so
# `echo gh pr create` and `grep -r "git push" .` both ask. That is deliberate and
# predates the PR verbs: anchoring would miss `cd sub && git commit`, and for a
# gate whose worst outcome is one extra prompt, a false ask beats a missed
# delivery. Asserted so nobody "fixes" it into silence. (The `deny` in
# 04-delivery-guard.py is the opposite case -- there a false positive blocks real
# work, and its Windows path bug is tracked separately.)
SUBSTRING_ASKS = ['echo gh pr create', "grep -r 'git push' .", 'echo git commit']

for cmd in GATED:
    if gate_decision(cmd) != 'ask':
        print(f'FAIL: review gate did not ask for {cmd!r}')
        fail = True
    else:
        print(f'OK: review gate asks for {cmd!r}')

for cmd in UNGATED:
    decision = gate_decision(cmd)
    if decision is not None:
        print(f'FAIL: review gate fired on read-only {cmd!r} -> {decision}')
        fail = True
    else:
        print(f'OK: review gate silent for {cmd!r}')

for cmd in SUBSTRING_ASKS:
    if gate_decision(cmd) != 'ask':
        print(f'FAIL: substring match lost -- gate went silent for {cmd!r}')
        fail = True
    else:
        print(f'OK: review gate asks on substring match {cmd!r}')

if fail:
    sys.exit(1)
print('All hook tests passed')
