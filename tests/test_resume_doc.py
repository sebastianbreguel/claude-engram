from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from wherewasi import ResumeDoc, build_resume_llm, resume_path_for  # noqa: E402


def test_write_then_load_roundtrip(tmp_path):
    p = tmp_path / "proj.md"
    ResumeDoc(
        project="proj",
        task="doing X",
        next_step="do Y",
        git={"branch": "main", "uncommitted": 2, "commits": ["abc fix"], "dirty_files": ["a.py"]},
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


def test_llm_skip_preserves_prior_narrative(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("WWI_SKIP_LLM", "1")
    repo = tmp_path / "r"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.co"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True, capture_output=True)
    (repo / "f").write_text("x")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "i"], cwd=repo, check=True, capture_output=True)
    path = resume_path_for(str(repo))
    ResumeDoc(
        project="r",
        task="prior task",
        next_step="prior next",
        git={"branch": "main", "uncommitted": 0, "commits": [], "dirty_files": []},
    ).write(path)
    build_resume_llm(str(repo), transcript=None)  # LLM skipped → narrative kept
    loaded = ResumeDoc.load(path)
    assert loaded.task == "prior task"
    assert loaded.next_step == "prior next"
