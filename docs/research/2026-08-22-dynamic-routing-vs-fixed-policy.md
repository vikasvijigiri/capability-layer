# Should this layer's routing become fully dynamic/autonomous instead of policy-driven?

**Asked because:** the user wants skill/workflow routing decided by the model
on the spot, gated only at Gate 1 (`ExitPlanMode`) and Gate 2
(`AskUserQuestion`), rather than what they perceive as a fixed policy that
burns tokens on unrelated or small tasks — and wants this checked against the
Notion "Agentic Workflows (IDE)" objectives and external prior art before
anything is built.

**Verdict:** The layer already implements the core of what was asked —
hooks never invoke a skill; the model alone decides, per
`decisions/2026-08-04-hooks-never-name-a-skill.md` and confirmed against
Anthropic's own Agent Skills spec. What is NOT dynamic, and is the real
source of the token burn, is three separate, already-diagnosed
implementation gaps: (1) no session-level skill-body cache — 209 reloads
cost ~376K tokens in one session, (2) an unconditional ~4,661-token
skill/command/agent listing every turn, (3) an unenforced knowledge-doc
length cap letting `LOG.md`/`ISSUES.md` balloon. None of these need a
"more dynamic" redesign — they need the Anti-Repetition Layer the Notion
spec already names (§10) and the layer does not yet have.

## Findings

### Sub-question 1: Does this repo already let the model decide skill invocation, or does a fixed policy force it?

**High confidence.** `decisions/2026-08-04-hooks-never-name-a-skill.md`
records that an earlier hook did pick skills by keyword table, was pointed
at a fabricated skill name, and every validating suite still passed — so it
was deleted. `.claude/hooks/prompt-intake/01-entry-classifier.py:27-31`
states in its own docstring: *"A hook cannot invoke a skill... No hook
output does that; the capability does not exist."* It only renders an
advisory `[state:<key>]` block from `workflow.md` and predicts an E0-E5
execution level — both are reports, never gates. `01-entry-classifier.py`
also quotes Anthropic's own framing directly: *"the model choosing to run a
formatter is different from the formatter running automatically."*
Independently confirmed against the primary source
(`mintlify.wiki/anthropics/skills/spec/loading-system`, fetched this pass):
Anthropic's canonical Agent Skills loading system is explicitly
model-driven — metadata (~50-200 words/skill) stays resident, the model
itself decides when a skill's full body loads, and nested references load
only as the model's own reasoning reaches for them. No external router.

**This repo's design already matches the target pattern the user is
describing.** The two hard gates (`ExitPlanMode`, `AskUserQuestion`) are
the only enforced stops — everything else, including the E0-E5 estimate
and the "entry check" nudge, is advisory text the model is free to weigh
or ignore.

### Sub-question 2: If it's already dynamic, why does it feel like a rigid policy that burns tokens on small tasks?

**High confidence, three separate causes, each independently measured this
session (see prior turn's telemetry read of `.claude/hooks/state/telemetry.jsonl`
and `tools/bench.py`):**

1. **No skill-body cache.** `bench.py` reported 209 skill-body loads this
   session totalling 1.46M chars (~376K tokens) against only 144KB
   (~36K tokens) of actual SKILL.md content on disk — the same handful of
   skills reloaded in full repeatedly. Notion §10 ("Anti-Repetition Layer")
   names exactly this as a first-class component — "Has this been done? →
   REUSE" — and it does not exist here. This is a build gap, not a design
   disagreement.
2. **Unconditional per-turn listing.** `bench.py` charges ~4,661 tokens
   every turn for the skill/command/agent description listing regardless
   of task size. `TASK.md`'s S1 entry already names this "deliberately
   unpaid." Anthropic's own spec budgets ~50-200 words (~65-260 tokens) per
   skill for this exact metadata; several of this repo's 14 descriptions
   carry long explicit trigger-phrase lists that push past that band.
3. **Doc-bloat backlog.** `tools/test_doc_entries.py`'s own docstring
   admits *"Nothing enforced it. Measured 2026-08-12: LOG's median entry
   was 39 lines against a cap of 15... ISSUES ran 24 against 12."* Both
   files are re-read whole at session boundaries; only new, uncommitted
   entries are checked, so the backlog can only grow, never shrink.

A fourth, softer cause: the entry-classifier's "entry check" block fires on
every prompt matching a task shape and reads as an instruction to follow
`workflow.md`'s stage table, even though nothing enforces it. Nothing
blocks on it, but the *presentation* is prescriptive — this is very likely
what reads as "policy that must be followed," separate from the token cost.

### Sub-question 3: What does external, well-regarded prior art say about dynamic vs. fixed routing?

**High confidence, two independent primary sources, both fetched in full
this pass, not taken from search snippets:**

- Anthropic, "Effective context engineering for AI agents"
  (anthropic.com/engineering/effective-context-engineering-for-ai-agents):
  *"smarter models require less prescriptive engineering, allowing agents
  to operate with more autonomy"* — framed as a spectrum tied to model
  capability, with "do the simplest thing that works" as the operating
  rule. No universal token-budget number is given.
- Anthropic Agent Skills spec (loading-system doc, fetched via mintlify
  mirror): confirms the model-driven trigger design above.
