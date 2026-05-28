from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from wherewasi import ResumeDoc  # noqa: E402


def test_write_then_load_roundtrip(tmp_path):
    p = tmp_path / "proj.md"
    ResumeDoc(
        project="proj",
        task="doing X",
        next_step="do Y",
        git={"branch": "main", "uncommitted": 2, "commits": ["abc fix"], "dirty_files": ["a.py"]},
        last_error="ninguno",
    ).write(p)
    loaded = ResumeDoc.load(p)
    assert loaded.task == "doing X"
    assert loaded.next_step == "do Y"


def test_rolling_preserves_narrative_when_not_provided(tmp_path):
    p = tmp_path / "proj.md"
    ResumeDoc(
        project="proj",
        task="LLM task",
        next_step="LLM next",
        git={"branch": "main", "uncommitted": 0, "commits": [], "dirty_files": []},
    ).write(p)
    # Rolling capture: fresh git, NO new narrative → carry the old task/next_step.
    prev = ResumeDoc.load(p)
    rolled = ResumeDoc(
        project="proj",
        task=prev.task,
        next_step=prev.next_step,
        git={"branch": "main", "uncommitted": 5, "commits": [], "dirty_files": ["z.py"]},
    )
    rolled.write(p)
    again = ResumeDoc.load(p)
    assert again.task == "LLM task"  # narrative preserved
    assert again.next_step == "LLM next"


def test_write_creates_prev_backup(tmp_path):
    p = tmp_path / "proj.md"
    ResumeDoc(
        project="proj",
        task="v1",
        next_step="",
        git={"branch": None, "uncommitted": 0, "commits": [], "dirty_files": []},
    ).write(p)
    ResumeDoc(
        project="proj",
        task="v2",
        next_step="",
        git={"branch": None, "uncommitted": 0, "commits": [], "dirty_files": []},
    ).write(p)
    assert (tmp_path / "proj.md.prev").exists()
    assert "v1" in (tmp_path / "proj.md.prev").read_text()
