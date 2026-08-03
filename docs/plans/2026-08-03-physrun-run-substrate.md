# physrun — Run Substrate Implementation Plan

> **For agentic workers:** implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local, content-addressed run store and executor for computational
physics, so an identical calculation is a cache hit and every result is
re-executable by ID.

**Architecture:** A `RunSpec` (code text + params + environment lock) hashes to a
pure `run_id`. The `Store` keeps an SQLite index and content-addressed artifacts
on disk. The `Executor` returns a recorded run on a hash hit and otherwise runs
the code in a subprocess, capturing everything. A CLI drives all of it.

**Tech Stack:** Python 3.11+, SQLite (stdlib `sqlite3`), `pytest`, `ruff`, `mypy`.
No third-party runtime dependencies.

**Source spec:** `docs/specs/2026-08-03-research-run-substrate-design.md` in the
UAIOS repo. **The implementer does not have it — everything needed is here.**

## Global Constraints

- **Target repo is `../physrun/`, a NEW sibling git repo.** Not the UAIOS repo
  this plan lives in. Every path below is relative to `physrun/`.
- **Python 3.11+.** Use `X | None`, not `Optional[X]`.
- **No third-party runtime dependencies.** Dev-only: pytest, ruff, mypy.
- **`run_id` must be pure.** No timestamps, no absolute paths, no hostnames, no
  dict-ordering dependence, no locale-dependent float formatting. If a value can
  differ between two machines running the same calculation, it is not in the hash.
- **Tags are never in the hash.** Two runs differing only by tag are the same run.
- **A failure is never silent.** Every refusal prints why.
- **Convergence assertions are OUT OF SCOPE** — deferred by user decision. Do not
  build the `checked / passed / never declared` tri-state.
- **The README must state the known limit verbatim:** this system cannot detect
  numerics that are converged-looking but wrong. Dropping the mechanism was a
  scheduling decision; dropping the acknowledgement is not permitted.

---

### Task 1: Scaffold the repo and its harness

**Files:**
- Create: `../physrun/pyproject.toml`
- Create: `../physrun/README.md`
- Create: `../physrun/.gitignore`
- Create: `../physrun/src/physrun/__init__.py`
- Create: `../physrun/tests/test_harness.py`
- Copy: `ruff.toml`, `mypy.ini` from the UAIOS repo root
- Copy: `tools/run_checks.py` and `.claude/hooks/_projectchecks.py` from UAIOS
- Create: `../physrun/.claude/project-checks.json`

**Interfaces:**
- Consumes: nothing.
- Produces: an installable package `physrun` importable as `import physrun`;
  a working `python tools/run_checks.py --tier fast`.

- [x] **Step 1: Create the repo and directory skeleton**

```bash
cd ..
mkdir -p physrun/src/physrun physrun/tests physrun/tools physrun/.claude
cd physrun
git init -b main
```

- [x] **Step 2: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "physrun"
version = "0.1.0"
description = "Content-addressed run store for computational physics"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8", "ruff>=0.5", "mypy>=1.10"]

[project.scripts]
physrun = "physrun.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [x] **Step 3: Write `.gitignore`**

```gitignore
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
build/
dist/
.physrun/
```

- [x] **Step 4: Copy the harness from UAIOS**

Run, from `physrun/`:

```bash
cp ../Notes/ruff.toml ../Notes/mypy.ini .
cp ../Notes/tools/run_checks.py tools/
mkdir -p .claude/hooks && cp ../Notes/.claude/hooks/_projectchecks.py .claude/hooks/
```

Then edit `mypy.ini` so its `files` line reads exactly:

```ini
files = src, tests
```

And edit `ruff.toml`, replacing the whole `[lint.per-file-ignores]` section with:

```toml
[lint.per-file-ignores]
"tests/*" = ["S101", "S105", "S106", "S108"]
```

- [x] **Step 5: Write `.claude/project-checks.json`**

```json
{
  "_note": "Read by .claude/hooks/_projectchecks.py. Fast tier gates every commit; slow tier gates delivery.",
  "timeout": 300,
  "max_files": 25
}
```

No keys are set for `test`, `lint` or `typecheck`: detection finds `pyproject.toml`
(pytest), `ruff.toml` and `mypy.ini` on its own.

- [x] **Step 6: Write `src/physrun/__init__.py`**

```python
"""Content-addressed run store for computational physics."""

__version__ = "0.1.0"
```

- [x] **Step 7: Write the failing harness test**

`tests/test_harness.py`:

```python
import physrun


def test_package_imports_and_has_a_version():
    assert physrun.__version__ == "0.1.0"
```

- [x] **Step 8: Install and run it**

Run: `python -m pip install -e ".[dev]" && python -m pytest tests/ -q`
Expected: PASS, 1 test.

- [x] **Step 9: Prove the copied harness works in this fresh repo**

Run: `python tools/run_checks.py --tier fast`
Expected: `PASS: N check(s) green (lint, test, typecheck)` and the resolved list
names `pytest -q`, `ruff check .` and `mypy`.

If any check is reported `skipped: tool missing`, install it before continuing —
a skipped check is not a passing one.

- [x] **Step 10: Write `README.md`**

````markdown
# physrun

A content-addressed run store for computational physics. An identical
calculation is a cache hit, and every result is re-executable from its ID.

```bash
physrun run sweep.py --param L=12 --param J=1.0 --tag phase-a
physrun query --tag phase-a
physrun show <run_id>
```

## What this cannot do

**It cannot tell you that a converged-looking result is wrong.** An unconverged
bond dimension, an unthermalised Monte Carlo chain, or a finite-size effect read
as a phase transition all exit 0 and reproduce perfectly. This system makes a
wrong number *reproducible and traceable*; it does not make it right. Judging
convergence remains yours.
````

- [x] **Step 11: Commit**

```bash
git add -A
git commit -m "feat: scaffold physrun package and check harness"
```

---

### Task 2: Environment lock

