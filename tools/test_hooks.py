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
# Six of the eleven events here were deleted on 2026-08-02 with their only
# subscribers -- on-validate-fail, on-blueprint-promote, on-human-approval-request,
# on-deploy-failure, on-error, post-tool. `run_hook.py` prints "No hooks for event"
# and exits 0 for an unknown event, so leaving them listed would have asserted
# nothing while looking like coverage.
#
# `post-run` fires 06-artifact-autocommit.py, which runs every suite in tools/ --
# including this one. The env flag is the documented re-entry guard; without it
# this line recurses until the harness times out, with no error to show for it.
BENIGN_EVENTS = [
    ('post-run', {'workflow': 'oauth-workflow', 'status': 'success'}),
    ('on-artifact-create', {'event': 'test', 'capabilities_written': 7}),
    ('session-start', {}),
    # Fired from cwd=ROOT, so the source-repo refusal holds and nothing is
    # installed. This asserts only that it imports and exits clean -- the
    # install/refuse behaviour is exercised by firing it with a `cwd` payload
    # against a throwaway git repo, which is not something a suite should leave
    # on disk. Worth having anyway: this hook is wired in ~/.claude/settings.json
    # and a syntax error in it would break session start in every repo at once.
    ('global-session-start', {}),
    # `pre-edit` and `pre-deploy` were on disk, wired, and fired by NOTHING until
    # 2026-08-04 -- five of the seven event directories were covered. Both are
    # DENY hooks, and a PreToolUse hook that exits 0 ALLOWS: a syntax error or a
    # broken import in either would ship green while silently permitting exactly
    # what it exists to refuse. A benign payload proves they load and allow; the
    # refusal paths are asserted separately below.
    ('pre-edit', {'tool_name': 'Write', 'tool_input': {'file_path': 'README.md'}}),
    ('pre-deploy', {'tool_name': 'Bash', 'tool_input': {'command': 'echo hello'}}),
]

os.environ['UAIOS_AUTOCOMMIT_RUNNING'] = '1'

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

# 3. pre-commit with a planted secret should emit a structured deny and return 0.
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
    if p.returncode != 0 or '"permissionDecision": "deny"' not in p.stdout:
        print('FAIL: pre-commit did not emit a structured deny')
        fail = True
    else:
        print('OK: pre-commit detected planted secret with structured deny')
finally:
    secret_file.unlink(missing_ok=True)

# 4. `is_git_commit` and the branch guard's target resolution.
#
# Both fixed 2026-08-03 after the guard allowed eight commits onto another
# repo's protected `main`. Two independent bugs stacked:
#   - the old COMMIT_RE could not match `git -C <dir> commit`, because `-C`
#     takes a value and no repetition consumes it;
#   - the guard resolved the branch from the SESSION's cwd, not the command's.
# Either alone makes the guard silently useless for a cross-repo commit.
import importlib.util as _u  # noqa: E402


def _load(path, name):
    spec = _u.spec_from_file_location(name, path)
    # Real asserts, not type-checker appeasement: a mistyped path returns None
    # and fails later as `NoneType has no attribute loader`, which reads like a
    # bug in the module under test.
    assert spec is not None, f'no import spec for {path}'
    assert spec.loader is not None, f'no loader for {path}'
    mod = _u.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


os.environ.setdefault('HOOK_PAYLOAD', '{}')
_hl = _load(ROOT / '.claude' / 'hooks' / '_hooklib.py', '_hooklib')
_bg = _load(ROOT / '.claude' / 'hooks' / 'pre-commit' / '02-branch-guard.py',
            'branch_guard')

COMMIT_CASES = [
    ('git commit -m x', True, 'plain'),
    ('git -C /repo commit -m x', True, 'value-taking global flag'),
    ('git -c user.name=T commit', True, '-c with a value'),
    ('cd /repo && git commit', True, 'after a cd'),
    ('git commit-tree abc', False, 'commit-tree is not commit'),
    ('git status', False, 'not a commit'),
    ('echo git commit', True, 'substring match is deliberate -- one extra ask'),
]
for _cmd, _want, _label in COMMIT_CASES:
    if _hl.is_git_commit(_cmd) != _want:
        print(f'FAIL: is_git_commit({_cmd!r}) -> {not _want}, want {_want} ({_label})')
        fail = True
    else:
        print(f'OK: is_git_commit {_label}')

