#!/usr/bin/env bash
# WhereWasI uninstaller
# Removes the tool, the slash command, and hook registrations.
# Also cleans up legacy engram data (memory.db, engram/ cache) from older installs.

set -euo pipefail

CLAUDE_DIR="$HOME/.claude"

echo "WhereWasI uninstaller"
echo "================================"
echo ""

echo "[1/3] Removing files..."
rm -f "$CLAUDE_DIR/tools/wherewasi.py"
rm -f "$CLAUDE_DIR/commands/wherewasi.md"
# WhereWasI resume data + counter
rm -rf "$CLAUDE_DIR/wherewasi"
rm -f "$CLAUDE_DIR/.wherewasi-prompt-count"
# Legacy engram artifacts (tools, skills, data) from older installs
rm -f "$CLAUDE_DIR/tools/engram.py" \
      "$CLAUDE_DIR/tools/memcapture.py" \
      "$CLAUDE_DIR/tools/memdoctor.py" \
      "$CLAUDE_DIR/tools/eval_corrections.py" \
      "$CLAUDE_DIR/tools/eval_warmstart.py" \
      "$CLAUDE_DIR/tools/mempatterns.py" \
      "$CLAUDE_DIR/commands/engram-reset.md" \
      "$CLAUDE_DIR/memory.db" \
      "$CLAUDE_DIR/.engram-prompt-count"
rm -rf "$CLAUDE_DIR/engram" "$CLAUDE_DIR/skills/reflect"
echo "  Removed tools, command, resume data, and legacy engram data."

echo "[2/3] Removing hook configuration..."
python3 << 'PYEOF'
import json
from pathlib import Path

settings_path = Path.home() / ".claude" / "settings.json"
if not settings_path.exists():
    raise SystemExit(0)

settings = json.loads(settings_path.read_text())
hooks = settings.get("hooks", {})

MARKERS = ("wherewasi.py", "engram.py", "memcapture", "memdigest", "memcompact", "mempatterns")


def strip(event_name):
    event = hooks.get(event_name, [])
    for entry in event:
        entry["hooks"] = [h for h in entry.get("hooks", []) if not any(m in h.get("command", "") for m in MARKERS)]
    hooks[event_name] = [e for e in event if e.get("hooks")]
    if not hooks[event_name]:
        del hooks[event_name]


for ev in ("PreCompact", "SessionStart", "UserPromptSubmit"):
    strip(ev)

settings_path.write_text(json.dumps(settings, indent=2) + "\n")
print("  Hooks removed from settings.json")
PYEOF

echo "[3/3] Done."
