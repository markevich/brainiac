from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .bootstrap import initialize_para_vault
from .config import load_vault_config, with_vault_overrides
from .duplicates import inspect_duplicates, list_exact_duplicate_groups
from .index import write_index
from .index_status import read_index_info
from .maintenance import maintenance_report
from .para import require_para_layout
from .retrieval import inspect_path, read_path, related_paths
from .routing import find_duplicates, route_content
from .scanner import scan_vault
from .search import search_index
from .structure import analyze_structure


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brainiac")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/vault.yml"),
        help="Path to Brainiac vault config.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create an empty PARA vault and its local vault config.")
    init_parser.add_argument("--vault-root", type=Path, required=True, help="Empty directory for the new vault.")

    scan_parser = subparsers.add_parser("scan", help="Build a read-only vault inventory index.")
    scan_parser.add_argument("--vault-root", type=Path, help="Override vault root from config.")
    scan_parser.add_argument("--index", type=Path, help="Override SQLite index output path.")
    scan_parser.add_argument(
        "--full-rebuild",
        action="store_true",
        help="Ignore any compatible existing index and rebuild from scratch.",
    )
    scan_parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Additional vault-relative folder or file path to ignore. Can be used more than once.",
    )

    search_parser = subparsers.add_parser("search", help="Search the existing vault index.")
    search_parser.add_argument("query", help="Search query.")
    search_parser.add_argument("--index", type=Path, help="Override SQLite index path.")
    search_parser.add_argument("--limit", type=int, default=10, help="Maximum number of results.")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect one indexed vault path.")
    inspect_parser.add_argument("path", help="Vault-relative path to inspect.")
    inspect_parser.add_argument("--index", type=Path, help="Override SQLite index path.")

    read_parser = subparsers.add_parser("read", help="Read one indexed vault path.")
    read_parser.add_argument("path", help="Vault-relative path to read.")
    read_parser.add_argument("--index", type=Path, help="Override SQLite index path.")
    read_parser.add_argument("--section", help="Read only one Markdown section by heading text.")
    read_parser.add_argument("--max-chars", type=int, default=6000, help="Maximum characters to print.")

    related_parser = subparsers.add_parser("related", help="Find notes related to one indexed path.")
    related_parser.add_argument("path", help="Vault-relative path.")
    related_parser.add_argument("--index", type=Path, help="Override SQLite index path.")
    related_parser.add_argument("--limit", type=int, default=10, help="Maximum number of results.")

    index_parser = subparsers.add_parser("index", help="Inspect index metadata and freshness.")
    index_subparsers = index_parser.add_subparsers(dest="index_command", required=True)
    index_info_parser = index_subparsers.add_parser("info", help="Show index metadata and optional filesystem drift.")
    index_info_parser.add_argument("--index", type=Path, help="Override SQLite index path.")
    index_info_parser.add_argument(
        "--check-filesystem",
        action="store_true",
        help="Walk the configured vault tree and compare it with the indexed file set.",
    )

    route_parser = subparsers.add_parser("route", help="Dry-run route new content into the vault.")
    route_parser.add_argument("content", nargs="?", help="Content to route. Use --file for longer input.")
    route_parser.add_argument("--file", type=Path, help="Read content to route from a file.")
    route_parser.add_argument("--index", type=Path, help="Override SQLite index path.")
    route_parser.add_argument("--limit", type=int, default=5, help="Maximum number of route candidates.")

    duplicates_parser = subparsers.add_parser(
        "find-duplicates",
        help="Find existing notes that overlap with new content.",
    )
    duplicates_parser.add_argument("content", nargs="?", help="Content to compare. Use --file for longer input.")
    duplicates_parser.add_argument("--file", type=Path, help="Read content to compare from a file.")
    duplicates_parser.add_argument("--index", type=Path, help="Override SQLite index path.")
    duplicates_parser.add_argument("--limit", type=int, default=5, help="Maximum number of results.")

    duplicates_maintenance_parser = subparsers.add_parser(
        "duplicates",
        help="Inspect exact duplicate groups and related semantic duplicate ideas.",
    )
    duplicates_subparsers = duplicates_maintenance_parser.add_subparsers(
        dest="duplicates_command",
        required=True,
    )
    duplicates_list_parser = duplicates_subparsers.add_parser(
        "list",
        help="List exact duplicate groups and their canonical candidates.",
    )
    duplicates_list_parser.add_argument("--index", type=Path, help="Override SQLite index path.")
    duplicates_list_parser.add_argument("--limit", type=int, default=50, help="Maximum number of exact duplicate groups.")

    duplicates_inspect_parser = duplicates_subparsers.add_parser(
        "inspect",
        help="Inspect one exact duplicate group by path or group id.",
    )
    duplicates_inspect_parser.add_argument("path_or_group", help="Indexed path or group id like sha256:abcd1234.")
    duplicates_inspect_parser.add_argument("--index", type=Path, help="Override SQLite index path.")
    duplicates_inspect_parser.add_argument(
        "--semantic-limit",
        type=int,
        default=5,
        help="Maximum number of semantic duplicate ideas to print.",
    )

    maintenance_parser = subparsers.add_parser(
        "maintenance",
        help="Vault maintenance diagnostics.",
    )
    maintenance_subparsers = maintenance_parser.add_subparsers(dest="maintenance_command", required=True)
    maintenance_report_parser = maintenance_subparsers.add_parser(
        "report",
        help="Report maintenance findings such as meaningful empty directories.",
    )
    maintenance_report_parser.add_argument("--index", type=Path, help="Override SQLite index path.")

    structure_parser = subparsers.add_parser("structure", help="Analyze canonical PARA roles and indexed profiles.")
    structure_parser.add_argument("--index", type=Path, help="Override SQLite index path.")
    structure_parser.add_argument("--limit", type=int, default=100, help="Maximum number of profiles.")

    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            return _init(args)
        if args.command == "scan":
            return _scan(args)
        if args.command == "search":
            return _search(args)
        if args.command == "inspect":
            return _inspect(args)
        if args.command == "read":
            return _read(args)
        if args.command == "related":
            return _related(args)
        if args.command == "index":
            return _index(args)
        if args.command == "route":
            return _route(args)
        if args.command == "find-duplicates":
            return _find_duplicates(args)
        if args.command == "duplicates":
            return _duplicates(args)
        if args.command == "maintenance":
            return _maintenance(args)
        if args.command == "structure":
            return _structure(args)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    parser.error(f"Unknown command: {args.command}")
    return 2


