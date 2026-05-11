from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_vault_config, with_vault_overrides
from .index import write_index
from .report import write_inventory_report
from .scanner import scan_vault


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

    args = parser.parse_args(argv)
    if args.command == "scan":
        return _scan(args)
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
