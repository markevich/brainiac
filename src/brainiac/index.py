from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterable

from .scanner import FileRecord, INDEX_SCHEMA_VERSION, ScanResult


REBUILD_SCHEMA = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS search_index;
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS wikilinks;
DROP TABLE IF EXISTS markdown_metadata;
DROP TABLE IF EXISTS markdown_headings;
DROP TABLE IF EXISTS files;
DROP TABLE IF EXISTS scan_meta;

CREATE TABLE scan_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE files (
  path TEXT PRIMARY KEY,
  extension TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  mtime REAL NOT NULL,
  sha256 TEXT NOT NULL,
  is_empty_note INTEGER NOT NULL,
  is_markdown INTEGER NOT NULL
);

CREATE TABLE markdown_headings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_path TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
  line INTEGER NOT NULL,
  level INTEGER NOT NULL,
  text TEXT NOT NULL
);

CREATE TABLE markdown_metadata (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_path TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
  key TEXT NOT NULL,
  value TEXT NOT NULL
);

CREATE TABLE wikilinks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_path TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
  line INTEGER NOT NULL,
  target TEXT NOT NULL,
  alias TEXT,
  resolved_path TEXT,
  preferred_path TEXT,
  is_resolved INTEGER NOT NULL,
  resolution_status TEXT NOT NULL,
  candidate_paths TEXT
);

CREATE TABLE tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_path TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
  line INTEGER NOT NULL,
  tag TEXT NOT NULL
);

CREATE TABLE tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_path TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
  line INTEGER NOT NULL,
  done INTEGER NOT NULL,
  text TEXT NOT NULL
);

CREATE VIRTUAL TABLE search_index USING fts5(
  path UNINDEXED,
  path_text,
  title,
  headings,
  tags,
  tasks,
  body,
  tokenize = 'unicode61 remove_diacritics 2'
);

CREATE INDEX idx_files_extension ON files(extension);
CREATE INDEX idx_headings_file ON markdown_headings(file_path);
CREATE INDEX idx_metadata_file_key ON markdown_metadata(file_path, key);
CREATE INDEX idx_metadata_key_value ON markdown_metadata(key, value);
CREATE INDEX idx_wikilinks_target ON wikilinks(target);
CREATE INDEX idx_wikilinks_file ON wikilinks(file_path);
CREATE INDEX idx_tags_tag ON tags(tag);
CREATE INDEX idx_tasks_done ON tasks(done);
"""

CREATE_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS scan_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
  path TEXT PRIMARY KEY,
  extension TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  mtime REAL NOT NULL,
  sha256 TEXT NOT NULL,
  is_empty_note INTEGER NOT NULL,
  is_markdown INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS markdown_headings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_path TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
  line INTEGER NOT NULL,
  level INTEGER NOT NULL,
  text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS markdown_metadata (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_path TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
  key TEXT NOT NULL,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wikilinks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_path TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
  line INTEGER NOT NULL,
  target TEXT NOT NULL,
  alias TEXT,
  resolved_path TEXT,
  preferred_path TEXT,
  is_resolved INTEGER NOT NULL,
  resolution_status TEXT NOT NULL,
  candidate_paths TEXT
);

CREATE TABLE IF NOT EXISTS tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_path TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
  line INTEGER NOT NULL,
  tag TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_path TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
  line INTEGER NOT NULL,
  done INTEGER NOT NULL,
  text TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
  path UNINDEXED,
  path_text,
  title,
  headings,
  tags,
  tasks,
  body,
  tokenize = 'unicode61 remove_diacritics 2'
);

CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension);
CREATE INDEX IF NOT EXISTS idx_headings_file ON markdown_headings(file_path);
CREATE INDEX IF NOT EXISTS idx_metadata_file_key ON markdown_metadata(file_path, key);
CREATE INDEX IF NOT EXISTS idx_metadata_key_value ON markdown_metadata(key, value);
CREATE INDEX IF NOT EXISTS idx_wikilinks_target ON wikilinks(target);
CREATE INDEX IF NOT EXISTS idx_wikilinks_file ON wikilinks(file_path);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);
"""


