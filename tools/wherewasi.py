from __future__ import annotations

import subprocess
from pathlib import Path


def _git_out(cwd: str, args: list[str], timeout: int = 2) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
        # rstrip only: porcelain status keeps a leading column space we must not eat.
        return r.stdout.rstrip() if r.returncode == 0 else ""
    except Exception:
        return ""


def build_git_context(cwd: str) -> dict:
    """Cheap git snapshot for the resume. Best-effort; empty fields on any failure."""
    empty = {"branch": None, "uncommitted": 0, "commits": [], "dirty_files": []}
    if not cwd or not (Path(cwd) / ".git").exists():
        return empty
    branch = _git_out(cwd, ["rev-parse", "--abbrev-ref", "HEAD"]) or None
    status = _git_out(cwd, ["status", "--porcelain"])
    dirty_lines = [ln for ln in status.splitlines() if ln.strip()]
    dirty_files = [ln[3:].strip() for ln in dirty_lines][:10]
    commits = [c for c in _git_out(cwd, ["log", "--oneline", "-5"]).splitlines() if c]
    return {
        "branch": branch,
        "uncommitted": len(dirty_lines),
        "commits": commits,
        "dirty_files": dirty_files,
    }
