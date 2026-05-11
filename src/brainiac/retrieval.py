from __future__ import annotations

import sqlite3
import re
from dataclasses import dataclass
from pathlib import Path


TOKEN_RE = re.compile(r"[\w/-]+", re.UNICODE)


@dataclass(frozen=True)
class LinkInfo:
    line: int
    target: str
    resolution_status: str
    resolved_path: str | None
    preferred_path: str | None
    candidate_paths: tuple[str, ...]


@dataclass(frozen=True)
class TaskInfo:
    line: int
    done: bool
    text: str


@dataclass(frozen=True)
class Inspection:
    path: str
    size_bytes: int
    is_empty_note: bool
    headings: tuple[tuple[int, int, str], ...]
    tags: tuple[str, ...]
    tasks: tuple[TaskInfo, ...]
    outgoing_links: tuple[LinkInfo, ...]
    backlinks: tuple[LinkInfo, ...]


@dataclass(frozen=True)
class RelatedResult:
    path: str
    score: int
    reasons: tuple[str, ...]


def inspect_path(index_path: Path, note_path: str) -> Inspection:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    with sqlite3.connect(index_path) as connection:
        file_row = connection.execute(
            """
            SELECT path, size_bytes, is_empty_note
            FROM files
            WHERE path = ?
            """,
            (note_path,),
        ).fetchone()
        if file_row is None:
            raise FileNotFoundError(f"Path not found in index: {note_path}")

        headings = tuple(
            connection.execute(
                """
                SELECT line, level, text
                FROM markdown_headings
                WHERE file_path = ?
                ORDER BY line
                """,
                (note_path,),
            ).fetchall()
        )
        tags = tuple(
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT tag FROM tags WHERE file_path = ? ORDER BY tag",
                (note_path,),
            ).fetchall()
        )
        tasks = tuple(
            TaskInfo(line=row[0], done=bool(row[1]), text=row[2])
            for row in connection.execute(
                "SELECT line, done, text FROM tasks WHERE file_path = ? ORDER BY line",
                (note_path,),
            ).fetchall()
        )
        outgoing_links = _link_rows(
            connection.execute(
                """
                SELECT line, target, resolution_status, resolved_path, preferred_path, candidate_paths
                FROM wikilinks
                WHERE file_path = ?
                ORDER BY line, target
                """,
                (note_path,),
            ).fetchall()
        )
        backlinks = _link_rows(
            connection.execute(
                """
                SELECT line, target, resolution_status, resolved_path, preferred_path, candidate_paths
                FROM wikilinks
                WHERE resolved_path = ?
                ORDER BY file_path, line
                """,
                (note_path,),
            ).fetchall()
        )

    return Inspection(
        path=file_row[0],
        size_bytes=int(file_row[1]),
        is_empty_note=bool(file_row[2]),
        headings=headings,
        tags=tags,
        tasks=tasks,
        outgoing_links=outgoing_links,
        backlinks=backlinks,
    )


def read_path(
    index_path: Path,
    note_path: str,
    *,
    section: str | None = None,
    max_chars: int = 6000,
) -> str:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    with sqlite3.connect(index_path) as connection:
        vault_root = _vault_root(connection)
        file_exists = connection.execute("SELECT 1 FROM files WHERE path = ?", (note_path,)).fetchone()
        if file_exists is None:
            raise FileNotFoundError(f"Path not found in index: {note_path}")
        headings = connection.execute(
            """
            SELECT line, level, text
            FROM markdown_headings
            WHERE file_path = ?
            ORDER BY line
            """,
            (note_path,),
        ).fetchall()

    absolute_path = _resolve_vault_file(vault_root, note_path)
    text = absolute_path.read_text(encoding="utf-8", errors="replace")
    if section:
        text = _extract_section(text, headings, section)
    if len(text) > max_chars:
        return text[:max_chars].rstrip() + "\n...[truncated]"
    return text


