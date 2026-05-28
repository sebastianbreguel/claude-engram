from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "tools" / "wherewasi.py"


def _run(args, stdin, home):
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        input=stdin,
        capture_output=True,
        text=True,
        env={"HOME": str(home), "PATH": "/usr/bin:/bin", "WWI_SKIP_LLM": "1"},
    )


def test_session_start_emits_additionalcontext(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True, capture_output=True)
    payload = json.dumps({"session_id": "s1", "cwd": str(repo)})
    r = _run(["on-session-start"], payload, tmp_path)
    out = json.loads(r.stdout)
    assert out["continue"] is True
    assert "where was i" in out["hookSpecificOutput"]["additionalContext"]


def test_user_prompt_malformed_stdin_does_not_crash(tmp_path):
    r = _run(["on-user-prompt"], "not json", tmp_path)
    assert json.loads(r.stdout)["continue"] is True


def test_cli_reset_removes_file(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (tmp_path / ".claude" / "wherewasi" / "resume").mkdir(parents=True)
    f = tmp_path / ".claude" / "wherewasi" / "resume" / (str(repo).replace("/", "-") + ".md")
    f.write_text("# where was i: repo\n")
    _run(["--reset", "--cwd", str(repo)], "", tmp_path)
    assert not f.exists()
