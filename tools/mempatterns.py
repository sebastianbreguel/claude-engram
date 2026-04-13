#!/usr/bin/env python3
"""mempatterns — Detect emergent patterns from memory.db and maintain an Obsidian wiki."""
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path.home() / ".claude" / "memory.db"
WIKI_DIR = Path.home() / ".claude" / "patterns"

CO_EDIT_THRESHOLD = 5
ERROR_RECURRENCE_THRESHOLD = 3
PROJECT_STREAK_THRESHOLD = 5
TOOL_ANOMALY_FACTOR = 2.0


def _slugify(path: str) -> str:
    """Convert a file path to a wiki-safe slug: src/auth.py → src-auth-py."""
    return re.sub(r"[^a-zA-Z0-9]+", "-", path).strip("-")


class WikiWriter:
    """Writes and maintains Obsidian-compatible wiki pages for patterns."""

    def __init__(self, wiki_dir: Path = WIKI_DIR):
        self.wiki_dir = wiki_dir
        for subdir in ("entities", "patterns", "suggestions", "corrections"):
            (wiki_dir / subdir).mkdir(parents=True, exist_ok=True)

    def write_entity_page(
        self,
        filepath: str,
        sessions: int,
        co_edits: list[tuple[str, int]],
        errors: list[str],
    ) -> None:
        """Write or merge entity page for a file."""
        slug = _slugify(filepath)
        page_path = self.wiki_dir / "entities" / f"{slug}.md"
        today = str(date.today())

        # Defaults — overridden if page already exists
        first_seen = today
        existing_co_edits: dict[str, int] = {}
        existing_errors: list[str] = []

        if page_path.exists():
            content = page_path.read_text()
            # Parse first_seen
            m = re.search(r"first_seen:\s*(\S+)", content)
            if m:
                first_seen = m.group(1)
            # Parse existing co_edits: lines like "- [[slug]] — N sessions"
            for line in content.splitlines():
                cm = re.match(r"-\s+\[\[([^\]]+)\]\]\s+[—-]+\s+(\d+)\s+sessions?", line)
                if cm:
                    existing_co_edits[cm.group(1)] = int(cm.group(2))
            # Parse existing errors: lines under "## Common errors"
            in_errors = False
            for line in content.splitlines():
                if line.strip() == "## Common errors":
                    in_errors = True
                    continue
                if in_errors:
                    if line.startswith("## "):
                        break
                    if line.startswith("- "):
                        existing_errors.append(line[2:])

        # Merge co_edits
        for partner, count in co_edits:
            partner_slug = _slugify(partner)
            existing_co_edits[partner_slug] = count

        # Merge errors (deduplicate)
        all_errors = list(existing_errors)
        for e in errors:
            if e not in all_errors:
                all_errors.append(e)

        # Build page
        co_edit_lines = "\n".join(
            f"- [[{s}]] — {c} sessions" for s, c in existing_co_edits.items()
        )
        error_lines = "\n".join(f"- {e}" for e in all_errors)

        content = f"""---
type: file
first_seen: {first_seen}
last_seen: {today}
sessions: {sessions}
---

# {filepath}

## Co-edited with
{co_edit_lines}

## Common errors
{error_lines}
"""
        page_path.write_text(content)

    def write_pattern_page(
        self,
        name: str,
        kind: str,
        confidence: int,
        threshold: int,
        description: str,
        files: list[str] | None = None,
    ) -> None:
        """Write or update a pattern page, preserving history."""
        page_path = self.wiki_dir / "patterns" / f"{name}.md"
        today = str(date.today())

        first_detected = today
        history_lines: list[str] = []

        if page_path.exists():
            content = page_path.read_text()
            m = re.search(r"first_detected:\s*(\S+)", content)
            if m:
                first_detected = m.group(1)
            # Parse existing history entries
            in_history = False
            for line in content.splitlines():
                if line.strip() == "## History":
                    in_history = True
                    continue
                if in_history:
                    if line.startswith("## "):
                        break
                    if line.startswith("- "):
                        history_lines.append(line[2:])
            # Prepend new reinforcement entry
            history_lines.insert(0, f"{today}: reinforced (confidence {confidence})")
        else:
            history_lines.append(f"{first_detected}: first detected")

        files_section = ""
        if files:
            file_lines = "\n".join(f"- [[{_slugify(f)}]]" for f in files)
            files_section = f"\n## Files\n{file_lines}\n"

        history_text = "\n".join(f"- {h}" for h in history_lines)

        content = f"""---
type: pattern
kind: {kind}
confidence: {confidence}
threshold: {threshold}
first_detected: {first_detected}
last_reinforced: {today}
status: active
---

# {name}

{description}
{files_section}
## History
{history_text}
"""
        page_path.write_text(content)

    def write_index(self) -> None:
        """Write index.md with wikilinks to all entities and patterns."""
        entity_links = "\n".join(
            f"- [[{p.stem}]]" for p in sorted((self.wiki_dir / "entities").glob("*.md"))
        )
        pattern_links = "\n".join(
            f"- [[{p.stem}]]" for p in sorted((self.wiki_dir / "patterns").glob("*.md"))
        )
        content = f"""# Patterns Wiki Index

## Entities
{entity_links}

## Patterns
{pattern_links}
"""
        (self.wiki_dir / "index.md").write_text(content)


