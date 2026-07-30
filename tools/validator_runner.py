#!/usr/bin/env python3
"""Simple validator runner that triggers hooks on failure.

Usage:
  python tools/validator_runner.py <validator-name> [--fail]
"""
import sys
import json
from pathlib import Path
import subprocess
import os

ROOT = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve().parents[0] / 'run_hook.py'


def run_validator(name, should_fail=False):
    print('Running validator', name)
    payload = {'validator': name}
    if should_fail:
        payload['failures'] = ['simulated failure']
        print('Validator failed; triggering on-validate-fail hooks')
        if RUNNER.exists():
            subprocess.run([sys.executable, str(RUNNER), 'on-validate-fail', json.dumps(payload)])
        return 2
    else:
        print('Validator passed')
        return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: validator_runner.py <validator-name> [--fail]')
        sys.exit(2)
    name = sys.argv[1]
    should_fail = '--fail' in sys.argv
    rc = run_validator(name, should_fail)
    sys.exit(rc)
