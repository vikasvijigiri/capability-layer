---
name: skill-authoring
description: Use when the capability layer needs a new skill - authoring one, or deciding whether it should exist at all. Triggers include "create a skill", "add a new skill", "scaffold a skill", "a skill that does X", "should this be a skill". Do NOT use to audit skills that already exist (no-slop), or to plan product work (task-brief, writing-plans).
effort: high
model: sonnet
---

# Skill Authoring

Create a skill that is actually reachable. Authoring the `SKILL.md` is the easy
half; a skill is **invisible** until five other files know about it, and nothing
errors when they do not — it simply never fires.

Cap visible output at ~500 tokens. The deliverable is the wired skill plus a
quoted checker run, not a tour of what you wrote.

<HARD-GATE>
NEVER create a skill without asking the user where it belongs.

Placement is not a detail you infer. Whether a capability is a numbered stage, an
off-chain entry, or not a skill at all determines the stage numbering of every
skill after it, the handoff diagram, and whether the chain stops dead at its
predecessor. Ask, with `AskUserQuestion`, before writing any file.

NEVER report a skill as created while the checker is red. `tools/new_skill_check.py`
is the gate, and its output gets quoted.
</HARD-GATE>

## Phase 0 — is it a skill at all?

Most requests for "a new skill" are better served by something else, and this is
the cheapest place to find that out. `.claude/workflow.md` puts it plainly:
adding a domain must not add a stage.

| What you have | What it should be | Why not a skill |
|---|---|---|
| Method that differs per platform, per language, per domain | `references/<domain>.md` under the skill that owns the stage | `releasing` carries the shape; Vercel and Fly are pack files. A `if vercel: … elif render: …` skill grows without bound |
| A fixed sequence a human triggers by name | `.claude/commands/<name>.md` | `/verify` and `/save` are procedures, not judgement. Skills are for decisions |
| Something that must happen whether or not the model chooses it | `.claude/hooks/<event>/NN-name.py` | A skill is an *offer*. A hook is a mechanism. CLAUDE.md: prefer deterministic mechanisms |
| Work that fans out over independent items | `.claude/agents/<name>.md` | An agent is a stage's parallelism, not a stage |
| A genuinely unowned stage of the chain | **a skill** | — |

**The test for "genuinely unowned": name the gate nobody owns.** `releasing`
earned its place because `pre-deploy/01-spend-guard.py` had been firing on cloud
CLIs with no skill owning the act it guards. An unowned gate is the clearest
evidence a stage is missing. Absent that, say so and stop — refusing is a
success for this skill, not a failure.

Thirteen process skills is already past the ceiling comparable repos converge on.
Growth belongs in a `references/` pack file under the skill that owns the stage.

## Phase 1 — ask where it goes

You **must** call `AskUserQuestion`. Two questions, and the second only if the
first says it is a skill:

**Q1 — Placement.** Offer exactly these, because they have different blast radii:

- *Off-chain, entered from anywhere* — like `research` and `systematic-debugging`.
  Gets a row in workflow.md's second table. Changes no stage number. **Recommend
  this by default**; it is the cheap option and it is usually right.
- *A numbered stage N* — renumbers every stage from N onward, and every one of
  those skills carries its own `Workflow stage N` line that must move with it.
  Also needs an edge in the handoff diagram and an entry-table row.
- *Not a skill* — one of the four rows in Phase 0. Say which.

**Q2 — Chain position**, only when Q1 says numbered: which stage number, and
therefore which skill's `## Next step` has to start naming it. Name the
predecessor explicitly in the option text; that file is the one people forget,
and forgetting it means the chain silently stops one stage early.

Do not proceed on an assumption. If the user picks "numbered", the renumbering is
part of this task, not a follow-up.

## Phase 2 — write it

Copy `references/TEMPLATE.md` and fill it. The constraints that are actually
enforced, with the number and what enforces it:

| Constraint | Limit | Enforced by |
|---|---|---|
| Directory name equals frontmatter `name:` | exact | `test_process_router.py` — mismatch makes the skill invisible with no error |
| Lives at `<name>/SKILL.md`, never a flat `<name>.md` | — | same; a flat file never appears |
| `description:` states triggers **and** a "Do NOT use" clause | ~380 chars | injected every turn, so it is a recurring cost; breadth belongs in the routing file |
| Whole frontmatter | ≤ 1024 chars | hard spec limit |
| `model:` and `effort:` present | — | `opus` planning/diagnosis · `sonnet` coding/procedure · `haiku` extraction |
| Every skill named in backticks resolves | — | `test_process_router.py`. A name in prose resolving to nothing is this layer's most-repeated defect, and it has shipped past a green suite before |

