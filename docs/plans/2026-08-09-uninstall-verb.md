# Uninstall Verb Implementation Plan

**Goal:** `capability-layer uninstall [--into DIR] [--dry-run]` removes the layer
it installed, keyed off the v2 manifest, never destroying local edits.

**Source brief:** `TASK.md`, "Add an `uninstall` verb, mirroring `install`"

**Slug:** uninstall-verb

**Architecture:** Mirrors `upgrade` exactly, because `upgrade` already solved the
hard half. `upgrade` compares each installed file's current sha256 against the
hash `write_manifest` recorded, and uses the answer to decide overwrite-vs-keep.
`uninstall` asks the same question and uses the answer to decide delete-vs-keep.
No new concept, no second source of truth: the manifest is already the layer's
statement of what it owns, and `_layer_owned` / `_layer_hashes` already read it.

The verb lands in `.claude/install.py` rather than a new script for the same
reason `upgrade` did — `install.py` is the only module that knows `MANIFEST`,
`PRESERVE`, `MERGE` and `SEED`, and a second module would have to duplicate all
four. `cli.py` dispatches it into `_PAYLOAD_ONLY` alongside install/upgrade.

**Tech stack and constraints:** Python 3.11+, stdlib only. Windows-first paths
(`PYTHONIOENCODING=utf-8` before any tool script). No network. The uninstaller
must be safe to run twice.

## The three files it must refuse to delete, and why

This is the whole risk surface, so it is stated before the tasks:

| File | Why deleting it is wrong |
|---|---|
| `.claude/settings.json` | `MERGE`, not `create`. It may carry hooks the host had before the layer arrived, and nothing recorded what those were. `write_manifest` still lists it as owned because it counts `merge` actions — that is the trap. |
| `CLAUDE.md`, `.claude/project-checks.json` | `PRESERVE`. Never written by the installer, already excluded from the manifest — asserted rather than assumed, because the exclusion lives in `write_manifest` and could regress. |
| Any file whose current sha256 ≠ the recorded one | Somebody edited it. Same rule `upgrade` uses, same reason: "I do not know" and "it is unchanged" must not be the same answer. |

A file with **no recorded hash** (v1 manifest, or added after install) counts as
edited. Over-cautious on purpose; the cost of a wrong keep is a leftover file,
the cost of a wrong delete is somebody's work.

## File map

| File | Action | Responsibility after the change |
|---|---|---|
| `.claude/install.py` | Modify | Gains `uninstall_plan()` and an `--uninstall` branch in `main()`; still owns `MANIFEST`, `PRESERVE`, `MERGE` |
| `capability_layer/cli.py` | Modify | `uninstall` in `_TARGETS` and `_PAYLOAD_ONLY`; `--uninstall` prepended like `upgrade` does |
| `tools/test_install.py` | Modify | Gains the uninstall assertions listed in the Done Checks |
| `README.md` | Modify | Install section names the verb and its safety rule |

## Progress

Ticked by `executing-plans` as each task's own **Verification** command is run
and quoted. Nothing here is ticked on a clean diff or a zero exit code.

- [x] Task 1 — `uninstall_plan()` decides what may be removed
- [x] Task 2 — `--uninstall` applies the plan and reports
- [x] Task 3 — `uninstall` reaches the CLI
- [x] Task 4 — README names the verb and its safety rule

**Amended during execution, 2026-08-09.** The plan shipped with no task
checkboxes, because `writing-plans`' task template does not emit any --
`executing-plans` says it "mandates that syntax expressly", and it does not.
This block is the local repair; the layer contradiction behind it is filed in
`ISSUES.md` rather than fixed mid-run.

## Tasks

### Task 1: `uninstall_plan()` decides what may be removed

**Purpose:** A pure function that turns an installed target into three lists —
remove, keep-edited, keep-protected — with no filesystem mutation.

**Files:**
- Modify: `.claude/install.py:uninstall_plan` — new function beside `plan()`
- Test: `tools/test_install.py` — unit assertions over the returned lists

**Depends on:** none

**Implementation notes:**
- Signature `uninstall_plan(target: Path) -> tuple[list[str], list[str], list[str]]`
  returning `(remove, kept_edited, kept_protected)`, each a sorted list of posix
  relative paths.
- Read `_layer_owned(target)` for the path list and `_layer_hashes(target)` for
  the baseline. Empty `paths` means no manifest — return three empty lists and
  let the caller refuse.
- A path goes to `kept_protected` if it is in `PRESERVE`, `MERGE` or `SEED`, or
  is `MANIFEST` itself (the manifest is removed by the caller, last). All three
  constants are read directly, never copied into a list here.
