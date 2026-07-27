from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from brainiac.bootstrap import INSTALLATION_VERSION, PARA_DIRECTORIES
from brainiac.cli import main
from brainiac.config import load_vault_config


class ParaVaultBootstrapTests(unittest.TestCase):
    def test_init_uses_default_local_config_paths_in_a_clean_workspace(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workspace = tmp_path / "workspace"
            workspace.mkdir()
            vault_root = tmp_path / "new-vault"
            previous_directory = Path.cwd()
            try:
                os.chdir(workspace)
                exit_code = main(["init", "--vault-root", str(vault_root)])
            finally:
                os.chdir(previous_directory)

            self.assertEqual(exit_code, 0)
            self.assertTrue((workspace / "config/brainiac.yml").is_file())
            self.assertFalse((workspace / "config/routing.yml").exists())
            self.assertEqual(load_vault_config(workspace / "config/brainiac.yml").layout, "para")
            self.assertTrue((workspace / "brainiac_me.md").is_file())
            self.assertTrue((workspace / ".state/setup.yml").is_file())
            self.assertTrue((workspace / ".state/update_check.yml").is_file())
            self.assertIn("status: in_progress", (workspace / ".state/setup.yml").read_text(encoding="utf-8"))
            self.assertIn("last_result: not_checked", (workspace / ".state/update_check.yml").read_text(encoding="utf-8"))

    def test_init_creates_empty_para_vault_and_local_configs(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault_root = tmp_path / "new-vault"
            workspace = tmp_path / "workspace"
            workspace.mkdir()

            output = StringIO()
            previous_directory = Path.cwd()
            try:
                os.chdir(workspace)
                with redirect_stdout(output):
                    exit_code = main(["init", "--vault-root", str(vault_root)])
            finally:
                os.chdir(previous_directory)

            self.assertEqual(exit_code, 0)
            self.assertIn("Created PARA vault", output.getvalue())
            for relative_path in PARA_DIRECTORIES:
                self.assertTrue((vault_root / relative_path).is_dir())
            vault_config = workspace / "config" / "brainiac.yml"
            vault = load_vault_config(vault_config)
            self.assertEqual(vault.root, vault_root.resolve())
            self.assertEqual(vault.name, "new-vault")
            self.assertEqual(vault.layout, "para")
            self.assertIn("config_version: 1", vault_config.read_text(encoding="utf-8"))
            personal_context = (tmp_path / "workspace" / "brainiac_me.md").read_text(encoding="utf-8")
            self.assertIn(f"installed_version: {INSTALLATION_VERSION}", personal_context)
            self.assertIn("## Personal Patterns", personal_context)
            template = (Path(__file__).resolve().parents[1] / "brainiac_me.template.md").read_text(encoding="utf-8")
            self.assertEqual(personal_context, template)
            update_state = (tmp_path / "workspace" / ".state/update_check.yml").read_text(encoding="utf-8")
            self.assertIn(f"last_local_version: {INSTALLATION_VERSION}", update_state)

    def test_init_refuses_an_existing_personal_context(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault_root = tmp_path / "new-vault"
            workspace = tmp_path / "workspace"
            (workspace / "brainiac_me.md").parent.mkdir(parents=True)
            (workspace / "brainiac_me.md").write_text("# Existing\n", encoding="utf-8")

            stderr = StringIO()
            previous_directory = Path.cwd()
            try:
                os.chdir(workspace)
                with redirect_stderr(stderr):
                    exit_code = main(["init", "--vault-root", str(vault_root)])
            finally:
                os.chdir(previous_directory)

            self.assertEqual(exit_code, 1)
            self.assertIn("installation file already exists", stderr.getvalue())
            self.assertFalse(vault_root.exists())

    def test_init_refuses_nonempty_vault_without_writing_configs(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault_root = tmp_path / "existing-vault"
            vault_root.mkdir()
            (vault_root / "Note.md").write_text("# Existing\n", encoding="utf-8")
            workspace = tmp_path / "workspace"
            workspace.mkdir()

            stderr = StringIO()
            previous_directory = Path.cwd()
            try:
                os.chdir(workspace)
                with redirect_stderr(stderr):
                    exit_code = main(["init", "--vault-root", str(vault_root)])
            finally:
                os.chdir(previous_directory)

            self.assertEqual(exit_code, 1)
            self.assertIn("creates new vaults only", stderr.getvalue())
            vault_config = workspace / "config" / "brainiac.yml"
            self.assertFalse(vault_config.exists())

    def test_init_refuses_to_overwrite_existing_config(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault_root = tmp_path / "new-vault"
            workspace = tmp_path / "workspace"
            vault_config = workspace / "config" / "brainiac.yml"
            vault_config.parent.mkdir(parents=True)
            vault_config.write_text("existing config", encoding="utf-8")

            stderr = StringIO()
            previous_directory = Path.cwd()
            try:
                os.chdir(workspace)
                with redirect_stderr(stderr):
                    exit_code = main(["init", "--vault-root", str(vault_root)])
            finally:
                os.chdir(previous_directory)

            self.assertEqual(exit_code, 1)
            self.assertIn("Refusing to overwrite", stderr.getvalue())
            self.assertFalse(vault_root.exists())

    def test_init_refuses_a_config_path_inside_the_vault(self):
        with TemporaryDirectory() as tmp:
            vault_root = Path(tmp) / "new-vault"
            vault_root.mkdir()

            stderr = StringIO()
            previous_directory = Path.cwd()
            try:
                os.chdir(vault_root)
                with redirect_stderr(stderr):
                    exit_code = main(["init", "--vault-root", str(vault_root)])
            finally:
                os.chdir(previous_directory)

            self.assertEqual(exit_code, 1)
            self.assertIn("must stay outside the vault root", stderr.getvalue())
            self.assertFalse((vault_root / "config" / "brainiac.yml").exists())


if __name__ == "__main__":
    unittest.main()
