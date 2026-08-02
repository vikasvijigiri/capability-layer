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

# The context-budget meter (post-tool/01-context-budget.py).
#
# Each case names the failure it prevents. The thresholds are calibrated
# against a real session, so a silent drift in either direction turns the
# meter into either noise or wallpaper -- both are worse than no meter.
_BUDGET = ROOT / '.claude' / 'hooks' / 'post-tool' / '01-context-budget.py'
_BUDGET_STATE = ROOT / '.claude' / 'hooks' / 'state' / 'context-budget.json'


def budget_context(payload):
    """Fire the meter directly and return its additionalContext ('' if silent)."""
    env = os.environ.copy()
    env['HOOK_PAYLOAD'] = json.dumps(payload)
    env['PYTHONIOENCODING'] = 'utf-8'
    p = subprocess.run([PY, str(_BUDGET)], env=env, capture_output=True,
                       text=True, cwd=ROOT)
    if p.returncode != 0:
        return f'<exit {p.returncode}: {p.stderr.strip()}>'
    if not p.stdout.strip():
        return ''
    try:
        return json.loads(p.stdout)['hookSpecificOutput']['additionalContext']
    except Exception as exc:
        return f'<unparseable: {exc}>'


def budget_read(session, chars, tool='Read', path='/x/y/some-file.md'):
    return budget_context({'session_id': session, 'tool_name': tool,
                           'tool_input': {'file_path': path},
                           'tool_response': 'x' * chars})


_BUDGET_STATE.unlink(missing_ok=True)

_budget_cases = []

# A result under the single-result threshold must not speak. A meter that
# fires on ordinary reads gets filtered out and stops being read at all.
_budget_cases.append(('small read stays silent',
                      budget_read('bt1', 11_999) == ''))

# A fat single result must name the cheaper alternative for THAT tool --
# generic advice is not actionable.
_fat = budget_context({'session_id': 'bt1',
                       'tool_name': 'mcp__github__get_file_contents',
                       'tool_input': {'path': 'some-skill/SKILL.md'},
                       'tool_response': [{'type': 'text', 'text': 'y' * 17_000}]})
_budget_cases.append(('fat result reports its size', '17,000 chars' in _fat))
_budget_cases.append(('fat result names the tool-specific cheaper route',
                      'fields: [name, size]' in _fat))

# The offender list must keep the parent directory: the reads this hook exists
# to catch were four different repos' files all named SKILL.md.
_budget_cases.append(('offender label keeps the parent directory',
                      'some-skill/SKILL.md' in _fat))

# Crossing a cumulative step must report the running total once...
_crossed = ''
for _ in range(9):
    _out = budget_read('bt1', 16_000)
    if 'ingested this session' in _out:
        _crossed = _out
_budget_cases.append(('cumulative step reports the running total',
                      'ingested this session' in _crossed))

# ...and never again for the same step. A warning that repeats is a warning
# that gets ignored.
_budget_cases.append(('cumulative warning does not repeat within a step',
                      'ingested this session' not in budget_read('bt1', 10)))

# Sessions must not pool. One session's spending is not another's.
_budget_cases.append(('sessions are metered independently',
                      budget_read('bt2', 10) == ''))

# Fails open on every shape it does not recognise: no output, exit 0.
for _shape in (None, '', {}, [], {'weird': {'nested': 1}}):
    _budget_cases.append((f'unrecognised response shape {_shape!r} is silent',
                          budget_context({'session_id': 'bt3', 'tool_name': 'X',
                                          'tool_response': _shape}) == ''))

for _label, _ok in _budget_cases:
    if _ok:
        print(f'OK: context-budget {_label}')
    else:
        print(f'FAIL: context-budget {_label}')
        fail = True

_BUDGET_STATE.unlink(missing_ok=True)

if fail:
    sys.exit(1)
print('All hook tests passed')
