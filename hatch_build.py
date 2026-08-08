"""Stage the payload during the build, because a manual pre-step is not a build.

`pyproject.toml` force-includes `build/payload` — a tree produced by
`tools/stage_payload.py` from `.claude/install.py:payload_files()`. That tree is
gitignored, and it has to be: it is a filtered copy of files this repository
already tracks, and committing it would duplicate the whole layer inside itself.

Which meant the build only worked if you happened to run the stager first.
`python -m build` did, in this checkout, because the working tree still had
`build/payload` from an earlier run. `pip install git+https://…` clones into a
fresh directory that has never seen it, and hatchling stops with

    FileNotFoundError: Forced include not found: …/build/payload

So the package was uninstallable by the one command its README gave, and every
check passed: `tools/test_package.py` runs the stager and then builds, which is
the same order a human follows and the opposite of what pip does. A build step
nobody can forget is the only kind that holds — the instruction "run the stager
first" was a rule, and this is the mechanism that replaces it.

`initialize()` runs before hatchling collects files, so the tree exists by the
time force-include looks for it. Staging is stdlib-only, so it works inside pip's
isolated build environment where this project's own dependencies are absent.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """Build the payload tree that `force-include` expects."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        root = Path(self.root)
        stager_path = root / "tools" / "stage_payload.py"

        if not stager_path.is_file():
            # An sdist built without `tools/` would land here. Better to say which
            # file is missing than to let force-include report a missing directory
            # and leave the reader hunting for who was supposed to create it.
            raise FileNotFoundError(
                f"{stager_path} is missing, so the payload cannot be staged. "
                f"The wheel force-includes build/payload and nothing else "
                f"produces it."
            )

        spec = importlib.util.spec_from_file_location(
            "_cl_stage_payload", stager_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {stager_path}")
        stager = importlib.util.module_from_spec(spec)
        sys.modules["_cl_stage_payload"] = stager
        spec.loader.exec_module(stager)

        dest = root / "build" / "payload"
        files, warnings = stager.stage(root, dest)

        # A warning here means `payload_files()` named something that is not on
        # disk. That is a payload which will silently arrive incomplete in
        # somebody else's repository, so it fails the build instead.
        if warnings:
            raise FileNotFoundError(
                "the payload manifest names files that do not exist: "
                + ", ".join(warnings[:5])
                + (f" (and {len(warnings) - 5} more)" if len(warnings) > 5 else "")
            )

        forbidden = stager.audit(files)
        if forbidden:
            raise ValueError(
                "the staged payload contains files that must never ship: "
                + ", ".join(forbidden)
            )

        self.app.display_info(f"staged {len(files)} payload file(s)")
