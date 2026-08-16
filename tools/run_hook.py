#!/usr/bin/env python3
"""Run registered hooks for a given event.

Usage:
  python tools/run_hook.py <event> '<json-payload>'
  python tools/run_hook.py <event> --file payload.json

This executes the event's registered dispatcher when one exists. Otherwise it
executes scripts in `.claude/hooks/<event>/` in lexical order.
Scripts should be executable Python scripts. The runner sets `HOOK_PAYLOAD`
in the environment for each script.

Windows PowerShell note: PowerShell strips embedded double-quotes when
forwarding a single-quoted argument to a native executable, silently turning
JSON payloads into invalid ones. Either escape inner quotes with a backslash
('{\\"key\\":\\"value\\"}') or use `--file payload.json` to avoid the issue.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = ROOT / '.claude' / 'hooks'


def run_event(event, payload):
    event_dir = HOOKS_DIR / event
    if not event_dir.exists():
        print('No hooks for event', event)
        return 0
    dispatcher = event_dir / '00-dispatch.py'
    scripts = [dispatcher] if dispatcher.is_file() else sorted(
        [p for p in event_dir.iterdir() if p.is_file()]
    )
    rc = 0
    for s in scripts:
        print('Running hook', s.name)
        env = os.environ.copy()
        env['HOOK_PAYLOAD'] = payload
        if s.suffix == '.py':
            p = subprocess.run([sys.executable, str(s)], env=env)
        else:
            # nosec B602 -- a non-.py hook is a shell script that only a shell can
            # run, and `s` is a path this loop read out of `.claude/hooks/<event>/`.
            # Anyone who can drop a file there can already run code. Annotated
            # per-site so a new shell=True somewhere else still fails the lint.
            p = subprocess.run([str(s)], env=env, shell=True)  # noqa: S602
        if p.returncode != 0:
            print('Hook failed:', s.name, 'exit', p.returncode)
            rc = p.returncode
    return rc


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: run_hook.py <event> [json-payload] | --file payload.json')
        sys.exit(2)
    event = sys.argv[1]
    if len(sys.argv) > 3 and sys.argv[2] == '--file':
        payload = Path(sys.argv[3]).read_text(encoding='utf-8')
    else:
        payload = sys.argv[2] if len(sys.argv) > 2 else '{}'
    rc = run_event(event, payload)
    sys.exit(rc)