- `SkillRouter` (github.com/zhengyanzhao1997/SkillRouter, cited from a
  search result, **not opened this pass — [UNVERIFIED]**): claims that at
  large-scale (~80K skills), metadata-only routing breaks down and the
  full skill body becomes the decisive signal — i.e. dynamic routing has a
  real scaling cost of its own. Directionally consistent with source 1 but
  not independently confirmed here; flagged rather than relied on.

**Grounded here:** nothing in the primary sources argues for *removing*
policy/workflow text — the recommendation is against *over-prescribing*
relative to what the model already handles well, and for keeping metadata
tiny while letting the model pull in detail on demand. This repo's
mechanism already does that; its metadata is merely oversized and its
bodies are being re-fetched instead of cached.

### Sub-question 4: What do the Notion objectives actually require, and does more autonomy conflict with any of them?

**High confidence — read the full page directly, not a summary.** Nothing
in the 30 objectives or 25 sections asks for *less* structure; several ask
for the opposite of "fully autonomous, no fixed policy":

- §7 Hook rule: *"If a deterministic program can enforce it, prefer a
  hook/tool over LLM reasoning."* — the reverse of "let the model decide
  everything."
- §25 principle 5: *"Hooks enforce deterministic invariants"* — a
  categorical split between what a hook does (enforce) and what the model
  does (reason/route), which is exactly this repo's existing spine/limb
  split (`decisions/2026-08-08-policy-spine-workflow-limbs.md`).
- §17 Human Intervention Policy lists narrow, concrete ask-triggers
  (materially ambiguous, irreversible/high-impact, missing
  credentials/permissions, policy requires) — this matches, almost
  verbatim, this repo's existing Gate 1/Gate 2 scope. Loosening beyond
  that is not what the objectives call for.
- §9 names a fixed catalog of exactly 5 workflows (W1 Universal Task, W2
  Change/Feature, W3 Debug/Repair, W4 Research/Investigation, W5 Large
  Delivery) as one of the architecture's own components — a workflow
  *catalog* is itself part of the target, not something the objectives
  want dissolved into pure improvisation.

**Confirmed this repo already has all five**, by the same names, at
`.claude/workflows/{universal-task,change,debug,research,delivery}.md` —
not previously connected to the Notion source in
`docs/research/2026-08-20-notion-objectives-audit.md`, which only checked
catalogue *sizes*, not this specific naming match. Per
`decisions/2026-08-08-policy-spine-workflow-limbs.md`, these are read by
the model (prose, "the model, reading a contract") rather than executed by
a script — a deliberate, reasoned choice (the one prior JS-workflow attempt
put agents in stranded worktrees and was deleted) that still satisfies the
Notion objective's intent (a named, bounded set of paths) without the
literal runtime-engine implementation the diagram implies.

One loose end found, out of scope for this pass: `.claude/workflows/`
also contains `no-slop-sweep.js`, alongside the five `.md` files. Whether
this is live, tested against `test_workflow_contract.py`, or a leftover
from before the 2026-08-08 decision was not checked here — worth a
one-line follow-up, not a redesign.

## Disagreements

None found between the two external primary sources and this repo's own
decisions — both converge on "model decides, metadata stays small, hooks
stay deterministic." The only tension is internal: `TASK.md` calls the
oversized per-turn listing "deliberately unpaid" (i.e., previously
triaged and consciously deferred), while the objectives and the Anthropic
spec both argue it should be smaller. That is a prioritization gap, not a
factual disagreement.

## Not adopted

- **A new autonomous router/classifier was not proposed.** The existing
  one (`01-entry-classifier.py`) already does this job and already reports
  rather than gates; building a second one would duplicate
  `decisions/2026-08-04-hooks-never-name-a-skill.md`'s exact mistake.
- **Rewriting `.claude/workflows/*.md` into an executable engine was not
  considered further.** `decisions/2026-08-08-policy-spine-workflow-limbs.md`
  already tried this once (`execute-rounds.js`), hit a real failure
  (worktrees based on the wrong commit), and deleted it. Reopening that
  needs to reckon with that specific failure, not restate the idea fresh.
- **SkillRouter's ~80K-scale findings were not adopted as a constraint.**
  This layer runs 14 skills, four orders of magnitude below the scale
  where that paper's routing-breakdown claim applies; noted only for
  completeness, not treated as evidence against the current approach.

## Sources

- `decisions/2026-08-04-hooks-never-name-a-skill.md` (read in full)
- `decisions/2026-08-08-policy-spine-workflow-limbs.md` (read in full)
- `decisions/2026-08-09-one-door-into-the-chain.md` (read in full)
- `.claude/hooks/prompt-intake/01-entry-classifier.py` (read in full)
- `docs/research/2026-08-20-notion-objectives-audit.md` (read in full,
  prior pass — reused rather than re-derived)
- Notion page "Agentic Workflows (IDE) — Universal Adaptive SDLC v2"
  (`3b9b1c6b-5e27-81b5-ba18-d753031e068d`, fetched in full this pass)
- Anthropic, "Effective context engineering for AI agents"
  (https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents,
  fetched in full this pass)
- Agent Skills progressive-disclosure loading-system spec
  (https://mintlify.wiki/anthropics/skills/spec/loading-system, fetched in
  full this pass)
- `.claude/hooks/state/telemetry.jsonl` + `python tools/bench.py` output
  (read this session, prior turn)
- `tools/test_doc_entries.py` (read in full, prior turn)
- `ls .claude/workflows/` (this pass — confirmed all 5 files exist)
