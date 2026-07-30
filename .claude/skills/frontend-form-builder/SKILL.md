---
name: frontend-form-builder
model: sonnet
description: Builds a form with its field types, validation rules, submission handling and error surfacing - including the failure paths that hand-written forms skip. Use for "build a form", "add a signup/checkout form", "form validation", "validate this input", "show the error next to the field", "the form loses my data", "double submit", "why does it clear when it fails", "required field handling". Prefer this over hand-wiring inputs and an onSubmit - the validation timing, the error placement and the resubmit path are exactly what gets skipped and exactly where users get stuck. Do NOT use for server-side validation of an API payload - that belongs with the endpoint.
---

# Form Builder Skill

Generates a form against `DESIGN.md` tokens, with validation and failure handling
specified rather than improvised. Forms are the highest bug-density surface in most
UIs because the unhappy paths outnumber the happy one.

## When to use
- "build a form", "add a signup form", "form validation", "show errors next to fields"
- "the form loses my data", "double submit", "it clears when it fails"

## Steps
1. **List the fields** with type, required/optional, and the real-world constraint each
   one encodes. A constraint with no user-facing message is not done.
2. **Set validation timing per field.** Validate on blur, not on every keystroke -
   validating as the user types marks a half-typed email as wrong before they finish.
   Re-validate on submit regardless.
3. **Place each error next to its field**, with a summary at the top only if the form is
   long enough to scroll. Announce errors to assistive tech, and move focus to the first
   invalid field on a failed submit.
4. **Handle submission properly** - disable the control while in flight, guard against
   double submit, and never clear entered values on a failed response.
5. **Define the failure paths** - field-level rejection, whole-form server error, network
   loss mid-submit, and session expiry. Each needs a visible message and a way to retry
   without retyping.
6. **Confirm success visibly.** A form that silently succeeds gets submitted twice.

## Notes
Client-side validation is a convenience, never a guarantee - the server validates the
same rules independently. State both sides so they cannot drift.

Preserving user input across a failure is the single highest-value behaviour here and
the one most often missing. Treat losing typed data as a defect.

Pull field styling, spacing and error colour from `DESIGN.md`; never introduce a new red.

## Routing

**Validator (required)** - `.claude/validators/frontend-visual-diff.md`. CLAUDE.md makes
this mandatory before any side effect is committed - it is not optional cleanup after the
fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/frontend-component.md` - a
matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/frontend-release.md` orchestrates this end to
end. It is a document to follow, not an executable - there is no workflow runtime in
Claude Code.

Requires `DESIGN.md` - run `design-system` first if the project has none. Accessibility
of the finished form is checked by `frontend-accessibility-check`.
