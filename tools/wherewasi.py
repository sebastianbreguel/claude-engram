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


_TAIL_LINES = 400  # cap how far back we scan


def parse_transcript_tail(transcript_path: Path) -> dict:
    """Pull a rough task (the last substantive user message) from the tail of a transcript
    JSONL. Used only as a fallback for `Last` when there is no LLM narrative yet.
    Best-effort; empty on any failure."""
    try:
        lines = Path(transcript_path).read_text(errors="ignore").splitlines()[-_TAIL_LINES:]
    except Exception:
        return {"rough_task": ""}
    rough_task = ""
    for ln in lines:
        try:
            obj = json.loads(ln)
        except Exception:
            continue
        content = obj.get("message", {}).get("content")
        if obj.get("type") == "user" and isinstance(content, str) and content.strip():
            rough_task = " ".join(content.split())[:200]  # latest wins; collapse newlines → one line
    return {"rough_task": rough_task}


# Display-only placeholders for an empty Last/Next. Shown in the banner / additionalContext,
# NEVER written to disk: render(placeholders=False) serializes raw values so an empty resume
# round-trips as empty instead of persisting this text as if it were a real task (which made
# `prev_task or fallback` short-circuit forever — the resume stuck on "(no task recorded)").
_NO_TASK = "(no task recorded)"
_NO_NEXT = "(no next step)"


class ResumeDoc:
    """Per-project resume. Markdown on disk, replace-on-write with a .prev backup.
    `Last`/`Next` (LLM narrative) are passed in by the caller; rolling captures
    preserve them by loading the prior doc and passing its values back in."""

    def __init__(self, project: str, task: str, next_step: str, git: dict):
        self.project = project
        self.task = (task or "").strip()
        self.next_step = (next_step or "").strip()
        self.git = git or {}

    def render(self, *, placeholders: bool = True) -> str:
        """Lean banner: the two narrative lines are the hero (Last = where you were,
        Next = what to do), with one compact git line for grounding. No file list, no
        last-error echo — the dev has `git` for that; padding it dilutes the two lines
        that actually carry intent.

        placeholders=True (display): show a friendly hint for an empty Last/Next.
        placeholders=False (disk, via write()): serialize raw values so an empty field
        round-trips as empty — writing the hint to disk made load() read it back as a
        real task and the fallback chain never recovered."""
        g = self.git
        branch = g.get("branch")
        head = f"# where was i: {self.project}"
        if branch:
            head += f"  ·  branch {branch}"
        last = self.task or (_NO_TASK if placeholders else "")
        nxt = self.next_step or (_NO_NEXT if placeholders else "")
        lines = [
            head,
            "",
            f"Last: {last}",
            f"Next: {nxt}",
        ]
        if branch:
            commits = g.get("commits") or []
            detail = f"{g.get('uncommitted', 0)} uncommitted" if g.get("uncommitted", 0) else "clean"
            if commits:
                detail += f" · {commits[0]}"
            lines += ["", detail]
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
        tmp.write_text(self.render(placeholders=False))  # raw values on disk; hints are display-only
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path) -> "ResumeDoc":
        text = Path(path).read_text()

        def _field(label: str) -> str:
            # Line-anchored on purpose: [ \t]* (not \s*, which eats the newline and would
            # capture the *next* field when this one is empty) and [^\n]* (not .*, so the
            # value can't bleed past its own line).
            m = re.search(rf"^{label}:[ \t]*([^\n]*)$", text, re.MULTILINE)
            return m.group(1).strip() if m else ""

        proj = ""
        m = re.search(r"^# where was i:\s*([^·]+)", text, re.MULTILINE)
        if m:
            proj = m.group(1).strip()
        task, next_step = _field("Last"), _field("Next")
        # Neutralize the display placeholders that pre-fix files wrote to disk, so an
        # already-stuck "(no task recorded)" resume recovers instead of shadowing the fallback.
        return cls(
            project=proj,
            task="" if task == _NO_TASK else task,
            next_step="" if next_step == _NO_NEXT else next_step,
            git={},
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
    tail = parse_transcript_tail(transcript) if transcript else {"rough_task": ""}
    prev_task = prev_next = ""
    if path.exists():
        prev = ResumeDoc.load(path)
        prev_task, prev_next = prev.task, prev.next_step
    task = prev_task or tail["rough_task"]  # keep LLM narrative if present
    ResumeDoc(project=_project_name(cwd), task=task, next_step=prev_next, git=git).write(path)


def render_session_start(cwd: str) -> str:
    """Render the resume for SessionStart. Git is refreshed LIVE so the banner
    reflects the repo's state at open (commits/dirty drift since last capture)."""
    path = resume_path_for(cwd)
    git = build_git_context(cwd)
    if path.exists():
        try:
            doc = ResumeDoc.load(path)  # narrative (Last/Next) from disk
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
    cmd = [claude_bin, "--print", "--strict-mcp-config"]
    model = os.environ.get("WWI_MODEL", "claude-sonnet-4-6")
    if model:
        cmd += ["--model", model]
    cmd += ["-p", prompt]
    # Mark the child so its SessionStart/SessionEnd hooks no-op. Without this, the
    # headless `claude --print` is itself a Claude session: its SessionEnd fires our
    # hook → spawns another `claude --print` → infinite loop.
    env = {**os.environ, "WWI_CHILD": "1"}
    try:
        r = subprocess.run(cmd, input=chunk, capture_output=True, text=True, timeout=timeout, env=env)
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
    tail = parse_transcript_tail(transcript) if transcript else {"rough_task": ""}
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
    num = "\033[1;33m"  # bold yellow — branch
    dim = "\033[90m"  # gray — separators + the git grounding line
    label = "\033[1;32m"  # bold green — the load-bearing Last/Next labels
    val = "\033[97m"  # bright white — Last/Next values
    sep = f" {dim}·{reset} "
    lines = []
    for ln in text.splitlines():
        if ln.startswith("# where was i:"):
            parts = [p.strip() for p in ln[len("# where was i:") :].strip().split("·")]
            head = f"{brand}where was i{reset}{dim}:{reset} {proj}{parts[0]}{reset}"
            if len(parts) > 1:
                head += sep + f"{dim}branch{reset} {num}{parts[1].replace('branch ', '', 1)}{reset}"
            lines.append(head)
        elif ln.startswith("Last:"):
            lines.append(f"{label}Last:{reset} {val}{ln.split(':', 1)[1].strip()}{reset}")
        elif ln.startswith("Next:"):
            lines.append(f"{label}Next:{reset} {val}{ln.split(':', 1)[1].strip()}{reset}")
        elif ln.strip():  # the git grounding line → low-signal gray
            lines.append(f"{dim}{ln}{reset}")
        else:
            lines.append(ln)  # blank line
    return "\n".join(lines)


def _spawn_capture(kind: str, cwd: str, transcript: Path | None) -> None:
    """Fire-and-forget detached capture (`capture-rolling` or `capture-llm`).
    start_new_session=True so it survives the hook process exiting and the session
    tearing down — the LLM capture must outlive a SessionEnd."""
    try:
        subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__)),
                kind,
                "--cwd",
                cwd,
                *(["--transcript", str(transcript)] if transcript else []),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


