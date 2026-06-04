# Architecture

WhereWasI is a Claude Code plugin with **four hooks and one Python file**. No database, no daemon, no network I/O, no API keys. The entire plugin is `tools/wherewasi.py` (stdlib only).

## File layout (after install)

```
~/.claude/
├── wherewasi/
│   ├── resume/<cwd-slug>.md        # Per-project resume (the thing you see at session start)
│   ├── resume/<cwd-slug>.md.prev   # Previous version (safety net against a half-written file)
│   └── .count-<cwd-slug>           # Per-project prompt counter (drives the rolling refresh)
│
└── tools/
    └── wherewasi.py                # The whole plugin: git context + transcript parser +
                                    #   ResumeDoc + hooks + CLI
```

`<cwd-slug>` is `cwd.replace("/", "-")`, e.g. `/Users/me/proj` → `-Users-me-proj`.

## Hook wiring

Registered in `hooks/hooks.json` (plugin) / `~/.claude/settings.json` (manual install). Four events, one tool:

```json
{
  "hooks": {
    "SessionStart":     [{"hooks": [{"type": "command",
      "command": "python3 ${CLAUDE_PLUGIN_ROOT}/tools/wherewasi.py on-session-start"}]}],
    "PreCompact":       [{"hooks": [{"type": "command",
      "command": "python3 ${CLAUDE_PLUGIN_ROOT}/tools/wherewasi.py on-precompact"}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command",
      "command": "python3 ${CLAUDE_PLUGIN_ROOT}/tools/wherewasi.py on-user-prompt"}]}],
    "SessionEnd":       [{"hooks": [{"type": "command",
      "command": "python3 ${CLAUDE_PLUGIN_ROOT}/tools/wherewasi.py on-session-end"}]}]
  }
}
```

Manual installs use `$HOME/.claude` instead of `$CLAUDE_PLUGIN_ROOT` — both paths work.

## The resume file

One Markdown file per project, **replace-on-write** (no history). The two `Last`/`Next`
lines are the LLM-written narrative (the hero); one compact git line grounds them.

```markdown
# where was i: <project>  ·  branch <branch>

Last: <last task — LLM, from the last compaction>
Next: <next step — LLM>

<N> uncommitted · <hash> <subject>
```

`ResumeDoc` (in `wherewasi.py`) owns this format: `render()` builds the Markdown,
`write()` saves it atomically (write to `.tmp`, then `replace`) after copying the prior
file to `.prev`, and `load()` parses back the project + `Last`/`Next` lines. Git is
**never** parsed back from disk — it's always rebuilt live (see below). There is
deliberately no file list or last-error line: it would just echo `git status` and dilute
the two lines that actually carry intent.

## Orchestration

### SessionStart (`wherewasi.py on-session-start`)

1. Read `cwd` from the hook payload.
2. `render_session_start(cwd)`: load the resume file (narrative from disk) and **refresh
   git live** so the banner reflects the repo's state at open. No file yet (first session)
   → render a minimal git-only resume so you never open blank.
3. Emit the resume as `additionalContext` (Claude sees it) + `systemMessage` banner (you
   see it, unless `WWI_SHOW_BANNER=0`). Zero LLM call, zero latency.

### UserPromptSubmit (`wherewasi.py on-user-prompt`)

1. Bump a **per-project** counter at `~/.claude/wherewasi/.count-<cwd-slug>` (per-cwd, not
   global — a single global counter starves the refresh when two sessions are open at once).
2. Every `WWI_DIGEST_EVERY` prompts (default 25), reset the counter and fire a
   **fire-and-forget detached** rolling capture (`capture-rolling`, **no LLM**): fresh git,
   preserving the prior `Last`/`Next`.
3. Return immediately — the active prompt is never blocked.

### PreCompact (`wherewasi.py on-precompact`)

1. `build_resume_llm(cwd, transcript)`: read the transcript tail (last ~12 KB), send it to
   `claude --print` with the resume prompt, and parse two lines (`TASK:` / `NEXT:`).
2. Write the resume with the fresh narrative + live git fields. Runs **inline** (compaction
   already pauses). On LLM skip/failure, carry the prior `Last`/`Next` forward.

### SessionEnd (`wherewasi.py on-session-end`)

1. Fire a **fire-and-forget detached** `capture-llm` (`build_resume_llm`) — `start_new_session`
   so the LLM call runs *after* the session exits and never delays it.
2. This is the staleness fix: a short session that never compacts still gets a fresh
   `Last`/`Next` written when you leave, so the next open isn't stale. A hard kill that skips
   SessionEnd is still covered by the rolling/compact paths.

## Core units (all in `tools/wherewasi.py`)

| Unit | Responsibility |
|---|---|
| `build_git_context(cwd)` | Branch, uncommitted count, recent commits, dirty files. Best-effort, 2s timeout, empty dict on non-repo. |
| `parse_transcript_tail(path)` | `rough_task` (the last user message) from the tail — a fallback for `Last` when there's no LLM narrative yet. |
| `ResumeDoc` | Load / render / write the resume Markdown, with a `.prev` backup. |
| `capture_rolling(cwd, transcript)` | No-LLM refresh (UserPromptSubmit path). |
| `build_resume_llm(cwd, transcript)` | LLM refresh (PreCompact inline + SessionEnd detached) + `_run_claude` with the `WWI_MODEL` override. |
| `_spawn_capture(kind, cwd, transcript)` | Fire-and-forget detached capture (`start_new_session`) — used by UserPromptSubmit and SessionEnd. |
| `render_session_start(cwd)` | Build the banner/context block; git refreshed live; first-session fallback. |
| `resume_path_for(cwd)` | Map a cwd to its slugged resume path under `~/.claude/wherewasi/resume/`. |
| hooks + `main()` | JSON-in/JSON-out hook handlers and the `show` / `--reset` CLI. |

## Design principles

1. **One job, done well.** Show the last task + next step when you reopen a project. No
   search, no recall, no knowledge base.
2. **Near-zero ambient cost.** ~120 tokens injected at SessionStart, read from a file. The
   only LLM work is `claude --print`, on two paths: PreCompact (inline) and SessionEnd
   (detached). Both are off the prompt hot path; set `WWI_SKIP_LLM=1` to disable them.
3. **Files, not a database.** One Markdown file per project. No SQLite, no schema, no
   migrations, no FTS. Trivial to inspect (`cat`), trivial to reset (`rm`).
4. **Best-effort, never blocks.** Every hook degrades silently: git failure → omit git
   fields; no transcript → minimal resume; LLM failure / `WWI_SKIP_LLM=1` → carry the prior
   narrative; IO failure → the `.prev` backup guards against a half-written file.
5. **Replace semantics.** The resume always reflects the current state; no history
   accumulates and nothing goes stale.
6. **Live git at display time.** The narrative is cached; git is rebuilt on every render, so
   the banner is accurate even if commits/dirty state drifted since the last capture.
7. **100% local.** No external services, no API keys. The LLM call goes through
   `claude --print` using your existing Claude Code auth.

## Why one file

The whole surface is small: read git, read the transcript tail, render a Markdown block,
wire four hooks. Collapsing it into a single `wherewasi.py` (vs. the multi-file
`engram.py` + `memcapture.py` + `memdoctor.py` it replaced) means one place to read, one
place to debug, and no import graph to hold in your head.
