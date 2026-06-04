from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from wherewasi import parse_transcript_tail  # noqa: E402


def _write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows))


def test_extracts_latest_user_message_as_rough_task(tmp_path):
    t = tmp_path / "t.jsonl"
    _write_jsonl(
        t,
        [
            {"type": "user", "message": {"role": "user", "content": "fix the auth retry bug"}},
            {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "on it"}]}},
            {"type": "user", "message": {"role": "user", "content": "now handle the timeout case"}},
        ],
    )
    out = parse_transcript_tail(t)
    assert out == {"rough_task": "now handle the timeout case"}  # latest user msg wins


def test_missing_file_returns_empty():
    assert parse_transcript_tail(Path("/nope/missing.jsonl")) == {"rough_task": ""}


def test_multiline_message_collapses_to_one_line(tmp_path):
    """A multi-line user message must collapse to a single line — a newline in rough_task
    would write a multi-line Last:, and load()'s line-anchored regex would truncate it."""
    t = tmp_path / "t.jsonl"
    _write_jsonl(
        t,
        [{"type": "user", "message": {"role": "user", "content": "do step one\nthen step two\n  and three"}}],
    )
    out = parse_transcript_tail(t)
    assert out == {"rough_task": "do step one then step two and three"}
    assert "\n" not in out["rough_task"]
