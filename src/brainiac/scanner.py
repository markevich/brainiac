from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path

from .config import VaultConfig
from .markdown import MarkdownFacts, extract_markdown_facts


MARKDOWN_EXTENSIONS = {".md", ".markdown"}
INDEX_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class FileRecord:
    path: str
    extension: str
    size_bytes: int
    mtime: float
    sha256: str
    is_empty_note: bool
    is_markdown: bool


@dataclass(frozen=True)
class ScanResult:
    files: tuple[FileRecord, ...]
    changed_files: tuple[FileRecord, ...]
    markdown: dict[str, MarkdownFacts]
    markdown_text: dict[str, str]
    markdown_refresh_paths: tuple[str, ...]
    deleted_paths: tuple[str, ...]
    deleted_markdown_paths: tuple[str, ...]
    changed_paths: tuple[str, ...]
    unchanged_paths: tuple[str, ...]
    full_rescan: bool
    meta: dict[str, str]


def scan_vault(config: VaultConfig, *, full_rescan: bool = False) -> ScanResult:
    if config.root is None:
        raise ValueError("Vault root is not configured. Pass --vault-root or set vault.root.")
    vault_root = config.root.resolve()
    if not vault_root.exists():
        raise FileNotFoundError(f"Vault root does not exist: {vault_root}")
    if not vault_root.is_dir():
        raise NotADirectoryError(f"Vault root is not a directory: {vault_root}")

    previous = _load_previous_index(config.index_path, vault_root) if not full_rescan else {}
    reuse_index = bool(previous) and not full_rescan

    records: list[FileRecord] = []
    changed_files: list[FileRecord] = []
    changed_paths: list[str] = []
    markdown_refresh_paths: list[str] = []
    unchanged_paths: list[str] = []
    markdown: dict[str, MarkdownFacts] = {}
    markdown_text: dict[str, str] = {}
    seen_paths: set[str] = set()

    for path, relative_path in walk_source_files(config):
        seen_paths.add(relative_path)
        stat = path.stat()
        extension = path.suffix.lower()
        is_markdown = extension in MARKDOWN_EXTENSIONS

        previous_record = previous.get(relative_path)
        current_record, requires_parse = _build_record(
            path,
            relative_path,
            stat,
            extension,
            is_markdown,
            previous_record,
        )
        records.append(current_record)

        if previous_record is None or current_record != previous_record:
            changed_files.append(current_record)
            changed_paths.append(relative_path)
        else:
            unchanged_paths.append(relative_path)

        if is_markdown and (requires_parse or full_rescan or not reuse_index):
            text = path.read_text(encoding="utf-8", errors="replace")
            if current_record.is_empty_note != (len(text.strip()) == 0):
                current_record = FileRecord(
                    path=current_record.path,
                    extension=current_record.extension,
                    size_bytes=current_record.size_bytes,
                    mtime=current_record.mtime,
                    sha256=current_record.sha256,
                    is_empty_note=len(text.strip()) == 0,
                    is_markdown=current_record.is_markdown,
                )
                records[-1] = current_record
                if changed_files and changed_files[-1].path == current_record.path:
                    changed_files[-1] = current_record
            markdown_text[relative_path] = text
            markdown[relative_path] = extract_markdown_facts(text)
            markdown_refresh_paths.append(relative_path)
        elif previous_record and previous_record.is_markdown and not is_markdown:
            markdown_refresh_paths.append(relative_path)

    deleted_paths = tuple(sorted(set(previous) - seen_paths))
    deleted_markdown_paths = tuple(
        path for path in deleted_paths if previous.get(path) and previous[path].is_markdown
    )

    effective_full_rescan = full_rescan or not reuse_index
    file_count = len(records)
    markdown_count = sum(1 for record in records if record.is_markdown)
    changed_markdown_count = sum(1 for record in changed_files if record.is_markdown)

    return ScanResult(
        files=tuple(records),
        changed_files=tuple(changed_files if reuse_index and not full_rescan else records),
        markdown=markdown,
        markdown_text=markdown_text,
        markdown_refresh_paths=tuple(
            markdown_refresh_paths if reuse_index and not full_rescan else [record.path for record in records if record.is_markdown]
        ),
        deleted_paths=deleted_paths,
        deleted_markdown_paths=deleted_markdown_paths,
        changed_paths=tuple(
            changed_paths if reuse_index and not full_rescan else [record.path for record in records]
        ),
        unchanged_paths=tuple(unchanged_paths if reuse_index and not full_rescan else ()),
        full_rescan=effective_full_rescan,
        meta={
            "schema_version": str(INDEX_SCHEMA_VERSION),
            "vault_name": config.name,
            "vault_root": vault_root.as_posix(),
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "scan_mode": "full" if effective_full_rescan else "incremental",
            "file_count": str(file_count),
            "markdown_count": str(markdown_count),
            "changed_file_count": str(file_count if effective_full_rescan else len(changed_files)),
            "changed_markdown_count": str(markdown_count if effective_full_rescan else changed_markdown_count),
            "deleted_file_count": str(len(deleted_paths)),
            "deleted_markdown_count": str(len(deleted_markdown_paths)),
            "unchanged_file_count": str(0 if effective_full_rescan else len(unchanged_paths)),
        },
    )


