---
name: adding-a-skill-or-agent
description: Pre-flight checklist for adding a new skill or agent to this layer — the checks two different validators require, and where every duplicated count lives. Read before writing the first frontmatter line, not after the first failed check.
---

# Adding a skill or agent — pre-flight checklist

Every item here was a real redo this session: discovered by trial and error,
one check run at a time, instead of known upfront. Read this once, before
writing `SKILL.md`'s first line.

## Two validators, disjoint rule sets

`new_skill_check.py <name>` and `test_process_router.py` both gate a new
skill's frontmatter and body — **passing one does not mean the other
passes.** Run both before trusting either.

| Rule | Enforced by |
|---|---|
| `name:` matches the directory | `new_skill_check.py` only |
| `description` ≤ 700 chars (hard), ≤ 550 (soft, advisory) | `new_skill_check.py` only |
| Frontmatter total ≤ 1300 chars | `new_skill_check.py` only |
| `model` ∈ opus/sonnet/haiku, `effort` ∈ low/medium/high | `new_skill_check.py` only |
| A row in `workflow.md` (chain or off-chain table) | `new_skill_check.py` only |
| **Description's first sentence ≤ 12 words** — capability first, not a condition | `test_process_router.py` only |
| **At least 6 `"quoted"` trigger phrases** in the description | `test_process_router.py` only |
| **Literal `Use this whenever` or `Use this proactively`** somewhere in the description | `test_process_router.py` only |
| **Body has ≥ 3 ordered steps** (`1.`, `## Phase N`, `## A1.`, or `**1.`) | `test_process_router.py` only |
| Every backtick-named skill/agent in the body resolves | `new_skill_check.py` (advisory) |
| No `mcp__`-prefixed tool name reused elsewhere with a conflicting phrase | `test_process_router.py` (trigger-phrase collision) |

## Description char budget — do the math before writing

Draft the description, then count it (`len(description)`) before adding the
next clause — not after hitting the cap three times. Reserve room for:

- A short lead sentence (capability, ≤ 12 words, ends in a period).
- **`Use this whenever ...`** or **`Use this proactively ...`**, verbatim.
- At least 6 phrases in `"double quotes"` — the literal strings a user types.
- A `Do NOT use` clause naming what this skill is not for.

## YAML-unsafe frontmatter

An unquoted `Word:` (colon + space) anywhere inside the `description:`
string breaks YAML parsing — `new_skill_check.py`'s naive line-partition
parser won't catch it, only a real YAML load (inside `test_process_router.py`)
does. Write `Triggers include X`, never a bare `Triggers: X`.

## The `Files:` block, if this skill also ships a plan

Every backticked token inside a plan task's `**Files:**` block is read as a
declared file by `tools/parallel_groups.py` — not just the actual
`- Create:`/`- Modify:` path. List illustrative filenames (e.g. what a SCAN
phase greps for) in `**Implementation notes:**` instead, without backticks
if they look like a real path.

## Every place a skill/agent count is duplicated

| File | What it says | Checked by |
|---|---|---|
| `README.md` | "the *N* skills" / "*N* subagents" | `test_referenced_paths.py` |
| `.claude/README.md` | "*N* capabilities" (not "skills" — aliased in `NOUN_ALIASES`) | `test_referenced_paths.py` |
| `MEMORY.md` | "*N* skills and *M* agents" | `test_referenced_paths.py` |
| the layer's own `test_layer_comparison_contract.py` (source repo only — not shipped by `install.py`) | a hardcoded `!= N` literal | itself (bump by hand — the historical report it also checks stays untouched) |
| `docs/evals/trigger-queries.json` | implicit total query count | `python tools/eval_triggers.py --list` (also refuses to run for a skill with no query set at all) |

Check every row, not just the one the first failing suite happens to name.

## Final check

```
python tools/new_skill_check.py <name>
python tools/new_skill_check.py --all
python tools/test_agent_standards.py        # if an agent was added
python tools/test_process_router.py
python tools/test_referenced_paths.py
python tools/eval_triggers.py --list        # confirm a real query count, not "no query set"
python tools/run_checks.py --tier all --require-test
```
