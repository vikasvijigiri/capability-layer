# Process-Skill Routing

Keyword routing for the skills in `.claude/skills/`. Read by
`.claude/hooks/pre-run/05-process-skill-router.py`, which scans every prompt and
injects the names of any skills that match.

Why this file exists: the skill listing is truncated against a token budget, so
a skill's `description:` — its only other trigger surface — can be absent on the
exact turn it was needed. This file is the routing signal that survives that
truncation. It is currently cheap to satisfy (twelve skills), and the budget is
a constraint on what gets added back, not a problem to solve later.

**Format contract.** One `## <skill-name>` heading per entry, matching a
directory under `.claude/skills/` exactly. Exactly one `Keywords:` line beneath
it, comma separated. `tools/test_process_router.py` asserts every heading
resolves to a real skill and that no skill is left unrouted.

**Keyword style — phrases, not words.** Naming a specific skill is a strong
claim, so entries lean on multi-word phrases lifted from each skill's own
`description:` trigger list rather than bare words that fire on anything.

---

## research

Keywords: use github, using github, see github, check github, from github, connect to github, a better version, see how people do it, how do people usually handle, is there a better version, fetching the best version, fetch some standard repos, whats the prior art, what is the prior art, standard approach, check whether this exists, look this up, investigate this, find evidence for, compare the options, what do other repos do, use github and see how people do it, what's the standard approach

## systematic-debugging

Keywords: this is broken, why is this failing, the test fails, tests are failing, it worked before, debug this, whats wrong with, what is wrong with, nothing happens, silently doing nothing, figure out why, root cause, root cause this, why does this return, the fix did not work, still failing, it's silently doing nothing, this returns the wrong, what's wrong with

## knowledge-manager

Keywords: log this, update the docs, record this, record this unit of work, write down what we decided, note this for later, capture this before we lose it, handoff, where did we get to, update handoff, add a decision record, log the decision

## code-review

Keywords: code review, review the diff, review this change, review my code, review the pr, review the branch, check this before i commit, look over these changes, sanity check this, is this ready to ship, no code review has been recorded, can you sanity check this

## task-brief

Keywords: task brief, six line brief, 6 line brief, scope this, scope the task, break this into a brief, structure this task, turn this into a task, write the brief, what is out of scope, add support for, can we support, i want users to be able to, it would be nice if, new feature request, fix the thing where

## brainstormer

Keywords: brainstorm, spitball, bounce ideas, any ideas, what could we do, throw some ideas, thinking out loud, give me some angles, what are our options, help me think this through, i am stuck, im stuck, what if we, ideate, riff on, riff on this, spitball this

## writing-plans

Keywords: implementation plan, write the implementation plan, turn the spec into tasks, plan the tasks, break the spec into steps, bite-sized tasks, task by task plan, hand this to a subagent, what does the engineer actually do

## executing-plans

Keywords: execute the plan, run the plan, work through the tasks, work through the plan, start building, start implementing, go ahead and implement, carry this out, continue the plan, pick up where we left off, do task, build it, implement this, implement the plan, start the experiment loop

## verifying-work

Keywords: is this done, are we finished, are we done, did we solve it, did it actually work, does this meet the brief, check this works, confirm it works, prove it works, verify this, validate this, is it working, did that fix it

## delivering

Keywords: ship it, ship this, deliver this, land this, merge this, open a pr, raise the pr, create the pr, push this up, wrap this up, finish the branch, finish this branch, how do we land this, what do we do with this branch

## releasing

Keywords: deploy this, deploy it, deploy to prod, deploy to production, deploy to staging, run the deploy, push it live, put it live, go live, is it live, roll this out, roll it out, release it, release to staging, promote to production, promote to prod, publish the package, publish it, cut a release, ship to prod, roll it back, roll back the deploy, revert the deploy, the deploy failed, deploy to render, put it on vercel, deploy to vercel

## no-slop

Keywords: no slop, no-slop check, audit the capability layer, audit the skill layer, review the .claude folder, review the claude folder, is the skill layer bloated, are the skills clean, are the skills overlapping, is the layer rotting, did the layer rot, check for slop, fix the slop, clean up the skills, clean up the claude folder, tidy the claude folder, skill layer health, layer decay, architectural decay
