import sqlite3
import unittest
from contextlib import closing
from os import utime
from pathlib import Path
from tempfile import TemporaryDirectory

from brainiac.config import VaultConfig
from brainiac.cli import main
from brainiac.index import write_index
from brainiac.report import write_inventory_report
from brainiac.scanner import scan_vault


class ScanTest(unittest.TestCase):
    def test_scan_writes_inventory_index_and_report(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            vault.mkdir()
            (vault / "Note A.md").write_text(
                "---\ntopic: Test topic\n---\n# Note A\n\nLinks to [[Folder/Note B]] and [[Missing]].\n\n- [ ] follow up\n#topic\n",
                encoding="utf-8",
            )
            folder = vault / "Folder"
            folder.mkdir()
            (folder / "Note B.md").write_text("# Note B\n", encoding="utf-8")
            ignored = vault / ".obsidian"
            ignored.mkdir()
            (ignored / "cache.json").write_text("{}", encoding="utf-8")
            (vault / "script.py").write_text("print(1)", encoding="utf-8")

            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(".obsidian/",),
                source_patterns=("*.md", "*.json"),
                index_path=tmp_path / "brainiac.sqlite",
                generated_root=tmp_path / "generated",
            )

            result = scan_vault(config)
            write_index(config.index_path, result)
            report_path = config.generated_root / "reports" / "inventory.md"
            write_inventory_report(config.index_path, report_path)

            with closing(sqlite3.connect(config.index_path)) as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM files").fetchone()[0], 2)
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM markdown_headings").fetchone()[0], 2
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM tasks WHERE done = 0").fetchone()[0], 1
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM tags WHERE tag = '#topic'").fetchone()[0],
                    1,
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM wikilinks WHERE is_resolved = 1").fetchone()[
                        0
                    ],
                    1,
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM wikilinks WHERE is_resolved = 0").fetchone()[
                        0
                    ],
                    1,
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM search_index").fetchone()[0],
                    2,
                )
                self.assertEqual(
                    connection.execute("SELECT value FROM markdown_metadata WHERE key = 'topic'").fetchone()[0],
                    "Test topic",
                )

            report = report_path.read_text(encoding="utf-8")
            self.assertIn("Brainiac Inventory Report", report)
            self.assertIn("Missing", report)
            self.assertIn("follow up", report)

    def test_cli_scan_excludes_archive_roots_from_routing_config(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "Archive").mkdir(parents=True)
            (vault / "Notes").mkdir()
            (vault / "Archive" / "Old.md").write_text("# Old\n\narchive copy\n", encoding="utf-8")
            (vault / "Notes" / "Active.md").write_text("# Active\n\nsource copy\n", encoding="utf-8")
            vault_config = tmp_path / "vault.yml"
            index_path = tmp_path / "brainiac.sqlite"
            generated_root = tmp_path / "generated"
            vault_config.write_text(
                f"""
vault:
  name: "Test vault"
  root: "{vault.as_posix()}"

exclude:
  - ".obsidian/"

source_formats:
  markdown:
    - "*.md"

generated_paths:
  root: "{generated_root.as_posix()}"

index:
  path: "{index_path.as_posix()}"
""",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
archive_roots:
  - "Archive/"
""",
                encoding="utf-8",
            )

            exit_code = main(
                [
                    "--config",
                    vault_config.as_posix(),
                    "scan",
                    "--routing-config",
                    routing_config.as_posix(),
                    "--no-report",
                ]
            )

            self.assertEqual(exit_code, 0)
            with closing(sqlite3.connect(index_path)) as connection:
                paths = connection.execute("SELECT path FROM files ORDER BY path").fetchall()
            self.assertEqual(paths, [("Notes/Active.md",)])

    def test_wikilink_resolution_leaves_ambiguous_stems_unresolved(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "A").mkdir(parents=True)
            (vault / "B").mkdir()
            (vault / "Source.md").write_text("[[Duplicate]] [[A/Duplicate]]", encoding="utf-8")
            (vault / "A" / "Duplicate.md").write_text("# A\n", encoding="utf-8")
            (vault / "B" / "Duplicate.md").write_text("# B\n", encoding="utf-8")

            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
                generated_root=tmp_path / "generated",
            )

            result = scan_vault(config)
            write_index(config.index_path, result)

            with closing(sqlite3.connect(config.index_path)) as connection:
                rows = connection.execute(
                    """
                    SELECT target, resolved_path, preferred_path, is_resolved, resolution_status, candidate_paths
                    FROM wikilinks
                    ORDER BY target
                    """
                ).fetchall()

            self.assertEqual(
                rows,
                [
                    ("A/Duplicate", "A/Duplicate.md", None, 1, "resolved", None),
                    ("Duplicate", None, "A/Duplicate.md", 0, "ambiguous", "A/Duplicate.md\nB/Duplicate.md"),
                ],
            )

    def test_incremental_scan_updates_only_changed_files_and_reresolves_links(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            vault.mkdir()
            (vault / "Source.md").write_text("[[Duplicate]]\n", encoding="utf-8")
            (vault / "Duplicate.md").write_text("# First\n", encoding="utf-8")

            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
                generated_root=tmp_path / "generated",
            )

            first = scan_vault(config)
            write_index(config.index_path, first)

            (vault / "Folder").mkdir()
            (vault / "Folder" / "Duplicate.md").write_text("# Second\n", encoding="utf-8")
            (vault / "Duplicate.md").unlink()

            second = scan_vault(config)
            write_index(config.index_path, second)

            self.assertEqual(second.meta["scan_mode"], "incremental")
            self.assertEqual(second.meta["changed_file_count"], "1")
            self.assertEqual(second.meta["deleted_file_count"], "1")
            self.assertEqual(second.meta["unchanged_file_count"], "1")
            self.assertEqual(second.changed_paths, ("Folder/Duplicate.md",))
            self.assertEqual(second.deleted_paths, ("Duplicate.md",))

            with closing(sqlite3.connect(config.index_path)) as connection:
                files = connection.execute("SELECT path FROM files ORDER BY path").fetchall()
                link = connection.execute(
                    """
                    SELECT resolved_path, preferred_path, resolution_status, candidate_paths
                    FROM wikilinks
                    WHERE file_path = 'Source.md'
                    """
                ).fetchone()

            self.assertEqual(files, [("Folder/Duplicate.md",), ("Source.md",)])
            self.assertEqual(link, ("Folder/Duplicate.md", None, "resolved", None))

    def test_incremental_scan_preserves_markdown_rows_when_only_mtime_changes(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            vault.mkdir()
            note = vault / "Topic.md"
            note.write_text("# Topic\n\nKimchi.\n", encoding="utf-8")

            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
                generated_root=tmp_path / "generated",
            )

            write_index(config.index_path, scan_vault(config))
            stat = note.stat()
            utime(note, (stat.st_atime, stat.st_mtime + 10))

            second = scan_vault(config)
            write_index(config.index_path, second)

            self.assertEqual(second.meta["scan_mode"], "incremental")
            self.assertEqual(second.meta["changed_file_count"], "1")
            self.assertEqual(second.markdown_refresh_paths, ())

            with closing(sqlite3.connect(config.index_path)) as connection:
                headings = connection.execute(
                    "SELECT COUNT(*) FROM markdown_headings WHERE file_path = 'Topic.md'"
                ).fetchone()[0]
                search_rows = connection.execute(
                    "SELECT COUNT(*) FROM search_index WHERE path = 'Topic.md'"
                ).fetchone()[0]

            self.assertEqual(headings, 1)
            self.assertEqual(search_rows, 1)


if __name__ == "__main__":
    unittest.main()
