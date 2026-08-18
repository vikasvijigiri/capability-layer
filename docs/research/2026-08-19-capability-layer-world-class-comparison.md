# Is capability-layer world class, verified against real public repos?

**Asked because:** the user wants a rigorous, line-by-line verified verdict, not
an impression, on whether this repo's Claude Code governance layer is
"world class," benchmarked against real GitHub repositories.

**Verdict:** No single number answers this honestly, because the repos found
are not one category. Against **deepseek-harness** (a full agent runtime, a
different kind of project) our layer cannot and should not be compared on
scale. Against the repos that actually *are* our category — a governed
`.claude/` skills+hooks+approval layer — our layer is **more rigorously
self-tested than any comparable repo found** (verified test suite that builds
and installs its own artifact, deterministic hook classification, a gate
mechanism pinned by its own test), but it is a **17-day-old, single-contributor,
unstarred private repo** with zero external users and one confirmed real defect.
"World class" implies proven at scale; this has not been exposed to scale yet.

## Sub-questions

### 1. Does our own test suite run green on real invariants, and are there remaining aspirational-vs-real gaps?

**Finding, high confidence** (verified by running the suite twice, fresh, in
this session): `python tools/run_checks.py --tier all --require-test` resolves
**37 checks, 33 pass**. Quoted output:

```
tier=all  resolved 37 check(s)
FAIL: test `python tools/test_process_router.py`: FAIL: at least one agent exists
FAIL: test `python tools/test_artifact_autocommit.py`: FAIL: commits the rest of the turn
FAIL: test `python tools/test_project_checks.py`: FAIL: ...and the failure names the command -- nothing ran -- test (`C:\Users\Vikas` not installed)
FAIL: test `python tools/test_install.py`: test_install.py: error: argument --upgrade: not allowed with argument --uninstall
```

Verified via `git stash` that **all four failures pre-exist on unmodified
`main`** — none are introduced by this session's edits. Root cause traced for
two:
- `pyyaml` is not installed in this dev environment (`ModuleNotFoundError: No
  module named 'yaml'`, confirmed directly) — an environment gap, not a repo
  defect, though `pyproject.toml:18` declares it a *hard* dependency the dev
  environment here doesn't satisfy.
- **A real, previously-unknown defect**, traced to source:
  `.claude/hooks/_projectchecks.py:334` and `:407` do `parts = command.split()`
  on a raw whitespace split to extract an executable name for
  `shutil.which()`-based "tool not installed" detection. This repo's own
  absolute path (`...\Vikas Vijigiri\...`) contains a space, so any check
  command embedding a quoted absolute path breaks the split, producing a
  garbage token and a false "not installed" / failure. This is exactly the
  class of defect the layer's own philosophy warns against (`CLAUDE.md`:
  "Prefer deterministic mechanisms") — the mechanism itself isn't fully
  deterministic on Windows paths with spaces.

**Aspirational-vs-real gap, high confidence, already remediated this session**:
`AGENTS.md`'s "Runtime model" section described a repository runner with
`--host-managed`/`--dry-run`/`--sdk-live` flags. Verified no such runner exists
anywhere under `tools/` (grep for the flags found only two test files
asserting the *strings*, not an implementation). Fixed in this session; a new
assertion in `tools/test_harness_contract.py` (`manifest does not claim an
unbuilt runner`) now guards against recurrence, mirroring the repo's existing
precedent of leaving `workflows` deliberately absent from `harnesses.json` for
the same reason. **I did not find a second instance of this pattern elsewhere**
after checking `harnesses.json`, `workflow.md`, and `.claude/hooks/README.md`
directly — but this was not an exhaustive line-by-line audit of every skill
file, so absence-of-a-second-instance is medium confidence, not high.

### 2. How rigorous is deepseek-harness's actual testing, verified by reading the scripts/docs, not the README?

**Finding, high confidence** (read `docs/testing.md` in full, 71 lines,
verified via `mcp__github__get_file_contents`, not a search snippet): the
policy is materially more rigorous than ours on one specific axis — **per-file
100% line coverage enforced as a CI gate** (`pnpm run test:coverage`) across
every package's `src/`, with an explicit philosophy that an uncovered line is
"often dead code the gate is correctly flagging for deletion, not a missing
test to bolt on." They also run **real-API end-to-end tests against a live
model** ("we are DeepSeek — do not ration real-API tests"), keyless snapshot
tests for every model-visible behavior change, and a browser-snapshot CI gate.

