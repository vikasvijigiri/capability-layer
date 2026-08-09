# Framing: verifying a request, and scoring what is left

The depth behind Stage A of `writing-plans`. Split out under the same 200-line
prose budget as the other references; the skill body keeps the six fields, the
`(inferred)` rule and the no-dialogue gate, because those are decisions rather
than method.

---

## Verify before you fill

Every claim is a hypothesis, including the user's. Use `Grep`/`Glob`/`Read` on
the cheap ones:

- do the named files, functions, commands, config keys and error strings exist?
- does the described behaviour match the code?

Sort what you find into **confirmed** / **disputed** / **unverifiable**, and
carry any disputed item into the brief explicitly. A brief on a wrong premise is
worse than none, because it looks approved.

Lightweight lookups only. If scoping needs real root-cause work, say so and stop
rather than absorbing another job — that is a `systematic-debugging` dispatch.

## Scoring confidence

0–100: how much of the six fields could you fill without guessing, after any
Stage B dispatch?

- Weight down hard for a missing **Constraints** or **Out-of-scope** — the two
  most often silently assumed.
- Weight down further if **Done-check** is not a runnable command with an
  expected result.

**≥75** state the brief and continue. **<75** state it, mark the weak fields
`(inferred)`, say in one line that the scope is thin, and continue anyway.

The score never decides whether to ask. It is information for the reader, and a
brief with more inferred fields than stated ones is a signal to say so in one
line — not to open a dialogue. The chain has two gates and this is not one.
