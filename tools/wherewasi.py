from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
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


class ResumeDoc:
    """Per-project resume. Markdown on disk, replace-on-write with a .prev backup.
    `Last`/`Next` (LLM narrative) are passed in by the caller; rolling captures
    preserve them by loading the prior doc and passing its values back in."""

    def __init__(
        self,
        project: str,
        task: str,
        next_step: str,
        git: dict,
        last_error: str = "none",
        edited_files: list[str] | None = None,
    ):
        self.project = project
        self.task = (task or "").strip()
        self.next_step = (next_step or "").strip()
        self.git = git or {}
        self.last_error = (last_error or "none").strip()
        self.edited_files = edited_files or []

    def render(self) -> str:
        g = self.git
        branch = g.get("branch") or "?"
        commits = g.get("commits") or []
        last_commit = commits[0] if commits else "—"
        files = ", ".join(dict.fromkeys((g.get("dirty_files") or []) + self.edited_files))[:300]
        lines = [
            f"# where was i: {self.project}  ·  branch {branch}",
            "",
            f"Last: {self.task or '(no task recorded)'}",
            f"Next: {self.next_step or '(no next step)'}",
            "",
            f"Repo: {branch} · {g.get('uncommitted', 0)} uncommitted · last: {last_commit}",
        ]
        if files:
            lines.append(f"Files: {files}")
        lines.append(f"Last error: {self.last_error or 'none'}")
        return "\n".join(lines) + "\n"

    def write(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            try:
                path.with_suffix(path.suffix + ".prev").write_text(path.read_text())
            except Exception:
                pass
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(self.render())
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path) -> "ResumeDoc":
        text = Path(path).read_text()

        def _field(label: str) -> str:
            m = re.search(rf"^{label}:\s*(.*)$", text, re.MULTILINE)
            return m.group(1).strip() if m else ""

        proj = ""
        m = re.search(r"^# where was i:\s*([^·]+)", text, re.MULTILINE)
        if m:
            proj = m.group(1).strip()
        return cls(
            project=proj,
            task=_field("Last"),
            next_step=_field("Next"),
            git={},
            last_error=_field("Last error"),
        )


def resume_path_for(cwd: str) -> Path:
    slug = cwd.replace("/", "-")
    return Path.home() / ".claude" / "wherewasi" / "resume" / f"{slug}.md"


def _project_name(cwd: str) -> str:
    return Path(cwd).name or cwd


def capture_rolling(cwd: str, transcript: Path | None) -> None:
    """No-LLM refresh: fresh git + transcript-tail fields, preserving prior narrative."""
    path = resume_path_for(cwd)
    git = build_git_context(cwd)
    tail = parse_transcript_tail(transcript) if transcript else {"rough_task": "", "edited_files": [], "last_error": ""}
    prev_task = prev_next = ""
    if path.exists():
        prev = ResumeDoc.load(path)
        prev_task, prev_next = prev.task, prev.next_step
    task = prev_task or tail["rough_task"]  # keep LLM narrative if present
    ResumeDoc(
        project=_project_name(cwd),
        task=task,
        next_step=prev_next,
        git=git,
        last_error=tail["last_error"] or "none",
        edited_files=tail["edited_files"],
    ).write(path)


def render_session_start(cwd: str) -> str:
    """Render the resume for SessionStart. Git is refreshed LIVE so the banner
    reflects the repo's state at open (commits/dirty drift since last capture)."""
    path = resume_path_for(cwd)
    git = build_git_context(cwd)
    if path.exists():
        try:
            doc = ResumeDoc.load(path)  # narrative (Last/Next/error) from disk
            doc.git = git  # refresh git live
            doc.project = _project_name(cwd)  # authoritative; avoids `·`-truncation from load
            return doc.render()
        except Exception:
            pass
    # First session / no file → minimal git-only resume.
    return ResumeDoc(project=_project_name(cwd), task="", next_step="", git=git).render()