- A path goes to `kept_edited` when `file_hash(target / rel)` differs from the
  recorded hash, or no hash is recorded, or the file is already gone.
- Everything else goes to `remove`.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_install.py`
- Expect: exit 0, and the new checks for the three lists print `OK:`

**Done when:** The function is importable and returns the three disjoint lists
for a fixture target, with no writes performed.

### Task 2: `--uninstall` applies the plan and reports

**Purpose:** The side-effecting half — deletes what Task 1 approved, prunes
directories it emptied, removes the manifest last, and prints every kept file.

**Files:**
- Modify: `.claude/install.py:main` — `--uninstall` argparse flag and its branch
- Test: `tools/test_install.py` — end-to-end install → uninstall on a temp repo

**Depends on:** 1

**Implementation notes:**
- `ap.add_argument("--uninstall", action="store_true")`. Mutually exclusive with
  `--upgrade`: argparse `add_mutually_exclusive_group` so the combination fails
  loudly rather than doing half of each.
- Refuse with exit 2 and a message when `_layer_owned(target)` is empty:
  "no `.claude/layer-manifest.json` — nothing here was installed by this layer".
- With `--dry-run`, print the three lists and write nothing. This must be the
  same code path that computes the real run's lists, so the dry run cannot
  describe a different tree — the defect `entry_point` already carries a comment
  about.
- Delete files, then remove now-empty directories bottom-up, then the manifest.
  Manifest last so an interrupted run is resumable.
- Print the kept lists with a reason per file. Silence about a kept file is the
  failure mode: the user must know the layer is not fully gone.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/test_install.py`
- Expect: exit 0; the end-to-end check reports the target has no
  `.claude/skills/` and still has `.claude/settings.json`

**Done when:** Installing into a temp repo and uninstalling leaves no
layer-owned file except the protected set, and running it twice is a clean no-op.

### Task 3: `uninstall` reaches the CLI

**Purpose:** `capability-layer uninstall` and `cl uninstall` dispatch to the
bundled payload's `install.py`, never to a copy inside the target.

**Files:**
- Modify: `capability_layer/cli.py:_TARGETS` — add `"uninstall": ".claude/install.py"`
- Modify: `capability_layer/cli.py:_PAYLOAD_ONLY` — add `"uninstall"`
- Modify: `capability_layer/cli.py:main` — prepend `--uninstall` as `upgrade` does
- Modify: `capability_layer/cli.py` module docstring — name the verb in the usage block
- Test: `tools/test_install.py` — assert the verb resolves and is payload-only

**Depends on:** 2

**Implementation notes:**
- `_PAYLOAD_ONLY` matters here for the opposite reason it does for install: a
  target that is being uninstalled still has `.claude/install.py` in it, and
  loading that copy would make `SOURCE` the target — the same aliasing the
  module docstring already warns about.
