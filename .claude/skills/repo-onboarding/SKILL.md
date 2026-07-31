---
name: repo-onboarding
model: opus
description: Writes or refreshes a repository's CLAUDE.md — what the project is, its architecture, stack, folder layout, commands, deployment, repo-local rules. Use for "document this repo", "write/update CLAUDE.md", "onboard me", "what is this repo", "what even is this repo", "what does this repo do", "explain this codebase", "nothing here says what this does", when CLAUDE.md or the README is missing, a stub, or contradicts the code, and always after a feature or build lands — one still describing the previous state is a defect. Prefer this over hand-writing project docs yourself. Do NOT use for TASK/PLAN/HANDOFF/LOG/ISSUES/MEMORY — knowledge-manager owns those.
effort: high
argument-hint: "[optional path, default: repo root]"
user-invocable: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - Edit
provides: [conventions]
requires: []
produces_artifact: true
retryable: true
---

# Repo Onboarding

Turns a bootstrapped `CLAUDE.md` skeleton into real content. The Repository
Bootstrap hook creates the skeleton mechanically (it's a deterministic
script, no LLM judgment available at hook time) — this skill is the
reasoning half: verifying what's actually true about the repo and writing
it down concisely.

**Don't do this reflexively at session start.** Only run it once you
actually have enough grounded knowledge of the repo to write something
better than the detected-stack heuristics already in the skeleton — either
because you've just done a research/exploration pass, or because you've
been working in the repo for a while and have accumulated real
understanding. Filling in a stub with guesses is worse than leaving it a
stub.

## Steps

1. **Verify, don't assume.** Read what's actually there: package
   manifests, entry points, existing docs (README, CONTRIBUTING), the test
   suite layout, recent `git log` for what's been actively worked on. Don't
   trust the bootstrap hook's `Detected stack` block blindly — it's marker-file
   heuristics, not verified fact; confirm or correct it. **Exception**: for a
   repo created by `mvp-builder`, don't re-derive the stack from scratch —
   defer to `stack-selector`'s recorded ADR in `decisions/` as the source of
   truth for what was chosen and why; this step's job there is just to
   record that decision into `CLAUDE.md`, not second-guess it.
2. **Fill in each section concisely** — this is a quick-reference doc, not
   a design document:
   - **What this is**: one or two sentences, the actual purpose, not a
     restatement of the repo name.
   - **Architecture**: the real shape (monolith/services/library, major
     modules and how they relate) — only if there's something non-obvious
     to say; skip for a simple/flat project.
   - **Layout**: the directories that matter and what lives in each,
     skipping generated/vendored/noise directories.
   - **Commands**: the actual commands that work in this repo (build,
     test, lint, run) — verified, not guessed from convention.
   - **Deployment**: only if the bootstrap hook detected a real target
     (e.g. Vercel) or one is otherwise confirmed; leave blank otherwise,
     don't invent one.
   - **Rules specific to this codebase**: genuine conventions this repo
     enforces that differ from or add to the global engineering-policy
     standard — not a restatement of that standard. **Exception, for
     portability**: the *load-bearing* global policies (the zero-cost-by-default
     posture, no AI/agent attribution in git history, never push/deploy
     without approval) are worth one line each here even though they're
     not repo-specific — `CLAUDE.md` is a plain file any capable coding
     agent can read *if pointed at it*, while `.claude/skills/` is this
     tool's own private layer nothing else sees. If this repo ever gets
     picked up by a different agent (Codex, or otherwise), the *global*
     `engineering-policy` skill is invisible to it — only what's actually
     written into this repo's own files travels with it. This is the one
     case where restating a global rule locally is correct, not
     duplication. Note the accepted tradeoff: this repo intentionally does
     not maintain an `AGENTS.md` mirror, so a tool that specifically
     auto-discovers that filename by convention won't find this repo's
     context on its own — see this repo's `CLAUDE.md`.
3. **Keep it short.** A long `CLAUDE.md` is loaded into every session in
   this repo — see `engineering-policy`'s context-economy principle. If a
   section has nothing non-obvious to say, leave it empty rather than
   padding it.
4. **Don't invent a decision record or task entry for this** — filling in
   the project handbook isn't itself a decision or a task worth an
   accountability-trail entry, unless something you learn while doing it
   surfaces a real decision that belongs in `decisions/` per
   `knowledge-manager`.