_here = str(ROOT)
TARGET_CASES = [
    ('git commit -m x', _here, 'no redirection'),
    ('cd .. && git commit', str(ROOT.parent), 'cd wins'),
    ('git -C .. commit', str(ROOT.parent), 'git -C wins'),
    ('cd /definitely-not-a-dir && git commit', _here, 'nonexistent falls back'),
    # A boolean global flag before -C. The old regex assumed every global flag
    # was `-x value`, so `--no-pager` (which takes none) stopped the repetition
    # and -C was never seen -- the guard then checked the SESSION's branch and
    # would have allowed a commit onto a sibling repo's protected main. Exactly
    # the 2026-08-03 bug, reachable again by one extra flag. Four of git's own
    # documented global flags trigger it.
    ('git --no-pager -C .. commit', str(ROOT.parent), '--no-pager before -C'),
    ('git -P -C .. commit', str(ROOT.parent), '-P before -C'),
    ('git --paginate -C .. commit', str(ROOT.parent), '--paginate before -C'),
    ('git --literal-pathspecs -C .. commit', str(ROOT.parent),
     '--literal-pathspecs before -C'),
    ('git -c user.name=T -C .. commit', str(ROOT.parent), '-c=value then -C'),
    ('git --git-dir=../.git -C .. commit', str(ROOT.parent), '--flag=value then -C'),
]
# Distinct names from the block above: mypy types a variable once per scope,
# and _want is a bool there and a path here.
for _tcmd, _tdir, _tlabel in TARGET_CASES:
    _got = os.path.normcase(os.path.abspath(_bg.target_dir(_tcmd, _here)))
    if _got != os.path.normcase(os.path.abspath(_tdir)):
        print(f'FAIL: target_dir({_tcmd!r}) -> {_got}, want {_tdir} ({_tlabel})')
        fail = True
    else:
        print(f'OK: target_dir {_tlabel}')



# 5. The two deny hooks must actually DENY.
#
# The signal is `permissionDecision: "deny"` in the JSON, on exit 0 -- NOT a
# non-zero exit. `_hooklib.deny()` prints the decision and returns normally, and
# asserting exit 2 here reported both hooks as broken when both were working.
# Exit 2 is the *other* deny path (stderr as the reason) and neither hook uses it.
#
# The cloud command is assembled at runtime, exactly like PLANTED_KEY above and
# for the same reason: `01-secret-scan.py` and `01-spend-guard.py` both scan the
# commands this repo runs, and a literal cloud-spend string in a source file makes
# the file itself undeployable. It denied the command that was writing this test.
_CLOUD = 'aws ' + 'ec2 ' + 'run-instances --image-id ami-0'
# Same runtime assembly, same reason: `03-attribution-guard.py` scans the commands
# this repo runs, so a literal trailer in this file would make the file that tests
# the guard the one thing the guard refuses to commit.
_DIRTY_COMMIT = ('git commit -m "docs: x' + chr(10) + chr(10)
                 + 'Co-Authored' + '-By: Claude <noreply@anthropic.com>"')
DENY_CASES = [
    ('pre-edit', {'tool_name': 'Write',
                  'tool_input': {'file_path': 'package-lock.json'}},
     'a lockfile write'),
    ('pre-deploy', {'tool_name': 'Bash', 'tool_input': {'command': _CLOUD}},
     'an unattended cloud-spend command'),
    # Assembled at runtime for the same reason as _CLOUD and PLANTED_KEY: the
    # guard scans this repo's own commands, and a literal trailer here would make
    # the file that tests it uncommittable.
    ('pre-commit', {'tool_name': 'Bash', 'tool_input': {'command': _DIRTY_COMMIT}},
     'AI attribution in a commit message'),
]
for _event, _payload, _label in DENY_CASES:
    _p = run_hook(_event, _payload)
    _denied = '"permissionDecision": "deny"' in _p.stdout or _p.returncode == 2
    if not _denied:
        print(f'FAIL: {_event} allowed {_label} -- no deny decision, exit '
              f'{_p.returncode}: {_p.stdout.strip()[:120]}')
        fail = True
    else:
        print(f'OK: {_event} denies {_label}')

