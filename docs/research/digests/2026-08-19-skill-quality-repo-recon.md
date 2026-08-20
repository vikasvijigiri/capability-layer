# Skill quality: repo-recon vs affaan-m/ECC onboarding skills

Comparable: `affaan-m/ECC` (public GitHub repo), `skills/codebase-onboarding/SKILL.md`
(closest match — same trigger space: "onboard me", "walk me through this repo",
first-time codebase mapping). Also read `skills/repo-scan/SKILL.md` as a
secondary candidate — it turned out to be a bootstrap *installer* for a
separate C++/Android/iOS/Web asset-classification tool (third-party vs
project-code auditing), not a general onboarding skill, so it is noted but not
used as the primary comparable. Both read in full via
`mcp__github__get_file_contents`.

## Gaps in ours (`.claude/skills/repo-recon/SKILL.md`, 149 lines)

1. **Zero worked examples.** ECC's skill has three full `User → Action →
   Output` examples plus inline filled-in templates tagged
   `<!-- Example for a Next.js project — replace with detected paths -->`
   (a real Tech Stack table, a real "Where to Look" table). Ours describes
   what each of the 6 map sections must contain in prose only — no sample
   excerpt of a subsystem paragraph, an unfinished-marker line, or a
   candidate-work line. A new session has to infer the exact shape.
   Fix: add one short worked excerpt (3–5 lines) of a `docs/recon/*.md` file
   directly in the SKILL.md.

2. **No literal output skeleton.** ECC's "Output 1: Onboarding Guide" is a
   complete fenced markdown template with every heading spelled out verbatim.
   Ours (Phase 3) only numbers six prose bullets ("What this repository is",
   "Stack and how to run it", …) without showing the actual `##` headings to
   use, so two sessions could format the same six sections differently.
   Fix: add a fenced markdown skeleton with the six headings verbatim.

3. **No shallow-history / no-git fallback.** ECC explicitly handles the edge
   case: "If the repo has no commits yet or only a shallow history (e.g.
   `git clone --depth 1`), skip this section and note 'Git history
   unavailable or too shallow to detect conventions.'" Ours relies on
   `tools/recon.py` for branch/remote/commit state but never states what the
   map should say when that data doesn't exist. Fix: one line under Phase 3
   step 2 or 6 covering the no-history case.

## Where ours is stronger

1. **Deterministic, parallel unit decomposition vs. a single prose pass.**
   Ours dispatches one `repo-cartographer` subagent per subsystem from
   `tools/recon.py --units` — subsystems that are "disjoint by construction,"
   fanned out in a single message so no two agents read the same file — with
   a scripted escalation ladder (`tools/loop.py --agent-status
   NEEDS_CONTEXT/BLOCKED`, "never re-dispatch the same brief to the same
   model"). ECC's Phase 1 only says "run these checks in parallel," meaning
   parallel tool calls inside the *same* context — no subagent fan-out, no
   disjointness guarantee, no escalation protocol for a stuck sub-scan.

2. **Verified-vs-inferred discipline and a mutation ban, both absent in
   ECC.** Every command in our map must be labelled *verified* (ran it) or
   *inferred* (read it in a manifest) — "the difference is whether you ran
   it." We also state explicitly: "Never run install, build, migrate or
   deploy commands to find out what they do... a recon pass that mutates the
   repository it is describing has changed the thing under measurement."
   ECC's closest equivalent is one vague best-practice line, "Verify, don't
   guess — if a framework is detected from config but the actual code uses
   something different, trust the code," with no labeling scheme in its
   output template and no stated non-mutation rule.

3. **Durable artifact wired into an enforced chain, not a standalone,
   often-ephemeral tool.** Ours persists to `docs/recon/YYYY-MM-DD-<repo>.md`
   and has a mandatory "Next step you MUST take": invoking `writing-plans`.
   ECC's own Example 1 says the Onboarding Guide is "printed directly to the
   conversation" — only the derivative `CLAUDE.md` is written to disk — and
   the skill has no required next step; it is a standalone generator with no
   downstream owner.

## Verdict

ECC is more approachable for a first read (worked examples, a literal output
template); ours is more rigorous and harder to game (parallel disjoint
subagent fan-out with an escalation ladder, verified/inferred labeling, a
non-mutation rule, and a durable artifact that mandatorily hands off into the
planning chain) — the fix is to keep our enforcement and borrow ECC's worked
examples and literal skeleton.
