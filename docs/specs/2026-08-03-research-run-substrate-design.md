# A run substrate for computational theoretical physics

**Status:** approved 2026-08-03 · **Stage:** 2 (design) · **Next:** `writing-plans`

## The problem

A computational theorist — condensed matter, quantum information, anything that
publishes off a workstation — loses time in four places, and named all four as
real: the arXiv firehose, the gap between physical intuition and runnable
numerics, sweep-and-figure chaos, and the writing.

No single pain dominates, so the first slice cannot be chosen by ranking hurt.
It is chosen by asking which slice is the **substrate** the others stand on.

## Scope

The original ask named six lifecycle stages. They do not decompose the way they
are listed:

| Subsystem | Depends on | Standalone value |
|---|---|---|
| A. Corpus — ingest, index, retrieve papers | nothing | yes |
| B. Reasoning — hypothesis, experiment design | A | no |
| C. Analysis — compute over data, interpret | data, not A | yes |
| D. Authoring — draft, cite, revise | A + C | weak |
| E. Provenance — reproducibility | everything | **not a stage** |

Two findings changed the plan:

- **Reproducibility is a property, not a phase.** Bolted on at the end it does
  not exist. It must be how A–D record what they did, from the first commit.
- **Only A and C stand alone.** Hypothesis generation without a corpus is a
  chatbot; paper writing without provenance is a plagiarism risk.

Three spines were considered — Run (unit = a computation), Document (unit = the
paper), Agent (unit = a research question). All three were chosen, which is
coherent only because they are **three faces of one system** rather than three
products: Run is a precondition for the other two.

Corpus is deliberately last and thin. Retrieval is the most contested surface in
this space (Elicit, Undermind, Semantic Scholar) and it is a *feature* of the
other three rather than a product on its own.

## Constraints

- **Local, single user.** Runs on one workstation. No auth, no multi-tenancy,
  no hosting, no compliance surface.
- **Python 3.11+, SQLite, filesystem.** Python because the domain runs on it —
  numpy/scipy, QuSpin, TeNPy, QuTiP — so the executor runs user code in-idiom
  rather than shelling into a foreign ecosystem.
- **Workstation-scale compute.** A run is minutes to hours, not a cluster job.

## The invariant

**Every factual claim traces to a re-executable run.**

This is not a logging convention. It is the reason the agent layer is safe at
all: in computational physics a plausible-but-wrong phase diagram is
indistinguishable from a correct one until you re-run it. Finite-size effects
and convergence failures look exactly like physics. So the architecture makes
re-running the cheap operation.

## §1 Architecture

```
                    ┌─────────────────────────────┐
   you  ──────────► │        Run Store            │  ◄──── the substrate
   agent ─────────► │  content-addressed, local   │
                    │  hash(code+params+env) → id │
                    └──────┬───────────┬──────────┘
                           │           │
              ┌────────────▼──┐   ┌────▼─────────────┐
              │   Executor    │   │     Binder       │
              │ runs, records │   │ doc ↔ run values │
              └───────────────┘   └──────────────────┘
                           │           │
                    ┌──────▼───────────▼──────────┐
                    │      Agent surface          │
                    │  tools, no privileged path  │
                    └─────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Corpus    │  (thin; arXiv metadata + local index)
                    └─────────────┘
```

Three decisions, each expensive to reverse:

**Content-addressing is the core, not a feature.** A run's identity is
`hash(code snapshot, parameters, environment lock)`. Two things fall out: an
identical calculation is a cache hit rather than four hours of CPU, and "have I
done this before" is a lookup rather than archaeology.

**The agent has no privileged path.** It calls the same run API a human does. It
cannot write files. Everything it does is recorded by construction, so "the gap
closes at L=12" always resolves to a run ID you can re-execute.

**Local-first.** Index in SQLite, artifacts on disk, environment as a lockfile.
The workstation premise makes this sufficient rather than a compromise.

Run Store and Executor are load-bearing. Binder and Agent are useless without
them. Corpus is last.

## §2 Components

### Run Store
```python
run_id(spec) -> str          # pure: sha256(code_blob, canonical_params, env_lock)
store.put(run) -> str
store.get(run_id) -> Run | None
store.query(params=..., tags=..., status=..., since=...) -> list[Run]
```
Depends on nothing. `run_id` **must be pure** — no timestamps, no absolute
paths, no hostname — or caching breaks silently.

### Executor
```python
executor.run(spec, *, force=False) -> Run    # cache hit unless force
```
Captures stdout, stderr, `artifacts/`, wall time, exit code, peak RSS. Depends
on Store. Idempotent by construction.

### Binder
```latex
\runval{sweep:L=12,J=1.0}{gap}        % a number, resolved at build
\runfig{sweep:phase-diagram}          % a figure, regenerated if stale
```
```python
binder.resolve(doc) -> (rendered_doc, manifest[run_id])
binder.stale(doc) -> list[run_id]
```
Depends on Store. The manifest makes "which runs does this paper depend on" a
fact.

The `sweep:L=12,J=1.0` syntax above is **illustrative, not specified**. What a
run query looks like — tag namespaces, parameter matching, what happens when a
query matches two runs or none — is a plan-time decision and a real one: it is
the surface a physicist types most often.

### Agent surface
```python
propose_run(question) -> RunSpec      # NEVER executes
execute(spec) -> Run
query_runs(filter) -> list[Run]
draft(section, from_runs=[...]) -> str
```
Depends on Store, Executor, Corpus. Proposing and running are separate
approvals. The LLM has no filesystem access.

**Deferred to plan time:** the model choice and API surface for the agent layer,
to be pinned against current documentation rather than asserted from memory.