RESUME_PROMPT = (
    "You are summarizing a coding session so the developer can resume next time. "
    "From the transcript, output exactly two lines:\n"
    "TASK: <one sentence — what they were actively doing>\n"
    "NEXT: <one sentence — the most likely next step>\n"
    "Be concrete and terse. No preamble."
)


def _run_claude(prompt: str, chunk: str, timeout: int = 120) -> str:
    if os.environ.get("WWI_SKIP_LLM") == "1":
        return ""
    claude_bin = shutil.which("claude")
    if not claude_bin:
        return ""
    cmd = [claude_bin, "--print"]
    model = os.environ.get("WWI_MODEL", "claude-sonnet-4-6")
    if model:
        cmd += ["--model", model]
    cmd += ["-p", prompt]
    try:
        r = subprocess.run(cmd, input=chunk, capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def _parse_llm_resume(out: str) -> tuple[str, str]:
    task = next_step = ""
    for ln in out.splitlines():
        if ln.upper().startswith("TASK:"):
            task = ln.split(":", 1)[1].strip()
        elif ln.upper().startswith("NEXT:"):
            next_step = ln.split(":", 1)[1].strip()
    return task, next_step


def build_resume_llm(cwd: str, transcript: Path | None) -> None:
    """Compaction path: LLM polishes task/next_step. On skip/failure, carry prior narrative."""
    path = resume_path_for(cwd)
    git = build_git_context(cwd)
    tail = parse_transcript_tail(transcript) if transcript else {"rough_task": "", "edited_files": [], "last_error": ""}
    prev_task = prev_next = ""
    if path.exists():
        prev = ResumeDoc.load(path)
        prev_task, prev_next = prev.task, prev.next_step

    chunk = ""
    if transcript:
        try:
            chunk = Path(transcript).read_text(errors="ignore")[-12000:]
        except Exception:
            chunk = ""
    task, next_step = _parse_llm_resume(_run_claude(RESUME_PROMPT, chunk)) if chunk else ("", "")

    ResumeDoc(
        project=_project_name(cwd),
        task=task or prev_task or tail["rough_task"],
        next_step=next_step or prev_next,
        git=git,
        last_error=tail["last_error"] or "none",
        edited_files=tail["edited_files"],
    ).write(path)


def _read_payload() -> dict:
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def _emit(additional_context: str = "", event: str = "SessionStart", banner: str = "") -> int:
    out: dict = {"continue": True}
    if additional_context:
        out["hookSpecificOutput"] = {"hookEventName": event, "additionalContext": additional_context}
        out["suppressOutput"] = True
    if banner:
        out["systemMessage"] = banner
    print(json.dumps(out))
    return 0


_DIGEST_EVERY = int(os.environ.get("WWI_DIGEST_EVERY", "25"))


def _counter_path(cwd: str) -> Path:
    """One prompt counter per project (cwd). A single global counter starves the
    rolling refresh when two sessions are open at once; per-cwd matches the per-project
    resume and never thrashes."""
    slug = cwd.replace("/", "-")
    return Path.home() / ".claude" / "wherewasi" / f".count-{slug}"


def _read_counter(path: Path) -> int:
    try:
        return int(path.read_text().strip())
    except Exception:
        return 0


def _write_counter(path: Path, n: int) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(n))
    except Exception:
        pass


def _find_transcript(payload: dict) -> Path | None:
    tp = payload.get("transcript_path")
    return Path(tp) if tp and Path(tp).exists() else None