**Write the "Do NOT use" clause first.** It is what stops the router naming this
skill and its neighbour together, and it is the half people skip.

## Phase 3 — wire it, all five places

Derived by grepping the repo for `brainstormer` and discarding history files.
Miss any one and the failure is silence:

| # | File | What to add | Failure if missed |
|---|---|---|---|
| 1 | `.claude/skills/<name>/SKILL.md` | the skill | — |
| 2 | `.claude/routing/process-skills.md` | `## <name>` heading + one `Keywords:` line | **Build fails.** The only routing signal that survives description truncation |
| 3 | `.claude/workflow.md` | a row — chain table if numbered, off-chain table if not | The chain has an owner nobody can find |
| 4 | `CLAUDE.md` | a row in the Skills table | Invisible to anyone reading the bootloader |
| 5 | the predecessor's `## Next step` | name this skill imperatively | **The chain stops there.** A handoff in a footnote reads as commentary |

Keywords have three mechanical rules, all asserted: **lowercase** (the hook
lowercases the prompt but not the file, so an uppercase keyword can never match),
**no keyword claimed by two different skills**, and **no keyword containing
another skill's keyword** — either makes the router name both for one prompt, which is
worse than naming none because the reader has to arbitrate the job the router
existed to do.

Prefer multi-word phrases lifted from the description's trigger list. Single
words fire on anything.

## Phase 4 — check, then quote it

    python tools/new_skill_check.py <name>
    python tools/test_process_router.py
    python tools/test_referenced_paths.py

The first is scoped to one skill and names the file to edit for each failure.
The other two are the repo's own adjudicators and cover the rest of the layer.

Then **fire the router against a prompt the skill should catch** — a wired skill
whose keywords never match is wired to nothing:

    python tools/run_hook.py pre-run '{"prompt":"<a real phrasing>"}'

Quote the checker's output. "It passes" without the lines is the one thing this
repo's working agreement forbids.

## Red Flags — stop, you are adding a stage that is not there

- "It doesn't fit any existing skill" — first check whether it fits a
  `references/` pack file under one.
- Writing the `SKILL.md` before asking about placement.
- A description with triggers but no "Do NOT use".
- Keywords invented rather than lifted from real phrasings someone would type.
- Renumbering a stage without moving the other skills' `Workflow stage N` lines.
- Reporting done on a green `SKILL.md` and an unedited `process-skills.md`.

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| A flat `.claude/skills/<name>.md` | Never appears, and nothing errors |
| Frontmatter `name:` differing from the directory | Same silent invisibility |
| Skipping the predecessor's `## Next step` | The chain stops one stage early and looks complete |
| Keywords that overlap another skill's | Router names both; the reader arbitrates |
| A skill for a domain rather than a stage | Every project then pays for the domains it does not use |
| Trusting a green suite as proof it is reachable | The suites check structure. Firing the router checks reachability |

## Routing

- Mandatory validator: `tools/new_skill_check.py <name>`, green and quoted.
- Entered from anywhere the layer itself needs changing.
- Terminal handoff: **whatever asked** — the same contract `research` states, and
  the one `.claude/workflow.md`'s off-chain table gives this skill. Off-chain, so
  there is no next stage to name; authoring a capability is not a stage of
  delivering a product.
- A new skill is a hard-to-reverse structural decision and earns a `decisions/`
  record via `knowledge-manager`. That is a consequence of the change, not a
  handoff this skill performs.
- `07-layer-drift.py` fires on a skill being added and names `no-slop`. The sweep
  is that hook's doing, not this skill's — naming it here as a conditional
  successor contradicted the off-chain contract two bullets above, which is the
  orchestration-leakage smell `no-slop` exists to catch.
- **Retiring a skill is not covered here.** Whether that is mechanical or needs a
  human gate is unresolved — `no-slop` classes it structural. See `TASK.md`.
- To install the layer into another repo, that is `/install-layer`, not this.

## Success

The checker is green and quoted, the router names the new skill when fired against
a phrasing a person would actually type, the placement was the user's decision
rather than yours, and all five wiring points were edited in the same change.
