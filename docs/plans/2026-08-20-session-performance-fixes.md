# Fix 2 of 4 session-performance bottlenecks Implementation Plan

## Approved

**Goal:** Close 2 of the 4 bottlenecks found in this session's own performance
audit with real mechanism — scope `spec-reviewer`/`test-verifier` dispatch
prompts to non-overlapping work, and make the layer's skill-body-load cost
visible in `tools/bench.py` — while explicitly NOT duplicating guidance that
already exists for the other 2.
**Source brief:** this conversation's own performance audit (`tools/bench.py`'s
shell-call counter: 272 calls, 17 repeats; subagent usage reports: 112,743 tok
combined; `wc -c` on the 9 loaded `SKILL.md` files: 104,352 chars)
**Slug:** session-performance-fixes
**Risk:** high (inferred, matches the prior unit's pattern — touches
`.claude/hooks/*` and `.claude/settings.json`, both `CONTROL_PATTERNS`
entries). Confirm with `python tools/scope.py --plan
docs/plans/2026-08-20-session-performance-fixes.md` once saved.
**Blast radius:** `.claude/settings.json` (fires on every `PostToolUse` for
the `Skill` tool, i.e. every skill invocation in every session from now on);
two `SKILL.md` files whose routing prose every future dispatcher reads.
Mitigated: the new hook is silent by default (writes to a state file, no
stdout unless something is genuinely wrong), matching
`.claude/hooks/post-tool/01-context-cost.py`'s own design, and is additive to
two skill files' existing sentences rather than restructuring them.
**Rollback:** revert the commit; the new hook file and its
`.claude/settings.json` registration both disappear together, and
`tools/bench.py` reports nothing extra rather than erroring on an absent
state file (matches `session_calls()`'s existing "not yet recorded" branch).
**Architecture:** No new subsystem. Task 1 mirrors an existing, working
pattern exactly — `.claude/hooks/post-tool/01-context-cost.py`'s
`WATCHED`/`TOTALS`/state-file-accumulation shape, extended to a second tool
(`Skill`) and a second state file, not merged into the first (different
concept, avoids coupling an unrelated schema into
`call-fingerprints.json`'s row-bounded structure). Task 2 adds one scoping
sentence to each of two already-existing dispatch instructions — no new
routing decision, no hook, no skill rename.
**Tech stack and constraints:** Python 3, stdlib only, matching every hook
and tool file in this repo. The new hook must stay silent by default (no
`print()` per invocation in the normal case) to respect
`decisions/2026-08-04-hooks-never-name-a-skill.md`'s spirit even though that
decision's literal AST-scan only forbids string-literal skill names in a
hook's *emitted* output, not its state-file writes.

## Grounding (verified before planning, not assumed)

- **Bottleneck #1's proposed fix does not apply.** Grepped both
  `.claude/skills/executing-plans/SKILL.md:83-85` and
  `.claude/skills/verifying-work/SKILL.md:110-115` — both already carry the
  exact "cheapest tier / `--scoped` mid-chain / full tier once before
  delivery" guidance this bottleneck's original fix would have restated. The
  real causes were (a) this session's branch inheriting unrelated commits
  from a prior session, which made `--scoped` exit 2 (`major`) every time it
  was tried, forcing fallback to full tier, and (b) my own inconsistent
  adherence to guidance that already exists. Neither is a documentation gap.
  **No task for this bottleneck** — recorded in Out of Scope, not silently
  dropped.
- **Bottleneck #4 (my own verbosity) is behavioral**, confirmed in the
  original audit — no code or doc mechanism proposed then, none added now.
  **No task for this bottleneck** either, for the same reason.
- **Bottleneck #3's hook-payload shape was empirically tested, not
  guessed.** Live-tested in this session: `.claude/settings.json`'s hook
  registrations are read once at session start — adding a temporary debug
  `PostToolUse` hook with matcher `"*"` and firing a real tool call
  afterward produced no new entry in its log, proving the registration
  change needed a fresh session to take effect. Cleaned up immediately
  (file deleted, `settings.json` reverted, confirmed via `git status
  --porcelain` showing no diff). **This session cannot prove the `Skill`
  matcher fires or what `tool_input` contains** — Task 1 is written
  defensively for that reason (see its Known limitation) rather than
  asserting a fact nobody has seen.
- **The `tool_input` field name is a grounded guess, not a blind one.** My
  own tool definition for `Skill` (given in this session's system context)
  declares its parameter as `"skill": {"type": "string", ...}` — Claude
  Code's hook payloads generally mirror a tool's own declared parameter
  names, so `"skill"` is the primary candidate, with `"skill_name"`/`"name"`
  as defensive fallbacks and an `"unattributed"` bucket if none match — so
  the raw invocation *count* stays honest even if per-skill attribution
  cannot.
- `python tools/memory.py --paths tools/bench.py .claude/settings.json
  .claude/hooks/post-tool/01-context-cost.py
  .claude/skills/executing-plans/SKILL.md
  .claude/skills/verifying-work/SKILL.md` → 30 entries, all directory-level
  except `decisions/2026-07-30-direct-hook-registration.md` (names
  `.claude/settings.json` directly) and `decisions/2026-08-04-hooks-never-
  name-a-skill.md` (names its directory). Both read in full:
  - `2026-07-30-direct-hook-registration.md`: register the new hook directly
    against its event in `settings.json`, self-filtering on `tool_name`
    inside the script — exactly the pattern `01-context-cost.py` already
    uses. No dispatcher, no adapter.
  - `2026-08-04-hooks-never-name-a-skill.md`: the ban is on a hook *naming a
    skill in anything it emits* (its stdout/stderr/JSON output reaching the
    session), enforced by AST-scanning literal string constants; state-file
    writes and docstrings are outside its scope. The new hook writes a
    skill's name to a JSON state file, never to stdout in the normal case —
    consistent with the decision's actual mechanism, not just its title.

## File map

- Create: `.claude/hooks/post-tool/02-skill-cost.py` — counts `Skill` tool
  invocations and estimates cumulative `SKILL.md` chars loaded, mirroring
  `01-context-cost.py`'s shape.
- Modify: `.claude/settings.json` — register the new hook under `PostToolUse`,
  matcher `"Skill"`.
- Modify: `tools/bench.py` — read the new state file and add one report line,
  next to the existing `session_calls()` line.
- Modify: `tools/test_hooks.py` — regression cases for the new hook (synthetic
  payloads: known field name, fallback field names, no matching field, missing
  skill file).
- Modify: `.claude/skills/executing-plans/SKILL.md` — one sentence scoping the
  `spec-reviewer` dispatch.
- Modify: `.claude/skills/verifying-work/SKILL.md` — one sentence scoping the
  `test-verifier` dispatch.

## Progress
- [x] Task 1 — skill-body-load counter in a new hook, reported by `bench.py`
- [ ] Task 2 — scope `spec-reviewer`/`test-verifier` dispatch prompts

## Tasks

### Task 1: Skill-body-load counter, reported by `bench.py`
**Purpose:** make the ~26K-token cumulative cost of loading full `SKILL.md`
bodies across a chain visible, the way `01-context-cost.py` already makes
Bash/PowerShell input cost visible — currently nothing measures it.
**Files:**
- Create: `.claude/hooks/post-tool/02-skill-cost.py` — `WATCHED = ("Skill",)`;
  on a matching payload, look up the invoked skill's name from
  `tool_input` trying keys `("skill", "skill_name", "name")` in order; if
  found, resolve `.claude/skills/<name>/SKILL.md`'s byte size (0 if the file
  does not exist — a stale/renamed skill name is itself worth surfacing, not
  hidden); accumulate into
  `.claude/hooks/state/skill-cost.json` as `{"calls": int, "chars": int,
  "unattributed": int}` — `chars` sums resolved file sizes,
  `unattributed` counts invocations where no candidate key was found. Silent
  by default (no `print()`), matching `01-context-cost.py`'s reporting
  posture — this is a counter, not a warning.
- Modify: `.claude/settings.json` — add a `PostToolUse` entry, `"matcher":
  "Skill"`, pointing at the new hook, placed after the existing `Bash|
  PowerShell` entry in the same array.
- Modify: `tools/bench.py` — add `skill_body_cost()` mirroring
  `session_calls()`'s shape (reads the new JSON state file, returns
  `(calls, chars, unattributed)` or `None` if the file is absent); one new
  printed line in `main()` alongside the existing shell-call report, same
  "not yet recorded" fallback message style for a fresh session.
- Modify: `tools/test_hooks.py` — synthetic payload cases: `{"tool_name":
  "Skill", "tool_input": {"skill": "no-slop"}}` resolves
  `.claude/skills/no-slop/SKILL.md`'s real size; `{"skill_name": "no-slop"}`
  and `{"name": "no-slop"}` both fall back correctly; `{"tool_input": {}}`
  (no candidate key) increments `unattributed`, not `calls` alone silently;
  `{"skill": "does-not-exist"}` resolves to size 0, not an error.
**Dependencies:** none
**Implementation notes:** Mirror `01-context-cost.py`'s `_load()`/`_save()`
pair exactly (same `json.loads`/`OSError` guard shape) rather than inventing
a new persistence pattern. `MAX_ENTRIES`-style bounding does not apply here —
this state file holds one running total, not per-call fingerprints, so it
cannot grow unbounded the way `call-fingerprints.json` can.
**Known limitation, stated rather than hidden:** whether the `Skill` tool
fires `PostToolUse` at all, and whether `tool_input`'s field is really
`"skill"`, is **not verified live** in this session — confirmed empirically
that `.claude/settings.json` changes need a fresh session to take effect, so
this can only be unit-tested against synthetic payloads here. Verification
below separates what this session proves (the hook's own logic, given a
payload) from what it cannot (whether Claude Code ever sends that payload).
**Rollback:** revert the commit; `.claude/hooks/post-tool/02-skill-cost.py`
and its `settings.json` registration disappear together;
`.claude/hooks/state/skill-cost.json` (if created) is untracked/gitignored
state, not committed.
**Preconditions:** none.
**Verification:**
- Run: `python tools/test_hooks.py`
- Expect: exit 0, including the 4 new synthetic cases above (known field,
  two fallback fields, no field, missing skill file) all passing.
- Run: `echo '{"tool_name":"Skill","tool_input":{"skill":"no-slop"}}' |
  PYTHONIOENCODING=utf-8 python .claude/hooks/post-tool/02-skill-cost.py`
  then `cat .claude/hooks/state/skill-cost.json`
- Expect: `{"calls": 1, "chars": <no-slop's real SKILL.md byte size>,
  "unattributed": 0}` — a real fire against a real payload, not just the
  suite.
- Run: `python tools/bench.py`
- Expect: a new line reporting the skill-body-load total, in the same shape
  as the existing shell-call line.
- **Not verified by this task, named rather than skipped:** whether Claude
  Code's real harness sends a `Skill`-named `PostToolUse` event with a
  `"skill"` field. First fresh session after this lands should show a
  non-zero `bench.py` skill-cost line; if it stays at zero after several
  real skill invocations, the field-name guess (or the event-firing
  assumption itself) was wrong and this needs revisiting with real data
  instead of another guess.
**Done when:** the hook's own logic is proven correct against every payload
shape this session could construct, `bench.py` reports the new metric or its
absent-state fallback, and the live-firing question is explicitly flagged
as open rather than asserted either way.

**Executed, one deviation found and fixed by the hook-self-test-nudge itself:**
first fire against a real payload (`{"skill":"no-slop"}`) returned `chars: 0`
instead of the real 13,174 — `SKILLS_DIR` was built as
`parents[2] / ".claude" / "skills"`, but `parents[2]` from
`.claude/hooks/post-tool/` already resolves to `.claude` itself, so the path
doubled to `.claude/.claude/skills` (nonexistent). Fixed to
`parents[2] / "skills"`, re-fired, confirmed `chars: 13174` matching
`wc -c .claude/skills/no-slop/SKILL.md` exactly. `python tools/test_hooks.py`:
all 6 new cases green (`All hook tests passed`). `python -m mypy
.claude/hooks/post-tool/02-skill-cost.py tools/bench.py tools/test_hooks.py`:
clean. `python tools/bench.py`: new line printed, populated by the suite's own
synthetic firings (`this session's skill-body loads: 10 (79,044 chars, ~19,761
tok) (2 unattributed)`) — proves the hook-to-report pipeline end to end at the
unit level; the live-firing question (does Claude Code's real harness send
this payload shape) remains explicitly open, as designed.

### Task 2: Scope `spec-reviewer`/`test-verifier` dispatch prompts
**Purpose:** stop the two independent-review dispatches from each redoing
~70% of the same work (both re-ran the same 5 test suites and read
overlapping diffs this session, 112,743 combined tokens) by telling whoever
composes each dispatch prompt what the *other* stage already covers.
**Files:**
- Modify: `.claude/skills/executing-plans/SKILL.md` — the sentence "Before
  that handoff, dispatch `spec-reviewer` when the implementation has an
  approved spec or material acceptance criteria" (in `## Next step`) gains
  one clause naming its scope: check plan-vs-diff compliance, not re-run the
  test suites (that is `verifying-work`'s `test-verifier`, dispatched next).
- Modify: `.claude/skills/verifying-work/SKILL.md` — the sentence "For
  material changes, dispatch `test-verifier` before declaring the result
  verified" (in the dedicated paragraph under "What proves what") gains one
  clause: it owns re-running the suites and the red-green proof;
  `spec-reviewer`'s plan-compliance check, if one already ran this unit, is
  not this dispatch's job to repeat.
**Dependencies:** 1 (both tasks touch no shared file, but sequencing keeps a
single, reviewable diff order — this task's edits are independent of
Task 1's and could run first or in parallel; declared as depending on it only
because Task 1 is listed first in this plan, not because of a real ordering
constraint. `tools/parallel_groups.py`, run below, is the actual authority on
this.)
**Implementation notes:** One added clause per file, not a restructure — both
skills already dispatch the right subagent for the right reason; the gap is
that neither dispatch prompt (composed fresh each time, per
`executing-plans`'s own "Give each agent... the plan's constraints" guidance)
was ever told to exclude the other stage's coverage. This session's own two
dispatch prompts are the concrete evidence: `spec-reviewer`'s prompt asked it
to "verify every task's Verification command actually passes... re-run
`python tools/test_entry_classifier.py`..." — full test re-execution, which
`verifying-work`'s subsequent `test-verifier` dispatch then also did in full,
independently.
**Rollback:** revert the commit; both files return to their prior wording,
no behavior change beyond prose.
**Preconditions:** none.
**Verification:**
- Run: `python tools/test_process_router.py`
- Expect: exit 0 — confirms neither skill's routing/dispatch structure broke
  (this suite validates skill frontmatter, successor names and dispatch
  tables; a prose addition inside an existing paragraph must not change any
  of those).
- Run: `python tools/new_skill_check.py --all`
- Expect: exit 0 — both files stay within frontmatter/structural limits.
**Done when:** both files name the split explicitly, `git diff` shows only
the one added clause per file (no restructuring), and the full suite is
still green.

## Constitution gate
- [x] I Evidence — every task names the exact command and the expected output
- [x] II Test first — Task 1's synthetic cases are written and run red before
  the hook exists; Task 2 has no new behavior to test-first (prose-only),
  covered instead by the existing structural suites re-run after
- [x] III Smallest change — bottlenecks #1 and #4 deliberately get no task;
  Task 1 mirrors an existing hook's shape rather than inventing a new one;
  Task 2 adds one clause per file rather than restructuring either
- [x] IV Reversibility — both tasks are additive commits with a one-line
  revert; no migration, no persisted state beyond a disposable counter file
- [x] V No silent degradation — Task 1's live-firing uncertainty is stated
  in its own "Known limitation" and Verification, not asserted as working
- [x] VI Mechanism — Task 1 is a real counter with real tests; Task 2's rule
  ("don't duplicate the other stage's coverage") is enforced by naming it
  inline in the exact sentence a future dispatcher reads, the same
  enforcement shape `executing-plans`/`verifying-work` already use for every
  other dispatch instruction in those files
- [x] VII Secrets — no credential enters the repo

## Complexity tracking
(none — all seven articles ticked)

## Out of Scope, and why (the other 2 of the 4 bottlenecks)

- **Bottleneck #1 (redundant full-tier reruns).** No task. Verified both
  `executing-plans/SKILL.md` and `verifying-work/SKILL.md` already carry the
  "cheapest tier" guidance this bottleneck's original fix would have
  restated. The real causes were a branch inheriting unrelated commits
  (making `--scoped` refuse with `major`) and this agent's own inconsistent
  adherence — neither fixable by adding prose that already exists. Worth a
  `knowledge-manager` note after this lands, not a `.claude/` change.
- **Bottleneck #4 (response verbosity).** No task, per the original audit's
  own conclusion — behavioral, and no enforcement mechanism was proposed or
  is proposed now. Inventing one (e.g. a hook that counts my own output
  length) would add exactly the kind of always-on tax this whole unit is
  trying to reduce, to catch something that self-correction already fixes
  once named.
