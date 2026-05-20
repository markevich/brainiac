import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from brainiac.config import VaultConfig
from brainiac.index import write_index
from brainiac.scanner import scan_vault
from brainiac.search import search_index


class SearchTest(unittest.TestCase):
    def test_searches_markdown_body_and_metadata(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            vault.mkdir()
            (vault / "Cooking.md").write_text(
                "# Fermentation\n\nKimchi and pickles live here.\n#food\n",
                encoding="utf-8",
            )
            (vault / "Travel.md").write_text("# Flights\n\nAirport notes.\n", encoding="utf-8")

            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
                generated_root=tmp_path / "generated",
            )

            write_index(config.index_path, scan_vault(config))

            body_results = search_index(config.index_path, "kimchi", limit=5)
            tag_results = search_index(config.index_path, "food", limit=5)
            path_results = search_index(config.index_path, "travel", limit=5)

            self.assertEqual([result.path for result in body_results], ["Cooking.md"])
            self.assertEqual([result.path for result in tag_results], ["Cooking.md"])
            self.assertEqual([result.path for result in path_results], ["Travel.md"])

    def test_applies_synthesis_boost_before_limiting_results(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "Notes").mkdir(parents=True)
            (vault / "Synthesis").mkdir()
            for index in range(40):
                (vault / "Notes" / f"A{index:02}.md").write_text(
                    "# Common\n\nneedle phrase\n",
                    encoding="utf-8",
                )
            (vault / "Synthesis" / "Z summary.md").write_text(
                "# Common\n\nneedle phrase\n",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
synthesis_roots:
  - "Synthesis/"
""",
                encoding="utf-8",
            )
            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
                generated_root=tmp_path / "generated",
            )

            write_index(config.index_path, scan_vault(config))
            results = search_index(config.index_path, "needle phrase", limit=1, routing_config_path=routing_config)

            self.assertEqual([result.path for result in results], ["Synthesis/Z summary.md"])


if __name__ == "__main__":
    unittest.main()
