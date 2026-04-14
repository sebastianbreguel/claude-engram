"""End-to-end contract tests — lock user-visible behavior.

These tests assert on stdout, exit codes, and injected context strings. They do
NOT assert on SQLite column contents or row counts — schema is internal.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "sample_transcript.jsonl"
REPO = Path(__file__).parent.parent


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    """Isolate ~/.claude to a tmp dir per test."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    (fake_home / ".claude").mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    return fake_home


def _memcap(args: list[str], **kw) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", str(REPO / "tools" / "memcapture.py"), *args],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
        **kw,
    )


def test_capture_transcript_exits_zero(tmp_home):
    """Feeding a transcript succeeds — no crash, no schema assertion."""
    result = _memcap(["--transcript", str(FIXTURE)])
    assert result.returncode == 0, f"capture failed: {result.stderr}"


def test_capture_then_stats_reports_activity(tmp_home):
    """After capture, --stats reports non-zero sessions. Contract: the user sees a summary."""
    _memcap(["--transcript", str(FIXTURE)])
    result = _memcap(["--stats"])
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert "session" in combined.lower(), f"stats should mention sessions: {combined!r}"


def test_ingest_digest_then_inject_surfaces_the_memory(tmp_home):
    """End-to-end contract: a digest line about `uv` appears in injected context.

    This is the core user-visible promise of engram: what the LLM learned comes
    back in the next SessionStart context.
    """
    # Capture a session (needed so --ingest-digest has a session_id to attach to).
    _memcap(["--transcript", str(FIXTURE)])

    digest_text = (
        "package_manager | durable | prefers uv over pip\n"
        "current_refactor | ephemeral | removing Docker references from repo\n"
        "\n"
        "HANDOFF: we decided to use uv and drop Docker. Next session should verify install.sh."
    )
    ingest = _memcap(
        ["--ingest-digest", "--session-id", "test-session", "--project", "engram-test"],
        input=digest_text,
    )
    assert ingest.returncode == 0, f"ingest failed: {ingest.stderr}"

    # Contract: the memory surfaces in the injected context string.
    inject = _memcap(["--inject"])
    assert inject.returncode == 0
    assert "uv" in inject.stdout.lower(), f"expected 'uv' in injected context, got: {inject.stdout!r}"


def test_project_scoped_inject_surfaces_handoff(tmp_home):
    """A project-scoped digest with a HANDOFF surfaces when --inject-project matches."""
    _memcap(["--transcript", str(FIXTURE)])
    digest = "test_topic | ephemeral | working on auth refactor\n\nHANDOFF: halfway through extracting auth middleware into its own module."
    _memcap(
        ["--ingest-digest", "--session-id", "s1", "--project", "my-project"],
        input=digest,
    )
    result = _memcap(["--inject", "--inject-project", "my-project"])
    assert result.returncode == 0
    # Handoff content should reach the user's context. Exact wording/placement is free.
    assert "auth" in result.stdout.lower(), f"project-scoped handoff should surface, got: {result.stdout!r}"


def test_semantic_error_regex_does_not_capture_code_lines(tmp_home, tmp_path):
    """After Task 4: lines that LOOK like 'raise ValueError' in a non-error tool_result
    should not surface as error memories. The LLM digest handles semantic judgment.
    """
    fake_transcript = tmp_path / "fake.jsonl"
    fake_transcript.write_text(
        json.dumps({"type": "user", "message": {"content": "edit the file"}})
        + "\n"
        + json.dumps(
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "content": "274:  raise ValueError('boom')\n275:  except Exception as e:",
                            "is_error": False,
                        }
                    ]
                },
            }
        )
        + "\n"
    )
    result = _memcap(["--transcript", str(fake_transcript)])
    assert result.returncode == 0

    # Contract: the --memories surface does not expose these code lines as error facts.
    memories = _memcap(["--memories"])
    assert memories.returncode == 0
    assert "raise ValueError" not in memories.stdout, f"code line should not appear as a memory, got: {memories.stdout!r}"