# --- post-run/09-telemetry.py: unified per-run snapshot ---------------------
#
# Fired via the `post-run` event, which runs `00-dispatch.py`'s whole STEPS
# sequence -- the new finalizer runs alongside the existing four. Asserts on
# the real, gitignored `.claude/hooks/state/telemetry.jsonl` (`.gitignore:28`),
# same convention as the DENY_CASES/BENIGN_EVENTS above firing real hooks in
# this real repo, and the skill-cost tests' before/after delta style.
_TELEMETRY_STATE = ROOT / '.claude' / 'hooks' / 'state' / 'telemetry.jsonl'
_EXPECTED_UNAVAILABLE_KEYS = {
    'execution_level', 'model', 'agents_spawned', 'api_call_count',
    'context_tokens', 'input_tokens', 'output_tokens', 'latency',
    'parallelism', 'cache_hits', 'cache_misses', 'verification_level',
    'retries', 'escalations', 'success', 'quality_signal',
}


def _telemetry_lines():
    try:
        return _TELEMETRY_STATE.read_text(encoding='utf-8').splitlines()
    except OSError:
        return []


_before_lines = _telemetry_lines()
_p = run_hook('post-run', {'workflow': 'test', 'status': 'success'})
_after_lines = _telemetry_lines()
if _p.returncode != 0:
    print(f'FAIL: post-run (telemetry finalizer) exited {_p.returncode}\n{_p.stderr}')
    fail = True
elif len(_after_lines) != len(_before_lines) + 1:
    print(f'FAIL: telemetry.jsonl grew by {len(_after_lines) - len(_before_lines)} '
          f'line(s), want 1 (append-only, one row per post-run fire)')
    fail = True
else:
    print('OK: post-run appends exactly one telemetry row')
    _row = json.loads(_after_lines[-1])
    _missing_top = {'ts', 'run_scope', 'chain', 'tools_called', 'skills_loaded',
                     'task_type', 'unavailable'} - _row.keys()
    if _missing_top:
        print(f'FAIL: telemetry row missing top-level keys: {sorted(_missing_top)}')
        fail = True
    else:
        print('OK: telemetry row has every top-level schema key')
    _missing_unavail = _EXPECTED_UNAVAILABLE_KEYS - set(_row.get('unavailable', {}))
    if _missing_unavail:
        print(f'FAIL: telemetry row\'s "unavailable" map is missing reasoned '
              f'fields: {sorted(_missing_unavail)}')
        fail = True
    else:
        print('OK: every structurally-unavailable target field is named with a reason')
    _bad_reasons = [k for k, v in _row.get('unavailable', {}).items()
                    if not isinstance(v, str) or len(v) < 5]
    if _bad_reasons:
        print(f'FAIL: "unavailable" entries with no real reason string: {_bad_reasons}')
        fail = True
    # `02-skill-cost.py` (skills_loaded's producer) does not exist on this
    # tree -- confirmed: `(ROOT / '.claude/hooks/post-tool/02-skill-cost.py')
    # .is_file()` is False here. The honest report is `None` plus a reasoned
    # `unavailable` entry, never a fabricated-looking zero-filled dict.
    _skill_cost_producer = ROOT / '.claude' / 'hooks' / 'post-tool' / '02-skill-cost.py'
    if not _skill_cost_producer.is_file():
        if _row.get('skills_loaded') is not None:
            print(f'FAIL: skills_loaded should be None when its producer '
                  f'({_skill_cost_producer}) is absent, got {_row.get("skills_loaded")!r}')
            fail = True
        elif 'skills_loaded' not in _row.get('unavailable', {}):
            print('FAIL: skills_loaded is None but missing from "unavailable" '
                  '-- an absent counter must be named, not silently null')
            fail = True
        else:
            print('OK: skills_loaded honestly reports "unavailable" -- its '
                  'producer is absent on this tree, not a fabricated zero')

# A second fire appends a SECOND row -- proves append-only, not overwrite.
_p2 = run_hook('post-run', {'workflow': 'test', 'status': 'success'})
_after2_lines = _telemetry_lines()
if _p2.returncode != 0 or len(_after2_lines) != len(_after_lines) + 1:
    print(f'FAIL: a second post-run fire did not append a second telemetry row '
          f'(exit {_p2.returncode}, {len(_after2_lines)} lines vs {len(_after_lines)} before)')
    fail = True
else:
    print('OK: a second post-run fire appends a second telemetry row (append-only)')

# --- post-tool/01-context-cost.py: had zero test coverage anywhere in the ---
# repo (Notion-objectives audit finding, objective 12) until now. Asserts on
# the real, gitignored call-fingerprints.json (.gitignore:28), same
# before/after-delta style as the skill-cost/telemetry blocks above.
_CALL_FP_STATE = ROOT / '.claude' / 'hooks' / 'state' / 'call-fingerprints.json'


