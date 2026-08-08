#!/usr/bin/env python3
"""Validate that the comparative pilot is explicit without faking live results."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
fixture = ROOT / "docs" / "pilots" / "designer-no-slop" / "fixture.md"
report = ROOT / "docs" / "pilots" / "designer-no-slop" / "report.md"
fixture_text = fixture.read_text(encoding="utf-8")
report_text = report.read_text(encoding="utf-8")
required = [
    "without reading the `designer` or `no-slop` skill",
    "invented color",
    "visible focus state",
    "empty state",
    "swallowed dependency error",
    "claim of completion",
]
for item in required:
    if item not in fixture_text:
        raise SystemExit(f"FAIL: pilot fixture missing {item!r}")
for item in ("Status: fixture contract verified; live comparative execution pending.", "without-skill output", "with-designer output", "with-no-slop findings"):
    if item not in report_text:
        raise SystemExit(f"FAIL: pilot report missing {item!r}")
print("OK: designer/no-slop comparative pilot fixture and honest report contract validated")
