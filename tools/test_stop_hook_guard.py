#!/usr/bin/env python3
"""Prove the Stop-hook re-entry guard short-circuits checkpoint creation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "post-run" / "03-checkpoint.py"

spec = importlib.util.spec_from_file_location("checkpoint_hook", HOOK)
assert spec is not None and spec.loader is not None
module: Any = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

module.load_payload = lambda: {"stop_hook_active": True}

def should_not_run(*args, **kwargs):
    raise AssertionError("checkpoint performed work during Stop-hook re-entry")

module.git = should_not_run
module.main()
print("OK: checkpoint Stop-hook re-entry is guarded")
