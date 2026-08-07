# agent-memory

Declared by `harnesses.json` as `paths.agent_memory`, so the directory is part of
the harness contract and exists whether or not anything has written to it yet.

Empty is the correct state until an adapter writes here. It holds per-agent
durable notes — not workflow state, which is derived from git by
`tools/resume.py`, and not knowledge docs, which are the repo-root files
`knowledge-manager` owns.

A `.gitkeep` stood here until 2026-08-07. An empty tracked file reads as
placeholder rubble to anyone auditing the layer, and `tools/test_no_slop.py`
fails on one; a file saying why the directory exists is the same one line of git
plumbing and answers the question instead of raising it.
