import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from brainiac.config import VaultConfig
from brainiac.index import write_index
from brainiac.index_status import read_index_info
from brainiac.scanner import scan_vault


class IndexStatusTest(unittest.TestCase):
    def test_reports_filesystem_drift(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            vault.mkdir()
            (vault / "A.md").write_text("# A\n", encoding="utf-8")
            (vault / "B.md").write_text("# B\n", encoding="utf-8")
            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
            )

            write_index(config.index_path, scan_vault(config))
            (vault / "A.md").write_text("# A\n\nChanged.\n", encoding="utf-8")
            (vault / "B.md").unlink()
            (vault / "C.md").write_text("# C\n", encoding="utf-8")

            info = read_index_info(config.index_path, config=config, check_filesystem=True)

            self.assertEqual(info.drift.added_files, 1)
            self.assertEqual(info.drift.deleted_files, 1)
            self.assertEqual(info.drift.metadata_changed_files, 1)
            self.assertEqual(info.drift.unchanged_files, 0)
            self.assertEqual(info.drift.added_examples, ("C.md",))
            self.assertEqual(info.drift.deleted_examples, ("B.md",))
            self.assertEqual(info.drift.changed_examples, ("A.md",))

    def test_reports_exact_duplicate_groups(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "A").mkdir(parents=True)
            (vault / "B").mkdir()
            text = "# Shared\n"
            (vault / "A" / "Same.md").write_text(text, encoding="utf-8")
            (vault / "B" / "Same.md").write_text(text, encoding="utf-8")
            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
            )

            write_index(config.index_path, scan_vault(config))
            info = read_index_info(config.index_path, config=config, check_filesystem=False)

            self.assertEqual(info.exact_duplicate_groups, 1)
            self.assertEqual(info.exact_duplicate_files, 2)
            self.assertEqual(info.duplicate_examples, (("A/Same.md", "B/Same.md"),))


if __name__ == "__main__":
    unittest.main()
