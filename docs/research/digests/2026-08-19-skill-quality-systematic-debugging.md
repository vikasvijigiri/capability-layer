# How does `systematic-debugging` compare to a real repo's equivalent?

**Asked because:** the same pass just run for `writing-plans` against
affaan-m/ECC's `commands/plan.md` found real gaps and real strengths on both
sides; `systematic-debugging` is next due the same scrutiny.

**Comparables (two, different scope):**

1. [SethGammon/Citadel](https://github.com/SethGammon/Citadel) (905 stars, 83
   forks, active) — `skills/systematic-debugging/SKILL.md` (full, ~100 lines).
   Same skill name, same purpose (an "operating layer for Claude Code +
   OpenAI Codex" — the closest project-shape match found), general root-cause
   debugging of any failure.
2. [affaan-m/ECC](https://github.com/affaan-m/ECC) (star-rated, public,
   active) — `skills/agent-introspection-debugging/SKILL.md` (full, ~120
   lines). Narrower scope: only agent-run failures (tool loops, context
   drift, env mismatch), not general code bugs — but the closest match for
   our own "Failure capture" / "Agent Self-Debug Report" templates, whose
   field names are near-identical to ECC's.

ECC has no generic root-cause-debugging skill; its per-language
`agents/*-build-resolver.md` files and `agents/silent-failure-hunter.md` are
narrower (build-fix only, or code-review for swallowed errors) and were ruled
out as non-matches.

Read in full: our `SKILL.md` (209 lines incl. frontmatter), Citadel's
`SKILL.md`, ECC's `agent-introspection-debugging/SKILL.md`.

**Verdict:** ours has the stronger methodology (an analog-comparison phase
neither comparable has) and the only durable, cross-session record; Citadel
has a sharper done-checklist and a "check for recurrence elsewhere" step
ours lacks; ECC has a symptom-to-cause lookup table and a worked
good/bad-pattern contrast ours lacks for the agent-failure case.

## Gaps in ours (with fixes)

**No "check for related occurrences" step.** Citadel's Phase 3 explicitly
asks, once root cause is confirmed: "Is this pattern used elsewhere? Could
the same bug exist in similar code?" and requires fixing those too. Our
Phase 4 goes straight from one fix to `ISSUES.md` with no instruction to
search for the same bug pattern elsewhere. *Fix:* add a step to Phase 4 —
"search for the same assumption or boundary elsewhere; fix or document each
instance found" — before "Record it in ISSUES.md."

**No symptom-to-cause lookup table for agent-run failures.** ECC's Phase 2
pairs concrete signatures (`ECONNREFUSED`/timeout, `429`/quota exhaustion,
"file missing after write") each with a likely cause and a one-line check.
Our "Silence is the usual symptom" section names failure categories in prose
but gives no such table. *Fix:* add a 4-6 row table under that section
mapping this repo's own recurring signatures (hook fails open, description
silently vanished, `UnicodeEncodeError` from missing `PYTHONIOENCODING`) to
their check.

**No documented fringe cases.** Citadel has an explicit section for bug is
intermittent, two fix attempts already failed, no test framework exists, and
error is in a dependency/generated file (with the answer: don't modify the
dependency, propose a workaround in the consuming code). Ours has no
equivalent — Phase 4 step 1 just says "write the failing test first" with no
stated exception path. *Fix:* add 2-3 fringe-case notes, especially the
dependency/vendored-code case and the no-test-harness case.

**No worked good/bad-pattern contrast for recovery actions.** ECC's Recovery
Heuristics explicitly names a bad pattern ("retrying the same action three
times with slightly different wording") against a good sequence (capture,
classify, one direct check, retry only if it supports the plan). Our
"Red Flags" section lists anti-pattern phrases but never pairs one against
the correct sequence side by side. *Fix:* add one such contrast under Red
Flags, reusing an actual incident from `ISSUES.md` if one fits.

## Where ours is ahead

**The only durable, cross-session record.** `ISSUES.md` (symptom, diagnosis,
every attempt with outcome, fix, status) persists across sessions per
`knowledge-manager`'s format. Citadel's "Exit Protocol" is a single
in-conversation `---HANDOFF---` block with no file it writes to — the failed
attempts its own philosophy claims to value ("prevents fix cascades") are
not actually saved anywhere the next session can read.

**Phase 2 — Pattern is a technique neither comparable has.** Find a working
analog elsewhere in the codebase, read it completely, list every difference.
Citadel jumps straight from reproduction to hypothesis with no instruction to
look at how similar, working code differs. ECC's protocol is scoped to agent
failures only and has no code-comparison step either.

**A real anecdote grounds a principle; both comparables are pure procedure.**
"Test the test before you trust it" recounts an actual incident (a gate test
reporting false failures from text-mode CRLF rewriting, not a code bug) as
evidence for "make the harness byte-exact before trusting its verdict."
Neither Citadel nor ECC's document contains a single concrete incident —
both are entirely prescriptive.

## One line

Ours diagnoses more rigorously and remembers what it found; Citadel is
better at defining "done" and catching recurrence, ECC is better at mapping
agent-failure symptoms to causes — porting three or four of their
checklist/table habits in costs little and closes the gaps above.
