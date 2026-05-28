from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from wherewasi import capture_rolling, render_session_start, resume_path_for  # noqa: E402


def _git(cwd, *a):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True)


def test_resume_path_is_slugged_under_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    p = resume_path_for("/Users/me/proj")
    assert p == tmp_path / ".claude" / "wherewasi" / "resume" / "-Users-me-proj.md"


def test_rolling_then_render(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t.co")
    _git(repo, "config", "user.name", "t")
    (repo / "f.py").write_text("x")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "init")
    capture_rolling(str(repo), transcript=None)
    out = render_session_start(str(repo))
    assert "where was i" in out
    assert "branch main" in out


def test_render_first_session_no_file_uses_git(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    repo = tmp_path / "repo2"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "dev")
    _git(repo, "config", "user.email", "t@t.co")
    _git(repo, "config", "user.name", "t")
    (repo / "f.py").write_text("x")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "seed")
    out = render_session_start(str(repo))  # no resume file yet
    assert "branch dev" in out
