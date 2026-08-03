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
    ('pre-run', {'workflow': 'oauth-workflow'}),
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
    # Reads git history only; the payload's `trigger` is optional and its
    # absence is the auto-compaction case.
    ('pre-compact', {'trigger': 'auto'}),
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


# --- 07-layer-drift.py -------------------------------------------------------
#
# Three bugs shipped in this hook in one session, every one silent and every one
# found only by firing it by hand:
#
#   1. `structural` was keyed on "<status> <path>", so a file reported `A` by
#      `git show` and `?` by `git status` occupied two slots and the hook
#      double-counted its own addition.
#   2. `--swept` deleted the state file, so the next turn re-read the same HEAD,
#      rebuilt the counter, and the suggestion repeated every turn -- the exact
#      "nobody reads it" failure the hook exists to prevent.
#   3. A lost state file seeded `since: ""`, which was then written straight
#      back, making the fallback permanent.
#
# All three are behaviour over a SEQUENCE of turns, which is why reading the
# code missed them. These tests drive the sequence.

import contextlib as _ctx  # noqa: E402
import io as _io  # noqa: E402

_DRIFT = ROOT / '.claude/hooks/post-run/07-layer-drift.py'


def _load_drift(state_dir):
    spec = _u.spec_from_file_location('drift', _DRIFT)
    assert spec and spec.loader          # narrows for mypy; a missing hook is a bug
    mod = _u.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Redirect state to a temp dir. Baking absolute paths at import is how an
    # earlier suite wrote its scratch into the developer's own tree.
    mod._state_path = lambda: Path(state_dir) / 'layer-drift.json'   # type: ignore[attr-defined]
    return mod


def _fire(mod, files):
    """One turn. Returns the SPOKEN TEXT, or '' when the hook stayed silent.

    Parsing the JSON matters and the first version of this helper did not: the
    hook prints one line of JSON, so `stdout.splitlines()` returned a single
    line holding every entry, and the duplicate-path assertion below counted 1
    no matter how many entries there were. Re-introducing the bug it was written
    to catch produced a green run.
    """
    mod.changed_layer_files = lambda since='': files
    buf = _io.StringIO()
    with _ctx.redirect_stdout(buf):
        mod.main()
    raw = buf.getvalue().strip()
    if not raw:
        return ''
    return json.loads(raw)['hookSpecificOutput']['additionalContext']


with tempfile.TemporaryDirectory() as _dd:
    _ADDED = [('A', '.claude/skills/x/SKILL.md')]

    # 1. one file, two statuses -> one entry
    _m = _load_drift(_dd)
    _out = _fire(_m, [('?', '.claude/skills/x/SKILL.md'),
                      ('A', '.claude/skills/x/SKILL.md')])
    _entries = [ln for ln in _out.splitlines() if '.claude/skills/x' in ln]
    if len(_entries) != 1:
        print(f'FAIL: drift double-counts one path across statuses: {_entries}')
        fail = True
    else:
        print('OK: drift counts one entry per path, not per status')

    # 2. the nudge must STOP after a sweep.
    #
    # This stubs `git`, NOT `changed_layer_files`, and the distinction is the
    # whole test. Stubbing the higher function was the first attempt and it
    # could not fail: it bypassed the since-vs-HEAD selection that the bug
    # lived in, so reverting `swept()` to `unlink()` still produced a green run.
    # Here HEAD keeps reporting the same addition forever -- exactly the real
    # situation -- and only a recorded SHA can silence it.
    def _fake_git(*args):
        if args[:1] == ('rev-parse',):
            return 0, 'sha1'
        if args[:1] == ('cat-file',):
            return (0, '') if 'sha1' in args[2] else (1, '')
        if args[:1] == ('diff',):
            return 0, ''                      # nothing new since the sweep
        if args[:1] == ('show',):
            return 0, 'A	.claude/skills/x/SKILL.md'   # HEAD, unchanging
        return 0, ''

    def _turn(state_dir):
        mod = _load_drift(state_dir)
        mod.git = _fake_git
        buf = _io.StringIO()
        with _ctx.redirect_stdout(buf):
            mod.main()
        return buf.getvalue().strip()

    with tempfile.TemporaryDirectory() as _d2:
        if not _turn(_d2):
            print('FAIL: drift stayed silent when HEAD added a skill')
            fail = True
        _sw = _load_drift(_d2)
        _sw.git = _fake_git
        with _ctx.redirect_stdout(_io.StringIO()):
            _sw.swept()
        if _turn(_d2):
            print('FAIL: drift still nudges after --swept -- it rebuilt from the '
                  'same HEAD')
            fail = True
        else:
            print('OK: drift goes quiet after --swept')

    # 3. an empty `since` must never be written back
    (Path(_dd) / 'layer-drift.json').unlink(missing_ok=True)
    _m = _load_drift(_dd)
    _fire(_m, [])
    _since = json.loads((Path(_dd) / 'layer-drift.json').read_text())['since']
    if not _since:
        print('FAIL: drift wrote an empty `since` -- the fallback is now permanent')
        fail = True
    else:
        print('OK: drift anchors `since` on first run after state loss')

    # 4. a `since` that no longer resolves must not raise
    _p = Path(_dd) / 'layer-drift.json'
    _d = json.loads(_p.read_text())
    _d['since'] = 'dead' * 10
    _p.write_text(json.dumps(_d))
    _m = _load_drift(_dd)
    try:
        _fire(_m, [])
        print('OK: drift survives a `since` that no longer resolves')
    except Exception as _exc:  # noqa: BLE001
        print(f'FAIL: drift raised on an unresolvable `since`: {_exc}')
        fail = True

if fail:
    sys.exit(1)
print('All hook tests passed')
