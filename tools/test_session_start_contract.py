#!/usr/bin/env python3
"""Contract tests for the SessionStart session-context and state-report hooks."""

from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import claude_session_start_contract as contract  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def load_settings() -> dict:
    try:
        return contract.load_settings()
    except Exception as exc:
        raise AssertionError(f"could not load settings: {exc}") from exc


def extract_session_start_scripts(commands: list[str]) -> list[str]:
    return [cmd for cmd in commands if ".claude/hooks/session-init/" in cmd]


def check_session_start_hooks() -> None:
    settings = load_settings()
    commands = contract.session_start_commands(settings)
    scripts = extract_session_start_scripts(commands)
    expected = set(contract.EXPECTED_SESSION_START_SCRIPT_RELATIVES)
    actual = {next((rel for rel in expected if rel in cmd), cmd) for cmd in scripts}

    check("SessionStart exposes exactly two hook scripts",
          len(scripts) == 2,
          f"found {len(scripts)} SessionStart hook command(s)")
    missing = expected - actual
    extra = {cmd for cmd in actual if cmd not in expected}
    check("SessionStart commands include session-context hook",
          any("02-session-context.py" in cmd for cmd in scripts),
          ", ".join(scripts))
    check("SessionStart commands include state report hook",
          any("03-state-report.py" in cmd for cmd in scripts),
          ", ".join(scripts))
    check("SessionStart has no unexpected session-start hook scripts",
          not extra,
          f"unexpected hooks: {sorted(extra)}")
    check("SessionStart uses only the configured hooks",
          not missing,
          f"missing hooks: {sorted(missing)}")


def check_bootstrap_whitelist() -> None:
    files = contract.list_bootstrap_files()
    check("bootstrap whitelist is exactly the seven known docs",
          files == contract.EXPECTED_BOOTSTRAP_FILES,
          f"got {files}")


def check_bootstrap_runtime() -> None:
    # `ignore_cleanup_errors` is not tidiness -- without it this suite fails
    # intermittently with a PASSING-looking output. Git writes loose objects
    # read-only, Windows refuses to delete read-only files, and rmtree raises
    # from `__exit__` after every check has already printed OK. The result is a
    # non-zero exit whose last line says "OK", which is the worst possible
    # failure report. Reproduced 2026-08-07:
    #     rmtree: PermissionError: [WinError 5] Access is denied
    #             .git/objects/7e/5fdb212a...
    # A leaked temp directory is the OS's problem; a red suite nobody can
    # explain is ours.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        tmp = Path(tmpdir)
        env = os.environ.copy()
        try:
            subprocess.run(["git", "init"], cwd=tmp, env=env, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "config", "user.email", "test@example.com"],
                           cwd=tmp, env=env, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "config", "user.name", "Test User"],
                           cwd=tmp, env=env, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError as exc:
            check("git is installed for runtime bootstrap checks", False, str(exc))
            return

        root_files_before = {p.name for p in tmp.iterdir() if p.is_file()}
        root_dirs_before = {p.name for p in tmp.iterdir() if p.is_dir()}

        # `stdin=DEVNULL` is the whole reason this test terminates.
        #
        # `_hooklib.load_payload()` falls back to reading stdin, guarded only by
        # `isatty()` -- and an inherited pipe is not a TTY, so the guard passes
        # and the read blocks until EOF that never comes. Spawning the hook
        # without redirecting stdin hands it whatever this process inherited;
        # under `run_checks.py` (itself launched from a pipe) that is an open
        # handle, so the hook hung and the suite died on its timeout. The hook
        # runs in ~0.25s with stdin closed.
        #
        # `_hooklib` documents this exact trap for `run_hook.py`. The test had
        # the same bug. Diagnosed 2026-08-07 after first misreading it as
        # machine contention and uselessly raising the timeout to 120s.
        proc = subprocess.run([sys.executable, str(contract.BOOTSTRAP_SCRIPT)],
                              cwd=tmp, env=env, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=30)
        check("bootstrap hook exits cleanly in a fresh repo",
              proc.returncode == 0,
              proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}")
        expected_root_files = set(contract.EXPECTED_BOOTSTRAP_FILES)
        actual_root_files = {p.name for p in tmp.iterdir() if p.is_file()}
        actual_dirs = {p.name for p in tmp.iterdir() if p.is_dir()}

        created_files = actual_root_files - root_files_before
        created_dirs = actual_dirs - root_dirs_before

        check("bootstrap hook does not author root strategic docs",
              not (created_files & expected_root_files),
              f"created {sorted(created_files & expected_root_files)}")
        check("bootstrap hook does not author directories",
              not created_dirs,
              f"created dirs: {sorted(created_dirs)}")
        check("bootstrap hook reports missing scaffolding",
              "Missing strategic documents" in proc.stdout,
              proc.stdout.strip())


