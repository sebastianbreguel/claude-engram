# Privacy Policy

**WhereWasI** — Per-project resume for Claude Code sessions

Author: Sebastian Breguel
License: MIT
Last updated: 2026-05-28

---

## Summary

WhereWasI is a local plugin. All data stays on your machine in plain Markdown files.
Nothing is sent to external servers except a single LLM call (see below) that runs through
your own Claude Code login.

## What is stored

WhereWasI keeps one Markdown file per project at `~/.claude/wherewasi/resume/<slug>.md`
(plus a `.prev` backup). It contains:

- **Project name and git context** — branch, uncommitted count, the last commit hash/subject
- **`Last` / `Next`** — two LLM-written sentences: the last task and the next step

## What is NOT stored

- Full conversation transcripts
- Source code or file content
- Secrets, API keys, or values from `.env` files
- Any history — the resume is replaced on each write, never appended

## Network activity

WhereWasI makes **zero network requests** of its own. No telemetry, no analytics, no
tracking.

The only LLM interaction is `claude --print --model claude-sonnet-4-6`, invoked on **two
paths**: on compaction (`PreCompact`) and when a session ends (`SessionEnd`). Each reads the
**tail of the current transcript** (last ~12 KB) and returns two lines (last task / next
step). It runs locally through your own Claude Code session and uses whatever model and
billing you already have configured — **no separate API key**. Set `WWI_SKIP_LLM=1` to
disable both entirely; the resume still refreshes from git on the rolling path. Override the
model with `WWI_MODEL` (set empty for your account default).

## Third-party services

None. WhereWasI has no external dependencies (Python stdlib only), no cloud backend, and no
third-party integrations.

## Data control

Your data is yours. You can:

- **Inspect** it any time: `cat ~/.claude/wherewasi/resume/<slug>.md`
- **Clear** a project's resume: `python3 ~/.claude/tools/wherewasi.py --reset --cwd "$PWD"` (or `/wherewasi --reset`)
- **Delete all** resume data: `rm -rf ~/.claude/wherewasi/`
- **Uninstall** cleanly: `./uninstall.sh` removes the tool, hooks, all resume data, and any legacy engram data

## Children's privacy

WhereWasI is a developer tool. It is not directed at children under 13.

## Changes to this policy

Updates will be posted in this file within the repository. No retroactive changes to data
handling will be made without a new release.

## Contact

For questions about this policy, open an issue on the [GitHub repository](https://github.com/sebastianbreguel/wherewasi) or contact Sebastian Breguel directly.