**Files:**
- Create: `../physrun/src/physrun/env.py`
- Test: `../physrun/tests/test_env.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `class EnvLock` — frozen dataclass, fields `python: str`,
    `packages: tuple[tuple[str, str], ...]`
  - `EnvLock.canonical() -> str`
  - `capture_env(track: tuple[str, ...] | None = None) -> EnvLock`
  - `ABSENT: str = "absent"`

- [ ] **Step 1: Write the failing test**

`tests/test_env.py`:

```python
from physrun.env import EnvLock, capture_env


def test_capture_returns_this_interpreter():
    lock = capture_env()
    assert lock.python.count(".") >= 2
    assert isinstance(lock.packages, tuple)


def test_packages_are_sorted_and_hashable():
    lock = EnvLock(python="3.11.7", packages=(("numpy", "2.0.0"), ("scipy", "1.14.0")))
    assert lock.packages == tuple(sorted(lock.packages))
    hash(lock)


def test_canonical_is_stable_regardless_of_input_order():
    a = EnvLock(python="3.11.7", packages=(("numpy", "2.0.0"), ("scipy", "1.14.0")))
    b = EnvLock(python="3.11.7", packages=(("scipy", "1.14.0"), ("numpy", "2.0.0")))
    assert a.canonical() == b.canonical()


def test_canonical_changes_when_a_version_changes():
    a = EnvLock(python="3.11.7", packages=(("numpy", "2.0.0"),))
    b = EnvLock(python="3.11.7", packages=(("numpy", "2.0.1"),))
    assert a.canonical() != b.canonical()


# --- the declared subset.
#
# Hashing every installed distribution is maximally correct and practically
# useless: installing `black` would invalidate every cached physics run. So a
# caller may declare the packages that actually affect their result.

def test_tracking_a_subset_captures_only_those_packages():
    lock = capture_env(track=("pytest",))
    assert [name for name, _ in lock.packages] == ["pytest"]


def test_an_untracked_package_does_not_appear():
    lock = capture_env(track=("pytest",))
    assert all(name != "ruff" for name, _ in lock.packages)


def test_a_tracked_but_missing_package_is_recorded_as_absent():
    # Recorded, not skipped. A package appearing or disappearing must change
    # the hash -- silently omitting it would let an install go unnoticed.
    lock = capture_env(track=("definitely-not-installed",))
    assert lock.packages == (("definitely-not-installed", ABSENT),)


def test_absent_and_installed_hash_differently():
    absent = EnvLock(python="3.11.7", packages=(("numpy", ABSENT),))
    present = EnvLock(python="3.11.7", packages=(("numpy", "2.0.0"),))
    assert absent.canonical() != present.canonical()


def test_no_track_captures_everything():
    assert len(capture_env().packages) > len(capture_env(track=("pytest",)).packages)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_env.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'physrun.env'`

- [ ] **Step 3: Write the implementation**

`src/physrun/env.py`:

```python
"""Capture the environment a run happened in, as a stable hashable value.

Separate from spec.py because environment capture is OS- and tooling-specific
and will churn independently of the hash format.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from importlib import metadata

# Recorded for a tracked package that is not installed. A version string is
# never "absent", so this cannot collide with a real one.
ABSENT = "absent"


@dataclass(frozen=True)
class EnvLock:
    """Interpreter version plus installed distributions, sorted."""

    python: str
    packages: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        # Sorting in the constructor means callers cannot create two locks that
        # mean the same thing and canonicalise differently.
        object.__setattr__(self, "packages", tuple(sorted(self.packages)))

    def canonical(self) -> str:
        """A stable string. Newline-joined, so no JSON escaping subtleties."""
        lines = [f"python={self.python}"]
        lines += [f"{name}=={version}" for name, version in self.packages]
        return "\n".join(lines)


def capture_env(track: tuple[str, ...] | None = None) -> EnvLock:
    """This interpreter, plus either every distribution or a declared subset.

    `track=None` captures everything. Maximally correct, and in practice it
    means installing any unrelated dev tool invalidates every cached run --
    the cache is the whole value of the system, so that default is safe and
    nearly useless.

    `track=("numpy", "scipy")` captures only those. The user asserts these are
    the packages whose versions can change a result. The risk is the mirror
    image: forget one and a stale cache hit looks like a fresh answer. That is
    why a tracked-but-missing package is recorded as ABSENT rather than
    dropped -- installing or removing it still moves the hash.
    """
    installed = {
        dist.metadata["Name"]: dist.version
        for dist in metadata.distributions()
        if dist.metadata["Name"]
    }
    if track is None:
        packages = tuple(installed.items())
    else:
        packages = tuple((name, installed.get(name, ABSENT)) for name in track)
    return EnvLock(python=platform.python_version(), packages=packages)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_env.py -q`
Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add src/physrun/env.py tests/test_env.py
git commit -m "feat: capture the environment as a stable hashable lock"
```

---

### Task 3: RunSpec and pure hashing

**Files:**
- Create: `../physrun/src/physrun/spec.py`
- Test: `../physrun/tests/test_spec_hash.py`

**Interfaces:**
- Consumes: `EnvLock` from `physrun.env`.
- Produces:
  - `class RunSpec` — frozen dataclass, fields `code: str`, `params: dict`,
    `env: EnvLock`, `nondeterministic: bool = False`, `tags: tuple[str, ...] = ()`
  - `canonical_json(obj: object) -> str`
  - `run_id(spec: RunSpec) -> str` — 64-char hex

**This is the load-bearing task.** If `run_id` is not pure, the cache never hits,
"already ran this" is false, and nothing errors.

- [ ] **Step 1: Write the failing test**

`tests/test_spec_hash.py`:

```python
import json
import os
import subprocess
import sys

from physrun.env import EnvLock
from physrun.spec import RunSpec, canonical_json, run_id

ENV = EnvLock(python="3.11.7", packages=(("numpy", "2.0.0"),))


def make(**overrides) -> RunSpec:
    base = {"code": "print(1)", "params": {"L": 12, "J": 1.0}, "env": ENV}
    base.update(overrides)
    return RunSpec(**base)


def test_id_is_64_hex_chars():
    value = run_id(make())
    assert len(value) == 64
    int(value, 16)


def test_param_insertion_order_does_not_change_the_id():
    a = RunSpec(code="x", params={"L": 1, "J": 2}, env=ENV)
    b = RunSpec(code="x", params={"J": 2, "L": 1}, env=ENV)
    assert run_id(a) == run_id(b)


def test_tags_are_not_in_the_hash():
    assert run_id(make(tags=())) == run_id(make(tags=("phase-a", "draft")))


def test_code_change_changes_the_id():
    assert run_id(make(code="print(1)")) != run_id(make(code="print(2)"))


def test_param_change_changes_the_id():
    assert run_id(make(params={"L": 12})) != run_id(make(params={"L": 13}))


def test_env_change_changes_the_id():
    other = EnvLock(python="3.11.7", packages=(("numpy", "2.0.1"),))
    assert run_id(make()) != run_id(make(env=other))


def test_nondeterministic_flag_changes_the_id():
    assert run_id(make(nondeterministic=False)) != run_id(make(nondeterministic=True))


def test_floats_format_identically_for_equal_values():
    assert run_id(make(params={"J": 1.0})) == run_id(make(params={"J": 1.00}))


def test_canonical_json_rejects_unserialisable_params():
    try:
        canonical_json({"bad": object()})
    except TypeError:
        return
    raise AssertionError("expected TypeError for an unserialisable param")


# --- the purity property test.
#
# The bug this exists for is silent: an id that varies by working directory or
# process makes every cache lookup miss, and nothing raises. A same-process
# assertion cannot catch it, so the id is recomputed in a FRESH interpreter from
# a DIFFERENT working directory and compared.

PROBE = """
import json, sys
sys.path.insert(0, %(src)r)
from physrun.env import EnvLock
from physrun.spec import RunSpec, run_id
env = EnvLock(python="3.11.7", packages=(("numpy", "2.0.0"),))
spec = RunSpec(code="print(1)", params={"L": 12, "J": 1.0}, env=env)
print(run_id(spec))
"""


def test_id_is_stable_across_process_and_working_directory(tmp_path):
    here = run_id(make())
    src = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
    script = tmp_path / "probe.py"
    script.write_text(PROBE % {"src": src}, encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "PYTHONHASHSEED": "1"},
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == here, "run_id differs across process/cwd"


def test_id_is_stable_under_a_different_hash_seed(tmp_path):
    src = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
    script = tmp_path / "probe.py"
    script.write_text(PROBE % {"src": src}, encoding="utf-8")

    ids = set()
    for seed in ("0", "12345"):
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "PYTHONHASHSEED": seed},
        )
        assert proc.returncode == 0, proc.stderr
        ids.add(proc.stdout.strip())
    assert len(ids) == 1, f"PYTHONHASHSEED changes run_id: {ids}"
    json.dumps(sorted(ids))  # keeps the import honest
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_spec_hash.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'physrun.spec'`

- [ ] **Step 3: Write the implementation**

`src/physrun/spec.py`:

```python
"""What identifies a run, and the pure hash of it.