def _init(args: argparse.Namespace) -> int:
    result = initialize_para_vault(args.vault_root, args.config)
    print(f"Created PARA vault at {result.vault_root}")
    print("Created directories:")
    for directory in result.created_directories:
        print(f"  {directory.relative_to(result.vault_root).as_posix()}/")
    print(f"Created vault config: {result.vault_config_path}")
    print("Next: run `brainiac scan` with these local config paths.")
    return 0


def _scan(args: argparse.Namespace) -> int:
    config = load_vault_config(args.config)
    config = _resolve_vault_config(config, args.vault_root, tuple(args.exclude))
    config = _with_archive_excludes(config)
    index_path = args.index or config.index_path
    result = scan_vault(config, full_rescan=args.full_rebuild)
    write_index(index_path, result)

    print(
        "Indexed "
        f"{len(result.files)} files "
        f"({result.meta['markdown_count']} Markdown) into {index_path}"
    )
    print(
        "Scan mode: "
        f"{result.meta['scan_mode']}; changed files: {result.meta['changed_file_count']}; "
        f"deleted files: {result.meta['deleted_file_count']}; unchanged files: {result.meta['unchanged_file_count']}"
    )
    return 0


def _resolve_vault_config(config, vault_root_arg: Path | None, excludes: tuple[str, ...]):
    normalized_excludes = tuple(_normalize_exclude(item) for item in excludes)
    if vault_root_arg is not None:
        return with_vault_overrides(config, root=vault_root_arg, exclude=config.exclude + normalized_excludes)
    if config.root is not None:
        return with_vault_overrides(config, exclude=config.exclude + normalized_excludes)
    if not sys.stdin.isatty():
        raise SystemExit("Vault root is not configured. Pass --vault-root or set vault.root in config/vault.yml.")

    vault_root = Path(input("Obsidian vault path: ").strip()).expanduser()
    ignored = input("Folders to ignore, comma-separated (optional): ").strip()
    extra_excludes = tuple(_normalize_exclude(item) for item in ignored.split(",") if item.strip())
    return with_vault_overrides(config, root=vault_root, exclude=config.exclude + normalized_excludes + extra_excludes)


