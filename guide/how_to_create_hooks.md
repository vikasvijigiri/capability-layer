# Creating a Hook — Full Guide & Template

A hook is NOT a file Claude reads — it's a JSON config block plus a shell
script. Two pieces, always:

1. **Registration** — a `hooks` block in a settings file, saying *which
   event* fires it and *which command* runs.
2. **The script** — reads JSON on stdin, does deterministic work, exits
   with a code (or prints structured JSON) that tells Claude Code what
   happened.

---

## Step-by-step

### 1. Pick the event
Ask: *at what exact moment does this need to fire?* → see the full event
table in Part 3. Most hooks live on `PreToolUse` (block/allow before
something happens) or `PostToolUse` (react after something happened).

### 2. Pick where it's registered
| Location | Scope | Shareable |
|---|---|---|
| `~/.claude/settings.json` | all your projects | no, local machine only |
| `.claude/settings.json` | this project | yes, commit it |
| `.claude/settings.local.json` | this project | no, gitignored |
| managed policy settings | org-wide | yes, admin-controlled |
| plugin `hooks/hooks.json` | wherever plugin is enabled | yes |
| skill/subagent frontmatter | only while that skill/agent is active | yes |

### 3. Write the registration JSON
```json
{
  "hooks": {
    "<EventName>": [
      {
        "matcher": "Edit|Write",
        "if": "Bash(git *)",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/my-hook.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```
If `settings.json` already has a `hooks` key, add your event as a
**sibling**, not a replacement — don't clobber existing events.

### 4. Write the script
```bash
#!/bin/bash
# .claude/hooks/my-hook.sh

INPUT=$(cat)                                          # JSON on stdin
FIELD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if <condition that should block>; then
  echo "Blocked: <reason Claude will see>" >&2         # stderr = feedback
  exit 2                                                # 2 = block
fi

exit 0                                                  # 0 = no objection
```
Make it executable: `chmod +x .claude/hooks/my-hook.sh`

### 5. Verify and test
```text
/hooks                          # confirms it's registered, shows details
```
Then trigger the condition yourself and check the transcript (`Ctrl+O`).
Debug with `claude --debug-file /tmp/claude.log` if it's not firing.

---

## Part 2 — Full annotated template (copy this)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "if": "Bash(git *)",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/protect-files.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

```bash
#!/bin/bash
# .claude/hooks/protect-files.sh
#
# EXIT CODES:
#   0 = no objection, action proceeds normally
#   2 = BLOCK. stderr becomes Claude's feedback so it can adjust
#   anything else = non-blocking error, action proceeds, warning shown
#
# For finer control than exit codes give you, skip exit 2 and instead
# print structured JSON to stdout with exit 0 (see Part 4).

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

PROTECTED=(".env" "package-lock.json" ".git/")

for pattern in "${PROTECTED[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "Blocked: $FILE_PATH matches protected pattern '$pattern'" >&2
    exit 2
  fi
done

exit 0
```

```bash
chmod +x .claude/hooks/protect-files.sh
```

---

## Part 3 — Event reference (pick the right moment)

| Event | Fires when | Can block? |
|---|---|---|
| `SessionStart` | session begins/resumes | context injection only |
| `UserPromptSubmit` | you submit a prompt, before Claude sees it | yes |
| `PreToolUse` | before any tool call executes | **yes — the main enforcement point** |
| `PermissionRequest` | Claude's about to ask you for permission | can auto-approve/deny |
| `PostToolUse` | after a tool call succeeds | no (already happened) — reactions only |
| `PostToolUseFailure` | after a tool call fails | no |
| `Notification` | Claude sends a notification (needs input, etc.) | no — side effects only |
| `SubagentStart` / `SubagentStop` | a subagent spawns / finishes | yes on Stop-equivalent |
| `Stop` | Claude finishes responding | yes — can force it to keep working |
| `PreCompact` / `PostCompact` | before/after context compaction | injection only |
| `FileChanged` | a watched file changes on disk | reactive only |
| `CwdChanged` | working directory changes (e.g. `cd`) | reactive only |
| `SessionEnd` | session terminates | cleanup only |

