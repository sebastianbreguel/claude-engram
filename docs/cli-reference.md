# CLI Reference

Everything goes through `wherewasi.py`, installed at `~/.claude/tools/wherewasi.py` (or
`${CLAUDE_PLUGIN_ROOT}/tools/wherewasi.py` when used as a Claude Code plugin). It's stdlib
only — run it with `python3`, no `uv`, no venv, no dependencies.

## Everyday commands

```bash
# Print this project's resume (same block injected at session start)
python3 ~/.claude/tools/wherewasi.py --cwd "$PWD"

# Clear this project's resume (removes the .md and its .prev backup)
python3 ~/.claude/tools/wherewasi.py --reset --cwd "$PWD"
```

`--cwd` defaults to the current directory if omitted. Only the given project is affected;
other projects are never touched.

Slash command equivalents: `/wherewasi` (show) · `/wherewasi --reset` (clear).

## Hooks (called by Claude Code, not by you)

```bash
python3 ~/.claude/tools/wherewasi.py on-session-start   # SessionStart: render the resume
python3 ~/.claude/tools/wherewasi.py on-user-prompt     # UserPromptSubmit: bump counter, rolling refresh
python3 ~/.claude/tools/wherewasi.py on-precompact      # PreCompact: LLM rewrite of last task / next step (inline)
python3 ~/.claude/tools/wherewasi.py on-session-end     # SessionEnd: LLM rewrite when you leave (detached)
python3 ~/.claude/tools/wherewasi.py capture-rolling --cwd PATH [--transcript FILE]   # rolling refresh, no LLM (spawned by on-user-prompt)
python3 ~/.claude/tools/wherewasi.py capture-llm --cwd PATH [--transcript FILE]       # LLM refresh (spawned by on-session-end)
```

To test a hook by hand, pipe the payload to stdin:

```bash
echo '{"session_id":"abc","cwd":"'"$PWD"'"}' | \
  python3 ~/.claude/tools/wherewasi.py on-session-start
```

## Environment variables

| Variable | Default | Effect |
|---|---|---|
| `WWI_SHOW_BANNER` | `1` | Set to `0` to suppress the visible banner (context still injects) |
| `WWI_SKIP_LLM` | unset | Set to `1` to skip the LLM rewrites (PreCompact + SessionEnd); resume still refreshes from git |
| `WWI_MODEL` | `claude-sonnet-4-6` | Model for the LLM rewrite. Set empty to use your account default |
| `WWI_DIGEST_EVERY` | `25` | Rolling-refresh cadence (prompts per `UserPromptSubmit` refresh) |

## Token budget

| Component | Tokens | When |
|---|---|---|
| SessionStart inject | ~120 | Every session (the resume block) |
| `on-user-prompt` rolling refresh | 0 | Every 25 prompts, no LLM |
| `on-precompact` LLM rewrite | ~3-5K input | On compaction, one inline `claude --print` call |
| `on-session-end` LLM rewrite | ~3-5K input | When a session ends, one detached `claude --print` call |
| **Ambient total** | **~120** | **Per session** (LLM rewrites are off the prompt hot path; `WWI_SKIP_LLM=1` disables them) |

## Manual install

If you skip `install.sh`:

```bash
cp tools/wherewasi.py ~/.claude/tools/
chmod +x ~/.claude/tools/wherewasi.py
cp commands/wherewasi.md ~/.claude/commands/
```

Then add these hooks to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {"matcher": "", "hooks": [
        {"type": "command", "command": "python3 $HOME/.claude/tools/wherewasi.py on-session-start"}
      ]}
    ],
    "PreCompact": [
      {"matcher": "", "hooks": [
        {"type": "command", "command": "python3 $HOME/.claude/tools/wherewasi.py on-precompact"}
      ]}
    ],
    "UserPromptSubmit": [
      {"matcher": "", "hooks": [
        {"type": "command", "command": "python3 $HOME/.claude/tools/wherewasi.py on-user-prompt"}
      ]}
    ],
    "SessionEnd": [
      {"matcher": "", "hooks": [
        {"type": "command", "command": "python3 $HOME/.claude/tools/wherewasi.py on-session-end"}
      ]}
    ]
  }
}
```

## Upgrading from engram

WhereWasI is the renamed, rewritten successor to **engram** (which was a generalized memory
bank: SQLite, FTS5 search, learned preferences). Re-running `./install.sh` strips the old
`engram.py` hook entries from `settings.json` and registers the `wherewasi.py` hooks.

`uninstall.sh` removes both WhereWasI's files and the legacy engram data
(`~/.claude/memory.db`, `~/.claude/engram/`, the old tools and counter). Your old
`memory.db` is no longer read by anything — WhereWasI starts fresh from git + transcripts.