def write_index(index_path: Path, result: ScanResult) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(index_path)) as connection:
        require_fts5(connection)
        with connection:
            if result.full_rescan or _schema_version(connection) != INDEX_SCHEMA_VERSION:
                connection.executescript(REBUILD_SCHEMA)
                _replace_scan_meta(connection, result.meta)
                _insert_files(connection, result.files)
                _replace_markdown_rows(connection, result.markdown_refresh_paths, result)
            else:
                connection.executescript(CREATE_SCHEMA)
                _delete_paths(connection, result.deleted_paths, result.deleted_markdown_paths)
                _upsert_files(connection, result.changed_files)
                _replace_markdown_rows(connection, result.markdown_refresh_paths, result)
                _replace_scan_meta(connection, result.meta)
            _refresh_wikilink_resolutions(connection)


def require_fts5(connection: sqlite3.Connection) -> None:
    try:
        connection.execute("CREATE VIRTUAL TABLE temp.fts5_probe USING fts5(content)")
        connection.execute("DROP TABLE temp.fts5_probe")
    except sqlite3.OperationalError as exc:
        raise RuntimeError(
            "Brainiac requires SQLite FTS5 support. "
            "Install a Python/SQLite build with FTS5 enabled and rerun the command."
        ) from exc


def _schema_version(connection: sqlite3.Connection) -> int | None:
    table_row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'scan_meta'"
    ).fetchone()
    if table_row is None:
        return None
    row = connection.execute("SELECT value FROM scan_meta WHERE key = 'schema_version'").fetchone()
    if row is None:
        return None
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return None


def _replace_scan_meta(connection: sqlite3.Connection, meta: dict[str, str]) -> None:
    connection.execute("DELETE FROM scan_meta")
    connection.executemany(
        "INSERT INTO scan_meta(key, value) VALUES (?, ?)",
        sorted(meta.items()),
    )


