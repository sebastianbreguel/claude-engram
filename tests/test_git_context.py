from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from wherewasi import build_git_context  # noqa: E402


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def test_git_context_reports_branch_commit_and_dirty(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@t.co")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.txt").write_text("hello")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-qm", "first commit")
    (tmp_path / "a.txt").write_text("changed")  # dirty

    ctx = build_git_context(str(tmp_path))
    assert ctx["branch"] == "main"
    assert ctx["uncommitted"] == 1
    assert any("first commit" in c for c in ctx["commits"])
    assert "a.txt" in ctx["dirty_files"]


def test_git_context_on_non_repo_returns_empty(tmp_path):
    ctx = build_git_context(str(tmp_path))
    assert ctx == {"branch": None, "uncommitted": 0, "commits": [], "dirty_files": []}
