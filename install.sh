#!/usr/bin/env bash
# WhereWasI installer
# Copies the single tool into ~/.claude/ and wires up settings.json hooks.

set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "WhereWasI installer"
echo "============================="
echo ""

command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is required."; exit 1; }

if [ ! -d "$CLAUDE_DIR" ]; then
    echo "Error: ~/.claude/ not found. Install Claude Code first."
    exit 1
fi

echo "[1/3] Creating directories..."
mkdir -p "$CLAUDE_DIR/tools"
mkdir -p "$CLAUDE_DIR/commands"

echo "[2/3] Installing files..."
cp "$SCRIPT_DIR/tools/wherewasi.py" "$CLAUDE_DIR/tools/wherewasi.py"
chmod +x "$CLAUDE_DIR/tools/wherewasi.py"
echo "  -> tools/wherewasi.py (the whole plugin: hooks + CLI)"

# Remove legacy engram artifacts from older installs (memory machinery is gone).
rm -f "$CLAUDE_DIR/tools/engram.py" \
      "$CLAUDE_DIR/tools/memcapture.py" \
      "$CLAUDE_DIR/tools/memdoctor.py" \
      "$CLAUDE_DIR/tools/eval_corrections.py" \
      "$CLAUDE_DIR/tools/eval_warmstart.py" \
      "$CLAUDE_DIR/tools/mempatterns.py"
rm -rf "$CLAUDE_DIR/skills/reflect" "$CLAUDE_DIR/patterns"

if [ -d "$SCRIPT_DIR/commands" ]; then
    for cmd in "$SCRIPT_DIR/commands"/*.md; do
        [ -e "$cmd" ] || continue
        cp "$cmd" "$CLAUDE_DIR/commands/$(basename "$cmd")"
        echo "  -> commands/$(basename "$cmd") (slash command)"
    done
fi
# Drop the old slash command if it lingers from an engram install.
rm -f "$CLAUDE_DIR/commands/engram-reset.md"

echo "[3/3] Configuring hooks..."

SETTINGS="$CLAUDE_DIR/settings.json"
[ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"

python3 << 'PYEOF'
import json
from pathlib import Path

settings_path = Path.home() / ".claude" / "settings.json"
settings = json.loads(settings_path.read_text())
hooks = settings.setdefault("hooks", {})

# Markers for stale registrations to strip: this plugin (idempotent reinstall) + legacy engram.
# Anchor on concrete script filenames (commands look like `python3 .../tools/<name>.py …`) —
# a bare "memcapture" would also strip an UNRELATED user hook whose command merely contains it.
STALE = ("wherewasi.py", "engram.py", "memcapture.py", "mempatterns.py")


def ensure_hook(event_name, command):
    event = hooks.setdefault(event_name, [])
    for entry in event:
        entry["hooks"] = [h for h in entry.get("hooks", []) if not any(m in h.get("command", "") for m in STALE)]
    event[:] = [e for e in event if e.get("hooks")]
    entry = next((e for e in event if e.get("matcher", "") == ""), None)
    if entry is None:
        entry = {"matcher": "", "hooks": []}
        event.append(entry)
    entry.setdefault("hooks", []).append({"type": "command", "command": command})
    print(f"  Added {event_name} hook: wherewasi.py")


ensure_hook("PreCompact", "python3 $HOME/.claude/tools/wherewasi.py on-precompact")
ensure_hook("SessionStart", "python3 $HOME/.claude/tools/wherewasi.py on-session-start")
ensure_hook("UserPromptSubmit", "python3 $HOME/.claude/tools/wherewasi.py on-user-prompt")
ensure_hook("SessionEnd", "python3 $HOME/.claude/tools/wherewasi.py on-session-end")

settings_path.write_text(json.dumps(settings, indent=2) + "\n")
PYEOF

echo ""
echo "Installation complete!"
echo ""
echo "What happens now:"
echo "  - SessionStart: shows your last task + next step for this project (zero latency)"
echo "  - Every 25 prompts: a cheap no-LLM refresh of the resume (git + edited files)"
echo "  - On compaction: the LLM rewrites 'last task / next step' from the transcript"
echo "  - On session end: the same LLM rewrite runs detached, so short sessions stay fresh"
echo ""
echo "Commands:"
echo "  python3 ~/.claude/tools/wherewasi.py --cwd \"\$PWD\"          # print this project's resume"
echo "  python3 ~/.claude/tools/wherewasi.py --reset --cwd \"\$PWD\"  # clear this project's resume"