def _with_archive_excludes(config):
    merged = tuple(dict.fromkeys(config.exclude + ("Archive/",)))
    return with_vault_overrides(config, exclude=merged)


def _normalize_exclude(value: str) -> str:
    normalized = value.strip().strip("/")
    return normalized + "/" if normalized else normalized


def _search(args: argparse.Namespace) -> int:
    config = load_vault_config(args.config)
    index_path = args.index or config.index_path
    results = search_index(index_path, args.query, limit=args.limit)
    if not results:
        print("No results.")
        return 0
    for position, result in enumerate(results, start=1):
        print(f"{position}. {result.path}")
        if result.snippet:
            print(f"   {result.snippet}")
    return 0


def _inspect(args: argparse.Namespace) -> int:
    config = load_vault_config(args.config)
    index_path = args.index or config.index_path
    inspection = inspect_path(index_path, args.path)
    print(f"Path: {inspection.path}")
    print(f"Role: {inspection.role}")
    print(f"Size: {inspection.size_bytes} bytes")
    print(f"Empty note: {inspection.is_empty_note}")
    print(f"Headings: {len(inspection.headings)}")
    for line, level, text in inspection.headings[:20]:
        print(f"  L{line} H{level} {text}")
    print(f"Tags: {', '.join(inspection.tags) if inspection.tags else '-'}")
    print(f"Tasks: {len(inspection.tasks)}")
    print(f"Outgoing links: {len(inspection.outgoing_links)}")
    for link in inspection.outgoing_links:
        suffix = f" -> {link.resolved_path}" if link.resolved_path else ""
        if not suffix and link.preferred_path:
            suffix = f" -> preferred {link.preferred_path}"
        print(f"  L{link.line} {link.resolution_status}: [[{link.target}]]{suffix}")
        if link.candidate_paths:
            print(f"    candidates: {', '.join(link.candidate_paths)}")
    print(f"Backlinks: {len(inspection.backlinks)}")
    for link in inspection.backlinks[:20]:
        suffix = f" -> {link.resolved_path}" if link.resolved_path else ""
        if not suffix and link.preferred_path:
            suffix = f" -> preferred {link.preferred_path}"
        print(f"  {link.file_path}:L{link.line} {link.resolution_status}: [[{link.target}]]{suffix}")
    print(f"Umbrella backlinks: {len(inspection.umbrella_backlinks)}")
    for path in inspection.umbrella_backlinks[:20]:
        print(f"  {path}")
    if inspection.exact_duplicates:
        print(f"Exact duplicates: {len(inspection.exact_duplicates)}")
        print(f"Canonical path: {inspection.canonical_path}")
        for path in inspection.exact_duplicates:
            print(f"  {path}")
    return 0


def _read(args: argparse.Namespace) -> int:
    config = load_vault_config(args.config)
    index_path = args.index or config.index_path
    print(read_path(index_path, args.path, section=args.section, max_chars=args.max_chars))
    return 0


def _related(args: argparse.Namespace) -> int:
    config = load_vault_config(args.config)
    index_path = args.index or config.index_path
    results = related_paths(index_path, args.path, limit=args.limit)
    if not results:
        print("No related notes.")
        return 0
    for position, result in enumerate(results, start=1):
        print(f"{position}. {result.path} ({result.score})")
        print(f"   {', '.join(result.reasons)}")
    return 0


