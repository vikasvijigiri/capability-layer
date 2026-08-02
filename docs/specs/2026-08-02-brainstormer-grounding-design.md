# Brainstormer Grounding — Design Spec

Date: 2026-08-02
Status: approved, not implemented

---

## Why

`brainstormer` has ten phases and none of them opens a source. Ideas are
generated from the model's own recollection and never checked against what
already exists. Observed on 2026-08-02: a brainstorm produced fifteen candidate
directions, cited nothing, and never asked whether any of them already shipped.

The whole superpowers lineage shares the defect. Its `brainstorming` skill lists
"No prior art" as a *criterion the model self-assesses* — a judgement made by
introspection, which is the failure mode, not the fix.

`research` already owns evidence-gathering and hands back to `brainstormer`. The
gap is that nothing in `brainstormer` ever reaches for it, and its Red Flags
(*"Invoking anything but `writing-plans`"*) actively discourage it.

## Units

### 1. Phase 1.5 — Seed (before the clarifying questions)

Evidence as input, so generation starts from what exists.

- **Budget:** 2 searches — one `mcp__github__search_code` or repo search, one
  `WebSearch`. At most **one** primary source opened.
- **Output:** 3-5 bullets of how the problem is already solved, **and what that
  prior art does not cover**.
- **Anti-anchoring**, since seeding risks producing variations on prior art:
  - Seed findings are stated as constraints and gaps, never as candidate
    solutions.
  - Generation must yield **at least one direction that contradicts the seed**.

### 2. Phase 4.5 — Kill (after approaches proposed, before converging)

Evidence as filter. Each surviving direction gets a genuine attempt to find the
thing that already does it.

- **Budget:** 2 searches per direction, ≤3 directions, ≤6 total. Open the
  primary source for any hit that looks like a real match — a search snippet is
  a claim about a source, not the source.
- **Verdict per direction**, exactly one of three. These must never collapse
  into each other:

| Verdict | Meaning | Consequence |
|---|---|---|
| `exists` | a named thing does this, with URL | direction dies, or states its difference explicitly |
| `partial` | closest prior art, plus what it misses | survives; the difference is recorded |
| `no prior art found` | searched, found nothing | survives — **not** a claim of novelty |

- **Over budget on any direction → hand off to `research`.** That is the
  boundary between the two skills.
- **Search unavailable → every direction marked `[UNVERIFIED]`** in the spec and
  said aloud. Never silently dropped.

### 3. Spec contract

Every spec gains one section, one line per direction, no prose:

```markdown
## Prior art
- <direction> — exists|partial|no prior art found — <URL or "searched: <query>"> — <what it misses>
```

### 4. Enforcement

In `tools/test_docs_gates.py` — already run by `/verify`, so no sixth suite to
wire up. Five mechanical rules, no model judgement:

1. Every `docs/specs/*.md` has a `## Prior art` heading.
2. At least one line under it carries one of the three exact verdict tokens.
3. `exists` and `partial` lines contain a URL.
4. `no prior art found` lines contain `searched: <query>` — absence of evidence
   is recorded as an action taken, not a shrug. This rule is the point of the
   whole unit.
5. `[UNVERIFIED]` passes but prints as a warning, never silently.

**Grandfathering:** applies to specs dated ≥ 2026-08-02.
`2026-08-01-evidence-ledger-design.md` is exempt and is not backfilled.

### 5. Text changes to `brainstormer`

- ≤35 lines added. Phases as a compact table, not prose.
- Routing: `research` named as a mid-flow escape, not only a predecessor.
- Red Flags: the "invoke nothing but `writing-plans`" rule reworded to bind the
  *terminal* handoff only, so it stops suppressing a mid-flow `research` call.
- New Red Flag: "proposed a direction without opening a source."

## Testing

| Unit | Proof |
|---|---|
| 3, 4 | a fixture spec missing `## Prior art` fails; one with `exists` and no URL fails; one with `no prior art found` and no `searched:` fails; a compliant one passes |
| 4 (grandfathering) | the 2026-08-01 spec passes untouched |
| 5 | `tools/test_process_router.py` still exits 0; the skill's description stays under budget |
| 1, 2 | not mechanically testable — budgets are model discipline. The spec section is the only observable artefact, which is why rule 4 exists |

## Out of scope

- Replacing `research`. This is a bounded check; a real evidence pass still
  belongs there.
- Grading idea *quality*. The gate proves a search happened, not that the idea
  is good.
- Backfilling prior art into existing specs.

## Prior art

- Seed pass (evidence before ideation) — partial — https://arxiv.org/html/2607.04439v1 — ResearchStudio-Idea's Paper-Search grounds ideation in literature, but targets research ideation over papers, not a bounded pass inside a repo design skill, and requires no gap statement.
- Kill pass (per-direction collision check) — partial — https://arxiv.org/html/2607.04439v1 — Scoop-Check does claim-level prior-art collision checking across decomposed axes. Richer than this, and unenforced: no artefact a test can fail.
- Self-assessed novelty (the thing being replaced) — exists — https://github.com/rfxlamia/ultrapowers/blob/main/skills/brainstorming/SKILL.md — the superpowers-lineage `brainstorming` skill treats "no prior art" as a criterion the model judges by introspection. Opens no source; this design exists to replace that.
- `## Prior art` as a spec-template section — exists — https://github.com/influxdata/telegraf/blob/master/docs/specs/template.md — an established convention (296 GitHub hits). Adopted as-is rather than invented.
- A test that fails a spec for lacking grounded prior art — no prior art found — searched: `"## Prior art" path:docs/specs extension:md` — 296 repos carry the section; the search surfaced no repo enforcing it mechanically. Weak evidence: the query finds sections, not enforcement, so treat this as unsearched for enforcement specifically rather than as novelty.