def _build_record(
    path: Path,
    relative_path: str,
    stat,
    extension: str,
    is_markdown: bool,
    previous_record: FileRecord | None,
) -> tuple[FileRecord, bool]:
    if previous_record is None:
        digest = _hash_file(path)
        return (
            FileRecord(
                path=relative_path,
                extension=extension,
                size_bytes=stat.st_size,
                mtime=stat.st_mtime,
                sha256=digest,
                is_empty_note=False,
                is_markdown=is_markdown,
            ),
            is_markdown,
        )

    metadata_changed = (
        previous_record.extension != extension
        or previous_record.size_bytes != stat.st_size
        or previous_record.mtime != stat.st_mtime
        or previous_record.is_markdown != is_markdown
    )
    if not metadata_changed:
        return previous_record, False

    digest = _hash_file(path)
    content_changed = (
        previous_record.sha256 != digest
        or previous_record.extension != extension
        or previous_record.is_markdown != is_markdown
    )
    is_empty_note = previous_record.is_empty_note
    if is_markdown and content_changed:
        is_empty_note = False
    elif not is_markdown:
        is_empty_note = False

    return (
        FileRecord(
            path=relative_path,
            extension=extension,
            size_bytes=stat.st_size,
            mtime=stat.st_mtime,
            sha256=digest,
            is_empty_note=is_empty_note,
            is_markdown=is_markdown,
        ),
        is_markdown and content_changed,
    )


def _load_previous_index(index_path: Path, vault_root: Path) -> dict[str, FileRecord]:
    if not index_path.exists():
        return {}
    try:
        with closing(sqlite3.connect(index_path)) as connection:
            meta = dict(connection.execute("SELECT key, value FROM scan_meta").fetchall())
            if meta.get("schema_version") != str(INDEX_SCHEMA_VERSION):
                return {}
            if meta.get("vault_root") != vault_root.as_posix():
                return {}
            rows = connection.execute(
                """
                SELECT path, extension, size_bytes, mtime, sha256, is_empty_note, is_markdown
                FROM files
                """
            ).fetchall()
    except sqlite3.Error:
        return {}
    return {
        row[0]: FileRecord(
            path=row[0],
            extension=row[1],
            size_bytes=int(row[2]),
            mtime=float(row[3]),
            sha256=row[4],
            is_empty_note=bool(row[5]),
            is_markdown=bool(row[6]),
        )
        for row in rows
    }


def walk_source_files(config: VaultConfig) -> tuple[tuple[Path, str], ...]:
    if config.root is None:
        raise ValueError("Vault root is not configured. Pass --vault-root or set vault.root.")
    vault_root = config.root.resolve()
    if not vault_root.exists():
        raise FileNotFoundError(f"Vault root does not exist: {vault_root}")
    if not vault_root.is_dir():
        raise NotADirectoryError(f"Vault root is not a directory: {vault_root}")
    return tuple(_iter_files(vault_root, config.exclude, config.source_patterns))


def _iter_files(root: Path, exclude: tuple[str, ...], source_patterns: tuple[str, ...]):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(root).as_posix()
        if _is_excluded(relative_path, exclude):
            continue
        if source_patterns and not _matches_source_patterns(relative_path, source_patterns):
            continue
        yield path, relative_path


def _is_excluded(relative_path: str, exclude: tuple[str, ...]) -> bool:
    for pattern in exclude:
        normalized = pattern.strip("/")
        if not normalized:
            continue
        if relative_path == normalized or relative_path.startswith(normalized + "/"):
            return True
    return False


def _matches_source_patterns(relative_path: str, source_patterns: tuple[str, ...]) -> bool:
    filename = Path(relative_path).name
    return any(fnmatch(filename, pattern) or fnmatch(relative_path, pattern) for pattern in source_patterns)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
