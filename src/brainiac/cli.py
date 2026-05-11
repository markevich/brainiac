from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_vault_config, with_vault_overrides
from .index import write_index
from .report import write_inventory_report
from .retrieval import inspect_path, read_path, related_paths
from .routing import find_duplicates, route_content
from .scanner import scan_vault
from .search import search_index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brainiac")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/vault.yml"),
        help="Path to Brainiac vault config.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Build a read-only vault inventory index.")
    scan_parser.add_argument("--vault-root", type=Path, help="Override vault root from config.")
    scan_parser.add_argument("--index", type=Path, help="Override SQLite index output path.")
    scan_parser.add_argument("--report", type=Path, help="Inventory report output path.")
    scan_parser.add_argument("--no-report", action="store_true", help="Skip inventory report generation.")
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

    route_parser = subparsers.add_parser("route", help="Dry-run route new content into the vault.")
    route_parser.add_argument("content", nargs="?", help="Content to route. Use --file for longer input.")
    route_parser.add_argument("--file", type=Path, help="Read content to route from a file.")
    route_parser.add_argument("--index", type=Path, help="Override SQLite index path.")
    route_parser.add_argument(
        "--routing-config",
        type=Path,
        default=Path("config/routing.yml"),
        help="Path to Brainiac routing config.",
    )
    route_parser.add_argument("--limit", type=int, default=5, help="Maximum number of route candidates.")

    duplicates_parser = subparsers.add_parser(
        "find-duplicates",
        help="Find existing notes that overlap with new content.",
    )
    duplicates_parser.add_argument("content", nargs="?", help="Content to compare. Use --file for longer input.")
    duplicates_parser.add_argument("--file", type=Path, help="Read content to compare from a file.")
    duplicates_parser.add_argument("--index", type=Path, help="Override SQLite index path.")
    duplicates_parser.add_argument("--limit", type=int, default=5, help="Maximum number of results.")

    args = parser.parse_args(argv)
    try:
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
        if args.command == "route":
            return _route(args)
        if args.command == "find-duplicates":
            return _find_duplicates(args)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    parser.error(f"Unknown command: {args.command}")
    return 2


def _scan(args: argparse.Namespace) -> int:
    config = load_vault_config(args.config)
    config = _resolve_vault_config(config, args.vault_root, tuple(args.exclude))
    index_path = args.index or config.index_path
    report_path = args.report or (config.generated_root / "reports" / "inventory.md")

    result = scan_vault(config)
    write_index(index_path, result)
    if not args.no_report:
        write_inventory_report(index_path, report_path)

    print(f"Indexed {len(result.files)} files ({len(result.markdown)} Markdown) into {index_path}")
    if not args.no_report:
        print(f"Wrote inventory report to {report_path}")
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


def _route(args: argparse.Namespace) -> int:
    config = load_vault_config(args.config)
    index_path = args.index or config.index_path
    result = route_content(
        index_path,
        args.routing_config,
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
        if suggestion.policy == "review_required":
            print("   policy: review_required before any write")

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
    results = find_duplicates(index_path, _content_arg(args.content, args.file), limit=args.limit)
    if not results:
        print("No likely duplicates.")
        return 0
    for position, result in enumerate(results, start=1):
        print(f"{position}. {result.path} ({result.score})")
        print(f"   {', '.join(result.reasons)}")
    return 0


def _content_arg(content: str | None, file_path: Path | None) -> str:
    if file_path is not None:
        return file_path.read_text(encoding="utf-8", errors="replace")
    if content:
        return content
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise ValueError("Pass content as an argument, with --file, or through stdin.")
