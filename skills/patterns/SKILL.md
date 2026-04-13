---
name: patterns
description: "Explore detected workflow patterns, review skill suggestions, and manage the patterns wiki. Use when asked to 'show patterns', 'what patterns', 'suggest skills', 'pattern report', or '/patterns'. Also trigger when the user asks about their workflow habits or wants to understand recurring behaviors across sessions."
---
# Patterns: Workflow Pattern Explorer

You are reviewing the user's detected workflow patterns from their session history.

The patterns wiki lives at `~/.claude/patterns/` and is updated automatically on each context compaction. It tracks:
- **File co-edits** — files that are always modified together
- **Error recurrence** — errors that keep appearing across sessions
- **Project streaks** — consecutive days of activity on a project
- **Tool anomalies** — unusual tool usage patterns per project

## Step 1: Show current patterns

Run:
```
uv run ~/.claude/tools/mempatterns.py --report
```

Show the results to the user, grouped by kind.

## Step 2: Check for skill suggestions

Run:
```
uv run ~/.claude/tools/mempatterns.py --suggest
```

If there are pending suggestions, present them conversationally:
- Explain what the pattern is and why it might be useful as a skill
- **Ask the user** what they'd want the skill to do — don't just generate it
- Shape the skill together through conversation
- Only create the SKILL.md once the user agrees on what it should do

## Step 3: Handle user requests

If the user asks to:
- **Forget a pattern**: `uv run ~/.claude/tools/mempatterns.py --forget <name>`
- **See wiki stats**: `uv run ~/.claude/tools/mempatterns.py --status`
- **Rebuild from scratch**: `uv run ~/.claude/tools/mempatterns.py --rebuild`

## Key rule

**Never create or update a skill without asking first.** The system proposes, the user decides. Always.