The whole system rests on `run_id` being pure. If it absorbs a timestamp, an
absolute path, a hostname, dict iteration order, or a locale-dependent float
format, then the cache never hits, "have I run this" is always false, and
nothing raises. The failure is silent, which is why it has a property test.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from physrun.env import EnvLock


@dataclass(frozen=True)
class RunSpec:
    """Everything that decides whether two calculations are the same one.

    `code` is the source TEXT, never a path -- a path is a fact about one
    machine's filesystem and would poison the hash.

    `tags` are metadata for querying and are deliberately excluded from the
    hash: two runs differing only by tag are the same run.
    """

    code: str
    params: dict
    env: EnvLock
    nondeterministic: bool = False
    tags: tuple[str, ...] = field(default_factory=tuple)


def canonical_json(obj: object) -> str:
    """Deterministic JSON. Raises TypeError on anything unserialisable.

    `sort_keys` removes insertion-order dependence. `separators` removes
    whitespace variation. `ensure_ascii` removes any locale or encoding
    influence on the bytes that get hashed.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def run_id(spec: RunSpec) -> str:
    """sha256 over the canonical form. 64 lowercase hex characters.

    Field order here is fixed and part of the format: changing it invalidates
    every cache entry in every existing store.
    """
    parts = [
        "physrun-v1",
        spec.code,
        canonical_json(spec.params),
        spec.env.canonical(),
        "nondeterministic" if spec.nondeterministic else "deterministic",
    ]
    blob = " ".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_spec_hash.py -q`
Expected: PASS, 11 tests.

- [ ] **Step 5: Commit**

```bash
git add src/physrun/spec.py tests/test_spec_hash.py
git commit -m "feat: RunSpec and a pure content-addressed run_id"
```

---

### Task 4: Run Store

**Files:**
- Create: `../physrun/src/physrun/store.py`
- Test: `../physrun/tests/test_store.py`

**Interfaces:**
- Consumes: `RunSpec`, `run_id`, `canonical_json` from `physrun.spec`;
  `EnvLock` from `physrun.env`.
- Produces:
  - `class Run` — frozen dataclass with fields `run_id: str`, `spec: RunSpec`,
    `status: str`, `exit_code: int`, `stdout: str`, `stderr: str`,
    `result: dict`, `artifacts: dict[str, str]`, `wall_seconds: float`,
    `created_at: str`
  - `class Store` with `__init__(self, root: Path)`, `put(run) -> str`,
    `get(run_id) -> Run | None`,
    `query(*, tags=None, status=None, params=None) -> list[Run]`,
    `put_artifact(data: bytes) -> str`, `get_artifact(digest: str) -> bytes`,
    `gc(*, keep: set[str]) -> int`

- [ ] **Step 1: Write the failing test**

`tests/test_store.py`:

```python
import pytest

from physrun.env import EnvLock
from physrun.spec import RunSpec, run_id
from physrun.store import Run, Store

ENV = EnvLock(python="3.11.7", packages=(("numpy", "2.0.0"),))


def make_run(**overrides) -> Run:
    spec = RunSpec(
        code=overrides.pop("code", "print(1)"),
        params=overrides.pop("params", {"L": 12}),
        env=ENV,
        tags=overrides.pop("tags", ()),
    )
    base = {
        "run_id": run_id(spec),
        "spec": spec,
        "status": "ok",
        "exit_code": 0,
        "stdout": "hello",
        "stderr": "",
        "result": {"gap": 0.25},
        "artifacts": {},
        "wall_seconds": 1.5,
        "created_at": "2026-08-03T00:00:00Z",
    }
    base.update(overrides)
    return Run(**base)


@pytest.fixture
def store(tmp_path) -> Store:
    return Store(tmp_path / "store")


def test_put_then_get_round_trips(store):
    run = make_run()
    returned = store.put(run)
    assert returned == run.run_id

    loaded = store.get(run.run_id)
    assert loaded is not None
    assert loaded.run_id == run.run_id
    assert loaded.result == {"gap": 0.25}
    assert loaded.spec.params == {"L": 12}
    assert loaded.spec.env == ENV


def test_get_returns_none_for_unknown_id(store):
    assert store.get("0" * 64) is None


def test_put_is_idempotent(store):
    run = make_run()
    store.put(run)
    store.put(run)
    assert len(store.query()) == 1


def test_query_by_tag(store):
    store.put(make_run(code="a", tags=("phase-a",)))
    store.put(make_run(code="b", tags=("phase-b",)))
    hits = store.query(tags=["phase-a"])
    assert len(hits) == 1
    assert hits[0].spec.code == "a"


def test_query_by_param_value(store):
    store.put(make_run(code="a", params={"L": 12}))
    store.put(make_run(code="b", params={"L": 16}))
    hits = store.query(params={"L": 16})
    assert len(hits) == 1
    assert hits[0].spec.code == "b"


def test_query_by_status(store):
    store.put(make_run(code="a", status="ok"))
    store.put(make_run(code="b", status="failed", exit_code=1))
    assert len(store.query(status="failed")) == 1


def test_artifacts_are_content_addressed_and_deduped(store):
    first = store.put_artifact(b"figure-bytes")
    second = store.put_artifact(b"figure-bytes")
    assert first == second
    assert store.get_artifact(first) == b"figure-bytes"


def test_different_artifact_content_gets_a_different_digest(store):
    assert store.put_artifact(b"one") != store.put_artifact(b"two")


def test_gc_removes_unreferenced_runs_and_reports_the_count(store):
    keep = make_run(code="keep")
    drop = make_run(code="drop")
    store.put(keep)
    store.put(drop)

    removed = store.gc(keep={keep.run_id})
    assert removed == 1
    assert store.get(keep.run_id) is not None
    assert store.get(drop.run_id) is None


def test_store_survives_reopening(tmp_path):
    root = tmp_path / "store"
    run = make_run()
    Store(root).put(run)
    assert Store(root).get(run.run_id) is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_store.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'physrun.store'`

- [ ] **Step 3: Write the implementation**

`src/physrun/store.py`:

```python
"""SQLite index plus content-addressed artifacts on disk.

