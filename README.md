# WhereWasI

[![tests](https://img.shields.io/github/actions/workflow/status/sebastianbreguel/wherewasi/test.yml?branch=main&label=tests&style=flat)](https://github.com/sebastianbreguel/wherewasi/actions/workflows/test.yml) [![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue?style=flat)](https://www.python.org/) [![license](https://img.shields.io/github/license/sebastianbreguel/wherewasi?style=flat)](LICENSE)

**Claude forgets everything between sessions.** What you were doing, what's next, what broke — gone the moment you close the terminal.

WhereWasI fixes that one thing well. Open a project tomorrow and the first thing you see is *the last task you were on and the next step* — so you pick up immediately. Per-project, automatic, no config.

This is **not** a memory bank. No search, no recall by topic, no accumulated history. Just the current state, to the point.

## What you see

When you open Claude Code in a project, WhereWasI injects a short resume at the top of the session:

```
# where was i: wherewasi  ·  branch wherewasi-v2

Last: Rewriting docs for the resume pivot (README + architecture).
Next: Run the full test suite + ruff, then deploy with install.sh.

3 uncommitted · a1b2c3d docs rewrite
```

Two load-bearing lines — **Last** (where you were) and **Next** (what to do) — over one compact git line for grounding. No file dumps, no stale error echoes (you have `git` for that). Zero latency: it's read from a file, no LLM call at open.

## How it works

WhereWasI is **files + hooks. No database.** One Markdown file per project at `~/.claude/wherewasi/resume/<cwd-slug>.md` (the cwd path, slashes turned to dashes), refreshed as you work:

1. **Every 25 prompts** (`UserPromptSubmit`, **no LLM**) — a cheap refresh of the git line (branch, uncommitted count, last commit). Your `Last`/`Next` narrative is preserved.
2. **On compaction** (`PreCompact`, **LLM**) — `claude --print` reads the transcript tail and rewrites `Last` + `Next` from what you were actually doing.
3. **On session end** (`SessionEnd`, **LLM**) — rewrites `Last` + `Next` when you leave, so a short session that never compacted isn't stale the next time you open. Runs detached, so it never delays your exit.
4. **On session start** (`SessionStart`) — the resume file is read and injected (with git refreshed live). First time in a project? You get a minimal git-derived resume so you never open blank.

Replace semantics: the file always reflects the current state. No history accumulates.

## Install

**Requirements:** [Claude Code](https://docs.anthropic.com/en/docs/claude-code), `python3` (stdlib only — no `uv`, no pip, no deps).

**As a Claude Code plugin (recommended):**

```bash
# In Claude Code:
/plugin install wherewasi@sebastianbreguel/wherewasi
```

**Or clone and run the installer:**

```bash
git clone https://github.com/sebastianbreguel/wherewasi.git
cd wherewasi && ./install.sh
```

> Use **the marketplace install OR `./install.sh`, not both** — each registers the hooks separately, so doing both fires every hook twice (and pays the compaction LLM cost twice).

> **First session in a project:** you get a minimal git-only resume.
> **After you've worked a bit:** the resume fills in with your last task + next step.

```bash
# Uninstall (also cleans up legacy engram data, if any)
cd wherewasi && ./uninstall.sh
```

## Commands

```bash
python3 ~/.claude/tools/wherewasi.py --cwd "$PWD"          # print this project's resume
python3 ~/.claude/tools/wherewasi.py --reset --cwd "$PWD"  # clear this project's resume
```

Or use the slash command: `/wherewasi` (show) · `/wherewasi --reset` (clear).

## Privacy and transparency

Everything lives in `~/.claude/wherewasi/resume/<cwd-slug>.md` (plain Markdown). Nothing leaves your machine except the one LLM call below.

- **Stored**: project name, git branch + uncommitted count + last commit, and the two LLM-written `Last`/`Next` lines.
- **NOT stored**: no full transcripts, no source code, no secrets from `.env`.
- **LLM calls**: on compaction (`PreCompact`) and at session end (`SessionEnd`), `claude --print` (default Sonnet 4.6 — override with `WWI_MODEL`, or set it empty for your account default) reads the **tail of the transcript** to write two lines. It runs under your existing Claude Code login — **no separate API key**. Set `WWI_SKIP_LLM=1` to disable it entirely (the resume still refreshes from git on the rolling path). Note: from **2026-06-15**, `claude -p` on subscription plans (Pro/Max/Team/Enterprise) draws from a monthly [Agent SDK credit](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan) you claim once. If it runs out, the LLM rewrite pauses but the rolling git refresh and session-start display keep working.

## Environment variables

| Variable | Default | Effect |
|---|---|---|
| `WWI_SHOW_BANNER` | `1` | Set to `0` to suppress the visible banner (context still injects) |
| `WWI_SKIP_LLM` | unset | Set to `1` to skip the LLM rewrites (PreCompact + SessionEnd); resume still refreshes from git |
| `WWI_MODEL` | `claude-sonnet-4-6` | Model for the LLM rewrite. Set empty to use your account default |
| `WWI_DIGEST_EVERY` | `25` | Rolling-refresh cadence (prompts per `UserPromptSubmit` refresh) |

## How it compares

| | WhereWasI | claude-mem | OpenMemory | cortex |
|---|---|---|---|---|
| Ambient token cost | **~120** | ~2K+ | ~1K+ (MCP) | ~3K (27 tools) |
| External services | None | Agent SDK worker | Docker + MCP server | MCP server |
| API keys required | No | Yes | No | No |
| Runtime | Python (stdlib) | Node worker | Docker | Rust binary |
| Storage | One MD file/project | SQLite + worker | Docker volume | Rust store |
| Install | `./install.sh` | npm + worker | docker compose | cargo |

## Docs

- [Architecture](docs/architecture.md) — files + hooks, the resume file, capture flow
- [CLI Reference](docs/cli-reference.md) — commands, hooks, environment variables
- [Privacy Policy](docs/privacy.md) — what's stored, what's not, network activity

## License

MIT
