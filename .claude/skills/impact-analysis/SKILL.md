---
name: impact-analysis
model: opus
description: Works out what a proposed change will actually touch before it is made - callers, dependants, data, running systems and people. Use for "what will this break", "is this safe to change", "what depends on this", "blast radius", "who else uses this", "can I just delete this", "will this affect anything else", "is anyone relying on this". Prefer this over grepping for the symbol name - the expensive breakages are the indirect ones, and a caller count is not an impact assessment. Do NOT use for a change that is provably local, such as a private function with no exported surface.
effort: high
---

# Impact Analysis

Answers "what does this change touch" **before** the change is written, while it is still
cheap to change course.

## Steps

1. **Define the change precisely.** One sentence: what becomes different. A vague change
   produces a vague impact assessment.
2. **Direct dependants.** Callers, importers, subclasses, template references, config
   keys. Use the `explore` agent for a broad sweep rather than many sequential reads.
3. **Indirect dependants.** Serialized shapes, database columns, API responses, event
   payloads, cached values, log formats others parse. This is where real breakage hides -
   nothing imports them, so search finds nothing.
4. **Runtime state.** In-flight jobs, existing rows, open sessions, cache entries built
   under the old behaviour. Migrations fail here, not in the code.
5. **Human surface.** Documented behaviour, published URLs, anything a person has
   memorised or scripted against.
6. **Report** each as: what it is, how it breaks, and whether it breaks loudly or
   silently. Rank silent breakage first - it is worse than a crash.

## Output

A blast-radius list, a verdict (`local` / `contained` / `wide`), and the checks that must
pass before this ships. Feed the verdict into `approval-brief` when a human gate applies.

## Honesty rule

State what you could not determine. "No dynamic callers found" is a different claim from
"there are no dynamic callers" - reflection, string-built names and config-driven dispatch
all defeat static search. Say which of those you checked.
