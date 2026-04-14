#!/usr/bin/env bash
# SessionStart hook — injects:
#   - additionalContext (invisible, for Claude): learned memories, handoff, snapshot
#   - systemMessage (visible to user, between welcome box and prompt): compact banner
# Gated: banner only renders when ENGRAM_SHOW_BANNER=1 (default off).

set -euo pipefail

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd // ""')

PROJECT_KEY=""
if [ -n "$CWD" ]; then
    PROJECT_KEY=$(echo "$CWD" | sed 's|/|-|g')
fi

TOOL="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/memcapture.py"

if [ -n "$PROJECT_KEY" ]; then
    CONTEXT=$(uv run "$TOOL" --inject --inject-project="$PROJECT_KEY" 2>/dev/null || true)
else
    CONTEXT=$(uv run "$TOOL" --inject 2>/dev/null || true)
fi

BANNER=""
if [ "${ENGRAM_SHOW_BANNER:-1}" = "1" ]; then
    DISPLAY_NAME=""
    if [ -n "$CWD" ]; then
        DISPLAY_NAME=$(basename "$CWD")
    fi
    if [ -n "$PROJECT_KEY" ]; then
        BANNER=$(uv run "$TOOL" --banner --banner-project="$PROJECT_KEY" --banner-name="$DISPLAY_NAME" 2>/dev/null || true)
    else
        BANNER=$(uv run "$TOOL" --banner 2>/dev/null || true)
    fi
fi

jq -n \
    --arg ctx "$CONTEXT" \
    --arg banner "$BANNER" \
    '{
        continue: true,
        suppressOutput: true,
        hookSpecificOutput: {
            hookEventName: "SessionStart",
            additionalContext: $ctx
        }
    } + (if $banner == "" then {} else {systemMessage: $banner} end)'

exit 0
