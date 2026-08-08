---
name: research
description: Gather outside evidence a decision can rest on. Triggers include "how do people usually handle this", "what is the prior art", "does this exist already", "compare the options", "investigate", "is this even possible", "what do others do". Do NOT use for a single-fact lookup, a repo question Grep settles, or once the evidence is in hand. Use this whenever a claim needs outside evidence, even if unasked.
when_to_use: when external evidence is required
effort: high
model: opus
disable-model-invocation: false
allowed-tools: Read Grep Glob WebFetch WebSearch Task
---

# Research

Gather evidence a decision can rest on, then land it somewhere pullable. Not a
summary of what you already believed.

Cap visible output at ~500 tokens. The report is the deliverable; do not paste
it into chat.

<HARD-GATE>
NEVER synthesise from something you have not read.

Every claim in the report traces to a source you actually opened this session.
A search-result snippet, a blog's description of a repo, or your own recollection
is not a source. Read the file.
</HARD-GATE>

## Search inside before outside

`.claude/workflow.md` makes research a stage entered from anywhere, and orders
its sources internal knowledge, repository, memory,
*then* web — and that order is load-bearing. A whole feature has been
proposed to guard against losing uncommitted work; `post-run/03-checkpoint.py`
had been snapshotting the tree every turn for two days. One `ls` of the hooks
directory would have replaced the design.

Before any web search: `ls` the relevant directory, grep for the concept, read
`ISSUES.md` and `decisions/` for a prior encounter, check `git log`.

## Context budget — read the least that settles the question

Every character a tool returns stays resident and is re-sent on every later
turn. One pass of this skill's own research ingested ~135,000 chars to
produce 24,000 of report: four SKILL.md files read whole, a 71k-char file
sliced three times, six local files read whole. `post-tool/01-context-budget.py`
metered this until it was deleted, so **nothing measures it now** —
the 12k-per-result and 150k-per-session figures below are a discipline you keep,
not a warning you will receive.

Climb this ladder and stop at the first rung that answers the question:

| Rung | Cost | Use when |
|---|---|---|
| Metadata — directory listing with `fields: [name, size]`, `git log --stat`, `ls -la` | ~200 chars | Structural questions: how big, how many, what exists, what's deferred |
| Headings — dump `^#` lines, `Grep -o` the pattern | ~500 chars | Locating which part of a file matters |
| Slice — `Read` with `offset`/`limit`, `Grep` with `-C` | 1-3k chars | You know which lines you need |
| Whole file | 5-70k chars | The file *is* the finding and you will quote most of it |

The whole-file rung is legitimate — the two primary sources of a research pass
usually earn it. The failure is taking it by default for the fifth-most
relevant source.

**Extract, don't ingest.** For a source too big to read but too important to
skip, ask the user whether to read it in a subagent that returns a digest file;
the parent context then holds the findings, not the source. Do not spawn one
unasked — but do offer, with the number: "that file is 71k chars, ~18k tokens."

**A tool result routed to a file never entered your context.** Redirect bulk
output to the scratchpad and slice it there.

## Phases

**1. Scope.** Write the question as one sentence, then 3-5 sub-questions, plus
what would change your mind. Name what is out of scope. No searching until this
block exists — unfocused evidence cannot be synthesised.

**2. Gather.** At least two independent sources per sub-question.

| Looking for | Use |
|---|---|
| How other repos solve it | `mcp__github__search_code`, then `get_file_contents` on the hit |
| Whether a library does it | `mcp__context7__query-docs` |
| Concepts, standards, current practice | `WebSearch`, then `WebFetch` the primary source |
| Prior art here | `Grep`, `Glob`, `git log`, `ISSUES.md`, `decisions/` |

- **Open the actual file.** A search result's summary is a claim about a source,
    not the source. Two of five searches in one pass leaned on a blog's summary
  and had to be redone against primaries.
- **Hit count is not quality.** The single most useful find that day came from a
  search returning exactly one result; a 508-hit search needed heavy filtering.
