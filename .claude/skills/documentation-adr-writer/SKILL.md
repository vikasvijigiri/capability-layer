---
name: documentation-adr-writer
model: opus
description: Writes an Architecture Decision Record (context, decision, alternatives considered, consequences) for a design choice. Use for "record this decision", "write an ADR", "document why we chose X over Y", "architecture decision record", "write down why we chose this", "we'll forget why we did it this way", "document the tradeoff". Prefer this over a commit message - an unrecorded decision becomes an unexplainable constraint later. Do NOT use for a trivial/reversible choice with no real tradeoff to record. Writes the ADR body; `knowledge-manager` owns where decision records live and their required format — follow it rather than inventing a layout.
---

# ADR Writer Skill

Writes a standard-format Architecture Decision Record: context, decision, alternatives considered, consequences.

## When to use
- "record this decision", "write an ADR", "why did we choose X over Y"

## Steps
1. State `context` — the problem forcing a decision.
2. State the `decision` and each rejected `alternatives` entry with why it lost.
3. State consequences (what this makes easier/harder going forward).
4. Return the `adr_document` in the repo's ADR numbering/format.

## Notes
An ADR without at least one rejected alternative isn't recording a decision — it's just narrating what happened.

## Routing

**Validator (required): `.claude/validators/documentation-link-check.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/documentation-structure.md` - a matching blueprint takes precedence over a hand-built solution.

For the multi-step case, `.claude/workflows/documentation-release.md` orchestrates this end to end. It is a document to follow, not an executable - there is no workflow runtime in Claude Code.
