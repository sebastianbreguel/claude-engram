---
description: Show where you left off in this project (last task + next step), or --reset to clear it
allowed-tools: Bash
argument-hint: "[--reset]"
---

WhereWasI keeps a per-project resume of the last thing you were doing and the next step.

- No arguments → print this project's resume (the same block injected at session start).
- `--reset` → clear this project's resume file (`~/.claude/wherewasi/resume/<slug>.md` + `.prev`).

Only the current working directory is affected; other projects are never touched.

Run:

```bash
python3 "$HOME/.claude/tools/wherewasi.py" --cwd "$PWD" $ARGUMENTS
```

Report the output back to the user verbatim.