### Corpus
arXiv metadata + full text, local index. Depends on nothing. Weakest component,
built last.

## §3 Data flow

**A sweep.** For each parameter point, hash the spec; a hit returns the recorded
run in zero seconds, a miss executes and stores. Adding `L=18` next week costs
one run, not nine.

**Agent investigation.** `question → propose_run → RunSpec shown, not executed →
approval → execute → agent reads outputs → proposes next`. Every assertion
carries a `run_id`.

**Paper build.** `binder.resolve` substitutes current values, re-executes or
reports stale ones, and **fails the build loudly on a missing run**. Emits
`rendered.tex` plus `manifest.json`.

**The referee cycle — the payoff.** "Please add L=20" becomes one new run (the
rest cache hits), a rebuild that regenerates the figure and updates every
`\runval` with it, and a manifest diff showing exactly which claims moved.
Today this is a week and a source of quiet figure/text inconsistency.

Three rules inside these flows:

- **A missing run fails the build.** No silent degraded path.
- **Staleness is computed, never tracked.** Rehash on demand; a dirty flag can
  lie, a hash cannot.
- **The agent writes to the store, never to the document.** It cannot type a
  number into a paper — only produce a run whose number the binder resolves.
  This is what stops a hallucinated value reaching a manuscript.

## §4 Failure modes

**Hash impurity — silent and fatal.** Any nondeterminism in `run_id` means the
cache never hits, "already ran this" is false, and nothing errors. Handled by
canonical serialisation plus a property test asserting stability across
processes, working directories and machines.

**Converged-looking and wrong — the physics failure.** Unconverged bond
dimension, unthermalised Monte Carlo, finite-size effects read as a transition.
The run exits 0 and the number is wrong. **The architecture cannot detect this.**
What it can do: a run carries optional convergence assertions (`gap stable to
1e-6 under bond-dim doubling`) and the store records whether they were
**checked, passed, or never declared** — so "verified" and "nothing was checked"
stop being the same state. The judgement stays human; its absence stops being
invisible.

| Mode | Handling |
|---|---|
| Randomised runs | If the code uses an RNG, the **seed is a required param** — which makes the run deterministic and therefore cacheable. Only a run that *cannot* be made deterministic is declared `nondeterministic`, and such a run is never cached, because returning one recorded sample as though it were re-derived is a lie |
| Environment drift | Lockfile is part of the hash. Stated cost: upgrading numpy invalidates every cache entry |
| Agent proposes plausible-wrong physics | `propose_run` never executes; the RunSpec is reviewable code before it burns CPU |
| Crash mid-sweep | Each run commits independently; a sweep is a query, not a transaction |
| Artifact bloat | Artifacts content-addressed and deduped; explicit `gc` with retention policy |

## §5 Testing

Fast tier, milliseconds each:

| Test | Why load-bearing |
|---|---|
| Hash purity, as a property test | If this fails, everything else is theatre |
| Cache hit does not execute | Assert the executor was *not called*, not merely that a Run returned |
| `force=True` does execute | The escape hatch must work or the cache stops being trusted |
| Nondeterministic specs never cached | Declare one, run twice, assert two distinct runs |
| Binder fails loudly on a missing run | Non-zero exit, never a blank where a number goes |
| Staleness is computed | Mutate an input, assert stale, with no dirty flag anywhere |
| Manifest completeness | Every `\runval` appears, or the paper has an untracked dependency |

**The one test that proves the physics:** end-to-end over the 1D
transverse-field Ising model, whose gap has a closed form. Run the real pipeline
and compare to the analytic value. A few spins, milliseconds. This is the only
test distinguishing "the plumbing works" from "the numbers mean something" —
every test above passes on a system computing confident nonsense.

**Deliberately not tested: LLM output quality.** No deterministic assertion for
"was that a good hypothesis" exists, and inventing one produces a green suite
that means nothing. The *contract* is tested instead: `propose_run` never
executes, every agent claim carries a resolvable `run_id`, the agent cannot
write outside the store. Test the harness, not the model.

**Tier mapping.** Fast tier: the seven plus the Ising fixture. Slow tier: a real
LaTeX build, and `tools/smoke.py` once a UI exists. This inherits the split
already in `.claude/hooks/_projectchecks.py` rather than reinventing it.

## How success is measured

Not adoption, not feature count. Four claims that are either true or false on
one physicist's real project:

1. **Re-running a completed sweep costs zero CPU.** Measurable: run a sweep
   twice, second pass is all cache hits.
2. **Every number in a draft resolves to a run ID.** Measurable: the manifest
   covers every `\runval` in the document, and the build fails when it does not.
3. **A referee's "add one more data point" is a rebuild, not a week.** Measurable:
   wall-clock from parameter change to updated figure *and* updated prose.
4. **No agent claim exists without a re-executable reference.** Measurable: audit
   the transcript; every quantitative assertion carries a resolvable ID.

The failure this is built against is a green system computing confident
nonsense, so none of these measures "the physics was right" — that stays human.
They measure whether being wrong is *detectable*.

## Out of scope for the first plan

- Cluster or queue submission. Workstation only.
- Multi-user anything — accounts, sharing, a server.
- Corpus beyond metadata + local index. No semantic search product.
- Any claim that the agent's physics is correct. The system makes claims
  checkable; it does not make them right.

## Open questions for `writing-plans`

1. Which layer is the first independently useful deliverable — Store+Executor
   alone, or the thinnest vertical slice touching all four components?
2. Whether convergence assertions belong in the first slice or are deferred.
   Flagged during design as possible over-engineering; the user approved them
   in, but the plan should re-test that against build cost.
3. The agent layer's model and API surface, deliberately unpinned here.
