from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from .config import VaultConfig
from .scanner import walk_source_files


@dataclass(frozen=True)
class FilesystemDrift:
    added_files: int
    deleted_files: int
    metadata_changed_files: int
    unchanged_files: int
    added_examples: tuple[str, ...]
    deleted_examples: tuple[str, ...]
    changed_examples: tuple[str, ...]


@dataclass(frozen=True)
class IndexInfo:
    meta: dict[str, str]
    file_count: int
    markdown_count: int
    exact_duplicate_groups: int
    exact_duplicate_files: int
    duplicate_examples: tuple[tuple[str, ...], ...]
    drift: FilesystemDrift | None


def read_index_info(
    index_path: Path,
    *,
    config: VaultConfig | None = None,
    check_filesystem: bool = False,
    example_limit: int = 10,
) -> IndexInfo:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    with closing(sqlite3.connect(index_path)) as connection:
        meta = dict(connection.execute("SELECT key, value FROM scan_meta ORDER BY key").fetchall())
        file_count = int(connection.execute("SELECT COUNT(*) FROM files").fetchone()[0])
        markdown_count = int(connection.execute("SELECT COUNT(*) FROM files WHERE is_markdown = 1").fetchone()[0])
        duplicate_rows = connection.execute(
            """
            SELECT sha256, COUNT(*) AS count
            FROM files
            WHERE is_markdown = 1
            GROUP BY sha256
            HAVING COUNT(*) > 1
            ORDER BY count DESC, sha256 ASC
            LIMIT ?
            """,
            (example_limit,),
        ).fetchall()
        duplicate_examples = []
        for sha, _count in duplicate_rows:
            paths = connection.execute(
                """
                SELECT path
                FROM files
                WHERE is_markdown = 1 AND sha256 = ?
                ORDER BY path
                """,
                (sha,),
            ).fetchall()
            duplicate_examples.append(tuple(path for (path,) in paths))
        exact_duplicate_groups = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM (
                  SELECT sha256
                  FROM files
                  WHERE is_markdown = 1
                  GROUP BY sha256
                  HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0]
        )
        exact_duplicate_files = int(
            connection.execute(
                """
                SELECT COALESCE(SUM(group_count), 0)
                FROM (
                  SELECT COUNT(*) AS group_count
                  FROM files
                  WHERE is_markdown = 1
                  GROUP BY sha256
                  HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0]
        )
        drift = None
        if check_filesystem:
            if config is None or config.root is None:
                raise ValueError("Filesystem freshness check requires a configured vault root.")
            drift = _filesystem_drift(connection, config, example_limit)
    return IndexInfo(
        meta=meta,
        file_count=file_count,
        markdown_count=markdown_count,
        exact_duplicate_groups=exact_duplicate_groups,
        exact_duplicate_files=exact_duplicate_files,
        duplicate_examples=tuple(duplicate_examples),
        drift=drift,
    )


def _filesystem_drift(
    connection: sqlite3.Connection,
    config: VaultConfig,
    example_limit: int,
) -> FilesystemDrift:
    indexed_rows = connection.execute(
        "SELECT path, extension, size_bytes, mtime, is_markdown FROM files"
    ).fetchall()
    indexed = {
        row[0]: (
            row[1],
            int(row[2]),
            float(row[3]),
            bool(row[4]),
        )
        for row in indexed_rows
    }
    current: dict[str, tuple[str, int, float, bool]] = {}
    for path, relative_path in walk_source_files(config):
        stat = path.stat()
        extension = path.suffix.lower()
        current[relative_path] = (
            extension,
            stat.st_size,
            stat.st_mtime,
            extension in {".md", ".markdown"},
        )

    added = sorted(set(current) - set(indexed))
    deleted = sorted(set(indexed) - set(current))
    metadata_changed = sorted(
        path
        for path in set(current) & set(indexed)
        if current[path] != indexed[path]
    )
    unchanged = len(current) - len(added) - len(metadata_changed)
    return FilesystemDrift(
        added_files=len(added),
        deleted_files=len(deleted),
        metadata_changed_files=len(metadata_changed),
        unchanged_files=unchanged,
        added_examples=tuple(added[:example_limit]),
        deleted_examples=tuple(deleted[:example_limit]),
        changed_examples=tuple(metadata_changed[:example_limit]),
    )
