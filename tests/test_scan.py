import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from brainiac.config import VaultConfig
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
                "# Note A\n\nLinks to [[Folder/Note B]] and [[Missing]].\n\n- [ ] follow up\n#topic\n",
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

            with sqlite3.connect(config.index_path) as connection:
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

            report = report_path.read_text(encoding="utf-8")
            self.assertIn("Brainiac Inventory Report", report)
            self.assertIn("Missing", report)
            self.assertIn("follow up", report)

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

            with sqlite3.connect(config.index_path) as connection:
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


if __name__ == "__main__":
    unittest.main()
