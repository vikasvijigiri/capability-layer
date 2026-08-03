# Skill template

Copy everything below the line into `.claude/skills/<name>/SKILL.md` and replace
every `<…>`. Delete the sections that do not apply — an empty section is slop,
and `tools/test_no_slop.py` looks for placeholders left behind.

Section order is not arbitrary. Gate first (so it is read before the work),
phases second, failure modes third, routing last. `## Routing` and `## Success`
are the two every skill has; `## Next step` replaces `## Routing`'s handoff bullet
when the skill sits on the numbered chain, because the chain check requires an
imperative successor rather than a descriptive one.

---

```markdown
---
name: <exactly the directory name>
description: Use when <the situation, not the feature>. Triggers include "<phrase someone types>", "<another>", "<another>". Do NOT use <the nearest neighbour skill and why it owns that case>.
effort: <low | medium | high>
model: <opus for planning and diagnosis | sonnet for coding and procedure | haiku for pure extraction>
---

# <Title Case Name>

<One or two sentences: what this turns into what. Name the input and the
artefact. No "this skill will help you".>

Cap visible output at ~500 tokens. <Name the deliverable, and say it is not
pasted into chat.>

<HARD-GATE>
NEVER <the single thing that makes this skill worthless if violated>.

<Two or three sentences on why, ideally naming a real failure. A gate with no
recorded failure behind it tends to get deleted as ceremony.>
</HARD-GATE>

## <Phase 1 name>

<What happens first, and what must exist before it can. State the refusal
condition: what makes you stop instead of proceeding.>

## <Phase 2 name>

<...>

## <The check>

    <the literal command, runnable from the repo root>

<What its output has to say. Quoting it is mandatory — "it passes" is not a
result.>

## Red Flags — <the failure mode in the reader's own words>

- <A thing you would catch yourself doing that means you have stopped doing this
  skill and started doing something easier.>
- <...>

**Each of these means: <the corrective action>.**

## Common Mistakes

| Mistake | Why it bites |
|---|---|
| <...> | <the concrete consequence, not "it is bad practice"> |

## Routing

- Mandatory validator: <a command, or "none" and what the gate is instead>.
- Terminal handoff: <the skill that comes next, and on what condition>.
- <When this skill hands sideways instead of forward, and to what.>

## Success

<One sentence a reader can check against reality. Not "the skill was followed" —
what is true about the artefact when it worked.>
```

---

## Filling the frontmatter

`description:` is injected **every turn**, for every skill, whether or not it is
relevant. Thirteen skills cost ~1,100 tokens per turn. Keep it near 380 characters
and put trigger breadth in `.claude/routing/process-skills.md` instead, which a
hook reads and costs nothing until it matches.

The `Do NOT use` clause is not politeness. It is the only thing separating two
adjacent skills for the router, and the most common reason a prompt names two.

## Filling the routing entry

In `.claude/routing/process-skills.md`:

```markdown
## <name>

Keywords: <phrase>, <phrase>, <phrase>
```

One heading, one `Keywords:` line, comma separated, all lowercase. A heading with
no `Keywords:` line is skipped silently — contributing zero keywords is
indistinguishable from being absent.

Lift the phrases from things a person would actually type. The corpus in
`tools/test_process_router.py` is real prompts, not invented ones, and the
task-shape fallback exists because "Build an AI platform that assists scientists"
matched nothing at all.

## Filling the workflow.md row

Off-chain (the common case):

```markdown
| <Stage> | `<name>` | <when it is entered> | <what it returns to> |
```

Numbered — and this renumbers everything after it:

```markdown
| <N> | <Stage> | `<name>` | <what it consumes> | <what it produces> |
```

Write any stage number in prose as ``N `owner` `` rather than a bare "stage N".
`tools/test_process_router.py` checks each one against the chain table, and it can
only do that when the owner is named beside the number.
