"""What "the checks pass" means for whatever project this is.

The auto-commit gates on a green suite. Until 2026-08-02 that meant one repo's
own Python suites, hardcoded, which was correct there and useless for the web app
it was about to be pointed at -- `npm test` would never have been found,
`run_suites()` would have returned "nothing to verify", and the one gate holding
up unattended committing would have passed vacuously on every commit.

There is no per-repo escape hatch in `detect_checks` any more either, for the same
reason: one was carried here for this repo's shape and it was the only branch in
the file that could not port. What a project's checks are is `MARKER_CHECKS` plus
`.claude/project-checks.json`, in every repo including this one.

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

**Nothing here is language-specific.** The three kinds -- test, typecheck, lint --
are the same question in every ecosystem, and which command answers them lives in
`MARKER_CHECKS`, a table. Node, Deno, Python, Rust, Go, Java, Kotlin, Ruby, PHP,
Elixir, .NET and plain `make` are rows in it; adding one more is a row, not a code
change. Node is the single special case, because its checks live in
`package.json` scripts rather than in a file's existence and the runner depends
on the lockfile.

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

# Two tiers, because cost differs by an order of magnitude and a gate nobody can
# afford to run is a gate that gets disabled.
#
#   FAST  runs at the end of every turn, gating the auto-commit. Seconds.
#   SLOW  runs once before delivery, gating push/PR. Minutes: a production build,
#         a vulnerability audit, a browser suite, a real server started and probed.
#
# Splitting them is the difference between "verified the source" and "verified the
# running system" -- the category of check this repo had none of until 2026-08-03.
# Running the slow tier per turn would add minutes to every reply; never running it
# is how an agent ships code that compiles, tests green, and does not boot.
FAST_KINDS = ("lint", "typecheck", "test")
SLOW_KINDS = ("build", "audit", "e2e", "smoke")
ALL_KINDS = FAST_KINDS + SLOW_KINDS

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


# Marker file -> the checks its presence implies. Language-agnostic by
# construction: supporting a new ecosystem is a row here, not a code change, and
# nothing above or below this table knows what language anything is written in.
#
# `{py}` expands to this interpreter, quoted. Double quotes and not shlex.quote:
# commands run under shell=True, which is cmd.exe on Windows, and cmd.exe does
# not treat '...' as quoting -- the interpreter path came through literally and
# every detected suite died with "The filename, directory name, or volume label
# syntax is incorrect."
#
# A marker only ever *adds* checks. Nothing here fails a project for lacking a
# toolchain, and `tool_missing` skips any command whose executable is absent, so
# a Rust repo on a machine without cargo is skipped-and-named, never blocked.
MARKER_CHECKS: dict[str, list[tuple[str, str]]] = {
    # --- Rust
    "Cargo.toml": [("test", "cargo test"), ("lint", "cargo clippy -- -D warnings"),
                   ("build", "cargo build --release"), ("audit", "cargo audit")],
    # --- Go
    "go.mod": [("test", "go test ./..."), ("lint", "go vet ./..."),
               ("build", "go build ./..."), ("audit", "govulncheck ./...")],
    # --- browser end-to-end. The config file is the marker; the runner is the
    # tool it configures. Nothing here assumes a language.
    "playwright.config.ts": [("e2e", "npx playwright test")],
    "playwright.config.js": [("e2e", "npx playwright test")],
    "cypress.config.ts": [("e2e", "npx cypress run")],
    "cypress.config.js": [("e2e", "npx cypress run")],
    # --- Java / Kotlin / JVM
    "pom.xml": [("test", "mvn -q -B test")],
    "build.gradle": [("test", "gradle --quiet test")],
    "build.gradle.kts": [("test", "gradle --quiet test")],
    # --- Ruby
    "Rakefile": [("test", "bundle exec rake test")],
    ".rubocop.yml": [("lint", "bundle exec rubocop")],
    # --- PHP
    "phpunit.xml": [("test", "vendor/bin/phpunit")],
    "phpunit.xml.dist": [("test", "vendor/bin/phpunit")],
    # --- Elixir
    "mix.exs": [("test", "mix test"), ("lint", "mix credo --strict")],
    # --- Deno
    "deno.json": [("test", "deno test -A"), ("lint", "deno lint"),
                  ("typecheck", "deno check .")],
    "deno.jsonc": [("test", "deno test -A"), ("lint", "deno lint")],
    # --- Python. Every Python tool is invoked as `{py} -m`, never bare.
    #
    # Two reasons, the second the serious one. A bare `pytest` needs a console
    # script on PATH: on 2026-08-03 a fresh repo reported `pytest` not installed
    # seconds after `python -m pytest` ran a passing suite, because the package
    # was importable but had no .exe. And a bare name can resolve to a DIFFERENT
    # interpreter's tool than the one running the checks -- linting with one
    # Python and testing with another, silently.
    "pyproject.toml": [("test", "{py} -m pytest -q"), ("audit", "{py} -m pip_audit")],
    "pytest.ini": [("test", "{py} -m pytest -q")],
    "ruff.toml": [("lint", "{py} -m ruff check .")],
    ".ruff.toml": [("lint", "{py} -m ruff check .")],
    "mypy.ini": [("typecheck", "{py} -m mypy")],
    ".mypy.ini": [("typecheck", "{py} -m mypy")],
}

# Markers matched by glob rather than exact name.
GLOB_MARKER_CHECKS: dict[str, list[tuple[str, str]]] = {
    "*.sln": [("test", "dotnet test")],
    "*.csproj": [("test", "dotnet test")],
}


def _node_checks(root: Path):
    """Node is the one ecosystem worth special-casing.

    Its checks live in `package.json` scripts rather than in the marker file's
    existence, and which runner invokes them depends on the lockfile. No table
    encodes that without becoming a program.
    """
    pkg = _package_json(root)
    scripts = pkg.get("scripts") or {} if isinstance(pkg, dict) else {}
    if not scripts:
        return []

    pm = _package_manager(root)
    runner = "npm run" if pm == "npm" else f"{pm} run"
    found = []
    if "test" in scripts:
        found.append(("test", f"{pm} test"))
    if "typecheck" in scripts:
        found.append(("typecheck", f"{runner} typecheck"))
    elif (root / "tsconfig.json").is_file():
        exec_prefix = {"npm": "npx", "pnpm": "pnpm exec",
                       "yarn": "yarn", "bun": "bunx"}[pm]
        found.append(("typecheck", f"{exec_prefix} tsc --noEmit"))
    if "lint" in scripts:
        found.append(("lint", f"{runner} lint"))
    # A project can lint, typecheck and test green and still fail to build --
    # a bundler config, a missing env var at build time, a bad import path that
    # only the production compiler rejects. This is the cheapest of the slow
    # checks and catches the most embarrassing failure.
    if "build" in scripts:
        found.append(("build", f"{runner} build"))
    if "e2e" in scripts:
        found.append(("e2e", f"{runner} e2e"))
    # `--audit-level=high` and not the default: a transitive `low` on a dev
    # dependency should not block delivery, and if it does, the gate gets turned
    # off within a week.
    if _package_manager(root) == "npm":
        found.append(("audit", "npm audit --audit-level=high"))
    return found


def _make_checks(root: Path):
    """`make test` / `make lint`, but only for targets that actually exist.

    A Makefile is the closest thing to a universal build interface, and also the
    easiest way to detect a target that was never written. Reading it is cheap.
    """
    makefile = next((root / n for n in ("Makefile", "makefile", "GNUmakefile")
                     if (root / n).is_file()), None)
    if makefile is None:
        return []
    try:
        text = makefile.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    import re as _re
    return [(kind, f"make {kind}") for kind in ("test", "lint", "typecheck")
            if _re.search(rf"(?m)^{kind}\s*:", text)]


def detect_checks(root=None):
    """[(kind, command)] this project appears to support, in run order.

    Detection is by marker file, never by guessing. A project with no markers
    detects nothing, and the caller decides what that means -- which for a change
    containing code is a refusal, not a pass.
    """
    root = Path(root) if root else REPO_ROOT
    found = []

    found.extend(_node_checks(root))

    for marker, checks in MARKER_CHECKS.items():
        if (root / marker).is_file():
            found.extend((kind, cmd.replace("{py}", f'"{sys.executable}"'))
                         for kind, cmd in checks)

    for pattern, checks in GLOB_MARKER_CHECKS.items():
        if any(root.glob(pattern)):
            found.extend(checks)

    # Small capability repositories often keep executable contract suites as
    # standalone `tools/test_*.py` scripts rather than a pytest project. Treat
    # each script as a test command so temporary fixtures and layer-only repos
    # still get real test evidence without inventing a package marker.
    tool_tests = sorted((root / "tools").glob("test_*.py"))
    found.extend(
        ("test", f'"{sys.executable}" "{p.relative_to(root)}"')
        for p in tool_tests
    )

    found.extend(_make_checks(root))

    # A marker can fire twice -- pyproject.toml and pytest.ini both mean pytest.
    seen, unique = set(), []
    for kind, cmd in found:
        if (kind, cmd) not in seen:
            seen.add((kind, cmd))
            unique.append((kind, cmd))
    return unique


def resolve_checks(root=None, kinds=FAST_KINDS):
    """(checks, disabled) after the config has had its say, for one tier.

    A configured command replaces every detected one of that kind -- naming
    `npm run test:fast` means that command *is* the test suite, not one more of
    them.
    """
    root = Path(root) if root else REPO_ROOT
    config = load_config(root)
    detected = detect_checks(root)
    checks: list[tuple[str, str]] = []
    disabled: list[str] = []

    for kind in kinds:
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


# Markers a failing run actually uses. Deliberately anchored to the start of a
# line rather than searched anywhere in it: this repo's suites print
# `OK: a failing suite is red`, and a substring match on "fail" would report a
# passing assertion as the reason a check failed.
FAILURE_MARKERS = ("FAIL", "ERROR", "Error:", "E   ", "AssertionError")


def failure_reason(proc) -> str:
    """The line that explains a non-zero exit, not merely the last one printed.

    This used to be `(proc.stdout or proc.stderr)[-1]`, so stdout won whenever it
    was non-empty. A suite that prints its checks to stdout and then dies during
    teardown -- traceback on stderr, `OK: ...` last on stdout -- was reported as

        FAIL: test `python tools/test_session_start_contract.py`: OK: bootstrap whitelist is exactly the six known docs

    which is a red build whose stated cause is a passing check. Diagnosing that
    on 2026-08-07 took a reproduction and a read of this function; the cause was
    a read-only git object defeating a temp-directory teardown, and none of that
    was visible in the report.

    Order: stderr (a traceback's last line IS the exception), then an explicit
    failure marker in stdout, then the last line as a fallback.
    """
    err = [ln for ln in (proc.stderr or "").strip().splitlines() if ln.strip()]
    out = [ln for ln in (proc.stdout or "").strip().splitlines() if ln.strip()]
    marker = next((ln for ln in reversed(out)
                   if ln.lstrip().startswith(FAILURE_MARKERS)), None)
    reason = (err[-1] if err else None) or marker or (out[-1] if out else None)
    return reason[:160] if reason else f"exit {proc.returncode}"


def run_checks(root=None, extra_env=None, kinds=FAST_KINDS):
    """(ok, detail, ran_test) for one tier. Never raises.

    `ran_test` is separate from `ok` on purpose. "Everything passed" and "there
    was nothing to run" are the same boolean and completely different facts, and
    conflating them is how an unattended commit gate quietly stops guarding.

    `kinds` selects the tier: FAST_KINDS for the per-turn commit gate, SLOW_KINDS
    or ALL_KINDS before delivery. The slow tier gets its own, longer timeout --
    a production build legitimately takes longer than a unit suite.
    """
    root = Path(root) if root else REPO_ROOT
    checks, disabled = resolve_checks(root, kinds)
    config = load_config(root)
    timeout = config.get("timeout", DEFAULT_TIMEOUT)
    if any(k in SLOW_KINDS for k, _ in checks):
        timeout = config.get("slow_timeout", max(timeout, 900))

    if not checks:
        note = f" ({', '.join(disabled)} disabled by config)" if disabled else ""
        return True, f"no checks detected{note}", False

    env = {**os.environ, "PYTHONIOENCODING": "utf-8", **(extra_env or {})}
    failed, ran, ran_test, skipped = [], 0, False, []

    for kind, command in checks:
        if tool_missing(command):
            # Skipped, and named in the detail. A silently absent check is the
            # thing this module exists to prevent. Name the *module* for
            # `python -m x`, not the interpreter -- "`python` not installed" is
            # both wrong and useless when the missing thing is `mypy`.
            parts = command.split()
            missing = (parts[2] if len(parts) > 2 and parts[1] == "-m"
                       else parts[0].strip('"'))
            skipped.append(f"{kind} (`{missing}` not installed)")
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
            failed.append(f"{kind} `{command}`: {failure_reason(proc)}")

    if failed:
        return False, "; ".join(failed), ran_test

    if not ran:
        note = f"; {', '.join(disabled)} disabled" if disabled else ""
        return True, f"nothing ran -- {', '.join(skipped) or 'no checks'}{note}", False

    kinds = ", ".join(sorted({k for k, c in checks if not tool_missing(c)}))
    note = f"; {', '.join(disabled)} disabled" if disabled else ""
    note += f"; skipped {', '.join(skipped)}" if skipped else ""
    return True, f"{ran} check(s) green ({kinds}){note}", ran_test
