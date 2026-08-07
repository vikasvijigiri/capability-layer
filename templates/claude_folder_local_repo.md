your-project/
├── CLAUDE.md                    # Project instructions, loaded every session
├── CLAUDE.local.md              # Personal overrides for this project (gitignore it)
├── .mcp.json                    # Team-shared MCP servers
├── .worktreeinclude             # Gitignored files to copy into new worktrees
└── .claude/
    ├── settings.json            # Permissions, hooks, env vars, model default — committed
    ├── settings.local.json      # Personal overrides for this project — gitignored
    ├── rules/                   # Topic-scoped instructions (optionally path-gated)
    │   ├── testing.md
    │   └── api-design.md
    ├── skills/                  # Reusable prompts/workflows, invoked as /name or auto-invoked
    │   └── code-review/          # references/ holds the security, supply-chain,
    │                              # performance and accessibility lenses
    │       ├── SKILL.md
    │       └── checklist.md     # any bundled supporting files
    ├── commands/                # Single-file prompts (legacy mechanism, skills now preferred)
    │   └── fix-issue.md
    ├── agents/                  # Subagents with their own context window & tools
    │   └── code-reviewer.md
    ├── workflows/                # Dynamic workflow scripts (.js) saved from /workflows
    │   └── release.js
    ├── output-styles/           # Project-shared output styles (rare — usually personal)
    └── agent-memory/            # Persistent memory for subagents (memory: project)
        └── code-reviewer/
            └── MEMORY.md