def _index(args: argparse.Namespace) -> int:
    config = load_vault_config(args.config)
    config = _with_archive_excludes(config)
    index_path = args.index or config.index_path
    if args.index_command == "info":
        info = read_index_info(index_path, config=config, check_filesystem=args.check_filesystem)
        print(f"Index: {index_path}")
        for key in (
            "vault_name",
            "vault_root",
            "schema_version",
            "scanned_at",
            "scan_mode",
            "file_count",
            "markdown_count",
            "changed_file_count",
            "deleted_file_count",
            "unchanged_file_count",
        ):
            if key in info.meta:
                print(f"{key}: {info.meta[key]}")
        print(f"indexed_files: {info.file_count}")
        print(f"indexed_markdown_files: {info.markdown_count}")
        print(f"exact_duplicate_groups: {info.exact_duplicate_groups}")
        print(f"exact_duplicate_files: {info.exact_duplicate_files}")
        if info.duplicate_examples:
            print("Exact duplicate examples:")
            for group in info.duplicate_examples:
                print("  group:")
                for path in group:
                    print(f"    {path}")
        if info.drift is not None:
            print("Filesystem drift:")
            print(f"  added_files: {info.drift.added_files}")
            print(f"  deleted_files: {info.drift.deleted_files}")
            print(f"  metadata_changed_files: {info.drift.metadata_changed_files}")
            print(f"  unchanged_files: {info.drift.unchanged_files}")
            for label, values in (
                ("added_examples", info.drift.added_examples),
                ("deleted_examples", info.drift.deleted_examples),
                ("changed_examples", info.drift.changed_examples),
            ):
                if values:
                    print(f"  {label}:")
                    for value in values:
                        print(f"    {value}")
        return 0
    raise ValueError(f"Unknown index command: {args.index_command}")


def _route(args: argparse.Namespace) -> int:
    config = load_vault_config(args.config)
    require_para_layout(config.root)
    index_path = args.index or config.index_path
    result = route_content(
        index_path,
        _content_arg(args.content, args.file),
        limit=args.limit,
    )
    print(f"Title: {result.title}")
    print(f"Confidence: {result.confidence}")
    print(f"Recommendation: {result.recommendation}")
    print("Route candidates:")
    if not result.candidates:
        print("  No route candidates.")
    for position, candidate in enumerate(result.candidates, start=1):
        suggestion = candidate.suggestion
        print(
            f"{position}. {candidate.destination.section}.{candidate.destination.key} "
            f"-> {candidate.destination.path} ({candidate.score})"
        )
        print(f"   reasons: {', '.join(candidate.reasons)}")
        print(f"   dry-run: {suggestion.action} {suggestion.path}")
        print(f"   link: {suggestion.link}")
    print("Duplicate candidates:")
    if not result.duplicates:
        print("  No likely duplicates.")
    for position, duplicate in enumerate(result.duplicates, start=1):
        print(f"{position}. {duplicate.path} ({duplicate.score})")
        print(f"   {', '.join(duplicate.reasons)}")
    return 0


def _find_duplicates(args: argparse.Namespace) -> int:
    config = load_vault_config(args.config)
    index_path = args.index or config.index_path
    results = find_duplicates(
        index_path,
        _content_arg(args.content, args.file),
        limit=args.limit,
    )
    if not results:
        print("No likely duplicates.")
        return 0
    for position, result in enumerate(results, start=1):
        print(f"{position}. {result.path} ({result.score})")
        print(f"   {', '.join(result.reasons)}")
    return 0