@contextlib.contextmanager
def _tmp_repo(files: dict[str, str]):
    """A throwaway git repo containing `files`, plus the hook's stdout after
    it runs there. Yields (proc, tmp) or (None, None) if git is unavailable.
    `ignore_cleanup_errors` for the same Windows read-only-git-object reason
    as check_bootstrap_runtime."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        tmp = Path(tmpdir)
        env = os.environ.copy()
        try:
            subprocess.run(["git", "init"], cwd=tmp, env=env, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            yield None, None
            return
        for name, body in files.items():
            (tmp / name).write_text(body, encoding="utf-8")
        proc = subprocess.run([sys.executable, str(contract.BOOTSTRAP_SCRIPT)],
                              cwd=tmp, env=env, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=30)
        yield proc, tmp


def _injected_context(proc: subprocess.CompletedProcess) -> str:
    return json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]


def check_head_region_contract() -> None:
    """The hook injects only the <!-- session-context --> region, and an
    over-ceiling head is cut at a newline, never mid-line."""
    task_md = (
        "# Tasks\n"
        "<!-- session-context:start -->\n"
        "| Task | Status | Updated |\n"
        "|---|---|---|\n"
        "| IN-REGION-ROW | Active | 2026-09-01 |\n"
        "<!-- session-context:end -->\n"
        "\nOUT-OF-REGION-ROW must never be injected\n"
    )
    with _tmp_repo({"TASK.md": task_md}) as (proc, _):
        if proc is None:
            check("git is installed for head-region checks", False)
            return
        ctx = _injected_context(proc)
        check("session-context region is injected", "IN-REGION-ROW" in ctx, ctx)
        check("text past session-context:end is NOT injected",
              "OUT-OF-REGION-ROW" not in ctx, ctx)

    # A marked region well over TASK_HEAD_CEILING (1200), built from
    # fixed-width lines so a mid-line cut leaves a final line that is not a
    # whole `LINEdddd`.
    body = "\n".join(f"LINE{n:04d}" for n in range(400))
    task_big = f"# Tasks\n<!-- session-context:start -->\n{body}\n<!-- session-context:end -->\n"
    with _tmp_repo({"TASK.md": task_big}) as (proc, _):
        if proc is None:
            return
        ctx = _injected_context(proc)
        check("an over-ceiling head is clipped with a pointer",
              "[... head over budget, Read TASK.md for the rest]" in ctx, ctx[:300])
        task_block = ctx.split("--- TASK.md (live ledger) ---\n", 1)[1].split("\n\n---", 1)[0]
        content = [ln for ln in task_block.splitlines()
                   if ln and not ln.startswith("[... head over budget")]
        bad = [ln for ln in content if not re.fullmatch(r"LINE\d{4}", ln)]
        check("over-ceiling head is cut at a line boundary, never mid-line",
              bool(content) and not bad,
              f"non-whole lines in clipped head: {bad[:5]}")


def check_workflow_state_tags() -> None:
    tags = contract.workflow_state_tags()
    required = {"docs-stale", "layer-unreviewed"}
    missing = required - tags
    check("workflow.md defines docs-stale and layer-unreviewed tags",
          not missing,
          f"missing tags: {sorted(missing)}")


def check_state_report_source() -> None:
    source = contract.state_report_source()
    check("state report uses workflow.md for state text",
          "WORKFLOW = REPO_ROOT / \".claude\" / \"workflow.md\"" in source,
          "expected WORKFLOW definition")
    check("state report defines TAG_RE",
          "TAG_RE" in source,
          "TAG_RE is missing")
    check("state report implements workflow_block()",
          "def workflow_block" in source,
          "workflow_block() is missing")


def main() -> int:
    check_session_start_hooks()
    check_bootstrap_whitelist()
    check_bootstrap_runtime()
    check_head_region_contract()
    check_workflow_state_tags()
    check_state_report_source()

    if failures:
        print(f"\n{len(failures)} required check(s) failed.")
        return 1
    print("\nAll session-start contract checks pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
