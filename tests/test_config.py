import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from brainiac.config import load_vault_config


class ConfigTest(unittest.TestCase):
    def test_loads_repository_vault_example_config_shape(self):
        config = load_vault_config(Path("config/vault.example.yml").resolve())

        self.assertEqual(config.name, "Unknown vault")
        self.assertIsNone(config.root)
        self.assertIn(".obsidian/", config.exclude)
        self.assertIn("*.md", config.source_patterns)
        self.assertIn("*.json", config.source_patterns)
        self.assertEqual(config.index_path, Path("memory/index/brainiac.sqlite").resolve())
        self.assertEqual(config.generated_root, Path("memory/generated").resolve())

    def test_missing_local_config_is_created_from_template(self):
        with TemporaryDirectory() as tmp:
            config_dir = Path(tmp) / "config"
            config_dir.mkdir()
            path = config_dir / "vault.yml"
            example_path = config_dir / "vault.example.yml"
            example_path.write_text(
                """vault:
  name: "Example"
  root: ""

exclude:
  - ".obsidian/"

source_formats:
  markdown:
    - "*.md"

generated_paths:
  root: "memory/generated/"

index:
  path: "memory/index/brainiac.sqlite"
""",
                encoding="utf-8",
            )

            config = load_vault_config(path)

            self.assertTrue(path.exists())
            self.assertEqual(config.name, "Example")
            self.assertEqual(config.source_patterns, ("*.md",))


if __name__ == "__main__":
    unittest.main()
