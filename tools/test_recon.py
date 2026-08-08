#!/usr/bin/env python3
"""Tests for tools/recon.py -- reading a repository nobody has read.

Two properties.

**Disjointness.** `recon_units` is the licence for the recon fan-out: one agent
per unit, dispatched together. If two units shared a file, two agents would read
and report the same code, and the parallelism would be a lie. Asserted over the
partition, not by example.

**No silent zeroes.** Every finding here feeds a judgement downstream, so a
metric that is quietly wrong is worse than one that is missing. Both defects this
suite pins were real and were found by running the script against its own repo:
`test_*.py` files were not counted as tests at all (reporting a 21-suite
repository as having none), and `xit\\(` matched `exit(`, reporting 49 skipped
tests in a repository with zero.

Run: python tools/test_recon.py
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None, f"cannot load {rel}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


rc = load("tools/recon.py", "recon_mod")


# --- a synthetic repository we know the answers for --------------------------


def build(root: Path, files: dict[str, str]) -> None:
    for rel, body in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")


FIXTURE = {
    "package.json": '{"name":"demo"}\n',
    "src/index.js": "export const main = () => 1;\n",
    "src/auth.js": "// TODO: verify the signature\nexport const login = () => {};\n",
    "src/pay.js": "function charge() { throw new Error('x'); }\n",
    "api/server.py": "def app():\n    raise NotImplementedError\n",
    "api/util.py": "import sys\n\n\ndef go():\n    sys.exit(0)\n",
    "tests/test_auth.py": "def test_login():\n    assert True\n",
    "tests/api.spec.js": "it('works', () => {});\n",
    "docs/readme-extra.md": "# notes\n",
    "node_modules/junk/index.js": "TODO nobody should read this\n",
    "README.md": "# Demo\n",
}

repo = Path(tempfile.mkdtemp())
build(repo, FIXTURE)
for args in (["init", "--quiet"],
             ["config", "user.email", "t@example.com"],
             ["config", "user.name", "t"],
             ["add", "-A"],
             ["commit", "--quiet", "-m", "initial"]):
    subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)

facts = rc.gather(repo)


# --- noise is excluded -------------------------------------------------------

walked = {p.as_posix() for p in rc.walk(repo)}
check("node_modules is not walked",
      not any(p.startswith("node_modules/") for p in walked),
      str([p for p in walked if p.startswith("node_modules")]))
check("...so its TODO is not counted",
      facts["unfinished_counts"].get("todo") == 1,
      f"todo={facts['unfinished_counts'].get('todo')} -- src/auth.js has the only one")


# --- test topology: the metric that was silently zero -----------------------

check("a pytest-style `test_*.py` file counts as a test",
      any("test_auth" in e for e in facts["tests"]["examples"]),
      str(facts["tests"]["examples"]))
check("a jest-style `*.spec.js` file counts as a test",
      any("api.spec" in e for e in facts["tests"]["examples"]),
      str(facts["tests"]["examples"]))
check("both are found, and neither is counted as production code",
      facts["tests"]["test_files"] == 2, str(facts["tests"]))
check("...and the code count excludes them",
      facts["tests"]["code_files"] == 5,
      f"{facts['tests']['code_files']} -- expected index, auth, pay, server, util")
check("the ratio is a real number, not zero-by-accident",
      0 < facts["tests"]["ratio"] <= 1, str(facts["tests"]["ratio"]))


# --- the marker scan: no false positives ------------------------------------

check("`sys.exit(` is not a skipped test",
      "skipped-test" not in facts["unfinished_counts"],
      f"{facts['unfinished_counts']} -- an unanchored `xit\\(` matches `exit(`, "
      f"which once reported 49 skipped tests in a repo with none")
check("raise NotImplementedError is found",
      facts["unfinished_counts"].get("not-implemented") == 1,
      str(facts["unfinished_counts"]))
check("every located marker carries file:line",
      all(":" in hit["at"] and hit["at"].split(":")[-1].isdigit()
          for hit in facts["unfinished"]),
      str(facts["unfinished"][:3]))
check("...and quotes the line rather than characterising it",
      all(hit["text"].strip() for hit in facts["unfinished"]))

REAL_SKIPS = {
    "py-mark": "@pytest.mark.skip\ndef test_a(): pass\n",
    "py-if": "import unittest\n\n\nclass T(unittest.TestCase):\n"
             "    def test_b(self):\n        self.skipTest('x')\n",
    "js-xit": "xit('pending', () => {});\n",
    "js-skip": "it.skip('pending', () => {});\n",
    "go": "func TestX(t *testing.T) { t.Skip(\"later\") }\n",
}
for label, body in REAL_SKIPS.items():
    hits = [k for pattern, k in rc.UNFINISHED if pattern.search(body)]
    check(f"a real skipped test is still detected ({label})",
          "skipped-test" in hits, f"matched {hits}")

for benign in ("sys.exit(1)", "os._exit(0)", "return exit(code)",
               "process.exit(1)", "def skipped(rel):"):
    hits = [k for pattern, k in rc.UNFINISHED if pattern.search(benign)]
    check(f"benign code is not a marker: {benign!r}", not hits, f"matched {hits}")


# --- units are disjoint, which is what licenses the fan-out -----------------

units = rc.recon_units(rc.walk(repo))
named = [u for u in units if not u["unit"].startswith("<")]
check("units are produced", bool(named), str(units))
check("the largest unit is first, so a capped fan-out drops the least",
      [u["files"] for u in named] == sorted((u["files"] for u in named), reverse=True),
      str([(u["unit"], u["files"]) for u in named]))

# The property, over the real partition rather than the fixture's shape: every
# file belongs to exactly one unit.
all_files = [p for p in rc.walk(repo)
             if p.suffix in rc.CODE_SUFFIXES
             or p.suffix in {".md", ".json", ".yaml", ".yml", ".toml"}]
buckets: dict[str, set[str]] = {}
for rel in all_files:
    key = rel.parts[0] if len(rel.parts) > 1 else "<root>"
    buckets.setdefault(key, set()).add(rel.as_posix())
keys = sorted(buckets)
overlaps = [
    (a, b, sorted(buckets[a] & buckets[b]))
    for i, a in enumerate(keys) for b in keys[i + 1:]
    if buckets[a] & buckets[b]
]
check("no two units share a file", not overlaps, str(overlaps[:2]))
check("...and every eligible file lands in exactly one unit",
      sum(len(v) for v in buckets.values()) == len(all_files),
      f"{sum(len(v) for v in buckets.values())} placed vs {len(all_files)} eligible")

# A capped fan-out that prints nothing about the cap reads as complete coverage.
many = [Path(f"unit{n:03d}/file.py") for n in range(rc.MAX_UNITS + 6)]
capped = rc.recon_units(many, limit=rc.MAX_UNITS)
check("a fan-out over the ceiling names its remainder rather than truncating",
      any(u["unit"] == "<remainder>" for u in capped), str([u["unit"] for u in capped]))
check("...and the remainder says how many it stands for",
      next(u for u in capped if u["unit"] == "<remainder>")["files"] == 6,
      str(next(u for u in capped if u["unit"] == "<remainder>")))
check("a fan-out under the ceiling has no remainder entry",
      not any(u["unit"] == "<remainder>"
              for u in rc.recon_units(many[:3], limit=rc.MAX_UNITS)))

# A single `src/` is the commonest layout there is, and partitioning by top-level
# directory alone turned a 24-file service into one unit of 24 -- a "parallel"
# recon that is one agent reading everything.
MONOLITH = ([Path(f"src/api/mod{n}.py") for n in range(14)]
            + [Path(f"src/core/c{n}.py") for n in range(10)]
            + [Path("src/main.py"), Path("README.md")])
split = rc.recon_units(MONOLITH)
names = [u["unit"] for u in split]
check("an oversized top-level directory is split by its children",
      "src/api" in names and "src/core" in names, str(names))
check("...and files sitting directly in it stay together",
      "src/*" in names, str(names))
check("...and the unsplit unit is gone, so nothing is counted twice",
      "src" not in names, str(names))

# Disjointness must survive the split -- it is the entire licence to fan out.
placed = [f for u in split for f in u["sample"]]
check("splitting preserves disjointness",
      len(placed) == len(set(placed)), "a file reported by two agents")

check("a small directory is left whole rather than split for its own sake",
      "tests" in [u["unit"] for u in rc.recon_units(
          [Path("tests/a/one.py"), Path("tests/b/two.py"), Path("README.md")])],
      "splitting two files into two units costs a dispatch and returns nothing")


# --- stack detection and degradation ----------------------------------------

check("the manifest is detected", "package.json" in facts["stack"]["manifests"],
      str(facts["stack"]))
check("...and yields an install and test hint",
      facts["stack"]["install_hint"] and facts["stack"]["test_hint"],
      str(facts["stack"]))
check("git facts are read", facts["git"]["commit_count"] == "1", str(facts["git"]))
check("the layer is correctly reported absent",
      facts["layer"]["has_claude_dir"] is False and facts["layer"]["plans"] == [],
      str(facts["layer"]))

empty = Path(tempfile.mkdtemp())
bare = rc.gather(empty)
check("a directory that is not a git repo degrades rather than raising",
      bare["git"]["branch"] is None and bare["git"]["commit_count"] == "0",
      str(bare["git"]))
check("...and reports no languages rather than guessing",
      bare["stack"]["languages"] == [], str(bare["stack"]))
check("...and renders without error", isinstance(rc.render(bare), str))
check("an empty repo's test ratio is 0.0, not a division error",
      bare["tests"]["ratio"] == 0.0, str(bare["tests"]))


# --- determinism -------------------------------------------------------------

check("two passes over the same tree agree",
      rc.gather(repo)["unfinished_counts"] == facts["unfinished_counts"]
      and rc.gather(repo)["units"] == facts["units"])

# --- and it survives its own repository -------------------------------------

#
# Scoped to the repository that OWNS the layer. In a target the layer was
# installed into, `gather` deliberately excludes the layer's own files, so
# "20+ suites are counted" is false there and asserting it made a correctly
# installed target report five red checks. A suite that only passes at home is
# not a portable check -- found by installing into a synthetic repo and running
# the fast tier there on 2026-08-07.
live = rc.gather(ROOT)
IS_SOURCE_REPO = not rc.layer_owned(ROOT)

if IS_SOURCE_REPO:
    check("this repository's own suites are counted as tests",
          live["tests"]["test_files"] >= 15,
          f"{live['tests']['test_files']} -- tools/ has 20+ test_*.py files, and "
          f"reporting zero was the original defect")
else:
    print("NOTE: installed target -- the layer's own suites are excluded by "
          "design, so the >=15 assertion does not apply here")
    check("an installed target excludes the layer from its own measurement",
          live["layer_files_excluded"] > 0,
          "the manifest is missing, so this repo is measuring the layer as its own")
# Every skipped-test hit in this repository is a fixture in THIS file -- the
# literal `xit(`, `it.skip(` and `t.Skip(` strings above. Asserted by location
# rather than by count, because "no skipped tests here" stopped being true the
# moment this suite was written, and a count would have to be edited every time a
# fixture is added. What must stay true is that no *real* suite is skipping.
_live_skips = [h["at"] for h in live["unfinished"] if h["kind"] == "skipped-test"]
if IS_SOURCE_REPO:
    check("no skipped test outside this suite's own fixtures",
          all(h.startswith("tools/test_recon.py:") for h in _live_skips),
          f"real skips: "
          f"{[h for h in _live_skips if not h.startswith('tools/test_recon.py:')]}")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All recon tests passed")
