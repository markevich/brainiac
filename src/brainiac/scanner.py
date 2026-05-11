from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path

from .config import VaultConfig
from .markdown import MarkdownFacts, extract_markdown_facts


MARKDOWN_EXTENSIONS = {".md", ".markdown"}


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
    markdown: dict[str, MarkdownFacts]
    resolved_wikilinks: dict[tuple[str, int, str], str]
    ambiguous_wikilinks: dict[tuple[str, int, str], tuple[str, ...]]
    meta: dict[str, str]


def scan_vault(config: VaultConfig) -> ScanResult:
    if config.root is None:
        raise ValueError("Vault root is not configured. Pass --vault-root or set vault.root.")
    vault_root = config.root.resolve()
    if not vault_root.exists():
        raise FileNotFoundError(f"Vault root does not exist: {vault_root}")
    if not vault_root.is_dir():
        raise NotADirectoryError(f"Vault root is not a directory: {vault_root}")

    records: list[FileRecord] = []
    markdown: dict[str, MarkdownFacts] = {}
    page_index: dict[str, str] = {}
    stem_index: dict[str, set[str]] = {}

    for path in sorted(_iter_files(vault_root, config.exclude, config.source_patterns)):
        relative_path = path.relative_to(vault_root).as_posix()
        stat = path.stat()
        extension = path.suffix.lower()
        is_markdown = extension in MARKDOWN_EXTENSIONS
        digest = _hash_file(path)
        is_empty_note = False

        if is_markdown:
            text = path.read_text(encoding="utf-8", errors="replace")
            is_empty_note = len(text.strip()) == 0
            markdown[relative_path] = extract_markdown_facts(text)
            page_index[Path(relative_path).with_suffix("").as_posix().lower()] = relative_path
            stem_index.setdefault(Path(relative_path).stem.lower(), set()).add(relative_path)

        records.append(
            FileRecord(
                path=relative_path,
                extension=extension,
                size_bytes=stat.st_size,
                mtime=stat.st_mtime,
                sha256=digest,
                is_empty_note=is_empty_note,
                is_markdown=is_markdown,
            )
        )

    resolved_wikilinks, ambiguous_wikilinks = _resolve_wikilinks(markdown, page_index, stem_index)
    return ScanResult(
        files=tuple(records),
        markdown=markdown,
        resolved_wikilinks=resolved_wikilinks,
        ambiguous_wikilinks=ambiguous_wikilinks,
        meta={
            "vault_name": config.name,
            "vault_root": vault_root.as_posix(),
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "file_count": str(len(records)),
            "markdown_count": str(len(markdown)),
        },
    )


def _iter_files(root: Path, exclude: tuple[str, ...], source_patterns: tuple[str, ...]):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(root).as_posix()
        if _is_excluded(relative_path, exclude):
            continue
        if source_patterns and not _matches_source_patterns(relative_path, source_patterns):
            continue
        yield path


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


def _resolve_wikilinks(
    markdown: dict[str, MarkdownFacts],
    page_index: dict[str, str],
    stem_index: dict[str, set[str]],
) -> tuple[dict[tuple[str, int, str], str], dict[tuple[str, int, str], tuple[str, ...]]]:
    resolved: dict[tuple[str, int, str], str] = {}
    ambiguous: dict[tuple[str, int, str], tuple[str, ...]] = {}
    for file_path, facts in markdown.items():
        for link in facts.wikilinks:
            if not link.target:
                continue
            key = (file_path, link.line, link.target)
            normalized = link.target.strip().removesuffix(".md").lower()
            match = page_index.get(normalized)
            if match is None:
                stem_matches = stem_index.get(Path(normalized).stem, set())
                if len(stem_matches) == 1:
                    match = next(iter(stem_matches))
                elif len(stem_matches) > 1:
                    ambiguous[key] = tuple(sorted(stem_matches))
            if match is not None:
                resolved[key] = match
    return resolved, ambiguous
