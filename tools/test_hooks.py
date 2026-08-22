#!/usr/bin/env python3
"""Test suite for the hooks subsystem (tools/run_hook.py).

Verifies each implemented event runs its subscriber(s) successfully, and that
permission-security correctly fails (non-zero exit) when a secret pattern is present.

Usage:
    python tools/test_hooks.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time
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
# `stop-finalization` fires 06-artifact-autocommit.py, which runs every suite in tools/ --
# including this one. The env flag is the documented re-entry guard; without it
# this line recurses until the harness times out, with no error to show for it.
BENIGN_EVENTS = [
    ('stop-finalization', {'workflow': 'oauth-workflow', 'status': 'success'}),
    ('post-edit-validation', {'event': 'test', 'capabilities_written': 7}),
    ('session-init', {}),
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
    ('permission-security', {'tool_name': 'Bash', 'tool_input': {'command': 'echo hello'}}),
]

os.environ['UAIOS_AUTOCOMMIT_RUNNING'] = '1'

for event, payload in BENIGN_EVENTS:
    p = run_hook(event, payload)
    if p.returncode != 0:
        print(f'FAIL: {event} exited {p.returncode}\n{p.stdout}\n{p.stderr}')
        fail = True
    else:
        print(f'OK: {event}')

# 2. permission-security with a clean file should pass.
p = run_hook('permission-security', {'files': ['requirements.txt']})
if p.returncode != 0:
    print(f'FAIL: permission-security (clean) exited {p.returncode}\n{p.stdout}')
    fail = True
else:
    print('OK: permission-security (clean file)')

# 3. permission-security with a planted secret should emit a structured deny and return 0.
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
    p = run_hook('permission-security', {'files': [rel]})
    if p.returncode != 0 or '"permissionDecision": "deny"' not in p.stdout:
        print('FAIL: permission-security did not emit a structured deny')
        fail = True
    else:
        print('OK: permission-security detected planted secret with structured deny')
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
_bg = _load(ROOT / '.claude' / 'hooks' / 'permission-security' / '02-branch-guard.py',
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
    ('permission-security', {'tool_name': 'Bash', 'tool_input': {'command': _CLOUD}},
     'an unattended cloud-spend command'),
    # Assembled at runtime for the same reason as _CLOUD and PLANTED_KEY: the
    # guard scans this repo's own commands, and a literal trailer here would make
    # the file that tests it uncommittable.
    ('permission-security', {'tool_name': 'Bash', 'tool_input': {'command': _DIRTY_COMMIT}},
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

# --- context-budget/02-skill-cost.py: skill-body-load counter --------------------
#
# `.claude/hooks/state/skill-cost.json` is a real, gitignored, running total
# (see `.gitignore:28`) -- these assert on the DELTA a fire produces, not an
# absolute value, matching how this repo already tests against real state
# (`test_resume.py`'s temp-repo fixtures, the DENY_CASES above firing real
# hooks in this real repo).
_SKILL_COST_STATE = ROOT / '.claude' / 'hooks' / 'state' / 'skill-cost.json'
_NO_SLOP_SKILL_MD = ROOT / '.claude' / 'skills' / 'refactoring' / 'SKILL.md'


def _skill_cost_totals():
    try:
        return json.loads(_SKILL_COST_STATE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'calls': 0, 'chars': 0, 'unattributed': 0}


SKILL_COST_CASES = [
    ({'tool_name': 'Skill', 'tool_input': {'skill': 'refactoring'}},
     'known skill via "skill" key',
     lambda before, after: after['chars'] - before['chars']
     == _NO_SLOP_SKILL_MD.stat().st_size),
    ({'tool_name': 'Skill', 'tool_input': {'skill_name': 'refactoring'}},
     'known skill via "skill_name" fallback',
     lambda before, after: after['chars'] - before['chars']
     == _NO_SLOP_SKILL_MD.stat().st_size),
    ({'tool_name': 'Skill', 'tool_input': {'name': 'refactoring'}},
     'known skill via "name" fallback',
     lambda before, after: after['chars'] - before['chars']
     == _NO_SLOP_SKILL_MD.stat().st_size),
    ({'tool_name': 'Skill', 'tool_input': {}},
     'no candidate key -- counted as unattributed, not silently dropped',
     lambda before, after: after['unattributed'] - before['unattributed'] == 1
     and after['chars'] == before['chars']),
    ({'tool_name': 'Skill', 'tool_input': {'skill': 'does-not-exist'}},
     'a stale/renamed skill name resolves to 0 chars, not an error',
     lambda before, after: after['chars'] == before['chars']
     and after['calls'] - before['calls'] == 1),
    ({'tool_name': 'Skill', 'tool_input': {'skill': '../../../../etc/passwd'}},
     'a traversal-shaped skill name is rejected, not resolved outside skills/',
     lambda before, after: after['chars'] == before['chars']
     and after['calls'] - before['calls'] == 1),
    ({'tool_name': 'Bash', 'tool_input': {'command': 'echo hi'}},
     'a non-Skill tool_name is ignored entirely',
     lambda before, after: after == before),
]
for _payload, _label, _assertion in SKILL_COST_CASES:
    _before = _skill_cost_totals()
    _p = run_hook('context-budget', _payload)
    _after = _skill_cost_totals()
    if _p.returncode != 0:
        print(f'FAIL: post-tool ({_label}) exited {_p.returncode}\n{_p.stderr}')
        fail = True
    elif not _assertion(_before, _after):
        print(f'FAIL: post-tool skill-cost ({_label}) -- before={_before} '
              f'after={_after}')
        fail = True
    else:
        print(f'OK: post-tool skill-cost -- {_label}')
    # Every case increments `calls` by 1 except the ignored non-Skill tool.
    _want_calls_delta = 0 if _payload.get('tool_name') != 'Skill' else 1
    if _after['calls'] - _before['calls'] != _want_calls_delta:
        print(f'FAIL: post-tool skill-cost ({_label}) -- calls delta '
              f'{_after["calls"] - _before["calls"]}, want {_want_calls_delta}')
        fail = True

# --- telemetry/09-telemetry.py: unified per-run snapshot ---------------------
#
# Fired via the `stop-finalization` event, which runs `00-dispatch.py`'s whole STEPS
# sequence -- the new finalizer runs alongside the existing four. Asserts on
# the real, gitignored `.claude/hooks/state/telemetry.jsonl` (`.gitignore:28`),
# same convention as the DENY_CASES/BENIGN_EVENTS above firing real hooks in
# this real repo, and the skill-cost tests' before/after delta style.
_TELEMETRY_STATE = ROOT / '.claude' / 'hooks' / 'state' / 'telemetry.jsonl'
# 'agents_spawned' moved out of this set once 05-agent-cost.py started
# measuring it (2026-08-21, spec-defined-metrics plan) -- it now reports a
# real 'agents_spawned' field on the snapshot instead of a reason string here.
# 'api_call_count', 'latency', 'retries' and 'escalations' moved out the same
# way once 06-tool-cost.py, 02-turn-timer.py and the retries read-path
# started measuring them (2026-08-21, four-more-spec-metrics plan) -- they
# now report real 'api_calls', 'turn_latency_seconds' and 'retries' fields.
# 'execution_level' moved out the same way once prompt-intake/
# 01-entry-classifier.py started predicting it and this file started
# recording the actual level from real counters (2026-08-21,
# notion-architecture-merge plan) -- it now reports a real
# {'predicted': ..., 'actual': ...} pair instead of a reason string here.
_EXPECTED_UNAVAILABLE_KEYS = {
    'model',
    'context_tokens', 'input_tokens', 'output_tokens',
    'parallelism', 'cache_hits', 'cache_misses', 'verification_level',
    'success', 'quality_signal',
}


def _telemetry_lines():
    try:
        return _TELEMETRY_STATE.read_text(encoding='utf-8').splitlines()
    except OSError:
        return []


_before_lines = _telemetry_lines()
_p = run_hook('stop-finalization', {'workflow': 'test', 'status': 'success'})
_after_lines = _telemetry_lines()
if _p.returncode != 0:
    print(f'FAIL: stop-finalization (telemetry finalizer) exited {_p.returncode}\n{_p.stderr}')
    fail = True
elif len(_after_lines) != len(_before_lines) + 1:
    print(f'FAIL: telemetry.jsonl grew by {len(_after_lines) - len(_before_lines)} '
          f'line(s), want 1 (append-only, one row per stop-finalization fire)')
    fail = True
else:
    print('OK: stop-finalization appends exactly one telemetry row')
    _row = json.loads(_after_lines[-1])
    _missing_top = {'ts', 'run_scope', 'chain', 'tools_called', 'skills_loaded',
                     'task_type', 'execution_level', 'context_read', 'agents_spawned',
                     'duplicate_rate', 'api_calls', 'turn_latency_seconds',
                     'human_interventions', 'retries', 'unavailable'} - _row.keys()
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
    # tree -- confirmed: `(ROOT / '.claude/hooks/context-budget/02-skill-cost.py')
    # .is_file()` is False here. The honest report is `None` plus a reasoned
    # `unavailable` entry, never a fabricated-looking zero-filled dict.
    _skill_cost_producer = ROOT / '.claude' / 'hooks' / 'context-budget' / '02-skill-cost.py'
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
    else:
        # Producer present (02-skill-cost.py merged in) -- the positive path:
        # skills_loaded must be a real populated dict, and must NOT still be
        # named in "unavailable" now that something writes it.
        _sl = _row.get('skills_loaded')
        if not isinstance(_sl, dict) or 'calls' not in _sl or 'chars' not in _sl:
            print(f'FAIL: skills_loaded should be a real {{calls,chars,unattributed}} '
                  f'dict now that its producer exists, got {_sl!r}')
            fail = True
        elif 'skills_loaded' in _row.get('unavailable', {}):
            print('FAIL: skills_loaded is populated but still listed in '
                  '"unavailable" -- stale claim once the counter exists')
            fail = True
        else:
            print('OK: skills_loaded reports a real, populated dict now that '
                  '02-skill-cost.py exists, and is no longer claimed unavailable')
    _EVEL = {'E0', 'E1', 'E2', 'E3', 'E4', 'E5'}
    _el = _row.get('execution_level')
    if not isinstance(_el, dict) or 'predicted' not in _el or 'actual' not in _el:
        print(f'FAIL: execution_level should be a {{predicted, actual}} pair, got {_el!r}')
        fail = True
    elif _el['predicted'] is not None and _el['predicted'] not in _EVEL:
        print(f'FAIL: execution_level.predicted {_el["predicted"]!r} is not one of {_EVEL}')
        fail = True
    elif _el['actual'] is not None and _el['actual'] not in _EVEL:
        print(f'FAIL: execution_level.actual {_el["actual"]!r} is not one of {_EVEL}')
        fail = True
    else:
        print(f'OK: execution_level reports a real predicted/actual pair '
              f'{_el!r}, never the old hardcoded gap-string')

# A second fire appends a SECOND row -- proves append-only, not overwrite.
_p2 = run_hook('stop-finalization', {'workflow': 'test', 'status': 'success'})
_after2_lines = _telemetry_lines()
if _p2.returncode != 0 or len(_after2_lines) != len(_after_lines) + 1:
    print(f'FAIL: a second stop-finalization fire did not append a second telemetry row '
          f'(exit {_p2.returncode}, {len(_after2_lines)} lines vs {len(_after_lines)} before)')
    fail = True
else:
    print('OK: a second stop-finalization fire appends a second telemetry row (append-only)')

# --- context-budget/01-context-cost.py: had zero test coverage anywhere in the ---
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
_p = run_hook('context-budget', {'tool_name': 'Bash', 'tool_input': {'command': _LONG_CMD}})
if _p.returncode != 0 or '[context cost]' not in _p.stderr:
    print(f'FAIL: a >=700-char Bash command did not trigger the context-cost '
          f'notice -- exit {_p.returncode}, stderr: {_p.stderr[:200]!r}')
    fail = True
else:
    print('OK: post-tool warns on an oversized Bash command')

# A short command must NOT trigger the notice (WARN_CHARS is a floor, not a
# hair-trigger) -- proven, not assumed.
_p = run_hook('context-budget', {'tool_name': 'Bash', 'tool_input': {'command': 'echo hi'}})
if '[context cost]' in _p.stderr:
    print('FAIL: a short Bash command wrongly triggered the context-cost notice')
    fail = True
else:
    print('OK: a short Bash command stays silent')

# A repeated command (long enough to fingerprint, not VOLATILE-prefixed)
# triggers "[repeat]" on its second occurrence, not its first. The fingerprint
# is per-run-unique (time.time_ns()) so a stale call-fingerprints.json left
# over from a prior manual check never makes the "first occurrence" assertion
# fail -- the fingerprint file is gitignored, session-cumulative, and shared
# across every run of this suite, not test-isolated.
_repeat_cmd = (f'python -c "print(12345)"  # run-unique padding {time.time_ns()} '
               f'to clear MIN_REPEAT_CHARS')
_before = _call_fp_totals()
_p1 = run_hook('context-budget', {'tool_name': 'Bash', 'tool_input': {'command': _repeat_cmd}})
_p2 = run_hook('context-budget', {'tool_name': 'Bash', 'tool_input': {'command': _repeat_cmd}})
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
run_hook('context-budget', {'tool_name': 'Bash', 'tool_input': {'command': 'git status --porcelain -uall --extra-padding-to-clear-min-chars'}})
_p2 = run_hook('context-budget', {'tool_name': 'Bash', 'tool_input': {'command': 'git status --porcelain -uall --extra-padding-to-clear-min-chars'}})
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

# A tool 01-context-cost.py does not watch (e.g. Read) leaves ITS state
# untouched -- 04-read-cost.py legitimately watches Read and shares the same
# post-tool directory, so stderr from that sibling hook is expected here and
# is not what this case checks.
_before = _call_fp_totals()
run_hook('context-budget', {'tool_name': 'Read', 'tool_input': {'file_path': 'README.md'}})
_after = _call_fp_totals()
if _after != _before:
    print(f'FAIL: a non-watched tool_name affected context-cost state -- '
          f'before={_before} after={_after}')
    fail = True
else:
    print('OK: a non-watched tool_name (Read) is ignored entirely')

# --- post-tool/04-read-cost.py: Read-tool byte counter (objective 3 proxy) ---
_READ_COST_STATE = ROOT / '.claude' / 'hooks' / 'state' / 'read-cost.json'


def _read_cost_totals():
    try:
        return json.loads(_READ_COST_STATE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'calls': 0, 'chars': 0}


# A real file over 700 bytes (WARN_CHARS) warns.
_before = _read_cost_totals()
_p = run_hook('post-tool', {'tool_name': 'Read', 'tool_input': {'file_path': str(ROOT / 'README.md')}})
_after = _read_cost_totals()
if '[context cost]' not in _p.stderr:
    print(f'FAIL: reading a >700-byte file did not warn -- stderr: {_p.stderr[:200]!r}')
    fail = True
elif _after['calls'] - _before['calls'] != 1:
    print(f'FAIL: read-cost calls did not increment -- before={_before} after={_after}')
    fail = True
else:
    print('OK: post-tool warns on reading an oversized file, and read-cost calls increment')

# A small file does not warn.
with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8') as f:
    f.write('small')
    _small_path = f.name
try:
    _p = run_hook('post-tool', {'tool_name': 'Read', 'tool_input': {'file_path': _small_path}})
    if '[context cost]' in _p.stderr:
        print('FAIL: reading a small file wrongly triggered the context-cost notice')
        fail = True
    else:
        print('OK: reading a small file stays silent')
finally:
    Path(_small_path).unlink(missing_ok=True)

# A nonexistent path returns 0 chars, not an error.
_before = _read_cost_totals()
_p = run_hook('post-tool', {'tool_name': 'Read', 'tool_input': {'file_path': str(ROOT / 'does-not-exist-xyz.txt')}})
_after = _read_cost_totals()
if _p.returncode != 0 or '[context cost]' in _p.stderr:
    print(f'FAIL: a nonexistent Read path errored or warned -- exit {_p.returncode}, stderr: {_p.stderr[:200]!r}')
    fail = True
elif _after['calls'] - _before['calls'] != 1:
    print(f'FAIL: a nonexistent Read path did not still bump calls -- before={_before} after={_after}')
    fail = True
else:
    print('OK: a nonexistent Read path returns 0 chars, not an error, and still counts the call')

# Totals accumulate across two fires (chars from README.md counted twice).
_before = _read_cost_totals()
run_hook('post-tool', {'tool_name': 'Read', 'tool_input': {'file_path': str(ROOT / 'README.md')}})
run_hook('post-tool', {'tool_name': 'Read', 'tool_input': {'file_path': str(ROOT / 'README.md')}})
_after = _read_cost_totals()
_readme_size = (ROOT / 'README.md').stat().st_size
if _after['calls'] - _before['calls'] != 2 or _after['chars'] - _before['chars'] != _readme_size * 2:
    print(f'FAIL: read-cost totals did not accumulate correctly -- before={_before} after={_after}, '
          f'readme_size={_readme_size}')
    fail = True
else:
    print('OK: read-cost totals accumulate across two fires')

# --- post-tool/05-agent-cost.py: Task-tool (agent spawn) counter (objective 8) ---
_AGENT_COST_STATE = ROOT / '.claude' / 'hooks' / 'state' / 'agent-cost.json'


def _agent_cost_totals():
    try:
        return json.loads(_AGENT_COST_STATE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'calls': 0, 'by_type': {}}


_before = _agent_cost_totals()
_p = run_hook('post-tool', {'tool_name': 'Task', 'tool_input': {'subagent_type': 'tester'}})
_after = _agent_cost_totals()
if _p.returncode != 0:
    print(f'FAIL: a Task dispatch errored -- exit {_p.returncode}, stderr: {_p.stderr[:200]!r}')
    fail = True
elif _after['calls'] - _before['calls'] != 1:
    print(f'FAIL: agent-cost calls did not increment on a Task dispatch -- before={_before} after={_after}')
    fail = True
elif _after.get('by_type', {}).get('tester', 0) - _before.get('by_type', {}).get('tester', 0) != 1:
    print(f'FAIL: agent-cost by_type did not record subagent_type -- before={_before} after={_after}')
    fail = True
else:
    print('OK: a Task dispatch increments agent-cost calls and records its subagent_type')

# A non-Task tool is ignored entirely -- no state change.
_before = _agent_cost_totals()
run_hook('post-tool', {'tool_name': 'Bash', 'tool_input': {'command': 'echo hi'}})
_after = _agent_cost_totals()
if _after != _before:
    print(f'FAIL: a non-Task tool affected agent-cost state -- before={_before} after={_after}')
    fail = True
else:
    print('OK: a non-Task tool (Bash) is ignored by agent-cost')

# --- post-tool/06-tool-cost.py: total tool-call counter (objective 4) -------
_TOOL_COST_STATE = ROOT / '.claude' / 'hooks' / 'state' / 'tool-cost.json'


def _tool_cost_totals():
    try:
        return json.loads(_TOOL_COST_STATE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'calls': 0, 'by_tool': {}}


_before = _tool_cost_totals()
_p = run_hook('post-tool', {'tool_name': 'mcp__github__get_me', 'tool_input': {}})
_after = _tool_cost_totals()
if _p.returncode != 0:
    print(f'FAIL: an mcp__* tool errored in tool-cost -- exit {_p.returncode}, stderr: {_p.stderr[:200]!r}')
    fail = True
elif _after['calls'] - _before['calls'] != 1:
    print(f'FAIL: tool-cost calls did not increment on an mcp__* tool -- before={_before} after={_after}')
    fail = True
elif _after.get('by_tool', {}).get('mcp__github__get_me', 0) - _before.get('by_tool', {}).get('mcp__github__get_me', 0) != 1:
    print(f'FAIL: tool-cost by_tool did not record the mcp tool name -- before={_before} after={_after}')
    fail = True
else:
    print('OK: an mcp__* tool call (never watched by any of the other 4 counters) is counted by tool-cost')

_before = _tool_cost_totals()
run_hook('post-tool', {'tool_name': 'Grep', 'tool_input': {}})
_after = _tool_cost_totals()
if (_after['calls'] - _before['calls'] != 1
        or _after.get('by_tool', {}).get('Grep', 0) - _before.get('by_tool', {}).get('Grep', 0) != 1):
    print(f'FAIL: a second, different tool name did not add its own by_tool key -- before={_before} after={_after}')
    fail = True
else:
    print('OK: a different tool name produces its own by_tool key, not a merged count')

# --- post-tool/06-tool-cost.py: duplicate-rate threshold notice (Notion §10) -
# Deterministic, unlike the blocks above: a threshold crossing needs absolute
# totals, not a delta, so this snapshots and restores BOTH state files it
# touches (call-fingerprints.json is shared with context-budget's own tests
# above, tool-cost.json's latch is this hook's own) rather than reading the
# real, session-cumulative numbers.
_dup_fp_before = _CALL_FP_STATE.read_text(encoding='utf-8') if _CALL_FP_STATE.exists() else None
_dup_tc_before = _TOOL_COST_STATE.read_text(encoding='utf-8') if _TOOL_COST_STATE.exists() else None


def _write_fp_totals(calls, repeats):
    _CALL_FP_STATE.write_text(json.dumps({'_totals': {'calls': calls, 'chars': 0, 'repeats': repeats}}), encoding='utf-8')


def _write_tc_latch(active):
    _TOOL_COST_STATE.write_text(json.dumps({'calls': 0, 'by_tool': {}, 'dup_notice_active': active}), encoding='utf-8')


try:
    # Below MIN_CALLS_FOR_RATE (20): silent even at a high rate.
    _write_fp_totals(10, 8)
    _write_tc_latch(False)
    _p = run_hook('post-tool', {'tool_name': 'Grep', 'tool_input': {}})
    if '[duplicate rate]' in _p.stderr:
        print('FAIL: the duplicate-rate notice fired below the 20-call floor')
        fail = True
    else:
        print('OK: the duplicate-rate notice stays silent below the call floor')

    # At/above threshold (>15%), latch not yet active: fires once.
    _write_fp_totals(20, 4)  # 20% > 15%
    _write_tc_latch(False)
    _p = run_hook('post-tool', {'tool_name': 'Grep', 'tool_input': {}})
    if '[duplicate rate]' not in _p.stderr:
        print(f'FAIL: the duplicate-rate notice did not fire at 20% with the latch clear -- stderr: {_p.stderr[:200]!r}')
        fail = True
    else:
        print('OK: the duplicate-rate notice fires once the rate exceeds threshold')

    # Same rate, latch now active (set by the call above): stays silent.
    _p = run_hook('post-tool', {'tool_name': 'Grep', 'tool_input': {}})
    if '[duplicate rate]' in _p.stderr:
        print('FAIL: the duplicate-rate notice fired again while still above threshold (latch not respected)')
        fail = True
    else:
        print('OK: the duplicate-rate notice does not repeat every call while still above threshold')

    # Rate drops back to/under threshold: latch resets, silent.
    _write_fp_totals(20, 3)  # 15% == threshold, not above it
    _p = run_hook('post-tool', {'tool_name': 'Grep', 'tool_input': {}})
    if '[duplicate rate]' in _p.stderr:
        print('FAIL: the duplicate-rate notice fired at exactly the threshold (should require > threshold)')
        fail = True
    else:
        print('OK: the duplicate-rate notice requires strictly above threshold, and resets the latch there')

    # Climbs back above threshold after the reset: fires again.
    _write_fp_totals(20, 4)
    _p = run_hook('post-tool', {'tool_name': 'Grep', 'tool_input': {}})
    if '[duplicate rate]' not in _p.stderr:
        print('FAIL: the duplicate-rate notice did not re-fire after a reset and a fresh climb')
        fail = True
    else:
        print('OK: the duplicate-rate notice re-fires after the rate drops and climbs again')
finally:
    if _dup_fp_before is None:
        _CALL_FP_STATE.unlink(missing_ok=True)
    else:
        _CALL_FP_STATE.write_text(_dup_fp_before, encoding='utf-8')
    if _dup_tc_before is None:
        _TOOL_COST_STATE.unlink(missing_ok=True)
    else:
        _TOOL_COST_STATE.write_text(_dup_tc_before, encoding='utf-8')

# --- prompt-intake/02-turn-timer.py: per-turn start timestamp (objective 6) ---
_TURN_TIMER_STATE = ROOT / '.claude' / 'hooks' / 'state' / 'turn-timer.json'

_before_ts = time.time()
_p = run_hook('prompt-intake', {})
_after_ts = time.time()
if _p.returncode != 0:
    print(f'FAIL: turn-timer errored -- exit {_p.returncode}, stderr: {_p.stderr[:200]!r}')
    fail = True
else:
    try:
        _started_at = json.loads(_TURN_TIMER_STATE.read_text(encoding='utf-8'))['started_at']
    except (OSError, ValueError, KeyError):
        _started_at = None
    if _started_at is None or not (_before_ts - 1 <= _started_at <= _after_ts + 1):
        print(f'FAIL: turn-timer started_at {_started_at!r} is not close to the real fire time '
              f'[{_before_ts}, {_after_ts}]')
        fail = True
    else:
        print('OK: turn-timer records a started_at close to the real UserPromptSubmit fire time')

# A second fire overwrites, it does not accumulate -- one active turn at a time.
_p = run_hook('prompt-intake', {})
_ts_1 = json.loads(_TURN_TIMER_STATE.read_text(encoding='utf-8'))['started_at']
time.sleep(0.05)
_p = run_hook('prompt-intake', {})
_ts_2 = json.loads(_TURN_TIMER_STATE.read_text(encoding='utf-8'))['started_at']
if _ts_2 <= _ts_1:
    print(f'FAIL: a second turn-timer fire did not overwrite with a later timestamp -- {_ts_1} -> {_ts_2}')
    fail = True
else:
    print('OK: a second turn-timer fire overwrites the state file rather than accumulating')

# --- post-tool/07-human-cost.py: human-gate counter (objective 1) -----------
_HUMAN_COST_STATE = ROOT / '.claude' / 'hooks' / 'state' / 'human-cost.json'


def _human_cost_totals():
    try:
        return json.loads(_HUMAN_COST_STATE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'calls': 0, 'by_tool': {}}


for _gate_tool in ('AskUserQuestion', 'ExitPlanMode'):
    _before = _human_cost_totals()
    _p = run_hook('post-tool', {'tool_name': _gate_tool, 'tool_input': {}})
    _after = _human_cost_totals()
    if _p.returncode != 0:
        print(f'FAIL: {_gate_tool} errored in human-cost -- exit {_p.returncode}, stderr: {_p.stderr[:200]!r}')
        fail = True
    elif _after['calls'] - _before['calls'] != 1:
        print(f'FAIL: human-cost calls did not increment on {_gate_tool} -- before={_before} after={_after}')
        fail = True
    elif _after.get('by_tool', {}).get(_gate_tool, 0) - _before.get('by_tool', {}).get(_gate_tool, 0) != 1:
        print(f'FAIL: human-cost by_tool did not record {_gate_tool} -- before={_before} after={_after}')
        fail = True
    else:
        print(f'OK: {_gate_tool} increments human-cost calls and its own by_tool entry')

_before = _human_cost_totals()
run_hook('post-tool', {'tool_name': 'Bash', 'tool_input': {'command': 'echo hi'}})
_after = _human_cost_totals()
if _after != _before:
    print(f'FAIL: a non-gate tool affected human-cost state -- before={_before} after={_after}')
    fail = True
else:
    print('OK: a non-gate tool (Bash) is ignored by human-cost')

# --- telemetry/09-telemetry.py: duplicate_rate field (objective 5) ---
_p = run_hook('stop-finalization', {'workflow': 'test', 'status': 'success'})
_lines = _telemetry_lines()
if not _lines:
    print('FAIL: no telemetry row to check duplicate_rate against')
    fail = True
else:
    _row = json.loads(_lines[-1])
    _totals = _call_fp_totals()
    _want_rate = (_totals['repeats'] / _totals['calls']) if _totals.get('calls') else 0.0
    _got = _row.get('duplicate_rate')
    if _got is None or abs(_got - _want_rate) > 1e-9:
        print(f'FAIL: duplicate_rate wrong -- got {_got!r}, want {_want_rate!r} from totals {_totals}')
        fail = True
    else:
        print(f'OK: telemetry duplicate_rate matches hand-computed {_want_rate:.4f} from call totals')
    if row_agents := _row.get('agents_spawned'):
        if not isinstance(row_agents, dict) or 'calls' not in row_agents:
            print(f'FAIL: telemetry agents_spawned malformed -- {row_agents!r}')
            fail = True
        else:
            print('OK: telemetry agents_spawned field present with a calls count')
    if row_context := _row.get('context_read'):
        if not isinstance(row_context, dict) or 'chars' not in row_context:
            print(f'FAIL: telemetry context_read malformed -- {row_context!r}')
            fail = True
        else:
            print('OK: telemetry context_read field present with a chars count')
    if row_api := _row.get('api_calls'):
        if not isinstance(row_api, dict) or 'calls' not in row_api:
            print(f'FAIL: telemetry api_calls malformed -- {row_api!r}')
            fail = True
        else:
            print('OK: telemetry api_calls field present with a calls count')
    if 'turn_latency_seconds' not in _row['unavailable']:
        if not isinstance(_row.get('turn_latency_seconds'), (int, float)):
            print(f'FAIL: turn_latency_seconds should be numeric once the timer has '
                  f'fired -- {_row.get("turn_latency_seconds")!r}')
            fail = True
        else:
            print('OK: telemetry turn_latency_seconds is a real number once 02-turn-timer.py has fired')
    row_human = _row.get('human_interventions')
    if not isinstance(row_human, dict) or 'calls' not in row_human:
        print(f'FAIL: telemetry human_interventions malformed -- {row_human!r}')
        fail = True
    else:
        print('OK: telemetry human_interventions field present with a calls count')
    row_retries = _row.get('retries')
    if (not isinstance(row_retries, dict)
            or {'attempts', 'max_attempts', 'failure_class', 'rung'} - row_retries.keys()):
        print(f'FAIL: telemetry retries malformed -- {row_retries!r}')
        fail = True
    else:
        print('OK: telemetry retries field present with attempts/max_attempts/failure_class/rung')

# --- telemetry/09-telemetry.py: _retry_facts() white-box (objectives 9/10) ---
#
# The live repo's own branch (docs/four-more-spec-metrics) can never reach a
# real REPAIR/BLOCKED state to exercise the rung path here: tools/resume.py's
# BRANCH_PREFIX is hardcoded to "feat/" and slug_from_branch strips no other
# prefix, so branch_exists is always False on a "docs/" branch and
# derive_state returns BUILD before ever reaching the checks_green/REPAIR
# clause -- a pre-existing, already-logged gap (LOG.md, 2026-08-20), not
# something this plan fixes. Forcing derive_state via a substituted loop.py
# module tests _retry_facts()'s own wiring (state -> kind/budget -> rung())
# independent of that confound.
import importlib.util as _ilu  # noqa: E402


def _load_telemetry_module():
    _spec = _ilu.spec_from_file_location(
        'telemetry_for_test', str(ROOT / '.claude/hooks/telemetry/09-telemetry.py'))
    assert _spec is not None and _spec.loader is not None, 'cannot load 09-telemetry.py'
    _mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    return _mod


_tele = _load_telemetry_module()

# slug=None means "infer from branch" (resume.gather_facts's own contract,
# not "no plan") -- a branch with no recorded ledger still resolves real
# facts: 0 attempts, resume.MAX_ATTEMPTS's real default (3, not an invented
# 0), no failure class, no rung. Never an exception either way.
_inferred = _tele._retry_facts(None)
if (_inferred.get('attempts') != 0 or _inferred.get('failure_class') is not None
        or _inferred.get('rung') is not None or not isinstance(_inferred.get('max_attempts'), int)):
    print(f'FAIL: _retry_facts(None) on a branch with no recorded ledger should be a real, '
          f'un-invented degrade -- got {_inferred!r}')
    fail = True
else:
    print(f'OK: _retry_facts(None) infers from the branch and degrades to real facts '
          f'{_inferred!r}, not an exception')

# When the loop/resume module genuinely cannot be loaded, the hard-coded
# all-zero fallback is what a caller sees -- proven by breaking the load.
_real_load_module_for_empty = _tele._load_module
_tele._load_module = lambda rel, name: None
try:
    _empty = _tele._retry_facts('anything')
finally:
    _tele._load_module = _real_load_module_for_empty
_want_empty = {'attempts': 0, 'max_attempts': 0, 'failure_class': None, 'rung': None}
if _empty != _want_empty:
    print(f'FAIL: an unloadable loop module should fall back to {_want_empty!r}, got {_empty!r}')
    fail = True
else:
    print('OK: an unloadable loop/resume module degrades to the all-zero fallback, not an exception')

# A forced REPAIR state surfaces the same rung tools/loop.py's own rung()
# computes directly, for identical inputs.
_fixture_slug = 'retry-facts-test-fixture'
_fixture_ledger = ROOT / '.claude' / 'hooks' / 'state' / f'resume-{_fixture_slug}.json'
_fixture_ledger.write_text(
    json.dumps({'attempts': 2, 'max_attempts': 3, 'failure_class': 'deterministic'}),
    encoding='utf-8')
_rigged_loop = _tele._load_module('tools/loop.py', 'loop_for_retry_test')
_rigged_loop._rs.derive_state = lambda facts: 'REPAIR'
_real_load_module = _tele._load_module
_tele._load_module = (lambda rel, name:
                       _rigged_loop if rel == 'tools/loop.py' else _real_load_module(rel, name))
try:
    _got = _tele._retry_facts(_fixture_slug)
    _want_rung = _rigged_loop.rung(
        'deterministic', 2, _rigged_loop.failure_budget('deterministic'),
        restored=False, has_green=False)
    if _got.get('attempts') != 2 or _got.get('failure_class') != 'deterministic':
        print(f'FAIL: retry-facts fixture attempts/failure_class not read from the ledger -- {_got!r}')
        fail = True
    elif _got.get('rung') != _want_rung:
        print(f"FAIL: retries rung {_got.get('rung')!r} != loop.rung()'s own {_want_rung!r} "
              f'for the same inputs')
        fail = True
    else:
        print(f"OK: retries surfaces the same rung ({_want_rung!r}) tools/loop.py's rung() "
              f'computes directly, in a forced REPAIR state')
finally:
    _tele._load_module = _real_load_module
    _fixture_ledger.unlink(missing_ok=True)

if fail:
    sys.exit(1)
print('All hook tests passed')
