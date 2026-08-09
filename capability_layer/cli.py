#!/usr/bin/env python3
"""`capability-layer <verb>` -- console entry point, replacing `python tools/x.py`.

This module dispatches; it never reimplements. Every verb loads the real
target module by path with `importlib.util.spec_from_file_location`, the
idiom already used throughout this repo (see the top of `tools/loop.py` and
`tools/run_checks.py`'s own `load_projectchecks()`), then calls its
`main(argv)`.

    capability-layer install   [--into DIR] [--dry-run]
    capability-layer upgrade   [--into DIR] [--dry-run]
    capability-layer uninstall [--into DIR] [--dry-run]
    capability-layer verify    [--tier fast|slow|all] [--require-test]
    capability-layer resume | loop | recon | schedule <plan> | identity
    capability-layer --version

Two different resolution rules, on purpose
-------------------------------------------
`install`, `upgrade` and `uninstall` always load `.claude/install.py` from the
**bundled payload** (`capability_layer/payload/`), never from the current directory. That script
computes its own `SOURCE` as `Path(__file__).resolve().parents[1]` -- the
tree it copies *from*. Loading a copy that a previous install already placed
in the target repo would make `SOURCE` the target itself, turning "install"
into "copy the target onto the target". `--into` still defaults to `.`, i.e.
the current working directory, never the payload -- that default lives in
`install.py`'s own argparse and is untouched here.

Every other verb (`verify`, `resume`, `loop`, `recon`, `schedule`,
`identity`) does the opposite: it prefers a copy **already installed** in the
current working tree (`./tools/<name>.py`), because those scripts compute
their own repository root the same way, and that root has to be the caller's
repo, not the installed package's payload. It falls back to the bundled
payload copy only when no local copy exists yet -- e.g. running `capability-layer
recon` against a repository the layer has never touched.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType

from capability_layer import __version__

PACKAGE_ROOT = Path(__file__).resolve().parent
PAYLOAD_ROOT = PACKAGE_ROOT / "payload"

# verb -> path of the module it dispatches to, relative to a repo root.
_TARGETS: dict[str, str] = {
    "install": ".claude/install.py",
    "upgrade": ".claude/install.py",
    "uninstall": ".claude/install.py",
    "verify": "tools/run_checks.py",
    "resume": "tools/resume.py",
    "loop": "tools/loop.py",
    "recon": "tools/recon.py",
    "schedule": "tools/parallel_groups.py",
    "identity": "tools/git_identity.py",
}

# Verbs whose module must always come from the bundled payload -- see the
# module docstring for why `install`/`upgrade` cannot use a local copy.
#
# `uninstall` is here for the sharper version of the same reason: its target
# still contains `.claude/install.py` right up until the moment it does not, and
# loading that copy would make `SOURCE` the target. It would also be deleting the
# module it is executing from.
_PAYLOAD_ONLY = {"install", "upgrade", "uninstall"}

# Verbs that reach `install.py`'s single `main()` through a flag rather than a
# subcommand. A map rather than a chain of `if verb ==` -- the second entry is
# where that chain would have started growing.
_MODE_FLAG = {"upgrade": "--upgrade", "uninstall": "--uninstall"}


def _resolve(verb: str, rel: str) -> Path:
    """Where the verb's target module actually lives on this machine."""
    bundled = PAYLOAD_ROOT / rel
    if verb in _PAYLOAD_ONLY:
        if not bundled.is_file():
            raise SystemExit(f"capability-layer: bundled payload is missing {rel}")
        return bundled

    local = Path.cwd() / rel
    if local.is_file():
        return local
    if bundled.is_file():
        return bundled
    raise SystemExit(
        f"capability-layer: cannot find {rel} in {Path.cwd()} or in the bundled payload"
    )


def _load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"capability-layer: cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _call_main(module: ModuleType, argv: list[str]) -> int:
    """Call the target's `main`, whichever shape it takes.

    Every target here accepts `main(argv)` except `tools/run_checks.py`,
    whose `main()` takes nothing and parses `sys.argv` itself. Rather than
    special-casing that one script -- which would be reimplementing part of
    it -- this inspects the signature and feeds it `sys.argv` when it wants
    that instead of an explicit list.
    """
    if len(inspect.signature(module.main).parameters) >= 1:
        return module.main(argv)
    saved_argv = sys.argv
    sys.argv = [getattr(module, "__file__", "capability-layer")] + argv
    try:
        return module.main()
    finally:
        sys.argv = saved_argv


def main(argv: list[str] | None = None) -> int:
    # `argv=[]` is treated the same as `argv=None`: both mean "read the
    # process's own sys.argv". A caller that wants an explicit empty
    # invocation gets the same usage message either way, so nothing is lost.
    args = list(argv) if argv else sys.argv[1:]

    if args and args[0] in ("--version", "-V"):
        print(__version__)
        return 0

    if not args or args[0] in ("-h", "--help"):
        verbs = ", ".join(sorted(_TARGETS))
        print(f"usage: capability-layer <verb> [args...]   (alias: cl)\n"
              f"       capability-layer --version\n"
              f"verbs: {verbs}")
        return 0 if args else 2

    verb, rest = args[0], args[1:]
    rel = _TARGETS.get(verb)
    if rel is None:
        print(f"capability-layer: unknown verb {verb!r}. Choose from: "
              f"{', '.join(sorted(_TARGETS))}", file=sys.stderr)
        return 2

    if verb in _MODE_FLAG:
        rest = [_MODE_FLAG[verb], *rest]

    module = _load(_resolve(verb, rel))
    return _call_main(module, rest)


if __name__ == "__main__":
    sys.exit(main())
