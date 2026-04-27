#!/usr/bin/env python3
"""eval_corrections — sample corrections from memory.db and build an annotation template.

Usage:
    uv run tools/eval_corrections.py sample [--n 30] [--out eval/corrections_sample.md]
    uv run tools/eval_corrections.py score  [--in eval/corrections_sample.md]
"""
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

from __future__ import annotations

import argparse
import json
import random
import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".claude" / "memory.db"
DEFAULT_OUT = Path("eval/corrections_sample.md")
WINDOW = 8


def extract_text(message_field) -> str:
    if isinstance(message_field, str):
        return message_field
    if isinstance(message_field, list):
        parts = []
        for item in message_field:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts)
    if isinstance(message_field, dict):
        return extract_text(message_field.get("content", ""))
    return ""


def read_transcript_context(transcript_path: str, source_line: int, window: int = WINDOW) -> dict:
    p = Path(transcript_path)
    if not p.exists():
        return {"error": f"transcript missing: {transcript_path}"}

    lines = p.read_text(errors="replace").splitlines()
    if not lines:
        return {"error": "empty transcript"}

    idx = max(0, min(source_line - 1, len(lines) - 1))
    start = max(0, idx - window)
    end = min(len(lines), idx + window + 1)

    nearest_user = None
    for i in range(idx, start - 1, -1):
        try:
            row = json.loads(lines[i])
        except json.JSONDecodeError:
            continue
        if row.get("type") == "user":
            msg = row.get("message", {})
            text = extract_text(msg.get("content", msg))
            if text and not text.startswith("<") and "tool_result" not in text[:40]:
                nearest_user = {"line": i + 1, "text": text.strip()[:800]}
                break

    fallback_lines = []
    for i in range(start, end):
        try:
            row = json.loads(lines[i])
        except json.JSONDecodeError:
            continue
        rtype = row.get("type", "?")
        if rtype in ("user", "assistant"):
            msg = row.get("message", {})
            text = extract_text(msg.get("content", msg))
            if text:
                fallback_lines.append(f"L{i + 1} [{rtype}]: {text.strip()[:200]}")

    return {
        "source_line": source_line,
        "nearest_user": nearest_user,
        "window": fallback_lines[:10],
    }


def sample(n: int, out: Path, db_path: Path = DB_PATH) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    sql = """
        SELECT f.id, f.session_id, f.source_line, f.content, f.created_at,
               s.transcript_path, s.project
        FROM facts f
        JOIN sessions s ON f.session_id = s.session_id
        WHERE f.type = 'correction'
        ORDER BY RANDOM()
        LIMIT ?
    """
    rows = conn.execute(sql, (n,)).fetchall()

    out.parent.mkdir(parents=True, exist_ok=True)

    header = [
        "# Corrections eval — precision sample",
        "",
        f"Sampled {len(rows)} corrections from memory.db.",
        "",
        "For each row, fill `accurate` (Y/N) and `gist` (one line).",
        "- **Y** = captured content matches what the user actually corrected",
        "- **N** = captured content hallucinates / misreads / is unrelated",
        "- **?** = unclear, skip",
        "",
        "Then run: `uv run tools/eval_corrections.py score --in eval/corrections_sample.md`",
        "",
        "---",
        "",
    ]

    entries = []
    for i, row in enumerate(rows, 1):
        ctx = read_transcript_context(row["transcript_path"], row["source_line"] or 1)
        entry = [
            f"## [{i}/{len(rows)}] fact_id={row['id']}",
            "",
            f"- session: `{row['session_id']}`",
            f"- project: `{row['project']}`",
            f"- created: `{row['created_at']}`",
            f"- source_line: `{row['source_line']}`",
            "",
            "**Captured correction:**",
            "```",
            row["content"],
            "```",
            "",
        ]
        if "error" in ctx:
            entry.append(f"*Transcript unavailable:* {ctx['error']}")
            entry.append("")
        else:
            nu = ctx.get("nearest_user")
            if nu:
                entry.append(f"**Nearest user message** (line {nu['line']}):")
                entry.append("```")
                entry.append(nu["text"])
                entry.append("```")
                entry.append("")
            entry.append("**Window around source_line:**")
            entry.append("```")
            for line in ctx.get("window", []):
                entry.append(line)
            entry.append("```")
            entry.append("")
        entry.append("**Annotation:**")
        entry.append("- accurate: <Y|N|?>")
        entry.append("- gist: <one-line summary of the real correction, if any>")
        entry.append("")
        entry.append("---")
        entry.append("")
        entries.extend(entry)

    out.write_text("\n".join(header + entries))
    print(f"Wrote {len(rows)} entries to {out}")


def score(path: Path) -> None:
    if not path.exists():
        print(f"Not found: {path}")
        return
    text = path.read_text()
    y = n = q = 0
    for line in text.splitlines():
        stripped = line.strip().lower()
        if stripped.startswith("- accurate:"):
            val = stripped.split(":", 1)[1].strip()
            if val == "y":
                y += 1
            elif val == "n":
                n += 1
            elif val == "?":
                q += 1
    total_judged = y + n
    precision = (y / total_judged) if total_judged else 0.0
    print(f"Y={y}  N={n}  ?={q}  judged={total_judged}")
    print(f"precision = {precision:.2%}")
    gate = "PROCEED to fase 1" if precision >= 0.70 else "FIX memcapture first"
    print(f"gate (>=70%): {gate}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="eval_corrections — sample and score")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("sample", help="sample N corrections and write an annotation template")
    ps.add_argument("--n", type=int, default=30)
    ps.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ps.add_argument("--db-path", type=Path, default=DB_PATH)
    ps.add_argument("--seed", type=int, default=None)

    psc = sub.add_parser("score", help="score an annotated template")
    psc.add_argument("--in", dest="inp", type=Path, default=DEFAULT_OUT)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.cmd == "sample":
        if args.seed is not None:
            random.seed(args.seed)
        sample(args.n, args.out, args.db_path)
    elif args.cmd == "score":
        score(args.inp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
