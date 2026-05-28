from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from wherewasi import parse_transcript_tail  # noqa: E402


def _write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows))


def test_extracts_task_edited_files_and_error(tmp_path):
    t = tmp_path / "t.jsonl"
    _write_jsonl(
        t,
        [
            {"type": "user", "message": {"role": "user", "content": "fix the auth retry bug"}},
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "tool_use", "name": "Edit", "input": {"file_path": "src/auth.py"}}],
                },
            },
            {
                "type": "user",
                "message": {"role": "user", "content": [{"type": "tool_result", "content": "Traceback: ValueError: bad token"}]},
            },
        ],
    )
    out = parse_transcript_tail(t)
    assert "auth retry" in out["rough_task"]
    assert "src/auth.py" in out["edited_files"]
    assert "ValueError" in out["last_error"]


def test_missing_file_returns_empty():
    out = parse_transcript_tail(Path("/nope/missing.jsonl"))
    assert out == {"rough_task": "", "edited_files": [], "last_error": ""}
