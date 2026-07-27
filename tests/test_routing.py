from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from brainiac.config import VaultConfig
from brainiac.index import write_index
from brainiac.routing import find_duplicates
from brainiac.scanner import scan_vault


class RoutingTests(unittest.TestCase):
    def test_find_duplicates_reports_same_title(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "Inbox").mkdir(parents=True)
            (vault / "Inbox" / "Coffee.md").write_text(
                "# Coffee\n\nTbilisi breakfast and pastries.\n", encoding="utf-8"
            )
            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
            )
            write_index(config.index_path, scan_vault(config))

            candidates = find_duplicates(
                config.index_path, "# Coffee\n\nA different coffee note.",
            )

            self.assertEqual(candidates[0].path, "Inbox/Coffee.md")
            self.assertIn("same title", candidates[0].reasons)

    def test_find_duplicates_returns_empty_for_unrelated_content(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "Inbox").mkdir(parents=True)
            (vault / "Inbox" / "Coffee.md").write_text(
                "# Coffee\n\nTbilisi breakfast and pastries.\n", encoding="utf-8"
            )
            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
            )
            write_index(config.index_path, scan_vault(config))

            candidates = find_duplicates(config.index_path, "# Telescope\n\nAstronomy observations.")

            self.assertEqual(candidates, ())


if __name__ == "__main__":
    unittest.main()
