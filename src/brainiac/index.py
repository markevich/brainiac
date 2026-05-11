from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterable

from .scanner import FileRecord, ScanResult


SCHEMA = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS search_index;
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS wikilinks;
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
CREATE INDEX idx_wikilinks_target ON wikilinks(target);
CREATE INDEX idx_wikilinks_file ON wikilinks(file_path);
CREATE INDEX idx_tags_tag ON tags(tag);
CREATE INDEX idx_tasks_done ON tasks(done);
"""


def write_index(index_path: Path, result: ScanResult) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(index_path)) as connection:
        require_fts5(connection)
        with connection:
            connection.executescript(SCHEMA)
            connection.executemany(
                "INSERT INTO scan_meta(key, value) VALUES (?, ?)",
                sorted(result.meta.items()),
            )
            _insert_files(connection, result.files)
            _insert_markdown(connection, result)


def require_fts5(connection: sqlite3.Connection) -> None:
    try:
        connection.execute("CREATE VIRTUAL TABLE temp.fts5_probe USING fts5(content)")
        connection.execute("DROP TABLE temp.fts5_probe")
    except sqlite3.OperationalError as exc:
        raise RuntimeError(
            "Brainiac requires SQLite FTS5 support. "
            "Install a Python/SQLite build with FTS5 enabled and rerun the command."
        ) from exc


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


def _insert_markdown(connection: sqlite3.Connection, result: ScanResult) -> None:
    heading_rows = []
    wikilink_rows = []
    tag_rows = []
    task_rows = []
    search_rows = []

    for file_path, facts in result.markdown.items():
        for heading in facts.headings:
            heading_rows.append((file_path, heading.line, heading.level, heading.text))
        for wikilink in facts.wikilinks:
            key = (file_path, wikilink.line, wikilink.target)
            resolved_path = result.resolved_wikilinks.get(key)
            candidate_paths = result.ambiguous_wikilinks.get(key)
            preferred_path = result.preferred_wikilinks.get(key)
            if resolved_path is not None:
                resolution_status = "resolved"
            elif candidate_paths:
                resolution_status = "ambiguous"
            else:
                resolution_status = "missing"
            wikilink_rows.append(
                (
                    file_path,
                    wikilink.line,
                    wikilink.target,
                    wikilink.alias,
                    resolved_path,
                    preferred_path,
                    int(resolved_path is not None),
                    resolution_status,
                    "\n".join(candidate_paths) if candidate_paths else None,
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
                result.markdown_text[file_path],
            )
        )

    connection.executemany(
        "INSERT INTO markdown_headings(file_path, line, level, text) VALUES (?, ?, ?, ?)",
        heading_rows,
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