def _duplicates(args: argparse.Namespace) -> int:
    config = load_vault_config(args.config)
    index_path = args.index or config.index_path
    if args.duplicates_command == "list":
        groups = list_exact_duplicate_groups(index_path, limit=args.limit)
        if not groups:
            print("No exact duplicate groups.")
            return 0
        for position, group in enumerate(groups, start=1):
            print(f"{position}. {group.group_id} ({len(group.paths)} files)")
            print(f"   canonical: {group.canonical.path}")
            print(f"   why canonical: {', '.join(group.canonical.reasons)}")
            for path in group.paths:
                suffix = " [canonical]" if path == group.canonical.path else ""
                print(f"   - {path}{suffix}")
        print("Semantic duplicate ideas are separate from exact duplicate groups. Use `brainiac duplicates inspect`.")
        return 0
    if args.duplicates_command == "inspect":
        inspection = inspect_duplicates(
            index_path,
            args.path_or_group,
            semantic_limit=args.semantic_limit,
        )
        print(f"Query: {inspection.query}")
        if inspection.exact_group is None:
            print("Exact duplicate group: none")
        else:
            group = inspection.exact_group
            print(f"Exact duplicate group: {group.group_id}")
            print(f"Canonical path: {group.canonical.path}")
            print(f"Why canonical: {', '.join(group.canonical.reasons)}")
            print("Group members:")
            for path in group.paths:
                suffix = " [canonical]" if path == group.canonical.path else ""
                print(f"  {path}{suffix}")
        print("Semantic duplicate ideas:")
        if not inspection.semantic_duplicates:
            print("  None outside the exact duplicate group.")
            return 0
        for position, duplicate in enumerate(inspection.semantic_duplicates, start=1):
            print(f"{position}. {duplicate.path} ({duplicate.score})")
            print(f"   {', '.join(duplicate.reasons)}")
        return 0
    raise ValueError(f"Unknown duplicates command: {args.duplicates_command}")


def _maintenance(args: argparse.Namespace) -> int:
    config = load_vault_config(args.config)
    config = _with_archive_excludes(config)
    index_path = args.index or config.index_path
    if args.maintenance_command == "report":
        report = maintenance_report(
            index_path,
            config=config,
        )
        print(f"Findings: {len(report.findings)}")
        print(f"Empty directories: {report.empty_directory_count}")
        print(f"Exact duplicate groups: {report.exact_duplicate_count}")
        print(f"Ambiguous wikilinks: {report.ambiguous_wikilink_count}")
        print(f"Missing wikilinks: {report.missing_wikilink_count}")
        print(f"Semantic duplicates: {report.semantic_duplicate_count}")
        if not report.findings:
            print("No maintenance findings.")
            return 0
        for finding in report.findings:
            print(f"{finding.severity.upper()} {finding.type} {finding.path}")
            print(f"  id: {finding.id}")
            print(f"  summary: {finding.summary}")
            print(f"  reasons: {', '.join(finding.reasons)}")
            print(f"  action: {finding.suggested_action}")
        return 0
    raise ValueError(f"Unknown maintenance command: {args.maintenance_command}")


def _structure(args: argparse.Namespace) -> int:
    config = load_vault_config(args.config)
    index_path = args.index or config.index_path
    analysis = analyze_structure(index_path, max_profiles=args.limit)
    print("Role roots:")
    if not analysis.role_roots:
        print("  No role roots configured.")
    for root in analysis.role_roots:
        print(f"  {root.role}: {root.path} ({root.source})")

    print("Profiles:")
    if not analysis.profiles:
        print("  No profiles found.")
    for profile in analysis.profiles:
        print(
            f"  {profile.role}: {profile.path} "
            f"({profile.note_count} notes, {profile.file_count} files)"
        )
        if profile.top_tags:
            print(f"    tags: {', '.join(profile.top_tags)}")
        if profile.top_terms:
            print(f"    terms: {', '.join(profile.top_terms)}")
        if profile.representative_notes:
            print(f"    examples: {', '.join(profile.representative_notes[:3])}")

    return 0


def _content_arg(content: str | None, file_path: Path | None) -> str:
    if file_path is not None:
        return file_path.read_text(encoding="utf-8", errors="replace")
    if content:
        return content
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise ValueError("Pass content as an argument, with --file, or through stdin.")
