# The No-Slop Checklist

Walk this top to bottom against every file checked. Each item: fix it, or write one line on why it's a deliberate exception.

## 1. Dead code
- No unused variables, imports, parameters, or functions
- No commented-out code blocks ("might need this later" — that's what git is for)
- No unreachable branches
- No config, flags, or dependencies added "just in case"

Dead code is a lie about what the program does. Delete it.

## 2. Unhandled errors
- Every fallible call (I/O, network, parse, external command) has a real failure path
- No swallowed exceptions (catch {} with nothing in it)
- No errors logged and then ignored as if handled
- Failure messages say what failed and what to do, not just "Error"

## 3. Duplication
- No copy-pasted blocks with minor edits — third occurrence means extract
- No parallel structures that must be kept in sync by hand
- Shared logic lives in one place

## 4. Naming
- No `data`, `info`, `temp`, `obj`, `handle`, `doStuff`, `process`, `manager` without a qualifier
- Names say what the thing is or does, specifically
- Booleans read as questions (`isReady`, `hasAccess`), not nouns
- Consistent vocabulary — don't call it `user` here and `account` there for the same thing

## 5. Untested edges
- Empty input, null/undefined, zero, negative, max-size
- The unhappy path — what happens when the thing it depends on is down
- Concurrency, if anything here can run in parallel
- The eval from the brief actually covers what "done" means — not just the happy path

## 6. Comments
- No comment that just restates the code (`// loop over users`)
- Comments that remain explain why, not what — the non-obvious decision, the constraint, the gotcha
- No stale comments describing code that changed

## 7. Consistency with the codebase
- Matches the surrounding file's idioms, structure, and naming — not your personal defaults
- Uses the project's existing utilities instead of reinventing them
- Same error-handling, logging, and import style as its neighbors

## 8. Scope
- Everything here is in the brief
- Anything extra is flagged explicitly, not smuggled in
- Nothing in the brief was silently dropped

## 9. Fake done
- No TODO / FIXME / XXX left without a tracked follow-up
- No stubbed returns or hardcoded values pretending to be real implementation
- No "works on my machine" assumptions baked in
- No console logs / debug prints left in

## 10. Verified, not claimed
- Anything reported as "working" was actually run
- Anything reported as "deployed" / "done" / "live" has proof from the same session — a passing test, a curl, a screenshot, a log line
- Test failures are reported as failures, with output — not hidden or hand-waved

---

**The rule**: the work is not eligible for the review gate while any item above is an unexplained hit. Fix, or justify in one line. No third option.