- Keep an evidence log as you go — source, claim, confidence, which
  sub-question. Write it down before synthesising; a context reset loses
  anything unsaved.

**3. Synthesise.** Group by sub-question. Two or more independent sources
agreeing is **high** confidence; a single source is **medium**; sources that
disagree are **low** and the disagreement itself is a finding. Mark anything you
could not ground `[UNVERIFIED]` rather than dropping it.

- **Ground every finding in our situation.** "Repo X does Y" is a fact about
  repo X. The finding is what it implies for a named thing here. An ungrounded
  survey is not the deliverable.
- **Verify, don't inherit.** Do not launder a source's framing into a
  conclusion. If a repo asserts something without evidence, that is their
  assertion, and it stays labelled as one.
- **Separate settled from unsettled.** Where a canonical answer exists, say so.
  Where practice is still forming, say that instead of manufacturing consensus.

**4. Check before reporting.** Is every finding traceable to a source you
opened? Does each map to a sub-question? Are single-source claims marked medium,
not high? Did you state what would have changed your mind and whether anything
did? Are conflicts shown rather than resolved by preference?

**5. Report** to `docs/research/YYYY-MM-DD-<topic>.md`:

```markdown
# <question>

**Asked because:** <the decision this feeds>
**Verdict:** <the answer, one or two sentences>

## Findings
<per sub-question: finding, confidence, source link, what it means HERE>

## Disagreements
<where sources conflict, and which way you lean and why>

## Not adopted
<what you found, decided against, and the reason — this is the section that
saves the next person rediscovering it>

## Sources
<every source actually opened>
```

Report the path in chat, not the contents. Then hand the verdict to whatever
asked for it.

## Red Flags — stop, you are not doing research

- "I know how this is usually done." Then cite where.
- Quoting a search snippet as a finding without opening the file.
- Reaching a conclusion that matches your opening guess, with sources attached
  afterwards.
- Searching the web before grepping this repo.
- One source, stated as fact.
- "Adopt this" for something you have only read a description of.
- Dropping a finding because it complicates the recommendation.

**Each of these means: go back and open a source.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| Synthesising while still searching | Confirmation bias — the first source frames every later one |
| Reporting the survey instead of the implication | "Repo X does Y" is not a decision input until mapped to something here |
| Leaving the findings in chat | The most valuable find of a session was deferred in prose and is now buried under 400 log lines |
| Skipping "Not adopted" | The next person re-runs the same search and reaches the same dead end |
| Treating hit count as signal | The best source that day was the only hit; the 508-hit query was mostly noise |

## Parallel work — `source-digger`

When a pass needs several sources and reading them here would be expensive, hand
each to a **`source-digger`** agent: one per source, all dispatched in the same
message so they run concurrently. Each reads its source in full and writes a
digest to `docs/research/digests/<topic>-<source>.md`; only the path and a few
lines come back. The sources never enter this context.

Three to five at once. Past that you spend more time merging digests than the
parallelism saves.

Give each: the one source, the research question, the sub-questions it should
answer, and its digest path. Then read the digests and synthesise here — Phase 3
is yours, not theirs. A digger reports; it does not conclude, and it cannot
compare, because it has seen exactly one source.

**Only when the user has asked for subagents.** Otherwise climb the context
ladder above and read the sources yourself.

## Routing

- Mandatory validator: none. The Phase 4 check is the gate.
- Terminal handoff: whatever needed the evidence — `brainstormer` when the
  design is still open, `task-brief` when it is settled, `systematic-debugging`
  when the question was a bug.
- Precedes design, never replaces it. A survey is not a decision.
- When the question is genuinely too broad for one pass, decompose into
  independent workstreams and research each separately rather than going shallow
  on all of them. Do not spawn subagents unless the user asks.
- A finding that changes how this repo works earns a `decisions/` record; a
  recurring source or a dead end earns a `MEMORY.md` line via
  `knowledge-manager`.

## Success

A reader can act on the verdict without repeating the searches, every claim
names a source that was opened, the disagreements are visible, and what was
rejected is written down with its reason.