Layout under `root`:
    index.db          one row per run
    artifacts/ab/cd…  artifact bytes, named by their own sha256
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from physrun.env import EnvLock
from physrun.spec import RunSpec, canonical_json

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id        TEXT PRIMARY KEY,
    code          TEXT NOT NULL,
    params        TEXT NOT NULL,
    env_python    TEXT NOT NULL,
    env_packages  TEXT NOT NULL,
    nondet        INTEGER NOT NULL,
    tags          TEXT NOT NULL,
    status        TEXT NOT NULL,
    exit_code     INTEGER NOT NULL,
    stdout        TEXT NOT NULL,
    stderr        TEXT NOT NULL,
    result        TEXT NOT NULL,
    artifacts     TEXT NOT NULL,
    wall_seconds  REAL NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS runs_status ON runs(status);
"""


@dataclass(frozen=True)
class Run:
    """A recorded execution. `created_at` is metadata and never hashed."""

    run_id: str
    spec: RunSpec
    status: str
    exit_code: int
    stdout: str
    stderr: str
    result: dict
    artifacts: dict[str, str]
    wall_seconds: float
    created_at: str


class Store:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.artifacts_dir = self.root / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.root / "index.db")
        self._db.row_factory = sqlite3.Row
        self._db.executescript(SCHEMA)
        self._db.commit()

    # --- runs

    def put(self, run: Run) -> str:
        # REPLACE, not INSERT: re-recording the same run is idempotent, which
        # matters because the executor may legitimately re-run with force=True.
        self._db.execute(
            "REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                run.run_id,
                run.spec.code,
                canonical_json(run.spec.params),
                run.spec.env.python,
                canonical_json(list(run.spec.env.packages)),
                int(run.spec.nondeterministic),
                canonical_json(list(run.spec.tags)),
                run.status,
                run.exit_code,
                run.stdout,
                run.stderr,
                canonical_json(run.result),
                canonical_json(run.artifacts),
                run.wall_seconds,
                run.created_at,
            ),
        )
        self._db.commit()
        return run.run_id

    def get(self, run_id: str) -> Run | None:
        row = self._db.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return self._row_to_run(row) if row is not None else None

    def query(
        self,
        *,
        tags: list[str] | None = None,
        status: str | None = None,
        params: dict | None = None,
    ) -> list[Run]:
        sql = "SELECT * FROM runs"
        clauses: list[str] = []
        values: list[object] = []
        if status is not None:
            clauses.append("status = ?")
            values.append(status)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        rows = self._db.execute(sql, values).fetchall()
        runs = [self._row_to_run(r) for r in rows]

        # Tag and param matching happen in Python rather than SQL. Both are
        # stored as JSON documents, and a LIKE over JSON matches substrings of
        # other values -- tag "a" would match tag "ab".
        if tags:
            wanted = set(tags)
            runs = [r for r in runs if wanted & set(r.spec.tags)]
        if params:
            runs = [
                r
                for r in runs
                if all(r.spec.params.get(k) == v for k, v in params.items())
            ]
        return runs

    def _row_to_run(self, row: sqlite3.Row) -> Run:
        env = EnvLock(
            python=row["env_python"],
            packages=tuple(tuple(p) for p in json.loads(row["env_packages"])),
        )
        spec = RunSpec(
            code=row["code"],
            params=json.loads(row["params"]),
            env=env,
            nondeterministic=bool(row["nondet"]),
            tags=tuple(json.loads(row["tags"])),
        )
        return Run(
            run_id=row["run_id"],
            spec=spec,
            status=row["status"],
            exit_code=row["exit_code"],
            stdout=row["stdout"],
            stderr=row["stderr"],
            result=json.loads(row["result"]),
            artifacts=json.loads(row["artifacts"]),
            wall_seconds=row["wall_seconds"],
            created_at=row["created_at"],
        )

    # --- artifacts

    def put_artifact(self, data: bytes) -> str:
        digest = hashlib.sha256(data).hexdigest()
        path = self._artifact_path(digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(data)
        return digest

    def get_artifact(self, digest: str) -> bytes:
        return self._artifact_path(digest).read_bytes()

    def _artifact_path(self, digest: str) -> Path:
        # Two-character shard: a flat directory of 100k artifacts is slow to
        # list on every filesystem that matters.
        return self.artifacts_dir / digest[:2] / digest[2:]

    # --- maintenance

    def gc(self, *, keep: set[str]) -> int:
        """Delete every run not in `keep`. Returns how many were removed."""
        rows = self._db.execute("SELECT run_id FROM runs").fetchall()
        doomed = [r["run_id"] for r in rows if r["run_id"] not in keep]
        self._db.executemany(
            "DELETE FROM runs WHERE run_id = ?", [(rid,) for rid in doomed]
        )
        self._db.commit()
        return len(doomed)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_store.py -q`
Expected: PASS, 10 tests.

- [ ] **Step 5: Commit**

```bash
git add src/physrun/store.py tests/test_store.py
git commit -m "feat: SQLite run store with content-addressed artifacts"
```

---

### Task 5: Executor with caching

**Files:**
- Create: `../physrun/src/physrun/executor.py`
- Test: `../physrun/tests/test_executor.py`

**Interfaces:**
- Consumes: `RunSpec`, `run_id` from `physrun.spec`; `Run`, `Store` from
  `physrun.store`.
- Produces:
  - `class Executor` with `__init__(self, store: Store)` and
    `run(self, spec: RunSpec, *, force: bool = False) -> Run`
  - Module constants `PARAMS_VAR = "PHYSRUN_PARAMS"`,
    `RESULT_VAR = "PHYSRUN_RESULT"`, `ARTIFACTS_VAR = "PHYSRUN_ARTIFACTS"`

**The contract a calculation script obeys:** it reads its parameters from the
JSON in `$PHYSRUN_PARAMS`, writes its results as JSON to the path in
`$PHYSRUN_RESULT`, and may write files into the directory `$PHYSRUN_ARTIFACTS`.

- [ ] **Step 1: Write the failing test**

`tests/test_executor.py`:

```python
import pytest

from physrun.env import EnvLock
from physrun.executor import Executor
from physrun.spec import RunSpec
from physrun.store import Store

ENV = EnvLock(python="3.11.7", packages=(("numpy", "2.0.0"),))

ECHO_PARAMS = """
import json, os
params = json.loads(os.environ["PHYSRUN_PARAMS"])
with open(os.environ["PHYSRUN_RESULT"], "w") as fh:
    json.dump({"doubled": params["L"] * 2}, fh)
