from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from brainiac.config import load_vault_config


class VaultConfigTests(unittest.TestCase):
    def test_requires_explicit_para_layout(self):
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config" / "brainiac.yml"
            config_path.parent.mkdir()
            config_path.write_text(
                """
brainiac:
  config_version: 1

vault:
  name: "Test vault"
  root: "/tmp/test-vault"

index:
  path: "memory/index/brainiac.sqlite"
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "vault.layout: para"):
                load_vault_config(config_path)

    def test_resolves_relative_index_path_from_local_workspace(self):
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            config_path = workspace / "config" / "brainiac.yml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                """
brainiac:
  config_version: 1

vault:
  name: "Test vault"
  root: "/tmp/test-vault"
  layout: para

source_formats:
  markdown:
    - "*.md"

index:
  path: "memory/index/brainiac.sqlite"
""",
                encoding="utf-8",
            )

            config = load_vault_config(config_path)

            self.assertEqual(config.index_path, workspace / "memory" / "index" / "brainiac.sqlite")
            self.assertEqual(config.source_patterns, ("*.md",))

    def test_rejects_an_unsupported_config_version(self):
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config" / "brainiac.yml"
            config_path.parent.mkdir()
            config_path.write_text(
                """
brainiac:
  config_version: 2

vault:
  root: "/tmp/test-vault"
  layout: para

index:
  path: "memory/index/brainiac.sqlite"
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "LLM upgrade flow"):
                load_vault_config(config_path)


if __name__ == "__main__":
    unittest.main()
