---
name: root-cause-analysis
model: opus
description: Traces a problem back to the condition that actually caused it, separating the trigger from the underlying cause and from the reason it went undetected. Use for "why did this happen", "root cause", "how did this get through", "post mortem", "it happened again", "this keeps coming back", "what went wrong here", "we fixed it but I do not know why it broke". Prefer this over fixing the symptom - a cause you never identified produces the same incident again under a different symptom. Do NOT use for a live outage in progress; restore service first and analyse after.
---

# Root Cause Analysis

For incidents and recurring problems, including non-code ones. Distinct from
`error-recovery`, which is a bounded fix loop for one failing check.

## Steps

1. **Establish the timeline.** What changed, when, what was observed - with evidence.
   No inference yet.
2. **Separate three things that get conflated constantly:**
   - **Trigger** - what made it happen now
   - **Cause** - the condition that made it possible at all
   - **Detection gap** - why nobody noticed until this point
   A fix addressing only the trigger leaves the other two live.
3. **Ask why until the answer stops being technical.** Most causes terminate in a missing
   check, an unstated assumption, or a decision nobody recorded - not in a line of code.
4. **Test the causal claim.** Would removing the proposed cause have prevented *this*
   incident? If not it is a contributing factor, not the cause. Say which.
5. **Name the counterfactual check** - the specific test, alert or gate that would have
   caught it, and whether it exists now.

## Output

Timeline, trigger, cause, detection gap, one preventive action per layer. Hand the record
to `knowledge-manager` for `ISSUES.md`. Check `.claude/blueprints/debugging-rca.md` for
the established shape before inventing one.

## Never

Do not name a person as a root cause. "Someone forgot" is a detection gap - it means
nothing was checking.
