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
- **Sources are explicit only** — no inference from prose, no model guessing
  what a diff asserts. Three sources, and only three:
  1. **Plan steps** — each step in a `docs/plans/*.md` covering the change.
  2. **Test names** — tests added or modified by the diff.
  3. **Declared repo invariants** — see below.
- A change with no plan still yields invariant claims. A change with no plan
  *and* no invariant touched yields no claims, and the ledger reports it as
  **unverifiable — not verified**. Those are different states and must never
  collapse into each other.

#### Declared repo invariants

Plan steps and test names are both *per-change* claim sources, and neither can
express "no hook names a skill that does not exist" — that is a property of the
repo, asserted by nobody, which is exactly why it broke. So the extractor has a
third source: a declared list of invariants, each a `(statement, check command)`
pair, held in one file.

- The extractor emits a claim for **every** declared invariant on every run,
  independent of the diff. Invariants are cheap and always-on; there is no
  relevance filter to get wrong.
- Adding an invariant is a deliberate act of writing down something previously
  only in someone's head. The list starts with the one that broke: every skill
  name appearing in a hook's user-visible output resolves to a real
  `.claude/skills/<name>/SKILL.md`.
- An invariant's check counts as part of the repo's check surface. Adding one
  therefore means adding it to `/verify` too — see the constraint in unit 2,
  which this does not weaken: the runner still may only invoke checks `/verify`
  runs, and the invariant list and `/verify` are kept in agreement by a test
  that fails if they diverge.

### 2. Check runner

Executes checks and captures results.

- **Input:** the claim list.
- **Output:** a run record per check — command, exit code, verbatim stdout/stderr.
- **Nothing is ever self-reported.** The runner may only report a check as
  passing if it executed it and captured the exit code. This is the repo's
  standing rule applied to the tool that enforces the repo's standing rules.
- Every check it can invoke must already be something `/verify` runs. It
  introduces no new check surface of its own. An invariant's check is added to
  `/verify` when the invariant is declared, so this holds by construction and a
  test enforces the agreement.

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
- **Ships advisory.** It reports and blocks nothing until it has earned
  blocking mode against a mechanical threshold. Rationale: an unreliable
  blocking gate teaches engineers to bypass gates, which is worse than no gate.

#### The flip to blocking

Not a judgment call. Three conditions, all required:

1. **Volume** — at least 20 changes have been run through the ledger that
   produced at least one claim. Changes reporting `unverifiable` do not count
   toward the 20; they exercise nothing.
2. **Adjudication** — every unbacked claim reported across those changes has
   been labeled by a human as `true` or `false-positive`, and the label is
   recorded next to the claim. An unlabeled report blocks the flip; silence is
   not consent.
3. **Rate** — false positives are **at most 10%** of adjudicated unbacked
   claims. If the rate exceeds it, the extractor's sources are wrong and the
   fix is to narrow them, not to raise the ceiling.

**A false positive is** an unbacked claim that is either (a) actually checked by
something the mapper failed to connect, or (b) not a falsifiable assertion at
all. A claim that is genuinely unchecked is a **true** report even if the human
judges it unimportant — "not worth checking" is a decision about the invariant
list, not an extractor defect, and conflating the two is how the rate gets
gamed.

10% is a stated tolerance, not a derived one: at that rate a human adjudicating
a 3-claim report sees a spurious claim roughly one run in three, which is
irritating but not yet training them to ignore the output. Revisit it with real
data; do not silently drift it.

### 5. Attention router — designed, not built

Across N concurrent changes, ranks what the human should look at by unbacked
risk. This is the fleet half of the bet and the reason units 1–4 emit
machine-readable coverage maps rather than prose. Out of scope for the first
plan.

## Data flow

    diff + plan + invariant list
      → [1] claims
      → [2] run records
      → [3] coverage map  (unbacked set = the product)
      → [4] verdict + reasons
      → [5] ranking across changes   (later)

Each arrow is a serializable value, so any unit can be tested with a fixture
and no upstream unit.

## Error handling

- **Extraction finds no plan and no invariant** → `unverifiable`, reported as
  such. Not a failure, not a pass.
- **The invariant list and `/verify` disagree** → loud failure of the ledger
  itself, not a per-claim `unbacked`. An invariant whose check nothing runs is a
  broken tool, not a broken change.
- **A check errors or times out** → the claim is `unbacked`, and the captured
  stderr is the reason. An erroring check never counts as evidence.
- **The ledger itself fails** → it must fail loudly. A silent ledger and a clean
  ledger look identical, which is the exact failure mode the hook layer already
  has.

## Testing

- **Unit 1:** fixture plan + fixture diff → expected claim list; a diff with no
  plan still yields the invariant claims; a repo with neither yields
  `unverifiable`.
- **Unit 2:** a passing check, a failing check, an erroring check, a timeout —
  four run records, exit codes captured verbatim.
- **Unit 3:** hand-written claims + run records → expected unbacked set.
- **Unit 4:** advisory mode reports and does not block; blocking mode blocks;
  the flip is refused when volume, adjudication or rate is unmet — one test per
  condition.
- **Invariant/`verify` agreement:** a declared invariant whose check `/verify`
  does not run makes the suite fail.
- **End to end, criterion 1:** plant a plan step with no check behind it and
  confirm it is reported.
- **End to end, criterion 2:** plant a hook naming a nonexistent skill, with
  every other check green, and confirm the invariant claim comes back unbacked.

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
2. It catches the historical failure: a hook naming a deleted skill, with every
   other check green, comes back as an unbacked invariant claim.
3. The gate refuses to flip to blocking until volume, adjudication and rate are
   all satisfied, and each refusal names which condition is unmet.

Criterion 1 is about completeness of the unbacked set within a change.
Criterion 2 is about catching what no per-change source can express — it is
reachable only through the declared-invariant source, and if the invariant list
is empty, criterion 2 fails by construction. That is the point: the ledger
cannot check what nobody has written down, and its value is that the omission
becomes visible instead of silent.

## Out of scope

Cryptographic attestation. Multi-repo. CI integration. Any UI beyond terminal
output. The attention router (unit 5). Replacing the existing hooks — the gate
is added alongside them; retiring the ritual gates is a later decision informed
by whether this one earns its blocking mode.