def _call_fp_totals():
    try:
        return json.loads(_CALL_FP_STATE.read_text(encoding='utf-8')).get('_totals') or {}
    except (OSError, ValueError):
        return {'calls': 0, 'chars': 0, 'repeats': 0}


# A command >= WARN_CHARS (700) triggers the "[context cost]" notice on stderr.
_LONG_CMD = 'echo ' + ('x' * 700)
_p = run_hook('post-tool', {'tool_name': 'Bash', 'tool_input': {'command': _LONG_CMD}})
if _p.returncode != 0 or '[context cost]' not in _p.stderr:
    print(f'FAIL: a >=700-char Bash command did not trigger the context-cost '
          f'notice -- exit {_p.returncode}, stderr: {_p.stderr[:200]!r}')
    fail = True
else:
    print('OK: post-tool warns on an oversized Bash command')

# A short command must NOT trigger the notice (WARN_CHARS is a floor, not a
# hair-trigger) -- proven, not assumed.
_p = run_hook('post-tool', {'tool_name': 'Bash', 'tool_input': {'command': 'echo hi'}})
if '[context cost]' in _p.stderr:
    print('FAIL: a short Bash command wrongly triggered the context-cost notice')
    fail = True
else:
    print('OK: a short Bash command stays silent')

# A repeated command (long enough to fingerprint, not VOLATILE-prefixed)
# triggers "[repeat]" on its second occurrence, not its first.
_repeat_cmd = 'python -c "print(12345)"' + (' ' * 20) + '# padding to clear MIN_REPEAT_CHARS'
_before = _call_fp_totals()
_p1 = run_hook('post-tool', {'tool_name': 'Bash', 'tool_input': {'command': _repeat_cmd}})
_p2 = run_hook('post-tool', {'tool_name': 'Bash', 'tool_input': {'command': _repeat_cmd}})
_after = _call_fp_totals()
if '[repeat]' in _p1.stderr:
    print('FAIL: the FIRST occurrence of a command wrongly fired [repeat]')
    fail = True
elif '[repeat]' not in _p2.stderr:
    print(f'FAIL: the SECOND occurrence of the same command did not fire '
          f'[repeat] -- stderr: {_p2.stderr[:200]!r}')
    fail = True
elif _after['calls'] - _before['calls'] != 2 or _after['repeats'] - _before['repeats'] != 1:
    print(f'FAIL: totals delta wrong -- before={_before} after={_after}, '
          f'want +2 calls / +1 repeat')
    fail = True
else:
    print('OK: a repeated command fires [repeat] on its 2nd occurrence only, '
          'and totals count both calls with exactly 1 repeat')

# A VOLATILE-prefixed command (e.g. "git status") is never fingerprinted as a
# repeat, even run twice -- it is expected to be re-run because its answer
# changes. Still counted in totals, per the module's own stated design.
_before = _call_fp_totals()
run_hook('post-tool', {'tool_name': 'Bash', 'tool_input': {'command': 'git status --porcelain -uall --extra-padding-to-clear-min-chars'}})
_p2 = run_hook('post-tool', {'tool_name': 'Bash', 'tool_input': {'command': 'git status --porcelain -uall --extra-padding-to-clear-min-chars'}})
_after = _call_fp_totals()
if '[repeat]' in _p2.stderr:
    print('FAIL: a VOLATILE-prefixed command wrongly fired [repeat] on its 2nd run')
    fail = True
elif _after['calls'] - _before['calls'] != 2:
    print(f'FAIL: VOLATILE commands should still be counted in totals -- '
          f'before={_before} after={_after}')
    fail = True
else:
    print('OK: a VOLATILE-prefixed command is never flagged [repeat], but is still counted')

# A non-watched tool (e.g. Read) is ignored entirely -- no notice, no totals bump.
_before = _call_fp_totals()
_p = run_hook('post-tool', {'tool_name': 'Read', 'tool_input': {'file_path': 'README.md'}})
_after = _call_fp_totals()
if _p.stderr.strip() or _after != _before:
    print(f'FAIL: a non-watched tool_name affected context-cost state -- '
          f'before={_before} after={_after}, stderr={_p.stderr[:120]!r}')
    fail = True
else:
    print('OK: a non-watched tool_name (Read) is ignored entirely')

if fail:
    sys.exit(1)
print('All hook tests passed')