Full list has 30+ events (config changes, worktree lifecycle, MCP
elicitation, etc.) — `/hooks` in a session shows every one with a live
count of what's configured.

### Matchers — narrow before you write logic
| Event | Matcher filters on | Example |
|---|---|---|
| `PreToolUse`/`PostToolUse` | tool name | `Bash`, `Edit\|Write`, `mcp__.*` |
| `SessionStart` | how it started | `startup`, `resume`, `compact` |
| `Notification` | notification type | `permission_prompt`, `idle_prompt` |
| `FileChanged` | literal filenames | `.envrc\|.env` |

For argument-level filtering (not just tool name), add `"if": "Bash(git *)"`
— that only spawns the hook process when the actual command matches.

**Never leave a `PermissionRequest` matcher empty if the hook auto-approves**
— an empty matcher there approves *every* prompt, including file writes and
shell commands. Scope it to the exact tool you mean.

---

## Part 4 — Decision control cheat sheet

### Simple: exit codes only
- `exit 0` → proceeds normally
- `exit 2` → blocked, stderr → Claude as feedback
- anything else → non-blocking error, proceeds, warning shown

### Fine-grained: JSON on stdout, exit 0
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Use rg instead of grep for better performance"
  }
}
```
`permissionDecision` values (PreToolUse only): `allow` | `deny` | `ask` | `defer` (non-interactive mode only)

### Auto-approving a permission prompt
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": { "behavior": "allow" }
  }
}
```

### Injecting context into the conversation (UserPromptSubmit)
```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Current branch: release-42. Deploy freeze until Friday."
  }
}
```
Must be nested inside `hookSpecificOutput` — top-level is silently ignored.

**Multiple hooks on the same event**: all run to completion, then combine.
For permission decisions, most restrictive wins: `deny` > `defer` > `ask` >
`allow`. One hook's `deny` never gets silently overridden by another's `allow`.

**Hooks outrank permission modes**: a `PreToolUse` deny blocks the tool even
under `bypassPermissions` — this is your one true unbypassable guardrail.

---

## Part 5 — Beyond command hooks

| Type | When to use |
|---|---|
| `"type": "command"` (default) | deterministic logic — the vast majority of hooks |
| `"type": "http"` | POST event JSON to a shared service, e.g. team-wide audit logging |
| `"type": "mcp_tool"` | call a tool on an already-connected MCP server |
| `"type": "prompt"` | single LLM call for a judgment decision ("are all tasks actually done?") |
| `"type": "agent"` | multi-turn subagent verification that needs to inspect files/run commands |

```json
// prompt hook example — Stop event, model checks completion
{
  "hooks": {
    "Stop": [{ "hooks": [{
      "type": "prompt",
      "prompt": "Check if all tasks are complete. If not, respond with {\"ok\": false, \"reason\": \"what remains\"}."
    }]}]
  }
}
```

Default to `command`. Reach for `prompt`/`agent` only when the decision
genuinely can't be expressed as deterministic logic.

---

## Part 6 — Guardrails before you ship one

- **Stop-hook loop guard**: check `stop_hook_active` in the input, exit 0
  early if `true` — Claude Code caps consecutive blocks at 8, but design
  for it explicitly rather than relying on the cap.
- **`PostToolUse` can't undo** — the action already happened. Use
  `PreToolUse` for anything that must never occur at all.
- **Review before adding to a shared repo** — hooks run arbitrary code with
  your permissions; never build one that echoes untrusted input into a
  shell command unescaped.
- **Absolute paths or `$CLAUDE_PROJECT_DIR`** — a hook that works from your
  cwd today breaks the moment someone runs Claude Code from elsewhere.

## Where to verify
`https://code.claude.com/docs/en/hooks-guide.md` (walkthroughs) ·
`https://code.claude.com/docs/en/hooks.md` (full event schemas & JSON reference)