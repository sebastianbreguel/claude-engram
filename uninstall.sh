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

# Anchor on concrete script filenames so we never strip an unrelated user hook that merely
# contains a substring like "memcapture". Keep this list identical to install.sh's STALE.
MARKERS = ("wherewasi.py", "engram.py", "memcapture.py", "mempatterns.py")


def strip(event_name):
    event = hooks.get(event_name, [])
    for entry in event:
        entry["hooks"] = [h for h in entry.get("hooks", []) if not any(m in h.get("command", "") for m in MARKERS)]
    hooks[event_name] = [e for e in event if e.get("hooks")]
    if not hooks[event_name]:
        del hooks[event_name]


for ev in ("PreCompact", "SessionStart", "UserPromptSubmit", "SessionEnd"):
    strip(ev)

settings_path.write_text(json.dumps(settings, indent=2) + "\n")
print("  Hooks removed from settings.json")
PYEOF

# Codex CLI cleanup (no-op if Codex was never wired). Resume data under
# ~/.claude/wherewasi was already removed above (shared state).
CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"
if [ -d "$CODEX_DIR" ]; then
    rm -f "$CODEX_DIR/tools/wherewasi.py"
    if [ -f "$CODEX_DIR/hooks.json" ]; then
        python3 - "$CODEX_DIR" << 'PYEOF'
import json, sys
from pathlib import Path

hp = Path(sys.argv[1]) / "hooks.json"
data = json.loads(hp.read_text())
hooks = data.get("hooks", {})
for ev in ("SessionStart", "UserPromptSubmit", "PreCompact"):
    arr = hooks.get(ev, [])
    for entry in arr:
        entry["hooks"] = [h for h in entry.get("hooks", []) if "wherewasi.py" not in h.get("command", "")]
    hooks[ev] = [e for e in arr if e.get("hooks")]
    if not hooks[ev]:
        del hooks[ev]
hp.write_text(json.dumps(data, indent=2) + "\n")
print("  Hooks removed from Codex hooks.json")
PYEOF
    fi
fi

echo "[3/3] Done."
