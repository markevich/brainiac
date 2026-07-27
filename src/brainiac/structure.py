from __future__ import annotations

import re
import sqlite3
from collections import Counter
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from .vault_roles import RoleRoot, para_role_roots


TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True)
class StructureProfile:
    role: str
    path: str
    note_count: int
    file_count: int
    top_tags: tuple[str, ...]
    top_terms: tuple[str, ...]
    representative_notes: tuple[str, ...]


@dataclass(frozen=True)
class StructureAnalysis:
    role_roots: tuple[RoleRoot, ...]
    profiles: tuple[StructureProfile, ...]


def analyze_structure(
    index_path: Path,
    *,
    max_profiles: int = 100,
) -> StructureAnalysis:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")

    role_roots = para_role_roots()
    with closing(sqlite3.connect(index_path)) as connection:
        profiles = _profiles(
            connection,
            role_roots,
            frozenset(),
        )

    ordered = tuple(sorted(profiles, key=lambda item: (item.role, item.path))[:max_profiles])
    return StructureAnalysis(
        role_roots=role_roots,
        profiles=ordered,
    )
def _profiles(
    connection: sqlite3.Connection,
    roots: tuple[RoleRoot, ...],
    stopwords: frozenset[str],
) -> tuple[StructureProfile, ...]:
    profiles: list[StructureProfile] = []
    seen: set[tuple[str, str]] = set()
    for root in roots:
        for path in _profile_paths(connection, root):
            key = (root.role, path)
            if key in seen:
                continue
            seen.add(key)
            note_paths = _note_paths_under(connection, path)
            file_count = _file_count_under(connection, path)
            profiles.append(
                StructureProfile(
                    role=root.role,
                    path=path,
                    note_count=len(note_paths),
                    file_count=file_count,
                    top_tags=_top_tags(connection, note_paths),
                    top_terms=_top_terms(connection, note_paths, stopwords),
                    representative_notes=tuple(note_paths[:5]),
                )
            )
    return tuple(profiles)


def _profile_paths(connection: sqlite3.Connection, root: RoleRoot) -> tuple[str, ...]:
    if root.role == "inbox":
        return (root.path,)
    child_dirs = set()
    direct_files = set()
    for (path,) in connection.execute("SELECT path FROM files WHERE path LIKE ?", (root.path + "%",)).fetchall():
        remainder = path[len(root.path) :]
        if not remainder:
            continue
        first = remainder.split("/", 1)[0]
        if first:
            if "/" in remainder:
                child_dirs.add(root.path + first + "/")
            else:
                direct_files.add(root.path + first)
    if not child_dirs:
        return (root.path,)
    return tuple(sorted(child_dirs | direct_files)) or (root.path,)


def _note_paths_under(connection: sqlite3.Connection, path: str) -> list[str]:
    if path.endswith("/"):
        query = "SELECT path FROM files WHERE is_markdown = 1 AND path LIKE ? ORDER BY path"
        args = (path + "%",)
    else:
        query = "SELECT path FROM files WHERE is_markdown = 1 AND path = ? ORDER BY path"
        args = (path,)
    return [row[0] for row in connection.execute(query, args).fetchall()]


def _file_count_under(connection: sqlite3.Connection, path: str) -> int:
    if path.endswith("/"):
        return int(connection.execute("SELECT COUNT(*) FROM files WHERE path LIKE ?", (path + "%",)).fetchone()[0])
    return int(connection.execute("SELECT COUNT(*) FROM files WHERE path = ?", (path,)).fetchone()[0])


def _top_tags(connection: sqlite3.Connection, note_paths: list[str]) -> tuple[str, ...]:
    if not note_paths:
        return ()
    placeholders = ",".join("?" for _ in note_paths)
    rows = connection.execute(
        f"""
        SELECT tag, COUNT(*) AS count
        FROM tags
        WHERE file_path IN ({placeholders})
        GROUP BY tag
        ORDER BY count DESC, tag ASC
        LIMIT 5
        """,
        tuple(note_paths),
    ).fetchall()
    return tuple(tag for tag, _ in rows)


def _top_terms(
    connection: sqlite3.Connection,
    note_paths: list[str],
    stopwords: frozenset[str],
) -> tuple[str, ...]:
    if not note_paths:
        return ()
    placeholders = ",".join("?" for _ in note_paths)
    rows = connection.execute(
        f"""
        SELECT path_text, title, headings, tags
        FROM search_index
        WHERE path IN ({placeholders})
        """,
        tuple(note_paths),
    ).fetchall()
    counts: Counter[str] = Counter()
    for row in rows:
        text = " ".join(value or "" for value in row)
        counts.update(_terms(text, stopwords))
    return tuple(term for term, _ in counts.most_common(8))


def _terms(text: str, stopwords: frozenset[str]) -> set[str]:
    return {
        token.lower().strip("-_/")
        for token in TOKEN_RE.findall(text)
        if len(token.strip("-_/")) > 2 and token.lower().strip("-_/") not in stopwords
    }
