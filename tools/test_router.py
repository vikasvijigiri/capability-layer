#!/usr/bin/env python3
"""Tests for capability routing: the hook's matching, and parser agreement.

`.claude/routing/capabilities.md` is parsed by three consumers -- the router
hook, `generate_registry.py` and `resolve_capability.py`. Nothing enforced that
they agreed about which `## ` headings count as capabilities, and they briefly
did not: the generator required a single whitespace-free token while the router
accepted any heading text, so a prose section carrying a `Keywords:` line would
have become a capability in one and not the other. That is the exact failure
consolidating nine index files into one was meant to make impossible, so it is
asserted here rather than left to review.

Run: python tools/test_router.py
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "pre-run" / "02-capability-router.py"
ROUTING = ROOT / ".claude" / "routing" / "capabilities.md"

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def run_hook(prompt: str) -> str:
    """Injected additionalContext for a prompt, or '' when the hook stays silent."""
    p = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"prompt": prompt}),
        capture_output=True, text=True, encoding="utf-8",
    )
    if p.returncode != 0:
        return f"<hook exited {p.returncode}: {p.stderr.strip()}>"
    out = p.stdout.strip()
    if not out:
        return ""
    return json.loads(out)["hookSpecificOutput"]["additionalContext"]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# --- 1. matching behaviour -------------------------------------------------

for prompt, expected in [
    ("the signup form validation is broken on mobile", "frontend"),
    ("add some unit tests", "testing"),           # plural tolerance
    ("this query is slow and the db is struggling", "backend"),
    ("deploy this to production", "deployment"),
]:
    ctx = run_hook(prompt)
    check(f"matches {expected!r} for {prompt!r}", f"**{expected}**" in ctx,
          f"got: {ctx[:120]!r}")

# Word-boundary matching: substrings must not fire. Regressed once already.
for prompt in ["that is amazing and rapid", "hello there"]:
    check(f"stays silent for {prompt!r}", run_hook(prompt) == "")

# --- 2. fail-open ----------------------------------------------------------

backup = ROUTING.read_text(encoding="utf-8")
try:
    ROUTING.unlink()
    check("fails open when routing file is missing", run_hook("the form is broken") == "")
finally:
    ROUTING.write_text(backup, encoding="utf-8")

# --- 3. the two parsers agree ---------------------------------------------

router = load_module(HOOK, "capability_router")
registry = load_module(ROOT / "tools" / "generate_registry.py", "generate_registry")

router_domains = [d for d, _ in router.load_capabilities()]
registry_domains = list(registry.capability_names())
check("router and registry agree on the capability list",
      router_domains == registry_domains,
      f"router={router_domains} registry={registry_domains}")

# A prose heading carrying a Keywords: line must be ignored by BOTH, not one.
try:
    ROUTING.write_text(
        backup + "\n\n## Deprecated domains\n\nKeywords: zzzsentinel\n",
        encoding="utf-8")
    registry.capability_names.cache_clear()
    r2 = [d for d, _ in router.load_capabilities()]
    g2 = list(registry.capability_names())
    check("multi-word heading ignored by router", "deprecated domains" not in r2)
    check("multi-word heading ignored by registry",
          not any(" " in d for d in g2))
    check("still agree after a prose section is added", r2 == g2,
          f"router={r2} registry={g2}")
finally:
    ROUTING.write_text(backup, encoding="utf-8")
    registry.capability_names.cache_clear()

# --- 4. every domain has keywords, and every prefix has skills -------------

for domain, words in router.load_capabilities():
    check(f"{domain} has keywords", bool(words))

skills = {p.name for p in (ROOT / ".claude" / "skills").iterdir() if p.is_dir()}
for domain in registry_domains:
    check(f"{domain} has at least one skill",
          any(s.startswith(f"{domain}-") for s in skills))

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All router tests passed")
