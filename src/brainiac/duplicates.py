from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path

from .vault_roles import RoleRoot, classify_path_role


def exact_duplicate_paths(connection: sqlite3.Connection, path: str) -> tuple[str, ...]:
    row = connection.execute(
        "SELECT sha256 FROM files WHERE path = ? AND is_markdown = 1",
        (path,),
    ).fetchone()
    if row is None:
        return ()
    rows = connection.execute(
        """
        SELECT path
        FROM files
        WHERE is_markdown = 1 AND sha256 = ?
        ORDER BY path
        """,
        (row[0],),
    ).fetchall()
    if len(rows) <= 1:
        return ()
    return tuple(item[0] for item in rows)


def canonical_duplicate_path(
    connection: sqlite3.Connection,
    path: str,
    role_roots: tuple[RoleRoot, ...],
) -> str:
    duplicates = exact_duplicate_paths(connection, path)
    if not duplicates:
        return path
    return choose_canonical_path(connection, duplicates, role_roots)


def choose_canonical_path(
    connection: sqlite3.Connection,
    paths: tuple[str, ...],
    role_roots: tuple[RoleRoot, ...],
) -> str:
    cache = _duplicate_stats_cache(connection)
    scored = sorted(paths, key=lambda item: _canonical_sort_key(item, role_roots, cache), reverse=True)
    return scored[0]


def _canonical_sort_key(
    path: str,
    role_roots: tuple[RoleRoot, ...],
    cache,
) -> tuple[int, int, int, int, float, int, str]:
    role = classify_path_role(path, role_roots)
    archive_like = _contains_folder(path, "archive")
    generated_like = _contains_folder(path, "generated")
    queue_like = _contains_folder(path, "queue")
    inbox_like = role == "inbox"
    role_rank = {
        "area": 4,
        "project": 4,
        "resource": 4,
        "unknown": 3,
        None: 3,
        "inbox": 2,
        "synthesis": 2,
        "queue": 1,
        "generated": 1,
        "archive": 0,
    }.get(role, 3)
    outgoing, backlinks, mtime = cache(path)
    return (
        0 if generated_like else 1,
        0 if queue_like else 1,
        0 if archive_like else 1,
        0 if inbox_like else 1,
        float(backlinks + outgoing),
        float(mtime),
        role_rank,
        _path_preference(path),
    )


def _contains_folder(path: str, folder: str) -> bool:
    normalized = "/" + path.casefold().strip("/") + "/"
    return f"/{folder.casefold()}/" in normalized


def _path_preference(path: str) -> str:
    return "\uffff" * max(0, 20 - len(Path(path).parts)) + path


def _duplicate_stats_cache(connection: sqlite3.Connection):
    @lru_cache(maxsize=None)
    def load(path: str) -> tuple[int, int, float]:
        outgoing = int(
            connection.execute("SELECT COUNT(*) FROM wikilinks WHERE file_path = ?", (path,)).fetchone()[0]
        )
        backlinks = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM wikilinks
                WHERE resolved_path = ? OR preferred_path = ?
                """,
                (path, path),
            ).fetchone()[0]
        )
        mtime = float(connection.execute("SELECT mtime FROM files WHERE path = ?", (path,)).fetchone()[0])
        return outgoing, backlinks, mtime

    return load