- The `verb == "upgrade"` branch becomes a small map so a third verb does not
  need a third `if`.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python -c "from capability_layer.cli import _TARGETS, _PAYLOAD_ONLY; assert 'uninstall' in _TARGETS and 'uninstall' in _PAYLOAD_ONLY; print('ok')"`
- Expect: `ok`

**Done when:** the assertions above pass. **Amended during execution,
2026-08-09** — the original read *"`python -m capability_layer uninstall --into
<tmp> --dry-run` prints the three lists and exits 0"*, and that command cannot
succeed in a source checkout for any verb.

`capability_layer/payload/` is staged at **wheel-build time**; `tools/stage_payload.py`
writes to `build/payload/`, and only the wheel maps it into the package. From a
source tree, `_resolve()` raises *"bundled payload is missing .claude/install.py"*
— measured, and `python -m capability_layer install` fails identically, so this
is a fact about the repository rather than a defect in this task.

The wheel-level proof therefore belongs to the slow tier, where
`tools/test_package.py` already builds the wheel, installs it into a clean venv
and runs a fresh repo's own tier. Task 4's full-tier run covers it.

### Task 4: README names the verb and its safety rule

**Purpose:** The install section is where a reader looks; a verb absent from it
is a verb nobody runs.

**Files:**
- Modify: `README.md` — the install/upgrade block gains uninstall

**Depends on:** 3

**Implementation notes:**
- Three lines, matching the existing `--dry-run` framing. State the one thing a
  reader cannot guess: an edited file is kept and named, and `settings.json` is
  never removed.
- No count is stated. `test_referenced_paths.py` checks counts in this file.

**Verification:**
- Run: `PYTHONIOENCODING=utf-8 python tools/run_checks.py --tier all --require-test`
- Expect: `PASS: 36 check(s) green (audit, build, lint, smoke, test, typecheck)`

**Done when:** The README documents the verb and the full tier is green.

## Constitution gate
- [x] I Evidence — every task names the exact command and the expected output
- [x] II Test first — Tasks 1 and 2 name their assertions before the code
- [x] III Smallest change — four files, no refactor beyond a two-branch `if` becoming a map
- [x] IV Reversibility — the destructive verb is `--dry-run`-first and refuses without a manifest
- [x] V No silent degradation — every kept file is printed with its reason
- [x] VI Mechanism — the safety rules are assertions in `test_install.py`, not prose
- [x] VII Secrets — no credential enters the repo

## Complexity tracking

No unticked boxes.

## Risks

- **`write_manifest` records `merge` actions as owned.** If a future change adds
  a second `MERGE` entry and the uninstaller's protected check is not updated,
  that file becomes deletable. Task 1 reads `MERGE` directly rather than listing
  paths, so the two cannot drift.
- **`SEED` files are indistinguishable after the fact.** A `ruff.toml` the
  installer seeded and one the host wrote look identical unless the hash matches.
  The hash rule handles it correctly by accident of design, not by intent —
  worth restating if `SEED` grows.

  **Resolved at Gate 1: `SEED` files are kept and named.** A repository that
  adopted the layer's lint config now depends on it, and removing the layer must
  not also break `ruff` and CI in the same step. They join `PRESERVE` and `MERGE`
  in `kept_protected`, printed with a reason so deleting them stays a one-line
  manual step rather than a surprise.

  This makes `SEED` the third protected category, so Task 1 reads all three
  constants directly rather than listing paths — the drift risk noted above
  applies to `SEED` growing too.
- **Untested on a real third-party repo.** Every verification here runs against
  `fresh_repo()` fixtures, same as the existing install tests.

## Approved

2026-08-09. Gate 1 passed. SEED files resolved as kept-and-named.

## Execution record — deviations, 2026-08-09

Two amendments, both made during the run and both because the plan asserted
something about the repository that was not true.

1. **Task 3's `Done when` named a command that cannot succeed here.**
   `python -m capability_layer <verb>` needs `capability_layer/payload/`, which
   only the wheel build creates; `tools/stage_payload.py` writes to
   `build/payload/`. `install` fails identically, so this is a fact about the
   source checkout rather than a defect in the verb. Wheel-level proof moved to
   the slow tier, where `test_package.py` already builds and installs it.

2. **The Task 3 assertions had to be guarded for an installed target.**
   They load `capability_layer/cli.py`, and the payload is `.claude/` plus
   `tools/` — an installed repo has this suite and no CLI module. `test_package.py`
   runs exactly that combination and went red. The block now skips with a stated
   reason, the same convention `test_entry_classifier.py` uses for the trigger
   corpus. Found by the slow tier, not by reading.

Nothing else diverged. Task 1 and Task 2 were built and verified as written.

## Recovery pass — 2026-08-09, after `verifying-work`

`verifying-work` returned **Gaps (2)**, not verified. Both were the same class:
the verb behaved correctly and the report said something else.

1. **The report claimed the manifest was kept, then deleted it.**
   `uninstall_plan` put `MANIFEST` in `kept_protected`, so the run printed
   `kept (yours)  .claude/layer-manifest.json` and `main()` unlinked it moments
   later. Deleting it is correct -- it is what makes a second run refuse -- but
   a reader was told the opposite. The manifest is now in none of the three
   lists and gets its own `removed last` line.

2. **`TASK.md`'s "and is named in the report" clause had no assertion.**
   Survival was asserted; naming was backed only by a manual capture during
   verification, so a regression that silenced the kept-list would have shipped
   green. Four assertions now read the captured stdout.

Neither was found by the suite. Both were found by reading `TASK.md`'s Done
Checks word by word against what the code actually printed, which is what that
stage is for.

## Second recovery pass — 2026-08-09

`verifying-work` returned Gaps again, and the gap was in the check written
during the first recovery pass rather than in the verb.

"the report does not claim the manifest was kept" inspected only the text before
the **first** occurrence of the manifest path. Reintroducing the defect emitted
both `removed last  .claude/layer-manifest.json` and
`kept (edited) .claude/layer-manifest.json`; the correct line came first, so the
assertion passed while the contradiction it was written to catch sat two lines
below. It tested the fix's happy path, not the defect.

Now asserted over every line mentioning the manifest, in three parts: mentioned
exactly once, never as kept, and explicitly as removed last. Red-green confirms
two of the three go red on the reintroduced defect.

**The lesson is the process one.** The behaviour was correct after the first
pass and stayed correct; only the guard was hollow. Nothing but re-running
red-green on a green suite would have found it, which is why that step is not
optional even when the tier is passing.
