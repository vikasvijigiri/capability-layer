---
name: feasibility-check
model: opus
description: Judges whether proposed work is achievable within its stated constraints, and says plainly what would have to give if it is not. Use for "can we do this", "how hard is this", "is this realistic", "can we get this done by Friday", "is this even possible", "how long will this take", "is it worth attempting", "should we try this". Prefer this over starting and finding out - the cheapest place to discover something cannot be done is before the work begins. Do NOT use once work is underway and the real question is scope rather than viability.
---

# Feasibility Check

## Steps

1. **Restate the ask as a testable claim.** "Users can export their data as CSV" is
   checkable; "improve exports" is not.
2. **List the hard constraints** actually in play - time, cost ceiling, platform limits,
   data you do not have, access you do not have, skills not present.
3. **Find the binding constraint.** Usually exactly one thing makes it hard. Name it;
   everything else is noise until that one is resolved.
4. **Classify**: `feasible as stated` / `feasible with a named cut` / `not feasible`.
   Never return a bare "it depends".
5. **If not feasible as stated, say what would have to give**, and give the smallest
   achievable version - so the answer is a path rather than a refusal.

## Output

Verdict, binding constraint, cheapest viable variant, and the single unknown that would
most change the answer if resolved.

## Rules

- **An estimate needs a basis.** "Two days" with no comparable work behind it is a guess
  wearing a number. State the basis, or state that there isn't one.
- **Distinguish hard from tedious.** Tedious is a resourcing question, hard is a
  feasibility question. They get confused constantly and have different answers.
- Stack and architecture viability goes to `stack-selector`; this skill asks whether the
  goal is reachable, not which technology reaches it.
