"""on-validate-fail -- a failing validator, not merely a failing command.

Two callers, and the filtering differs between them:

  PostToolUseFailure   fires for every failed tool call, so this script must
                       decide for itself whether the command was a validator.
                       Without that check every failed `ls` would be logged as
                       a validation failure and the log would mean nothing.
  a validator          calls `run_hook.py on-validate-fail` directly, per
                       CLAUDE.md. It already knows it failed, so a payload with
                       an explicit `failures` key skips the command check.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import command_of, load_payload, write_log  # noqa: E402

VALIDATOR_RE = re.compile(
    r"\b(pytest|unittest|jest|vitest|mocha|npm\s+(run\s+)?test|yarn\s+test|"
    r"pnpm\s+test|tox|nox|ruff|flake8|pylint|mypy|eslint|tsc|"
    r"npm\s+run\s+build|cargo\s+(test|clippy)|go\s+test|mvn\s+test|gradle\s+test)\b"
)


def main():
    payload = load_payload()
    if payload.get("is_interrupt"):
        return

    invoked_by_validator = "failures" in payload
    if not invoked_by_validator and not VALIDATOR_RE.search(command_of(payload)):
        return

    write_log("validate-fail.log", "VALIDATION-FAIL", payload)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
