#!/usr/bin/env python3
"""Simulate a workflow runner that invokes hooks at key points.

Usage:
  python tools/run_workflow.py <workflow-name> [--auto-approve] [--provision]
"""
import sys
import json
from pathlib import Path
import subprocess
import os

ROOT = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve().parents[0] / 'run_hook.py'
VALIDATOR = Path(__file__).resolve().parents[0] / 'validator_runner.py'


def run_workflow(name, auto_approve=False, provision=False):
    print('Starting workflow', name)
    payload = {'workflow': name}
    if RUNNER.exists():
        subprocess.run([sys.executable, str(RUNNER), 'pre-run', json.dumps(payload)])

    # Stage: Validate
    print('Stage: Validate')
    # Call a validator (simulate)
    val_rc = subprocess.run([sys.executable, str(VALIDATOR), 'smoke-test'])
    if val_rc.returncode != 0:
        print('Validation failed; aborting workflow')
        return 3

    # Stage: Provision
    if provision:
        if not auto_approve:
            # request approval
            print('Requesting human approval')
            if RUNNER.exists():
                subprocess.run([sys.executable, str(RUNNER), 'on-human-approval-request', json.dumps({'workflow':name})])
            print('No auto-approve; failing')
            return 4
        else:
            print('Provisioning...')
            # simulated provision step
            # if something fails, trigger on-deploy-failure
            prov_ok = True
            if not prov_ok:
                if RUNNER.exists():
                    subprocess.run([sys.executable, str(RUNNER), 'on-deploy-failure', json.dumps({'workflow':name,'status':'failed'})])
                return 5

    # Stage: Post-run
    if RUNNER.exists():
        subprocess.run([sys.executable, str(RUNNER), 'post-run', json.dumps({'workflow':name,'status':'success'})])
    print('Workflow completed')
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: run_workflow.py <workflow-name> [--auto-approve] [--provision]')
        sys.exit(2)
    name = sys.argv[1]
    auto = '--auto-approve' in sys.argv
    prov = '--provision' in sys.argv
    rc = run_workflow(name, auto_approve=auto, provision=prov)
    sys.exit(rc)