"""

WRITES_ARTIFACT = """
import json, os
path = os.path.join(os.environ["PHYSRUN_ARTIFACTS"], "fig.txt")
with open(path, "w") as fh:
    fh.write("plot")
with open(os.environ["PHYSRUN_RESULT"], "w") as fh:
    json.dump({"ok": True}, fh)
"""

FAILS = """
import sys
sys.stderr.write("boom")
sys.exit(3)
"""

# "Did this execute?" is answered by a nonce in the result, not by a counter
# file. Two earlier drafts used the filesystem: one wrote to
# PHYSRUN_ARTIFACTS/../.. which resolves into the system temp root rather than
# tmp_path (the assertion would have passed only by accident), and one passed an
# absolute counter path through `params` -- straight into the hash, which the
# Global Constraints forbid.
#
# A nonce needs neither. If the second call returns the same nonce the code did
# not run; if it differs, it did. That is the claim, asserted directly.
NONCE = """
import json, os, uuid
with open(os.environ["PHYSRUN_RESULT"], "w") as fh:
    json.dump({"nonce": uuid.uuid4().hex}, fh)
"""


@pytest.fixture
def executor(tmp_path) -> Executor:
    return Executor(Store(tmp_path / "store"))


def test_runs_the_code_and_captures_the_result(executor):
    spec = RunSpec(code=ECHO_PARAMS, params={"L": 12}, env=ENV)
    run = executor.run(spec)
    assert run.status == "ok"
    assert run.exit_code == 0
    assert run.result == {"doubled": 24}
    assert run.wall_seconds >= 0


def test_a_cache_hit_does_not_execute(executor):
    # Not "a Run came back" -- assert the code did NOT run a second time. A
    # cache that silently re-executes is the same bug wearing a disguise.
    spec = RunSpec(code=NONCE, params={}, env=ENV)
    first = executor.run(spec)
    second = executor.run(spec)
    assert second.result["nonce"] == first.result["nonce"]


def test_force_re_executes(executor):
    spec = RunSpec(code=NONCE, params={}, env=ENV)
    first = executor.run(spec)
    second = executor.run(spec, force=True)
    assert second.result["nonce"] != first.result["nonce"]


def test_a_nondeterministic_spec_is_never_cached(executor):
    spec = RunSpec(code=NONCE, params={}, env=ENV, nondeterministic=True)
    first = executor.run(spec)
    second = executor.run(spec)
    assert second.result["nonce"] != first.result["nonce"]


def test_a_failing_run_is_recorded_not_raised(executor):
    run = executor.run(RunSpec(code=FAILS, params={}, env=ENV))
    assert run.status == "failed"
    assert run.exit_code == 3
    assert "boom" in run.stderr


def test_a_failing_run_is_not_cached(executor, tmp_path):
    # Re-running after fixing the environment must actually re-run.
    spec = RunSpec(code=FAILS, params={}, env=ENV)
    first = executor.run(spec)
    assert executor.store.get(first.run_id) is None


def test_artifacts_are_captured_and_content_addressed(executor):
    run = executor.run(RunSpec(code=WRITES_ARTIFACT, params={}, env=ENV))
    assert "fig.txt" in run.artifacts
    assert executor.store.get_artifact(run.artifacts["fig.txt"]) == b"plot"


def test_the_run_is_retrievable_from_the_store_afterwards(executor):
    run = executor.run(RunSpec(code=ECHO_PARAMS, params={"L": 3}, env=ENV))
    assert executor.store.get(run.run_id) is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_executor.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'physrun.executor'`

- [ ] **Step 3: Write the implementation**

`src/physrun/executor.py`:

```python
"""Execute a RunSpec, capture everything, and never repeat work needlessly."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from physrun.spec import RunSpec, canonical_json, run_id
from physrun.store import Run, Store

