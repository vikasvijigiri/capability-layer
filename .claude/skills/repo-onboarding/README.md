# Repo Onboarding

Turns a repo's bootstrapped `CLAUDE.md` skeleton (created mechanically by
the Repository Bootstrap hook — marker-file heuristics only, no real
understanding) into real, verified project documentation.

This is the reasoning half of a hook/skill split that shows up throughout
this AgentOS: the hook can detect *that* `CLAUDE.md` is still a stub (it
checks for the "Auto-bootstrapped stub" marker and nudges in
`additionalContext`), but only a skill can write what should actually go
in it, since that requires verifying what's true about the repo rather
than guessing from file-extension heuristics.

Deliberately not run reflexively at every session start — only once
there's enough real context about the repo to write something worth
writing. See [`SKILL.md`](SKILL.md) for the exact steps.
