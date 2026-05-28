from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
from wherewasi import _counter_path, _read_counter, _write_counter  # noqa: E402


def test_counter_is_per_cwd_and_independent(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    a = _counter_path("/Users/me/projA")
    b = _counter_path("/Users/me/projB")
    assert a != b
    # Writing projA's counter must not touch projB's — two open sessions in different
    # projects can't starve each other's rolling refresh.
    _write_counter(a, 7)
    assert _read_counter(a) == 7
    assert _read_counter(b) == 0


def test_counter_missing_reads_zero(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert _read_counter(_counter_path("/never/written")) == 0
