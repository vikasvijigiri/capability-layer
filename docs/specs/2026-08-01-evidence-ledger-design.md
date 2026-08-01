# Evidence Ledger — Design Spec

Date: 2026-08-01
Status: approved, not implemented

---

## Why

The forecast this comes out of: over the next ten years the durable unit of
software work stops being a diff and becomes **a change plus the evidence that
justifies it**. Two forces drive it, and neither works alone —

- **Fleets.** One human directs many agents. The unit of work becomes a queue,
  not a branch. Volume goes up by an order of magnitude.
- **Trust scarcity.** Generation becomes cheap; justified confidence does not.
  Review time per change collapses toward zero.

At one agent, the confidence gap is absorbed by a human reading the diff. At
fifty it is not, and review degrades into rubber-stamping. This repo already has
the failure: six hooks shipped naming skills that had been deleted, past a green
test suite, because nothing asserted "the skill this hook names exists."

Existing tooling reports **what passed**. The scarce number is **what was
asserted and never checked**. A human can read fifty lines of "3 unbacked
claims". Nobody can read fifty diffs.

## Scope of this spec

The five-unit design below is the shape. **Units 1–4 are in scope for the first
implementation plan. Unit 5 is not** — it is recorded here because it is the
reason the shape is what it is, and it is pointless until 1–4 work on a single
change.

## Units

Each has one purpose, a defined interface, and is testable alone.

### 1. Claim extractor

Turns a change into a list of falsifiable assertions.

- **Input:** the diff, plus `docs/plans/*.md` if one covers the change.
- **Output:** a list of claims, each with a source location.
- **Sources are explicit only** — plan steps, test names, hook registrations in
  `.claude/settings.json`. No inference from prose. No model guessing what a
  diff asserts.
- A change with no plan yields no claims, and the ledger reports it as
  **unverifiable — not verified**. Those are different states and must never
  collapse into each other.

### 2. Check runner

Executes checks and captures results.

- **Input:** the claim list.
- **Output:** a run record per check — command, exit code, verbatim stdout/stderr.
- **Nothing is ever self-reported.** The runner may only report a check as
  passing if it executed it and captured the exit code. This is the repo's
  standing rule applied to the tool that enforces the repo's standing rules.
- Every check it can invoke must already be something `/verify` runs. It
  introduces no new check surface.

### 3. Coverage mapper

Maps claims to executed evidence.

- **Input:** claim list + run records.
- **Output:** for each claim, `backed` (with the run record) or `unbacked`.
- The **unbacked set is the primary output.** The backed set is a byproduct.

### 4. Evidence gate

Decides whether the change proceeds.

- **Input:** the coverage map.
- **Output:** a verdict, and the unbacked claims as the reason.
- Gates on "is this assertion actually checked?" — replacing ritual gates
  (docs-updated?, attribution-absent?) as the model for what a gate is for.
- **Ships advisory.** It reports and blocks nothing until extraction has run
  over roughly 20 real changes and its false-positive rate has been measured.
  Flipping to blocking is a config change and a deliberate decision, never the
  default. Rationale: an unreliable blocking gate teaches engineers to bypass
  gates, which is worse than no gate.

### 5. Attention router — designed, not built

Across N concurrent changes, ranks what the human should look at by unbacked
risk. This is the fleet half of the bet and the reason units 1–4 emit
machine-readable coverage maps rather than prose. Out of scope for the first
plan.

## Data flow

    diff + plan
      → [1] claims
      → [2] run records
      → [3] coverage map  (unbacked set = the product)
      → [4] verdict + reasons
      → [5] ranking across changes   (later)

Each arrow is a serializable value, so any unit can be tested with a fixture
and no upstream unit.

## Error handling

- **Extraction finds no plan** → `unverifiable`, reported as such. Not a
  failure, not a pass.
- **A check errors or times out** → the claim is `unbacked`, and the captured
  stderr is the reason. An erroring check never counts as evidence.
- **The ledger itself fails** → it must fail loudly. A silent ledger and a clean
  ledger look identical, which is the exact failure mode the hook layer already
  has.

## Testing

- **Unit 1:** fixture plan + fixture diff → expected claim list.
- **Unit 2:** a passing check, a failing check, an erroring check, a timeout —
  four run records, exit codes captured verbatim.
- **Unit 3:** hand-written claims + run records → expected unbacked set.
- **Unit 4:** advisory mode reports and does not block; blocking mode blocks.
- **End to end:** plant a plan step with no check behind it and confirm it is
  reported.

## Constraints

- Python, standard library only, no new dependencies.
- Hook payloads via `_hooklib.load_payload()`, per the existing hooks.
- Runs on Windows. Path handling must not repeat the `04-delivery-guard.py`
  bug where a backslash in a path was read as content.
- No CI integration, no cryptographic attestation, no multi-repo, no UI beyond
  terminal output.

## Success criteria

1. For a change with a plan, the ledger names **every** plan step with no
   executed check behind it, and misses none. Validated by planting an unbacked
   step and confirming it is reported.
2. It catches the historical failure: a hook naming a deleted skill, green
   suite, no claim covering "the named skill exists."

Criterion 1 is about completeness of the unbacked set. Criterion 2 is about the
extractor finding claims that nobody wrote down as a test. If 2 fails while 1
passes, the extractor's source list is too narrow and that is the finding.

## Out of scope

Cryptographic attestation. Multi-repo. CI integration. Any UI beyond terminal
output. The attention router (unit 5). Replacing the existing hooks — the gate
is added alongside them; retiring the ritual gates is a later decision informed
by whether this one earns its blocking mode.
