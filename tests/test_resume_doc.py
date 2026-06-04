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


def test_empty_fields_do_not_roundtrip_as_placeholder(tmp_path):
    """Regression: render() used to write '(no task recorded)' to disk, load() read it back
    as real data, so `prev_task or fallback` short-circuited forever and the resume stuck."""
    p = tmp_path / "proj.md"
    ResumeDoc(
        project="proj",
        task="",
        next_step="",
        git={"branch": "main", "uncommitted": 0, "commits": [], "dirty_files": []},
    ).write(p)
    disk = p.read_text()
    assert "(no task recorded)" not in disk  # raw on disk, not the placeholder
    assert "(no next step)" not in disk
    loaded = ResumeDoc.load(p)
    assert loaded.task == ""  # empty round-trips as empty
    assert loaded.next_step == ""
    # so the rolling/LLM-skip fallback chain actually reaches the transcript fallback
    assert (loaded.task or "task from transcript") == "task from transcript"


def test_load_neutralizes_legacy_placeholder_files(tmp_path):
    """Files written by the old buggy render() still hold the placeholder on disk; load()
    must treat it as empty so an already-stuck resume recovers on the next capture."""
    p = tmp_path / "legacy.md"
    p.write_text("# where was i: proj\n\nLast: (no task recorded)\nNext: (no next step)\n\nclean\n")
    loaded = ResumeDoc.load(p)
    assert loaded.task == ""
    assert loaded.next_step == ""


def test_load_does_not_grab_next_line_when_last_is_empty(tmp_path):
    """Regression: the \\s*(.*) regex ate the newline and captured the Next: line as the task."""
    p = tmp_path / "proj.md"
    ResumeDoc(
        project="proj",
        task="",
        next_step="ship it",
        git={"branch": "main", "uncommitted": 0, "commits": [], "dirty_files": []},
    ).write(p)
    loaded = ResumeDoc.load(p)
    assert loaded.task == ""  # not "Next: ship it"
    assert loaded.next_step == "ship it"


def test_render_placeholder_is_display_only(tmp_path):
    """The friendly hint shows in the banner (placeholders=True) but never on disk."""
    doc = ResumeDoc(
        project="proj",
        task="",
        next_step="",
        git={"branch": None, "uncommitted": 0, "commits": [], "dirty_files": []},
    )
    assert "(no task recorded)" in doc.render()  # display default
    assert "(no task recorded)" not in doc.render(placeholders=False)  # disk


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
