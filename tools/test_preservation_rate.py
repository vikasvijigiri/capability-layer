#!/usr/bin/env python3
"""Objective 17 (non-destructive integration) -- preservation rate.

"coexist with existing workflows; preserve working behavior; avoid
unnecessary restructuring." Reports what fraction of a target's OWN
pre-existing files survive an install byte-identical, extending
`tools/test_install.py`'s fixture machinery per `docs/specs/2026-08-21-
qualitative-objective-metrics.md`'s Cluster B design. Report only: exits 0
unconditionally, per that spec's "report before gate" constraint.

Scoped to the host's own files, not the layer's own payload paths: a file
`.claude/install.py` OWNS (anything under `TREES`/`FILES` -- e.g.
`.claude/workflow.md`) is *entitled* to be written or refreshed as part of
installing the layer -- overwriting IT is not a violation of "preserve
working behavior". Deliberately narrower than `inst.payload_files()`, which
also folds in SEED (`ruff.toml`, `mypy.ini`, `.github/workflows/checks.yml`,
`CODEOWNERS` -- create-if-absent, preserve-if-present) and `EXTRA_PAYLOAD`
(packaging-only; `plan()`/`apply()` never act on `README.md` at all,
confirmed by reading `install.py` this session) -- both of those ARE exactly
the host-preservation cases objective 17 is about, so a pre-existing
`ruff.toml`/`mypy.ini`/`CODEOWNERS` stays IN the ratio below rather than
being excluded from it, same for `CLAUDE.md` and
`.claude/project-checks.json` (the two `PRESERVE` entries).
`.claude/settings.json` (in `inst.MERGE`) is excluded and reported
separately -- it is neither preserved nor destroyed, it is intentionally
mutated by union, a third bucket `test_install.py` already covers in depth.

`--dry-run` writing nothing is already proven by `test_install.py`
("--dry-run wrote nothing at all" against a byte-for-byte snapshot) -- not
re-implemented here to avoid a near-duplicate of an existing check.

Run: python tools/test_preservation_rate.py
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# Duplicated from `tools/test_install.py` rather than imported -- that file
# is a top-level script whose import executes its entire suite as a side
# effect. Same accepted exception as this repo's own `_load()` duplication
# across 10 files (`docs/plans/2026-08-20-router-progress-consistency.md`'s
# Grounding), reused by `tools/test_idempotence.py` in this same cluster.
def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None, f"cannot load {rel}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def fresh_repo() -> Path:
    d = Path(tempfile.mkdtemp()) / "target"
    d.mkdir()
    for args in (["init", "--quiet"],
                 ["config", "user.email", "t@example.com"],
                 ["config", "user.name", "t"]):
        subprocess.run(["git", *args], cwd=str(d), capture_output=True, text=True)
    return d


def layer_owned_paths(inst, source: Path) -> set[str]:
    """TREES + FILES only -- content `install.py` copies/overwrites
    unconditionally. See module docstring for why this is narrower than
    `inst.payload_files()`."""
    out: set[str] = set()
    for tree in inst.TREES:
        out |= {p.as_posix() for p in inst.iter_tree(source, tree)}
    for name in inst.FILES:
        if (source / name).is_file():
            out.add(name)
    return out


def host_snapshot(root: Path, layer_paths: set[str]) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel.startswith(".git/") or rel in layer_paths or rel == ".claude/settings.json":
            continue
        out[rel] = p.read_bytes()
    return out


def preservation_ratio(before: dict[str, bytes],
                        after: dict[str, bytes]) -> tuple[float, list[str]]:
    """Fraction of `before` paths whose bytes are unchanged in `after`.

    Pure function so the seeded-violation proof below needs no filesystem
    mutation to set up or revert -- only synthetic dicts.
    """
    if not before:
        return 1.0, []
    mismatched = sorted(p for p, b in before.items() if after.get(p) != b)
    return (len(before) - len(mismatched)) / len(before), mismatched


def main() -> int:
    inst = load(".claude/install.py", "install_mod_preservation")
    layer_paths = layer_owned_paths(inst, inst.SOURCE)

    target = fresh_repo()
    (target / "src").mkdir()
    (target / "src" / "app.py").write_text("def main():\n    return 1\n",
                                            encoding="utf-8")
    (target / "README.md").write_text("# Their project\n\nTheir own readme.\n",
                                       encoding="utf-8")
    (target / "docs").mkdir()
    (target / "docs" / "notes.md").write_text("their own notes\n", encoding="utf-8")
    (target / "CLAUDE.md").write_text("# Their project\n\nTheir rules.\n",
                                       encoding="utf-8")
    (target / ".claude").mkdir()
    (target / ".claude" / "project-checks.json").write_text(
        json.dumps({"test": False, "_why": "no tests here yet"}), encoding="utf-8")
    (target / "ruff.toml").write_text("line-length = 79\n", encoding="utf-8")
    (target / "mypy.ini").write_text("[mypy]\nstrict = True\n", encoding="utf-8")

    before = host_snapshot(target, layer_paths)
    actions, _ = inst.plan(target)
    inst.apply(target, actions)
    after = host_snapshot(target, layer_paths)

    ratio, mismatched = preservation_ratio(before, after)
    print(f"objective 17 (preservation rate over the host's own files): "
          f"{len(before) - len(mismatched)}/{len(before)} preserved "
          f"({ratio:.4f})")
    for path in mismatched:
        print(f"  NOT preserved: {path}")
    for name in ("CLAUDE.md", ".claude/project-checks.json", "ruff.toml",
                  "mypy.ini"):
        print(f"  {'OK' if name not in mismatched else 'FAIL'}: {name} "
              f"({'PRESERVE' if name in inst.PRESERVE else 'SEED'})")

    shutil.rmtree(target.parent, ignore_errors=True)

    # Proof the ratio arithmetic itself can fail before it is trusted --
    # entirely synthetic, no filesystem mutation to revert (the spec's
    # "Testing the instruments themselves" rule).
    _seed_before = {"x.txt": b"AAA", "y.txt": b"BBB"}
    _seed_after = {"x.txt": b"AAA", "y.txt": b"CHANGED"}
    _seed_ratio, _seed_mismatched = preservation_ratio(_seed_before, _seed_after)
    assert abs(_seed_ratio - 0.5) < 1e-9 and _seed_mismatched == ["y.txt"], (
        f"preservation_ratio() failed to flag a seeded change: "
        f"ratio={_seed_ratio}, mismatched={_seed_mismatched}")
    print("  self-check: preservation_ratio() correctly flags a seeded byte "
          "change (y.txt, ratio=0.5) -- proven before trusting it against "
          "the real installer above")

    print("\n.claude/settings.json is excluded above: it is MERGED by "
          "design (a third bucket, neither preserved nor destroyed), "
          "already covered by tools/test_install.py's own merge assertions.")
    print("--dry-run writing nothing is already proven by "
          "tools/test_install.py; not re-asserted here.")
    print("\nReport only -- exits 0 regardless, per 'report before gate'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
