from __future__ import annotations

import sqlite3
from pathlib import Path


def write_inventory_report(index_path: Path, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(index_path) as connection:
        summary = _summary(connection)
        extensions = connection.execute(
            """
            SELECT COALESCE(NULLIF(extension, ''), '[none]') AS ext, COUNT(*) AS count
            FROM files
            GROUP BY ext
            ORDER BY count DESC, ext ASC
            LIMIT 20
            """
        ).fetchall()
        empty_notes = connection.execute(
            """
            SELECT path FROM files
            WHERE is_empty_note = 1
            ORDER BY path
            LIMIT 50
            """
        ).fetchall()
        unresolved = connection.execute(
            """
            SELECT file_path, line, target FROM wikilinks
            WHERE resolution_status = 'missing'
            ORDER BY file_path, line
            LIMIT 100
            """
        ).fetchall()
        ambiguous = connection.execute(
            """
            SELECT file_path, line, target, preferred_path, candidate_paths FROM wikilinks
            WHERE resolution_status = 'ambiguous'
            ORDER BY file_path, line
            LIMIT 100
            """
        ).fetchall()
        open_tasks = connection.execute(
            """
            SELECT file_path, line, text FROM tasks
            WHERE done = 0
            ORDER BY file_path, line
            LIMIT 100
            """
        ).fetchall()

    report_path.write_text(
        _render_report(summary, extensions, empty_notes, unresolved, ambiguous, open_tasks),
        encoding="utf-8",
    )


def _summary(connection: sqlite3.Connection) -> dict[str, int | str]:
    scalar_queries = {
        "files": "SELECT COUNT(*) FROM files",
        "markdown_files": "SELECT COUNT(*) FROM files WHERE is_markdown = 1",
        "empty_notes": "SELECT COUNT(*) FROM files WHERE is_empty_note = 1",
        "headings": "SELECT COUNT(*) FROM markdown_headings",
        "wikilinks": "SELECT COUNT(*) FROM wikilinks",
        "unresolved_wikilinks": "SELECT COUNT(*) FROM wikilinks WHERE is_resolved = 0",
        "missing_wikilinks": "SELECT COUNT(*) FROM wikilinks WHERE resolution_status = 'missing'",
        "ambiguous_wikilinks": "SELECT COUNT(*) FROM wikilinks WHERE resolution_status = 'ambiguous'",
        "tags": "SELECT COUNT(*) FROM tags",
        "tasks": "SELECT COUNT(*) FROM tasks",
        "open_tasks": "SELECT COUNT(*) FROM tasks WHERE done = 0",
    }
    summary: dict[str, int | str] = {}
    for key, query in scalar_queries.items():
        summary[key] = int(connection.execute(query).fetchone()[0])
    meta = dict(connection.execute("SELECT key, value FROM scan_meta").fetchall())
    summary["vault_name"] = meta.get("vault_name", "")
    summary["scanned_at"] = meta.get("scanned_at", "")
    return summary


def _render_report(
    summary,
    extensions,
    empty_notes,
    unresolved,
    ambiguous,
    open_tasks,
) -> str:
    lines = [
        "# Brainiac Inventory Report",
        "",
        f"- Vault: {summary['vault_name']}",
        f"- Scanned at: {summary['scanned_at']}",
        f"- Files: {summary['files']}",
        f"- Markdown files: {summary['markdown_files']}",
        f"- Empty notes: {summary['empty_notes']}",
        f"- Headings: {summary['headings']}",
        f"- Wikilinks: {summary['wikilinks']}",
        f"- Missing wikilinks: {summary['missing_wikilinks']}",
        f"- Ambiguous wikilinks: {summary['ambiguous_wikilinks']}",
        f"- Tags: {summary['tags']}",
        f"- Tasks: {summary['tasks']} ({summary['open_tasks']} open)",
        "",
        "## File Extensions",
        "",
    ]
    lines.extend(f"- `{extension}`: {count}" for extension, count in extensions)
    lines.extend(["", "## Empty Notes", ""])
    lines.extend(_path_lines(empty_notes, "No empty notes found."))
    lines.extend(["", "## Missing Wikilinks", ""])
    if unresolved:
        lines.extend(f"- `{path}:{line}` -> `[[{target}]]`" for path, line, target in unresolved)
    else:
        lines.append("No missing wikilinks found.")
    lines.extend(["", "## Ambiguous Wikilinks", ""])
    if ambiguous:
        for path, line, target, preferred_path, candidate_paths in ambiguous:
            candidates = ", ".join(f"`{candidate}`" for candidate in candidate_paths.splitlines())
            lines.append(
                f"- `{path}:{line}` -> `[[{target}]]` preferred: `{preferred_path}`; "
                f"candidates: {candidates}"
            )
    else:
        lines.append("No ambiguous wikilinks found.")
    lines.extend(["", "## Open Tasks", ""])
    if open_tasks:
        lines.extend(f"- `{path}:{line}` {text}" for path, line, text in open_tasks)
    else:
        lines.append("No open tasks found.")
    lines.append("")
    return "\n".join(lines)


def _path_lines(rows, empty_message: str) -> list[str]:
    if not rows:
        return [empty_message]
    return [f"- `{row[0]}`" for row in rows]
