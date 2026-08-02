"""What "the checks pass" means for whatever project this is.

The auto-commit gates on a green suite. Until 2026-08-02 that meant literally
`tools/test_*.py`, hardcoded, which is correct for this repo and useless for the
web app it was about to be pointed at -- `npm test` would never have been found,
`run_suites()` would have returned "nothing to verify", and the one gate holding
up unattended committing would have passed vacuously on every commit.

Three ideas here, the first two taken from carlrannaberg/claudekit's
`test-project.ts` and `typecheck-project.ts`, which solve the same problem for
19 hooks:

  1. **Config overrides detection.** `config.command ?? packageManager.test`.
     Detection is a good default and a bad law; a project with a slow suite needs
     to name a fast one.
  2. **A check that does not apply is skipped, not failed.** No `tsconfig.json`
     means TypeScript is not this project's problem.
  3. **Silence is not a pass.** This is the part claudekit does not need and we
     do: it returns 0 when no test script exists, which is right for a linter
     that also has other hooks. Here that same silence would be the entire
     safety story evaporating. So `run_checks` reports whether a *test* actually
     ran, and the caller refuses to commit code on the strength of nothing.

Config lives in `.claude/project-checks.json`:

    {
      "test":      "npm run test:fast",   // a command, or false to disable
      "typecheck": "tsc --noEmit",
      "lint":      false,
      "timeout":   300
    }

Every value is optional. `false` disables a check and is a decision someone
typed; an absent key means "detect it".
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
REPO_ROOT = HOOKS_DIR.parents[1]

CONFIG_NAME = ".claude/project-checks.json"
DEFAULT_TIMEOUT = 300

# Extensions that mean "this turn changed behaviour", so a green test run is
# load-bearing rather than a formality. Prose, config and lockfiles are excluded
# deliberately: gating a README edit on a test suite is how a gate becomes noise.
CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".rb",
    ".java", ".kt", ".cs", ".php", ".swift", ".c", ".h", ".cc", ".cpp", ".hpp",
    ".scala", ".ex", ".exs", ".vue", ".svelte", ".sql",
}


def changed_includes_code(paths):
    """True when the change touches something a test suite could have caught."""
    return any(Path(p).suffix.lower() in CODE_EXTENSIONS for p in paths)


def load_config(root=None):
    root = Path(root) if root else REPO_ROOT
    try:
        with open(root / CONFIG_NAME, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _package_manager(root: Path) -> str:
    """Whichever lockfile is present decides. npm is the fallback, not a guess."""
    for lock, manager in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"),
                          ("bun.lockb", "bun"), ("package-lock.json", "npm")):
        if (root / lock).is_file():
            return manager
    return "npm"


def _package_json(root: Path) -> dict:
    try:
        with open(root / "package.json", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def detect_checks(root=None):
    """[(kind, command)] this project appears to support, in run order.

    Detection is by marker file, never by guessing: a `test` script in
    package.json, a `tsconfig.json` next to a typescript dep, a `pyproject.toml`.
    A project with none of them detects nothing, and the caller decides what that
    means.
    """
    root = Path(root) if root else REPO_ROOT
    found = []

    pkg = _package_json(root)
    scripts = pkg.get("scripts") or {} if isinstance(pkg, dict) else {}
    if scripts:
        pm = _package_manager(root)
        runner = f"{pm} run" if pm != "npm" else "npm run"
        if "test" in scripts:
            found.append(("test", f"{pm} test" if pm != "yarn" else "yarn test"))
        if "typecheck" in scripts:
            found.append(("typecheck", f"{runner} typecheck"))
        elif (root / "tsconfig.json").is_file():
            exec_prefix = {"npm": "npx", "pnpm": "pnpm exec",
                           "yarn": "yarn", "bun": "bunx"}[pm]
            found.append(("typecheck", f"{exec_prefix} tsc --noEmit"))
        if "lint" in scripts:
            found.append(("lint", f"{runner} lint"))

    # Python. `tools/test_*.py` is this repo's own shape and stays supported;
    # pytest is what an application would use.
    if (root / "pyproject.toml").is_file() or (root / "pytest.ini").is_file() \
            or (root / "tests").is_dir():
        found.append(("test", "pytest -q"))
    py_suites = sorted((root / "tools").glob("test_*.py")) if (root / "tools").is_dir() else []
    for suite in py_suites:
        # Double quotes, not shlex.quote: these run under shell=True, which is
        # cmd.exe on Windows, and cmd.exe does not treat '...' as quoting -- the
        # interpreter path came through literally and every suite failed with
        # "The filename, directory name, or volume label syntax is incorrect."
        # Double quotes are understood by both cmd.exe and POSIX shells.
        found.append(("test", f'"{sys.executable}" tools/{suite.name}'))
    if (root / "ruff.toml").is_file() or (root / ".ruff.toml").is_file():
        found.append(("lint", "ruff check ."))

    if (root / "Cargo.toml").is_file():
        found += [("test", "cargo test"), ("lint", "cargo clippy -- -D warnings")]
    if (root / "go.mod").is_file():
        found += [("test", "go test ./..."), ("lint", "go vet ./...")]

    return found


def resolve_checks(root=None):
    """(checks, disabled) after the config has had its say.

    A configured command replaces every detected one of that kind -- naming
    `npm run test:fast` means that command *is* the test suite, not one more of
    them.
    """
    root = Path(root) if root else REPO_ROOT
    config = load_config(root)
    detected = detect_checks(root)
    checks, disabled = [], []

    for kind in ("test", "typecheck", "lint"):
        override = config.get(kind)
        if override is False:
            disabled.append(kind)
            continue
        # A list, because one kind often needs several commands -- `ruff check`
        # and a JSON-validity pass are both "lint" and neither is the other's
        # subcommand. Chaining them into one shell string hides which failed.
        if isinstance(override, list):
            checks.extend((kind, c.strip()) for c in override
                          if isinstance(c, str) and c.strip())
            continue
        if isinstance(override, str) and override.strip():
            checks.append((kind, override.strip()))
            continue
        checks.extend((k, c) for k, c in detected if k == kind)

    return checks, disabled


def tool_missing(command: str) -> bool:
    """True when the command's executable is not on PATH.

    A configured check naming an uninstalled tool must skip, never fail. Failing
    would refuse every commit until someone installed it -- and the person who
    hits that is usually a new clone, not the person who wrote the config.
    claudekit calls this `checkToolAvailable` and skips for the same reason.

    `python -m x` is resolved by importability, not PATH, so it is checked that
    way; anything else is a plain executable lookup on the first token.
    """
    import shutil
    parts = command.split()
    if not parts:
        return True
    if parts[0].strip('"').endswith(("python", "python.exe", "python3")) \
            and len(parts) > 2 and parts[1] == "-m":
        return importlib.util.find_spec(parts[2].split(".")[0]) is None
    exe = parts[0].strip('"')
    return shutil.which(exe) is None and not Path(exe).exists()


def run_checks(root=None, extra_env=None):
    """(ok, detail, ran_test). Never raises.

    `ran_test` is separate from `ok` on purpose. "Everything passed" and "there
    was nothing to run" are the same boolean and completely different facts, and
    conflating them is how an unattended commit gate quietly stops guarding.
    """
    root = Path(root) if root else REPO_ROOT
    checks, disabled = resolve_checks(root)
    timeout = load_config(root).get("timeout", DEFAULT_TIMEOUT)

    if not checks:
        note = f" ({', '.join(disabled)} disabled by config)" if disabled else ""
        return True, f"no checks detected{note}", False

    env = {**os.environ, "PYTHONIOENCODING": "utf-8", **(extra_env or {})}
    failed, ran, ran_test, skipped = [], 0, False, []

    for kind, command in checks:
        if tool_missing(command):
            # Skipped, and named in the detail. A silently absent check is the
            # thing this module exists to prevent.
            skipped.append(f"{kind} (`{command.split()[0]}` not installed)")
            continue
        try:
            # nosec B602 -- shell=True is required and the input is not hostile.
            # `command` comes from detection or from .claude/project-checks.json,
            # both inside the repo; anyone who can write that file can already
            # write the hooks themselves. Commands are strings like `npm test`,
            # which need a shell to resolve. Annotated per-site rather than
            # silencing B602 repo-wide, so a NEW shell=True elsewhere still fails.
            proc = subprocess.run(  # noqa: S602
                command, cwd=str(root), shell=True, capture_output=True,
                text=True, encoding="utf-8", errors="replace",
                timeout=timeout, env=env,
            )
        except subprocess.TimeoutExpired:
            # claudekit's call, and it is right: a slow suite is a configuration
            # problem, not a broken change. Blocking on it trains people to
            # disable the gate entirely.
            failed.append(f"{kind} timed out after {timeout}s -- set a faster "
                          f"command in {CONFIG_NAME}")
            continue
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{kind} could not run ({exc})")
            continue

        ran += 1
        if kind == "test":
            ran_test = True
        if proc.returncode != 0:
            tail = (proc.stdout or proc.stderr or "").strip().splitlines()
            failed.append(f"{kind} `{command}`: "
                          f"{tail[-1][:160] if tail else 'exit ' + str(proc.returncode)}")

    if failed:
        return False, "; ".join(failed), ran_test

    if not ran:
        note = f"; {', '.join(disabled)} disabled" if disabled else ""
        return True, f"nothing ran -- {', '.join(skipped) or 'no checks'}{note}", False

    kinds = ", ".join(sorted({k for k, c in checks if not tool_missing(c)}))
    note = f"; {', '.join(disabled)} disabled" if disabled else ""
    note += f"; skipped {', '.join(skipped)}" if skipped else ""
    return True, f"{ran} check(s) green ({kinds}){note}", ran_test
