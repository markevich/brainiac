from __future__ import annotations

import sqlite3
import re
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from .duplicates import canonical_duplicate_path, exact_duplicate_paths
from .vault_roles import classify_note_role, classify_path_role, para_role_roots


TOKEN_RE = re.compile(r"[\w/-]+", re.UNICODE)


@dataclass(frozen=True)
class LinkInfo:
    file_path: str
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
    role: str
    size_bytes: int
    is_empty_note: bool
    headings: tuple[tuple[int, int, str], ...]
    tags: tuple[str, ...]
    tasks: tuple[TaskInfo, ...]
    outgoing_links: tuple[LinkInfo, ...]
    backlinks: tuple[LinkInfo, ...]
    umbrella_backlinks: tuple[str, ...]
    exact_duplicates: tuple[str, ...]
    canonical_path: str


@dataclass(frozen=True)
class RelatedResult:
    path: str
    score: int
    reasons: tuple[str, ...]


def inspect_path(
    index_path: Path,
    note_path: str,
) -> Inspection:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    with closing(sqlite3.connect(index_path)) as connection:
        role_roots = para_role_roots()
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
                SELECT file_path, line, target, resolution_status, resolved_path, preferred_path, candidate_paths
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
                SELECT file_path, line, target, resolution_status, resolved_path, preferred_path, candidate_paths
                FROM wikilinks
                WHERE resolved_path = ? OR preferred_path = ?
                ORDER BY file_path, line
                """,
                (note_path, note_path),
            ).fetchall()
        )
        role = classify_note_role(connection, note_path, role_roots)
        umbrella_backlinks = tuple(
            sorted(
                {
                    link.file_path
                    for link in backlinks
                    if classify_note_role(connection, link.file_path, role_roots) == "umbrella"
                }
            )
        )
        exact_duplicates = exact_duplicate_paths(connection, note_path)
        canonical_path = canonical_duplicate_path(connection, note_path, role_roots)

    return Inspection(
        path=file_row[0],
        role=role,
        size_bytes=int(file_row[1]),
        is_empty_note=bool(file_row[2]),
        headings=headings,
        tags=tags,
        tasks=tasks,
        outgoing_links=outgoing_links,
        backlinks=backlinks,
        umbrella_backlinks=umbrella_backlinks,
        exact_duplicates=exact_duplicates,
        canonical_path=canonical_path,
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
    with closing(sqlite3.connect(index_path)) as connection:
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


def related_paths(
    index_path: Path,
    note_path: str,
    *,
    limit: int = 10,
) -> tuple[RelatedResult, ...]:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    with closing(sqlite3.connect(index_path)) as connection:
        file_exists = connection.execute("SELECT 1 FROM files WHERE path = ?", (note_path,)).fetchone()
        if file_exists is None:
            raise FileNotFoundError(f"Path not found in index: {note_path}")

        role_roots = para_role_roots()
        note_role = classify_path_role(note_path, role_roots)
        note_canonical_path = canonical_duplicate_path(connection, note_path, role_roots)
        scores: dict[str, int] = {}
        reasons: dict[str, list[str]] = {}
        canonical_cache: dict[str, str] = {}

        def add(path: str | None, score: int, reason: str) -> None:
            if not path or path == note_path:
                return
            canonical = canonical_cache.get(path)
            if canonical is None:
                canonical = canonical_duplicate_path(connection, path, role_roots)
                canonical_cache[path] = canonical
            if canonical == note_path:
                return
            scores[canonical] = scores.get(canonical, 0) + score
            reasons.setdefault(canonical, []).append(reason)
            if canonical != path:
                reasons.setdefault(canonical, []).append(f"exact duplicate canonicalized from {path}")

        if note_canonical_path != note_path:
            scores[note_canonical_path] = scores.get(note_canonical_path, 0) + 115
            reasons.setdefault(note_canonical_path, []).append("exact duplicate canonical candidate")

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
            "SELECT file_path FROM wikilinks WHERE resolved_path = ? OR preferred_path = ?",
            (note_path, note_path),
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
        folder_size = 0
        if folder != ".":
            folder_prefix = folder + "/"
            folder_paths = connection.execute(
                """
                SELECT path
                FROM files
                WHERE is_markdown = 1 AND path != ? AND path LIKE ?
                LIMIT 100
                """,
                (note_path, folder_prefix + "%"),
            ).fetchall()
            folder_size = len(folder_paths)
            if folder_size <= 5 and note_role != "resource":
                for file_path in folder_paths:
                    add(file_path[0], 5, "same folder")

        source_terms = _search_terms(
            connection.execute(
                """
                SELECT title, headings, tags
                FROM search_index
                WHERE path = ?
                """,
                (note_path,),
            ).fetchone()
        )
        if source_terms:
            candidate_paths = _lexical_candidates(connection, note_path, source_terms)
            for path, title, headings, tags in candidate_paths:
                overlap = source_terms & _search_terms((title, headings, tags))
                if len(overlap) >= 2:
                    score = min(len(overlap), 4) * 8
                    candidate_role = classify_path_role(path, role_roots)
                    if note_role and candidate_role and note_role == candidate_role:
                        score += 8
                        reasons.setdefault(path, []).append(f"same role {note_role}")
                    add(path, score, f"shared title/heading terms: {', '.join(sorted(overlap)[:4])}")

    ordered = sorted(
        ((path, score) for path, score in scores.items() if score >= 10),
        key=lambda item: (-item[1], item[0]),
    )[:limit]
    return tuple(
        RelatedResult(path=path, score=score, reasons=tuple(dict.fromkeys(reasons[path])))
        for path, score in ordered
    )


def _link_rows(rows) -> tuple[LinkInfo, ...]:
    return tuple(
        LinkInfo(
            file_path=file_path,
            line=int(line),
            target=target,
            resolution_status=resolution_status,
            resolved_path=resolved_path,
            preferred_path=preferred_path,
            candidate_paths=tuple(candidate_paths.splitlines()) if candidate_paths else (),
        )
        for file_path, line, target, resolution_status, resolved_path, preferred_path, candidate_paths in rows
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


def _lexical_candidates(connection: sqlite3.Connection, note_path: str, source_terms: set[str]) -> tuple[tuple[str, str, str, str], ...]:
    if len(source_terms) < 2:
        return ()
    query = _fts_or_query(sorted(source_terms)[:8])
    if not query:
        return ()
    rows = connection.execute(
        """
        SELECT path, title, headings, tags
        FROM search_index
        WHERE search_index MATCH ? AND path != ?
        ORDER BY bm25(search_index) ASC, path ASC
        LIMIT 40
        """,
        (query, note_path),
    ).fetchall()
    return tuple((row[0], row[1] or "", row[2] or "", row[3] or "") for row in rows)


def _fts_or_query(tokens: list[str]) -> str:
    quoted = ['"' + token.replace('"', '""') + '"' for token in tokens if token.strip("-_/")]
    return " OR ".join(quoted)


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
