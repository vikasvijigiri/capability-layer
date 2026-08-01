# Process-Skill Routing

Keyword routing for the **unprefixed process skills** — `brainstormer`,
`code-review`, `error-recovery` and the rest. Companion to `capabilities.md`,
which routes only the `<domain>-` prefixed capability skills.

Why this file exists: `capabilities.md` maps keywords to a *name prefix*, so
`02-capability-router.py` can only ever say "skills prefixed `frontend-` are in
the listing". The 33 process skills carry no prefix, belong to no domain, and
were therefore unreachable by the router — the one routing signal that survives
skill-listing truncation could not name them. A physics brainstorm matched
`research` (via "papers") and never surfaced `brainstormer`; that is the failure
this file responds to.

**Format contract.** One `## <skill-name>` heading per entry, matching a
directory under `.claude/skills/` exactly. Exactly one `Keywords:` line beneath
it, comma separated. `tools/test_process_router.py` asserts every heading
resolves to a real skill.

**Keyword style — phrases, not words.** `capabilities.md` can afford single
words because a domain match is cheap and vague. Naming a specific skill is a
stronger claim, so entries here lean on multi-word phrases lifted from each
skill's own `description:` trigger list. A bare word that also appears in a
capability keyword list ("design", "test", "error") is deliberately omitted —
the domain router already covers it, and duplicating it produces two blocks of
injected text for one signal.

`task-intake` is deliberately absent: `03-task-brief-nudge.py` already nudges it
on every prompt, and a second nudge for the same skill is pure noise.

---

## acceptance-verifier

Keywords: does this meet the requirements, check it against the spec, did we build the right thing, verify the acceptance criteria, are we done, does this satisfy the brief, tick off the requirements

## approval-brief

Keywords: is this ok to do, can i go ahead, do you approve, should i proceed, about to ship, ready to push, shall i run it, is it safe to merge

## blueprint-promoter

Keywords: promote to blueprint, make this a blueprint, reusable pattern, we keep doing this, worth generalising, worth generalizing

## brainstormer

Keywords: brainstorm, spitball, bounce ideas, any ideas, what could we do, throw some ideas, thinking out loud, give me some angles, what are our options, help me think this through, i am stuck, im stuck, what if we, ideate, riff on

## business-outcome-review

Keywords: did this solve the problem, did this actually help, was it worth building, did it move the needle, are people using it, meet the goal

## change-summary

Keywords: summarize the changes, summarise the changes, what changed, describe this diff, write the commit message

## code-review

Keywords: review this, code review, check my code, is this ready, can i ship, audit diff, find bugs, pre-commit check, review the diff, look over my changes

## context-economy-audit

Keywords: too many tokens, context is filling up, token bloat, trim the config, sessions feel slower, too many skills, this is expensive

## dependency-upgrade

Keywords: upgrade dependencies, bump packages, update deps, outdated packages, dependency upgrade, newer version of

## design-system

Keywords: design system, design.md, look better, looks off, what font, colour scheme, color scheme, feel more polished, match our brand, spacing looks wrong

## engineering-policy

Keywords: best practice, engineering standards, code standards, policy check, architecture rules, is this good code, over-engineered, definition of done

## error-recovery

Keywords: still failing, nothing i do fixes, going in circles, same error as before, it broke again, tried everything, keeps breaking

## execution-planner

Keywords: plan this out, break this down, write the plan, what order, where do we start, what needs to happen first, give me the steps, how should we approach this

## feasibility-check

Keywords: is this feasible, is this possible, can we even do this, will this work, how hard would it be, is it realistic

## impact-analysis

Keywords: what will this break, blast radius, what depends on this, impact of this change, who uses this, knock-on effect

## knowledge-manager

Keywords: handoff, log this, record this decision, update the docs, where did we get to, note this for later, write down what we decided

## mvp-builder

Keywords: build me an mvp, build me a saas, build and deploy this, build project from scratch, create app unattended, complete product unattended

## no-slop-check

Keywords: check for slop, dead code, unused files, leftover junk, clean this up, tidy the repo, nobody imports this, stale code

## release-packager

Keywords: cut a release, package this release, version bump, tag a release, prepare the release

## repo-onboarding

Keywords: claude.md, onboard me, what is this repo, what does this repo do, document this repo, explain this codebase

## requirements-analyst

Keywords: prd, requirements, acceptance criteria, scope this, what should we build, define the requirements, write the spec

## requirements-traceability

Keywords: traceability, trace requirements, requirement coverage, which requirement does this satisfy

## retrospective

Keywords: retro, retrospective, what went wrong, lessons learned, post-mortem, postmortem, how did that go

## root-cause-analysis

Keywords: five whys, why did this happen, underlying cause, what actually caused

## runbook-writer

Keywords: runbook, operational guide, on-call doc, oncall doc, what do we do when it breaks

## safe-refactor

Keywords: refactor, restructure this, extract this into, tidy this code, rename this everywhere

## simplify

Keywords: simplify, too complicated, over-complicated, overcomplicated, make this simpler, cut the complexity

## stack-selector

Keywords: what stack, tech stack, which framework, which database, which db, postgres or mongo, how should we architect, monolith or services

## work-decomposition

Keywords: split this up, break into tasks, decompose, parallelise this, parallelize this, divide the work

## writing-plans

Keywords: implementation plan, write the implementation plan, turn the spec into tasks, plan the tasks, break the spec into steps, bite-sized tasks, task by task plan, hand this to a subagent

## workflow-orchestrator

Keywords: run pipeline, step by step, full task pipeline, multi-file change, big feature, refactor project, end to end pipeline
