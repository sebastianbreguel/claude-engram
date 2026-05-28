from __future__ import annotations

import json
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


_EDIT_TOOLS = {"Edit", "Write", "NotebookEdit"}
_TAIL_LINES = 400  # cap how far back we scan


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(b.get("text", ""))
        return " ".join(parts)
    return ""


def parse_transcript_tail(transcript_path: Path) -> dict:
    """Pull a rough task (last substantive user msg), edited files, and last error
    from the tail of a transcript JSONL. Best-effort; empty fields on any failure."""
    empty = {"rough_task": "", "edited_files": [], "last_error": ""}
    try:
        lines = Path(transcript_path).read_text(errors="ignore").splitlines()[-_TAIL_LINES:]
    except Exception:
        return empty

    rough_task = ""
    edited: list[str] = []
    last_error = ""
    for ln in lines:
        try:
            obj = json.loads(ln)
        except Exception:
            continue
        msg = obj.get("message", {})
        content = msg.get("content")
        if obj.get("type") == "user" and isinstance(content, str) and content.strip():
            rough_task = content.strip()[:200]  # latest wins
        if obj.get("type") == "assistant" and isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in _EDIT_TOOLS:
                    fp = (b.get("input") or {}).get("file_path")
                    if fp and fp not in edited:
                        edited.append(fp)
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    txt = _text_of(b.get("content"))
                    if any(k in txt for k in ("Error", "Traceback", "error:", "Exception")):
                        last_error = txt.strip()[:200]  # latest wins
    return {"rough_task": rough_task, "edited_files": edited[-10:], "last_error": last_error}