def _hooks_disabled() -> bool:
    """True when running inside a headless `claude --print` (the LLM capture in
    _run_claude). Guards every hook entrypoint against re-entrant recursion. Two
    independent signals so one host change can't silently reopen the fork-bomb loop:
      1. WWI_CHILD=1 — we set this on the spawned `claude`; its hooks inherit it.
      2. CLAUDE_CODE_ENTRYPOINT=sdk-cli — the headless `--print` entrypoint; the
         user's interactive session is `cli`, so this never suppresses real sessions."""
    return os.environ.get("WWI_CHILD") == "1" or os.environ.get("CLAUDE_CODE_ENTRYPOINT") == "sdk-cli"


def on_session_start() -> int:
    if _hooks_disabled():
        return _emit()
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
    if _hooks_disabled():
        return _emit(event="UserPromptSubmit")
    p = _read_payload()
    cwd = p.get("cwd") or ""
    if not cwd:
        return _emit(event="UserPromptSubmit")
    cpath = _counter_path(cwd)
    n = _read_counter(cpath) + 1
    if n >= _DIGEST_EVERY:
        _write_counter(cpath, 0)
        _spawn_capture("capture-rolling", cwd, _find_transcript(p))  # no LLM, fire-and-forget
    else:
        _write_counter(cpath, n)
    return _emit(event="UserPromptSubmit")


def on_precompact() -> int:
    if _hooks_disabled():
        return 0
    p = _read_payload()
    cwd = p.get("cwd") or ""
    if cwd:
        try:
            build_resume_llm(cwd, _find_transcript(p))  # inline: compaction already pauses
        except Exception:
            pass
    return 0


def on_session_end() -> int:
    # Refresh the narrative when you leave, so short sessions that never compact aren't
    # stale next open. Fire-and-forget + detached: the LLM call runs AFTER the session
    # exits (never hangs it). Hard-kills that skip SessionEnd are covered by rolling/compact.
    if _hooks_disabled():
        return 0
    p = _read_payload()
    cwd = p.get("cwd") or ""
    if cwd:
        _spawn_capture("capture-llm", cwd, _find_transcript(p))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wherewasi")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("on-session-start")
    sub.add_parser("on-user-prompt")
    sub.add_parser("on-precompact")
    sub.add_parser("on-session-end")
    for name in ("capture-rolling", "capture-llm"):
        cp = sub.add_parser(name)
        cp.add_argument("--cwd", required=True)
        cp.add_argument("--transcript")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--cwd", dest="show_cwd")
    args = parser.parse_args(argv)

    if args.cmd == "on-session-start":
        return on_session_start()
    if args.cmd == "on-user-prompt":
        return on_user_prompt()
    if args.cmd == "on-precompact":
        return on_precompact()
    if args.cmd == "on-session-end":
        return on_session_end()
    if args.cmd in ("capture-rolling", "capture-llm"):
        try:
            t = Path(args.transcript) if args.transcript else None
            (capture_rolling if args.cmd == "capture-rolling" else build_resume_llm)(args.cwd, t)
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
