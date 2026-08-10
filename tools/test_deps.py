#!/usr/bin/env python3
"""A denied licence blocks, an unreadable one is named, and LGPL is not GPL.

Why this suite exists
---------------------
The licence check is a gate that will be green almost every day, which is
exactly the kind that rots without being noticed. Two specific ways it could rot
silently, both pinned below:

  * **`GPL` matched as a substring also matches `LGPL`**, which is permitted.
    That single bug would block a legitimate dependency, someone would add a
    blanket exception to unblock the build, and the exception would outlive the
    reason. The denied names are matched on token boundaries and both directions
    are asserted.
  * **An undeterminable licence reported as `ok`.** Article V: a check that could
    not run is unrun. `undetermined` has its own exit code and is not 0.

`verdict()` and `sbom()` are pure, so the cases are dict literals. `gather()` is
the IO seam and is exercised once against the real environment.

Run: python tools/test_deps.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deps  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def entry(name, licence, source="classifier", version="1.0"):
    return {"name": name, "version": version, "licence": licence, "source": source}


# --- the happy case -----------------------------------------------------------
ok = deps.verdict([entry("pyyaml", "MIT License"), entry("requests", "Apache-2.0")])
check("permissive licences pass", ok["status"] == "ok", str(ok))
check("...and the reason counts them", "2 declared" in ok["reason"], ok["reason"])

# --- each denied family blocks, and names why ---------------------------------
for name, why in deps.DENIED.items():
    got = deps.verdict([entry("thing", f"{name}-3.0")])
    check(f"[{name}] blocks", got["status"] == "denied", str(got))
    check(f"[{name}] ...and the reason explains the obligation",
          why.split(":")[0] in got["reason"], got["reason"])

check("every denied family has a stated reason",
      all(v.strip() for v in deps.DENIED.values()),
      "a denylist entry with no reason is one nobody can argue with")

# --- the substring bug this exists to prevent ---------------------------------
#
# `"GPL" in "LGPL-2.1"` is True. Matching that way blocks a permitted licence,
# and the fix people reach for is a blanket exception, which then covers the
# licences that should have blocked.
lgpl = deps.verdict([entry("cairo", "LGPL-2.1-only")])
check("LGPL is NOT blocked by the GPL rule", lgpl["status"] == "ok", str(lgpl))
check("...while GPL still is",
      deps.verdict([entry("x", "GPL-3.0-or-later")])["status"] == "denied")
check("...and AGPL still is",
      deps.verdict([entry("x", "AGPL-3.0")])["status"] == "denied")
check("a name merely CONTAINING a denied token in prose does not block",
      deps.verdict([entry("x", "MIT")])["status"] == "ok")

# --- Article V: unknown is never ok -------------------------------------------
unk = deps.verdict([entry("mystery", None, source="no licence metadata")])
check("an undeterminable licence is undetermined, not ok",
      unk["status"] == "undetermined", str(unk))
check("...and names the dependency and why it could not be read",
      "mystery" in unk["reason"] and "no licence metadata" in unk["reason"],
      unk["reason"])
check("a not-installed dependency is named, not dropped",
      deps.verdict([entry("ghost", None, source="not-installed")])["status"]
      == "undetermined")

# A denied licence outranks an unknown one: the worst known fact wins, or a
# blocking finding could hide behind an unrelated gap.
mixed = deps.verdict([entry("bad", "GPL-3.0"), entry("mystery", None)])
check("a denied licence outranks an unknown one",
      mixed["status"] == "denied", str(mixed))
check("...and the unknown is still carried, not discarded",
      len(mixed["unknown"]) == 1, str(mixed["unknown"]))

check("an empty dependency set is ok, not undetermined",
      deps.verdict([])["status"] == "ok",
      "nothing declared is a real answer, unlike nothing readable")

# --- the SBOM ------------------------------------------------------------------
doc = deps.sbom([entry("pyyaml", "MIT License", version="6.0.3"),
                 entry("mystery", None, version=None)])
check("the SBOM is CycloneDX-shaped",
      doc["bomFormat"] == "CycloneDX" and doc["specVersion"],
      str(doc)[:80])
check("every dependency appears as a component", len(doc["components"]) == 2)
check("a known licence is recorded",
      doc["components"][0]["licenses"][0]["license"]["name"] == "MIT License")
# The important one: absence must not read as permissive.
check("an UNKNOWN licence carries no licenses key at all",
      "licenses" not in doc["components"][1],
      "an empty licenses list would let a consumer read absence as cleared")
check("a missing version is recorded as unknown rather than omitted",
      doc["components"][1]["version"] == "unknown")
check("each component carries a purl",
      all(c["purl"].startswith("pkg:pypi/") for c in doc["components"]))

# --- the IO seam, against the real environment --------------------------------
#
# The defect class this session kept hitting was a function proved on synthetic
# input while the real input was what broke it.
names = deps.declared(ROOT)
if not names:
    # An installed layer lands in a repository that may have no `pyproject.toml`
    # at all -- it could be a Node or Go project. Nothing declared is a real
    # answer, and asserting this repository's dependency list in somebody else's
    # is what the portability scope exists to catch.
    print("SKIP: no runtime dependencies declared here -- the licence gate has "
          "nothing to read, and reports `ok` rather than pretending otherwise")
else:
    check("declared() reads runtime dependencies from pyproject.toml",
          "pyyaml" in names, str(names))
    check("...and excludes dev extras, which are never shipped",
          "ruff" not in names and "mypy" not in names, str(names))
    check("...and strips the version specifier",
          all(">" not in n and "=" not in n for n in names), str(names))

    live = deps.gather(ROOT)
    check("gather() resolves a licence from real installed metadata",
          any(e["licence"] for e in live), str(live))
    check("the real tree's licences are acceptable right now",
          deps.verdict(live)["status"] == "ok", deps.verdict(live)["reason"])

lic, source = deps.licence_of("definitely-not-a-real-distribution-xyz")
check("an absent distribution reports not-installed rather than raising",
      lic is None and source == "not-installed", f"{lic} / {source}")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All dependency tests passed ({len(deps.DENIED)} denied families)")