def _insert_files(connection: sqlite3.Connection, records: Iterable[FileRecord]) -> None:
    connection.executemany(
        """
        INSERT INTO files(path, extension, size_bytes, mtime, sha256, is_empty_note, is_markdown)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                record.path,
                record.extension,
                record.size_bytes,
                record.mtime,
                record.sha256,
                int(record.is_empty_note),
                int(record.is_markdown),
            )
            for record in records
        ),
    )


def _upsert_files(connection: sqlite3.Connection, records: Iterable[FileRecord]) -> None:
    connection.executemany(
        """
        INSERT INTO files(path, extension, size_bytes, mtime, sha256, is_empty_note, is_markdown)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
          extension = excluded.extension,
          size_bytes = excluded.size_bytes,
          mtime = excluded.mtime,
          sha256 = excluded.sha256,
          is_empty_note = excluded.is_empty_note,
          is_markdown = excluded.is_markdown
        """,
        (
            (
                record.path,
                record.extension,
                record.size_bytes,
                record.mtime,
                record.sha256,
                int(record.is_empty_note),
                int(record.is_markdown),
            )
            for record in records
        ),
    )


def _delete_paths(
    connection: sqlite3.Connection,
    deleted_paths: tuple[str, ...],
    deleted_markdown_paths: tuple[str, ...],
) -> None:
    if deleted_markdown_paths:
        connection.executemany("DELETE FROM search_index WHERE path = ?", ((path,) for path in deleted_markdown_paths))
    if deleted_paths:
        connection.executemany("DELETE FROM files WHERE path = ?", ((path,) for path in deleted_paths))


def _replace_markdown_rows(connection: sqlite3.Connection, changed_paths: Iterable[str], result: ScanResult) -> None:
    paths = tuple(dict.fromkeys(changed_paths))
    if not paths:
        return
    connection.executemany("DELETE FROM markdown_headings WHERE file_path = ?", ((path,) for path in paths))
    connection.executemany("DELETE FROM markdown_metadata WHERE file_path = ?", ((path,) for path in paths))
    connection.executemany("DELETE FROM wikilinks WHERE file_path = ?", ((path,) for path in paths))
    connection.executemany("DELETE FROM tags WHERE file_path = ?", ((path,) for path in paths))
    connection.executemany("DELETE FROM tasks WHERE file_path = ?", ((path,) for path in paths))
    connection.executemany("DELETE FROM search_index WHERE path = ?", ((path,) for path in paths))

    heading_rows = []
    metadata_rows = []
    wikilink_rows = []
    tag_rows = []
    task_rows = []
    search_rows = []

    for file_path in paths:
        facts = result.markdown.get(file_path)
        text = result.markdown_text.get(file_path)
        if facts is None or text is None:
            continue
        for heading in facts.headings:
            heading_rows.append((file_path, heading.line, heading.level, heading.text))
        for key, values in facts.frontmatter.items():
            for value in values:
                metadata_rows.append((file_path, key, value))
        for wikilink in facts.wikilinks:
            wikilink_rows.append(
                (
                    file_path,
                    wikilink.line,
                    wikilink.target,
                    wikilink.alias,
                    None,
                    None,
                    0,
                    "missing",
                    None,
                )
            )
        for tag in facts.tags:
            tag_rows.append((file_path, tag.line, tag.value))
        for task in facts.tasks:
            task_rows.append((file_path, task.line, int(task.done), task.text))
        search_rows.append(
            (
                file_path,
                file_path,
                Path(file_path).stem,
                "\n".join(heading.text for heading in facts.headings),
                " ".join(tag.value for tag in facts.tags),
                "\n".join(task.text for task in facts.tasks),
                text,
            )
        )

    connection.executemany(
        "INSERT INTO markdown_headings(file_path, line, level, text) VALUES (?, ?, ?, ?)",
        heading_rows,
    )
    connection.executemany(
        "INSERT INTO markdown_metadata(file_path, key, value) VALUES (?, ?, ?)",
        metadata_rows,
    )
    connection.executemany(
        """
        INSERT INTO wikilinks(
          file_path, line, target, alias, resolved_path, preferred_path,
          is_resolved, resolution_status, candidate_paths
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        wikilink_rows,
    )
    connection.executemany(
        "INSERT INTO tags(file_path, line, tag) VALUES (?, ?, ?)",
        tag_rows,
    )
    connection.executemany(
        "INSERT INTO tasks(file_path, line, done, text) VALUES (?, ?, ?, ?)",
        task_rows,
    )
    connection.executemany(
        """
        INSERT INTO search_index(path, path_text, title, headings, tags, tasks, body)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        search_rows,
    )


def _refresh_wikilink_resolutions(connection: sqlite3.Connection) -> None:
    markdown_paths = [
        row[0]
        for row in connection.execute(
            "SELECT path FROM files WHERE is_markdown = 1 ORDER BY path"
        ).fetchall()
    ]
    page_index = {
        Path(path).with_suffix("").as_posix().lower(): path
        for path in markdown_paths
    }
    stem_index: dict[str, set[str]] = {}
    for path in markdown_paths:
        stem_index.setdefault(Path(path).stem.lower(), set()).add(path)

    updates = []
    rows = connection.execute(
        "SELECT id, file_path, target FROM wikilinks ORDER BY id"
    ).fetchall()
    for row_id, file_path, target in rows:
        resolved_path, preferred_path, resolution_status, candidate_paths = _resolve_target(
            file_path,
            target,
            page_index,
            stem_index,
        )
        updates.append(
            (
                resolved_path,
                preferred_path,
                int(resolved_path is not None),
                resolution_status,
                "\n".join(candidate_paths) if candidate_paths else None,
                row_id,
            )
        )

    connection.executemany(
        """
        UPDATE wikilinks
        SET resolved_path = ?, preferred_path = ?, is_resolved = ?, resolution_status = ?, candidate_paths = ?
        WHERE id = ?
        """,
        updates,
    )


def _resolve_target(
    source_path: str,
    target: str,
    page_index: dict[str, str],
    stem_index: dict[str, set[str]],
) -> tuple[str | None, str | None, str, tuple[str, ...] | None]:
    normalized = target.strip().removesuffix(".md").lower()
    match = page_index.get(normalized)
    if match is not None:
        return match, None, "resolved", None
    stem_matches = stem_index.get(Path(normalized).name, set())
    if len(stem_matches) == 1:
        only = next(iter(stem_matches))
        return only, None, "resolved", None
    if len(stem_matches) > 1:
        candidates = tuple(sorted(stem_matches))
        return None, _preferred_candidate(source_path, candidates), "ambiguous", candidates
    return None, None, "missing", None


def _preferred_candidate(source_path: str, candidates: tuple[str, ...]) -> str:
    source_parts = Path(source_path).parts

    def score(candidate: str) -> tuple[int, int, str]:
        candidate_parts = Path(candidate).parts
        common_prefix = 0
        for source_part, candidate_part in zip(source_parts, candidate_parts):
            if source_part != candidate_part:
                break
            common_prefix += 1
        same_top_folder = int(bool(source_parts and candidate_parts and source_parts[0] == candidate_parts[0]))
        return (-common_prefix, -same_top_folder, candidate)

    return min(candidates, key=score)