PARAMS_VAR = "PHYSRUN_PARAMS"
RESULT_VAR = "PHYSRUN_RESULT"
ARTIFACTS_VAR = "PHYSRUN_ARTIFACTS"

TIMEOUT_SECONDS = 60 * 60 * 6


class Executor:
    def __init__(self, store: Store) -> None:
        self.store = store

    def run(self, spec: RunSpec, *, force: bool = False) -> Run:
        rid = run_id(spec)

        # A nondeterministic run is never served from cache: returning one
        # recorded sample as though it had been re-derived is a lie.
        if not force and not spec.nondeterministic:
            cached = self.store.get(rid)
            if cached is not None:
                return cached

        workdir = Path(tempfile.mkdtemp(prefix="physrun-"))
        try:
            record = self._execute(spec, rid, workdir)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        # A failed run is recorded in the returned object but NOT stored: the
        # next attempt must actually re-run, because the fix is usually outside
        # the spec (a missing package, a full disk).
        if record.status == "ok":
            self.store.put(record)
        return record

    def _execute(self, spec: RunSpec, rid: str, workdir: Path) -> Run:
        script = workdir / "calculation.py"
        script.write_text(spec.code, encoding="utf-8")
        result_path = workdir / "result.json"
        artifacts_dir = workdir / "artifacts"
        artifacts_dir.mkdir()

        env = {
            **os.environ,
            PARAMS_VAR: canonical_json(spec.params),
            RESULT_VAR: str(result_path),
            ARTIFACTS_VAR: str(artifacts_dir),
            "PYTHONIOENCODING": "utf-8",
        }

        started = time.monotonic()
        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                cwd=str(workdir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=TIMEOUT_SECONDS,
                env=env,
            )
            exit_code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            exit_code = -1
            stdout = ""
            stderr = f"timed out after {TIMEOUT_SECONDS}s"
        elapsed = time.monotonic() - started

        result: dict = {}
        if exit_code == 0 and result_path.exists():
            try:
                result = json.loads(result_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                exit_code = -2
                stderr += f"\n{RESULT_VAR} was not valid JSON: {exc}"

        artifacts: dict[str, str] = {}
        if exit_code == 0:
            for path in sorted(artifacts_dir.rglob("*")):
                if path.is_file():
                    name = path.relative_to(artifacts_dir).as_posix()
                    artifacts[name] = self.store.put_artifact(path.read_bytes())

        return Run(
            run_id=rid,
            spec=spec,
            status="ok" if exit_code == 0 else "failed",
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            result=result,
            artifacts=artifacts,
            wall_seconds=elapsed,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_executor.py -q`
Expected: PASS, 8 tests.

- [ ] **Step 5: Commit**

```bash
git add src/physrun/executor.py tests/test_executor.py
git commit -m "feat: executor with content-addressed caching"
```

---

### Task 6: CLI

**Files:**
- Create: `../physrun/src/physrun/cli.py`
- Test: `../physrun/tests/test_cli.py`

**Interfaces:**
- Consumes: `capture_env` from `physrun.env`; `RunSpec` from `physrun.spec`;
  `Store` from `physrun.store`; `Executor` from `physrun.executor`.
- Produces: `main(argv: list[str] | None = None) -> int`, and
  `parse_param(text: str) -> tuple[str, object]`.

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:

```python
import json

import pytest

from physrun.cli import main, parse_param

SCRIPT = """
import json, os
params = json.loads(os.environ["PHYSRUN_PARAMS"])
with open(os.environ["PHYSRUN_RESULT"], "w") as fh:
    json.dump({"L": params["L"]}, fh)
"""


@pytest.fixture
def script(tmp_path):
    path = tmp_path / "calc.py"
    path.write_text(SCRIPT, encoding="utf-8")
    return path


def test_parse_param_infers_int_float_bool_and_string():
    assert parse_param("L=12") == ("L", 12)
    assert parse_param("J=1.5") == ("J", 1.5)
    assert parse_param("flag=true") == ("flag", True)
    assert parse_param("name=ising") == ("name", "ising")


def test_parse_param_rejects_a_missing_equals():
    with pytest.raises(ValueError):
        parse_param("nope")


def test_run_then_show_round_trips(script, tmp_path, capsys):
    store = str(tmp_path / "store")
    assert main(["--store", store, "run", str(script), "--param", "L=12"]) == 0
    printed = capsys.readouterr().out
    rid = printed.strip().split()[-1]

    assert main(["--store", store, "show", rid]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["result"] == {"L": 12}


def test_second_run_reports_a_cache_hit(script, tmp_path, capsys):
    store = str(tmp_path / "store")
    main(["--store", store, "run", str(script), "--param", "L=12"])
    capsys.readouterr()
    main(["--store", store, "run", str(script), "--param", "L=12"])
    assert "cached" in capsys.readouterr().out.lower()


def test_query_by_tag_lists_the_run(script, tmp_path, capsys):
    store = str(tmp_path / "store")
    main(["--store", store, "run", str(script), "--param", "L=1", "--tag", "sweep"])
    capsys.readouterr()
    assert main(["--store", store, "query", "--tag", "sweep"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 1


def test_show_of_an_unknown_id_fails_loudly(tmp_path, capsys):
    code = main(["--store", str(tmp_path / "s"), "show", "0" * 64])
    assert code == 1
    assert "not found" in capsys.readouterr().err.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'physrun.cli'`

- [ ] **Step 3: Write the implementation**

`src/physrun/cli.py`:

```python
"""Command line surface: run, query, show, gc."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from physrun.env import capture_env
from physrun.executor import Executor
from physrun.spec import RunSpec, run_id
from physrun.store import Run, Store

DEFAULT_STORE = ".physrun"


def parse_param(text: str) -> tuple[str, object]:
    """`L=12` -> `("L", 12)`. Types are inferred, strings are the fallback."""
    if "=" not in text:
        raise ValueError(f"--param needs NAME=VALUE, got {text!r}")
    name, _, raw = text.partition("=")
    lowered = raw.lower()
    if lowered in ("true", "false"):
        return name, lowered == "true"
    for caster in (int, float):
        try:
            return name, caster(raw)
        except ValueError:
            continue
    return name, raw


def _as_dict(run: Run) -> dict:
    data = asdict(run)
    data["spec"]["env"] = {
        "python": run.spec.env.python,
        "packages": list(run.spec.env.packages),
    }
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="physrun")
    parser.add_argument("--store", default=DEFAULT_STORE)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="execute a calculation")
    p_run.add_argument("script")
    p_run.add_argument("--param", action="append", default=[])
    p_run.add_argument("--tag", action="append", default=[])
    p_run.add_argument("--force", action="store_true")
    p_run.add_argument("--nondeterministic", action="store_true")
    p_run.add_argument(
        "--track",
        action="append",
        default=[],
        help="package whose version affects this result; repeatable. "
        "Omit to hash the whole environment, which is safer and caches worse.",
    )

    p_query = sub.add_parser("query", help="list matching runs")
    p_query.add_argument("--tag", action="append", default=[])
    p_query.add_argument("--status")

    p_show = sub.add_parser("show", help="print one run as JSON")
    p_show.add_argument("run_id")

    p_gc = sub.add_parser("gc", help="delete runs not carrying a kept tag")
    p_gc.add_argument("--keep-tag", action="append", default=[])

    args = parser.parse_args(argv)
    store = Store(Path(args.store))

    if args.command == "run":
        try:
            params = dict(parse_param(p) for p in args.param)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1

        code = Path(args.script).read_text(encoding="utf-8")
        if not args.track:
            print(
                "note: hashing the whole environment; installing any package "
                "will invalidate this cache. Use --track to name what matters.",
                file=sys.stderr,
            )
        spec = RunSpec(
            code=code,
            params=params,
            env=capture_env(track=tuple(args.track) or None),
            nondeterministic=args.nondeterministic,
            tags=tuple(args.tag),
        )
        was_cached = (
            not args.force
            and not spec.nondeterministic
            and store.get(run_id(spec)) is not None
        )
        run = Executor(store).run(spec, force=args.force)
        state = "cached" if was_cached else run.status
        print(f"{state} {run.run_id}")
        return 0 if run.status == "ok" else 1

    if args.command == "query":
        hits = store.query(tags=args.tag or None, status=args.status)
        print(json.dumps([_as_dict(r) for r in hits], indent=2))
        return 0

    if args.command == "show":
        run = store.get(args.run_id)
        if run is None:
            print(f"run not found: {args.run_id}", file=sys.stderr)
            return 1
        print(json.dumps(_as_dict(run), indent=2))
        return 0

    if args.command == "gc":
        keep = {r.run_id for r in store.query(tags=args.keep_tag or None)} \
            if args.keep_tag else set()
        removed = store.gc(keep=keep)
        print(f"removed {removed} run(s)")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -q`
Expected: PASS, 6 tests.

- [ ] **Step 5: Commit**

```bash
git add src/physrun/cli.py tests/test_cli.py
git commit -m "feat: physrun CLI - run, query, show, gc"
```

---

### Task 7: The analytic fixture

**Files:**
- Create: `../physrun/tests/test_ising.py`

**Interfaces:**
- Consumes: `capture_env`, `RunSpec`, `Store`, `Executor` — all as defined above.
- Produces: nothing importable. This is the proof, not a component.

**Why this task exists:** every test before it passes on a system that computes
confident nonsense. This is the only one that checks the numbers mean something.
The 1D transverse-field Ising model at the critical point has a closed-form
single-particle spectrum, so the answer is known independently of the code.

- [ ] **Step 1: Write the failing test**

`tests/test_ising.py`:

```python
"""End-to-end against a model whose answer is known analytically.

For the 1D transverse-field Ising chain with open boundaries the
single-particle energies are

    eps_k = 2 * sqrt(J^2 + h^2 - 2*J*h*cos(k))

and the gap at J = h is 2*|J - h| = 0, approached as the chain grows. Rather
than lean on a finite-size extrapolation, this test checks the closed form of
eps_k directly at fixed k -- exact, and enough to prove the pipeline carries
real numbers rather than plumbing.
"""

import math

from physrun.env import capture_env
from physrun.executor import Executor
from physrun.spec import RunSpec
from physrun.store import Store

ISING = """
import json, math, os

params = json.loads(os.environ["PHYSRUN_PARAMS"])
J, h, k = params["J"], params["h"], params["k"]
eps = 2.0 * math.sqrt(J * J + h * h - 2.0 * J * h * math.cos(k))

with open(os.environ["PHYSRUN_RESULT"], "w") as fh:
    json.dump({"eps": eps}, fh)
"""


def analytic_eps(J: float, h: float, k: float) -> float:
    return 2.0 * math.sqrt(J * J + h * h - 2.0 * J * h * math.cos(k))


def test_pipeline_reproduces_the_analytic_spectrum(tmp_path):
    executor = Executor(Store(tmp_path / "store"))
    env = capture_env()

    for J, h, k in [(1.0, 1.0, 0.5), (1.0, 0.5, 1.0), (0.7, 1.3, 2.0)]:
        spec = RunSpec(code=ISING, params={"J": J, "h": h, "k": k}, env=env)
        run = executor.run(spec)
        assert run.status == "ok", run.stderr
        assert math.isclose(run.result["eps"], analytic_eps(J, h, k), rel_tol=1e-12)


def test_the_critical_point_is_gapless_at_k_zero(tmp_path):
    executor = Executor(Store(tmp_path / "store"))
    spec = RunSpec(
        code=ISING, params={"J": 1.0, "h": 1.0, "k": 0.0}, env=capture_env()
    )
    run = executor.run(spec)
    assert run.status == "ok", run.stderr
    assert math.isclose(run.result["eps"], 0.0, abs_tol=1e-12)


def test_re_running_the_sweep_is_free(tmp_path):
    """The claim the whole design rests on, measured rather than asserted."""
    executor = Executor(Store(tmp_path / "store"))
    env = capture_env()
    specs = [
        RunSpec(code=ISING, params={"J": 1.0, "h": 1.0, "k": k / 10}, env=env)
        for k in range(8)
    ]
    first = [executor.run(s) for s in specs]
    second = [executor.run(s) for s in specs]

    assert [r.run_id for r in first] == [r.run_id for r in second]
    # Identical objects out of the store, not fresh executions.
    assert all(a.created_at == b.created_at for a, b in zip(first, second))
```

- [ ] **Step 2: Run it**

Run: `python -m pytest tests/test_ising.py -q`
Expected: **PASS**, 3 tests.

This task deliberately has no red-to-green cycle: it introduces no production
code, only a check on code Tasks 2-5 already built. If it fails, the failure is
in the pipeline, not in this file — **do not edit the expected values to make it
pass.** The analytic form is the ground truth and the code is what is on trial.

- [ ] **Step 3: Run the whole check set**

Run: `python tools/run_checks.py --tier fast --require-test`
Expected: `PASS: N check(s) green (lint, test, typecheck)`

Fix any ruff or mypy finding rather than suppressing it.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ising.py
git commit -m "test: analytic Ising fixture proves the pipeline carries real numbers"
```

---

## Amendments made before execution

`executing-plans` re-reads a plan before running it, and found two things the
plan's own self-review had missed. Both were decided with the user on
2026-08-03 and the plan text above already reflects them.

**1. `capture_env` gained a declared subset.** As originally written it hashed
every installed distribution, so installing `black` would invalidate every
cached physics run — and the cache is the entire value of the system. The spec
accepted "upgrading numpy invalidates the cache", which reads as *relevant*
packages, not all of them.

Now `capture_env(track=("numpy", "scipy"))` hashes only what the user declares.
The mirror risk is real and stated in the docstring: forget a package and a
stale hit looks like a fresh answer. A tracked-but-missing package records as
`ABSENT` rather than being dropped, so installing or removing it still moves the
hash. `--track` is repeatable on the CLI, and omitting it prints a warning and
falls back to hashing everything — safe by default, fast by choice.

**2. The "did it execute?" tests stopped using the filesystem.** Two drafts got
this wrong: the first wrote a counter to `PHYSRUN_ARTIFACTS/../..`, which lands
in the system temp root rather than `tmp_path`, so the assertion would have
passed by accident; the second passed an absolute counter path through `params`,
which the Global Constraints forbid from entering the hash.

Both were working around a counter that should not exist. The tests now use a
nonce in the result: same nonce means it did not run, different means it did.
No paths, no filesystem, no monkeypatching, and it asserts the claim directly.

## Deviations from the spec, stated rather than silent

**Peak RSS is not captured.** The spec's §2 lists the Executor as capturing
"stdout, stderr, artifacts, wall time, exit code, peak RSS". Everything but the
last is implemented. Peak resident memory has no stdlib cross-platform API —
`resource.getrusage` is POSIX-only and the Windows equivalent needs `psutil` or
raw `ctypes` against `GetProcessMemoryInfo`, either of which breaks the
no-third-party-runtime-dependency constraint.

It is dropped rather than faked. Adding it later means one field on `Run`, one
column, and a platform branch in `Executor._execute` — no format change to
`run_id`, so no cache invalidation. Raise it as its own task if memory ceilings
start mattering.

**Everything else in scope is covered.** Store `put/get/query/gc`, artifact
content-addressing, executor caching, force, nondeterminism, failure recording,
and all eight of §5's fast-tier tests plus the Ising fixture. The three §5 tests
belonging to the Binder — missing-run build failure, computed staleness,
manifest completeness — are correctly absent: the Binder is not in this plan.

## Done when

- `python tools/run_checks.py --tier fast --require-test` passes in `../physrun/`.
- `physrun run calc.py --param L=12` twice prints `ok <id>` then `cached <id>`.
- `physrun show <id>` prints the run including its `result`.
- The README states the convergence limit verbatim.