def _colorize_banner(text: str) -> str:
    """ANSI-color the SessionStart banner. Applied to the visible systemMessage only —
    the resume file and additionalContext stay plain (no ANSI on disk / in model context).
    Honors NO_COLOR and TERM=dumb."""
    if os.environ.get("NO_COLOR") or os.environ.get("TERM", "") == "dumb":
        return text
    reset = "\033[0m"
    brand = "\033[1;35m"  # bold magenta — "where was i"
    proj = "\033[1;36m"  # bold cyan — project name
    num = "\033[1;33m"  # bold yellow — branch / counts
    dim = "\033[90m"  # gray — separators, low-signal lines
    label = "\033[1;32m"  # bold green — the load-bearing Last/Next labels
    val = "\033[97m"  # bright white — Last/Next values
    err = "\033[1;31m"  # bold red — a real last error
    sep = f" {dim}·{reset} "
    lines = []
    for ln in text.splitlines():
        if ln.startswith("# where was i:"):
            parts = [p.strip() for p in ln[len("# where was i:") :].strip().split("·")]
            head = f"{brand}where was i{reset}{dim}:{reset} {proj}{parts[0]}{reset}"
            if len(parts) > 1:
                head += sep + f"{dim}branch{reset} {num}{parts[1].replace('branch ', '', 1)}{reset}"
            lines.append(head)
        elif ln.startswith("Last error:"):
            v = ln.split(":", 1)[1].strip()
            lines.append(f"{dim}Last error:{reset} {dim if v == 'none' else err}{v}{reset}")
        elif ln.startswith("Last:"):
            lines.append(f"{label}Last:{reset} {val}{ln.split(':', 1)[1].strip()}{reset}")
        elif ln.startswith("Next:"):
            lines.append(f"{label}Next:{reset} {val}{ln.split(':', 1)[1].strip()}{reset}")
        elif ln.startswith("Repo:") or ln.startswith("Files:"):
            lines.append(f"{dim}{ln}{reset}")
        else:
            lines.append(ln)
    return "\n".join(lines)


def on_session_start() -> int:
    p = _read_payload()
    cwd = p.get("cwd") or ""
    if not cwd:
        return _emit()
    try:
        ctx = render_session_start(cwd)
    except Exception:
        ctx = ""
    show = os.environ.get("WWI_SHOW_BANNER", "1") == "1"
    return _emit(ctx, event="SessionStart", banner=_colorize_banner(ctx) if show else "")


def on_user_prompt() -> int:
    p = _read_payload()
    cwd = p.get("cwd") or ""
    if not cwd:
        return _emit(event="UserPromptSubmit")
    cpath = _counter_path(cwd)
    n = _read_counter(cpath) + 1
    if n >= _DIGEST_EVERY:
        _write_counter(cpath, 0)
        transcript = _find_transcript(p)
        # fire-and-forget rolling capture (no LLM)
        try:
            subprocess.Popen(
                [
                    sys.executable,
                    str(Path(__file__)),
                    "capture-rolling",
                    "--cwd",
                    cwd,
                    *(["--transcript", str(transcript)] if transcript else []),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
    else:
        _write_counter(cpath, n)
    return _emit(event="UserPromptSubmit")


def on_precompact() -> int:
    p = _read_payload()
    cwd = p.get("cwd") or ""
    if cwd:
        try:
            build_resume_llm(cwd, _find_transcript(p))
        except Exception:
            pass
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wherewasi")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("on-session-start")
    sub.add_parser("on-user-prompt")
    sub.add_parser("on-precompact")
    cr = sub.add_parser("capture-rolling")
    cr.add_argument("--cwd", required=True)
    cr.add_argument("--transcript")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--cwd", dest="show_cwd")
    args = parser.parse_args(argv)

    if args.cmd == "on-session-start":
        return on_session_start()
    if args.cmd == "on-user-prompt":
        return on_user_prompt()
    if args.cmd == "on-precompact":
        return on_precompact()
    if args.cmd == "capture-rolling":
        try:
            t = Path(args.transcript) if args.transcript else None
            capture_rolling(args.cwd, t)
        except Exception:
            pass
        return 0
    # bare CLI: reset or show
    cwd = args.show_cwd or os.getcwd()
    if args.reset:
        resume_path_for(cwd).unlink(missing_ok=True)
        resume_path_for(cwd).with_suffix(".md.prev").unlink(missing_ok=True)
        print("resume cleared")
        return 0
    print(render_session_start(cwd))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