Their stated first principle — **"Verify the world, not the self-report... a
keyword probe on the agent's own output lets a cheating agent pass. Assert
untouched files are byte-identical."** — is the same principle our own
`CLAUDE.md` states ("Validate, don't assume. Never report a check as passing
unless you ran it and can quote its output") and that `tools/test_package.py`
implements concretely (it builds a real wheel, installs it into a real venv
and a real synthetic target repo, and re-runs that target's *own* test suite
against the installed artifact — not a mock of installation). **Independently
arrived-at, structurally identical philosophy**, verified on both sides by
reading the actual scripts/docs, not by taking either repo's word for it.

Where deepseek is unambiguously ahead: coverage measurement (we have none —
our suites are pass/fail, not line-coverage-gated) and real-API e2e (we have
no equivalent, by design, since this layer never calls a model directly).
Where the comparison is not meaningful: their scale (dozens of TypeScript
packages, a shipped runtime) makes 100%-line-coverage tractable and valuable
in a way it would not obviously be for `.claude/hooks/*.py`'s exception-swallowing,
stateless scripts.

### 3. Do other real, comparable "Claude Code governance layer" repos exist, and how do they compare structurally?

**Finding, high confidence**, three verified via direct file-tree and file
reads (not README summaries):

| Repo | Verified via | Structure found |
|---|---|---|
| [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) | root tree + `docs/testing.md` read in full + 10 commits read | Full agent runtime, not a governance layer over an existing one. Different category. |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | root tree + `tests/` directory listing | **The closest real comparable to "harness-agnostic capability layer."** Root has dot-directories for essentially every coding-agent product (`.claude`, `.codex`, `.cursor`, `.gemini`, `.hermes`, `.kimi`, `.kiro`, `.openclaw`, `.opencode`, `.pi`, `.qwen`, `.trae`, `.zed`) plus `skills/`, `hooks/`, `agents/`, `commands/`, `workflows/`, `rules/`. Crucially, **it ships per-adapter tests** — `tests/codex-config.test.js`, `tests/codex-native-hooks.test.js`, `tests/opencode-config.test.js`, `tests/opencode-plugin-hooks.test.js`, `tests/opencode-tools.test.js`, plus a 34KB `tests/plugin-manifest.test.js` — i.e. it does not just *assert* harness-agnosticism in a manifest the way our `harnesses.json` currently does; it has automated tests proving each adapter's config is structurally valid. **This is a genuine capability gap in our layer**: we test that `harnesses.json` *declares* Codex/Gemini/VS-Code paths correctly; we have no test that exercises what a Codex or Gemini session would actually see. |
| [philoserf/claude-code-config](https://github.com/philoserf/claude-code-config) | root tree + `hooks/` directory read | Honest, small, explicitly labeled "reference, not a starter template." Four hooks, all simple logging/notification (`log-skill-use.sh`, `notify-agent.sh`) — no enforcement/deny logic, no approval-gate concept, no test suite found. Different ambition tier from ours; not a fair "world class" comparison target, but a useful floor. |

**What this means here**: our repo's genuinely distinguishing feature —
deterministic enforcement hooks with a classified contract (detect drift /
enforce safety / record state / never author strategic content, per
`capability-layer-maintenance/SKILL.md`) and two hard `AskUserQuestion` approval
gates pinned by `test_process_router.py` — **was not found, as a tested,
verified mechanism, in any of the three repos above**. philoserf's hooks are
purely observational; ECC's hooks were not read in enough depth this pass to
rule out an equivalent (its `hooks/` and `plugins/` directories exist but
weren't opened — **[UNVERIFIED]**, flagged rather than assumed). This is the
single strongest evidenced claim in our favor, and it comes with an explicit
caveat about what wasn't checked.

### 4. What do verified maintenance/activity signals say about each, checked via the GitHub API?

**Finding, high confidence**, all four numbers pulled live via
`mcp__github__search_repositories`, not estimated:

| Repo | Stars | Forks | Open issues | Created | Contributors seen | Notes |
|---|---|---|---|---|---|---|
| deepseek-ai/deepseek-harness | 159,743 | 16,685 | 0 | 2026-08-13 (5 days old) | 4 distinct logins in 10 commits | **[UNVERIFIED anomaly]**: `created_at` postdates internal doc citations (`docs/testing.md` links notes dated `2026-06-19`, `2026-07-24`) it should predate if the public repo were the original history. Consistent with "open-sourced as one push after months of private work," but not confirmed either way. `open_issues_count: 0` at this scale is also atypical and unverified as to cause (disabled vs. aggressively triaged vs. API artifact). Real, coherent release train to `dsh@0.1.0-rc.7` and real distinct contributor logins are independently confirmed and not in question. |
| affaan-m/ECC | 240,906 | 36,540 | 135 | 2026-01-18 (~7 months old) | not sampled this pass | Growth curve over 7 months is large but not physically anomalous the way deepseek's 5-day figure is. Real, substantial `tests/` tree confirmed directly. |
| philoserf/claude-code-config | 13 | 0 | 0 | 2025-12-31 | 1 (personal repo) | Small, honest, actively maintained (`updated_at: 2026-08-17`). |
| **This repo** | 0 (private) | 0 (private) | n/a | first commit 2026-07-31 | **1** (`vikas.v@ngenux.com`) | `git log --all` (all branches, not just merged `main`): **89 commits over 17 days** (2026-07-31 → 2026-08-16). Not publicly visible or forkable — cannot be starred, cannot be independently used or challenged by anyone outside this session. |

**What this means here**: on every external-validation axis — stars, forks,
issue volume from real strangers, independent contributors, wall-clock time
survived — this repo is at the very bottom of the comparison set, by a wide
margin. That is not a quality judgment (a private 17-day solo project cannot
be expected to have GitHub stars), but it is the single fact that most directly
contradicts an unqualified "world class" claim: nobody outside this
conversation has used this, broken it, or extended it yet.

### 5. Governance-gate design — verified structurally, not from either side's own claims

**Finding, medium confidence** (grounded in `CLAUDE.md`, `test_process_router.py`'s
described behavior, and the three external repos' verified file trees, but not
a full read of every external hook/skill file): our two-gate design —
exactly two `AskUserQuestion` approval points in the entire chain, each marked
by a `<!-- GATE n: ... -->` comment a test greps for, with a documented
rejection-durability mechanism (`## Rejected <date> (plan <hash>)` appended
verbatim, re-presentation blocked on unchanged hash) — is a **specific,
enforced, tested invariant**. None of the three external repos were found to
have an equivalent structural concept during this pass: deepseek-harness's
gates are human PR review and CI, not an in-agent approval-question mechanism
(different problem, since it's not primarily driven by a single agent's
in-session actions the way this layer is); ECC and philoserf's repos show no
equivalent in their root-level file trees. **This is the layer's most
defensible specific claim to distinction** — narrowly scoped, but verified
against what actually exists in each comparison repo rather than assumed.

## Disagreements

None of the sources directly disagree — no two repos made opposing claims
about the same fact. The tension is in the **framing**: deepseek-harness's own
material implicitly frames "world class" as scale + coverage rigor + real-API
verification; this repo's own `CLAUDE.md` implicitly frames it as
determinism + gate integrity + self-testing installability. Both are
internally coherent; they are not measuring the same thing, which is why a
single blended score would misrepresent both.

## Not adopted

- **Did not treat any repo's star count as a quality signal on its own** —
  ECC's 240K stars and deepseek's 159K/5-days figure are reported as observed,
  with the second flagged as an unverified anomaly, specifically because
  hit-count/star-count is not evidence of engineering quality per this skill's
  own discipline.
- **Did not open ECC's `hooks/`, `plugins/`, or `skills/` directory contents**,
  nor philoserf's `skills/` or `rules/` — the file-tree-level evidence already
  answered the structural sub-questions this pass scoped to; a claim about
  what's *inside* those files is intentionally left unmade and flagged
  `[UNVERIFIED]` above rather than assumed favorable or unfavorable.
- **Did not re-verify deepseek-harness's core runtime architecture** (agent
  loop, plugin system) — covered in this session's earlier comparison turn and
  out of scope for this pass, which was scoped to the "world class" evidence
  question specifically.

## Sources

- [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) — root tree, `docs/testing.md` (read in full), 10 most recent commits
- [affaan-m/ECC](https://github.com/affaan-m/ECC) — root tree, `tests/` directory listing, repo metadata via API
- [philoserf/claude-code-config](https://github.com/philoserf/claude-code-config) — root tree, `hooks/` directory listing, repo metadata via API
- This repo: `python tools/run_checks.py --tier all --require-test` (run twice, fresh), `git stash`-verified baseline, `.claude/hooks/_projectchecks.py:334,407` (read), `git log --all` (read), `pyproject.toml:18` (read)
