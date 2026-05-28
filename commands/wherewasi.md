---
description: Wipe all engram memory (memory.db rows, executive cache, Claude Code auto-memory files) for the current project
allowed-tools: Bash
argument-hint: "[--yes] [--dry-run]"
---

Run the engram reset CLI scoped to the current working directory. Wipes:

- `memory.db` rows for this cwd (sessions, memories, facts, FTS, compactions)
- executive summary cache (`~/.claude/engram/executive/<slug>.md` + `.prev`)
- Claude Code auto-memory files (`~/.claude/projects/<slug>/memory/*.md`)

Other projects are never touched. The command prompts before deleting unless `--yes` is passed; use `--dry-run` to preview.

Run:

```bash
uv run "$HOME/.claude/tools/engram.py" reset $ARGUMENTS
```

Report the summary output back to the user verbatim so they can see what was (or would be) deleted.