class PatternDetector:
    """Detects patterns from memory.db data."""

    def __init__(self, db_path: Path = DB_PATH, wiki_dir: Path = WIKI_DIR):
        self.db_path = db_path
        self.wiki_dir = wiki_dir
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.conn.close()

    def detect_co_edits(self, threshold: int = CO_EDIT_THRESHOLD) -> list[dict]:
        """Find file pairs frequently edited together in the same session."""
        sql = """
            SELECT a.path AS file_a, b.path AS file_b, COUNT(*) AS cnt
            FROM files_touched a
            JOIN files_touched b
                ON a.session_id = b.session_id
               AND a.path < b.path
            WHERE a.action IN ('edit', 'write', 'create')
              AND b.action IN ('edit', 'write', 'create')
            GROUP BY a.path, b.path
            HAVING cnt >= ?
        """
        rows = self.conn.execute(sql, (threshold,)).fetchall()
        return [
            {
                "files": [row["file_a"], row["file_b"]],
                "count": row["cnt"],
                "kind": "co_edit",
            }
            for row in rows
        ]

    def detect_error_recurrence(
        self, threshold: int = ERROR_RECURRENCE_THRESHOLD
    ) -> list[dict]:
        """Find errors appearing across multiple sessions."""
        sql = """
            SELECT content, content_hash, COUNT(*) AS cnt
            FROM facts
            WHERE type = 'error'
            GROUP BY content_hash
            HAVING cnt >= ?
        """
        rows = self.conn.execute(sql, (threshold,)).fetchall()
        return [
            {
                "content": row["content"],
                "hash": row["content_hash"],
                "count": row["cnt"],
                "kind": "error_recurrence",
            }
            for row in rows
        ]

    def detect_project_streaks(
        self, threshold: int = PROJECT_STREAK_THRESHOLD
    ) -> list[dict]:
        """Find consecutive days of activity per project."""
        sql = """
            SELECT project, DATE(captured_at) AS day
            FROM sessions
            GROUP BY project, day
            ORDER BY project, day
        """
        rows = self.conn.execute(sql).fetchall()

        # Group dates by project
        project_days: dict[str, list[date]] = defaultdict(list)
        for row in rows:
            project_days[row["project"]].append(date.fromisoformat(row["day"]))

        results = []
        for project, days in project_days.items():
            days_sorted = sorted(set(days))
            # Find longest consecutive run
            max_streak = 1
            current_streak = 1
            for i in range(1, len(days_sorted)):
                if days_sorted[i] - days_sorted[i - 1] == timedelta(days=1):
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 1
            if max_streak >= threshold:
                results.append(
                    {"project": project, "streak": max_streak, "kind": "project_streak"}
                )
        return results

    def detect_tool_anomalies(self, factor: float = TOOL_ANOMALY_FACTOR) -> list[dict]:
        """Find projects with unusual tool usage compared to global average."""
        sql = """
            SELECT s.project, tu.tool_name, AVG(tu.count) AS proj_avg
            FROM tool_usage tu
            JOIN sessions s ON tu.session_id = s.session_id
            GROUP BY s.project, tu.tool_name
        """
        proj_rows = self.conn.execute(sql).fetchall()

        global_sql = """
            SELECT tu.tool_name, AVG(tu.count) AS global_avg
            FROM tool_usage tu
            GROUP BY tu.tool_name
        """
        global_rows = self.conn.execute(global_sql).fetchall()
        global_avgs = {row["tool_name"]: row["global_avg"] for row in global_rows}

        results = []
        for row in proj_rows:
            g_avg = global_avgs.get(row["tool_name"], 0)
            if g_avg == 0:
                continue
            ratio = row["proj_avg"] / g_avg
            if ratio > factor:
                results.append(
                    {
                        "project": row["project"],
                        "tool": row["tool_name"],
                        "project_avg": row["proj_avg"],
                        "global_avg": g_avg,
                        "ratio": ratio,
                        "kind": "tool_anomaly",
                    }
                )
        return results