def related_paths(index_path: Path, note_path: str, *, limit: int = 10) -> tuple[RelatedResult, ...]:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    with sqlite3.connect(index_path) as connection:
        file_exists = connection.execute("SELECT 1 FROM files WHERE path = ?", (note_path,)).fetchone()
        if file_exists is None:
            raise FileNotFoundError(f"Path not found in index: {note_path}")

        scores: dict[str, int] = {}
        reasons: dict[str, list[str]] = {}

        def add(path: str | None, score: int, reason: str) -> None:
            if not path or path == note_path:
                return
            scores[path] = scores.get(path, 0) + score
            reasons.setdefault(path, []).append(reason)

        for resolved_path, preferred_path, status in connection.execute(
            """
            SELECT resolved_path, preferred_path, resolution_status
            FROM wikilinks
            WHERE file_path = ?
            """,
            (note_path,),
        ).fetchall():
            if resolved_path:
                add(resolved_path, 100, "outgoing link")
            elif status == "ambiguous":
                add(preferred_path, 60, "ambiguous link preferred candidate")

        for file_path in connection.execute(
            "SELECT file_path FROM wikilinks WHERE resolved_path = ?",
            (note_path,),
        ).fetchall():
            add(file_path[0], 90, "backlink")

        note_tags = {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT tag FROM tags WHERE file_path = ?",
                (note_path,),
            ).fetchall()
        }
        for tag in note_tags:
            tag_score = _tag_score(tag)
            for file_path in connection.execute(
                """
                SELECT DISTINCT file_path
                FROM tags
                WHERE tag = ? AND file_path != ?
                """,
                (tag, note_path),
            ).fetchall():
                add(file_path[0], tag_score, f"shared tag {tag}")

        folder = Path(note_path).parent.as_posix()
        if folder != ".":
            folder_prefix = folder + "/"
            for file_path in connection.execute(
                """
                SELECT path
                FROM files
                WHERE is_markdown = 1 AND path != ? AND path LIKE ?
                LIMIT 100
                """,
                (note_path, folder_prefix + "%"),
            ).fetchall():
                add(file_path[0], 5, "same folder")

        source_terms = _search_terms(
            connection.execute(
                """
                SELECT path_text, title, headings
                FROM search_index
                WHERE path = ?
                """,
                (note_path,),
            ).fetchone()
        )
        if source_terms:
            for path, path_text, title, headings in connection.execute(
                """
                SELECT path, path_text, title, headings
                FROM search_index
                WHERE path != ?
                """,
                (note_path,),
            ).fetchall():
                overlap = source_terms & _search_terms((path_text, title, headings))
                if len(overlap) >= 2:
                    add(path, min(len(overlap), 5) * 5, "shared title/heading terms")

    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return tuple(
        RelatedResult(path=path, score=score, reasons=tuple(dict.fromkeys(reasons[path])))
        for path, score in ordered
    )


def _link_rows(rows) -> tuple[LinkInfo, ...]:
    return tuple(
        LinkInfo(
            line=int(line),
            target=target,
            resolution_status=resolution_status,
            resolved_path=resolved_path,
            preferred_path=preferred_path,
            candidate_paths=tuple(candidate_paths.splitlines()) if candidate_paths else (),
        )
        for line, target, resolution_status, resolved_path, preferred_path, candidate_paths in rows
    )


def _search_terms(row) -> set[str]:
    if row is None:
        return set()
    text = " ".join(value or "" for value in row)
    return {token.lower() for token in TOKEN_RE.findall(text) if len(token) > 2}


def _tag_score(tag: str) -> int:
    if tag.startswith("#todo/"):
        return 5
    return 20


def _vault_root(connection: sqlite3.Connection) -> Path:
    row = connection.execute("SELECT value FROM scan_meta WHERE key = 'vault_root'").fetchone()
    if row is None:
        raise ValueError("Index is missing scan_meta.vault_root. Run `brainiac scan` again.")
    return Path(row[0])


def _resolve_vault_file(vault_root: Path, note_path: str) -> Path:
    relative_path = Path(note_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"Only indexed vault-relative paths can be read: {note_path}")
    absolute_path = (vault_root / relative_path).resolve()
    if not absolute_path.is_file():
        raise FileNotFoundError(f"Indexed file no longer exists: {note_path}")
    return absolute_path


def _extract_section(text: str, headings, section: str) -> str:
    selected = None
    normalized_section = section.strip().lower()
    for index, (line, level, heading_text) in enumerate(headings):
        if heading_text.strip().lower() != normalized_section:
            continue
        end_line = None
        for next_line, next_level, _ in headings[index + 1 :]:
            if next_level <= level:
                end_line = next_line
                break
        selected = (line, end_line)
        break
    if selected is None:
        raise ValueError(f"Section not found: {section}")

    lines = text.splitlines()
    start_line, end_line = selected
    if end_line is None:
        return "\n".join(lines[start_line - 1 :])
    return "\n".join(lines[start_line - 1 : end_line - 1])
