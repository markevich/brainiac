from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from brainiac.bootstrap import initialize_para_vault
from brainiac.cli import main
from brainiac.config import VaultConfig, load_vault_config
from brainiac.index import write_index
from brainiac.maintenance import maintenance_report
from brainiac.para import validate_para_layout
from brainiac.scanner import scan_vault


class ParaLayoutTests(unittest.TestCase):
    def test_initialized_vault_is_para_compliant(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault_root = tmp_path / "vault"
            vault_config = tmp_path / "workspace" / "config" / "vault.yml"
            initialize_para_vault(vault_root, vault_config)

            self.assertEqual(validate_para_layout(vault_root), ())

    def test_maintenance_reports_missing_para_directory_for_managed_vault(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault_root = tmp_path / "vault"
            vault_config = tmp_path / "workspace" / "config" / "vault.yml"
            initialize_para_vault(vault_root, vault_config)
            (vault_root / "Resources").rmdir()
            config = load_vault_config(vault_config)
            write_index(config.index_path, scan_vault(config))

            report = maintenance_report(config.index_path, config=config)
            findings = [finding for finding in report.findings if finding.type == "missing_para_directory"]

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].path, "Resources/")
            self.assertEqual(findings[0].severity, "high")

    def test_route_is_blocked_for_noncompliant_managed_vault(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault_root = tmp_path / "vault"
            vault_config = tmp_path / "workspace" / "config" / "vault.yml"
            initialize_para_vault(vault_root, vault_config)
            (vault_root / "Areas").rmdir()

            stderr = StringIO()
            with redirect_stderr(stderr):
                exit_code = main(
                    [
                        "--config",
                        str(vault_config),
                        "route",
                        "# A note",
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("route is blocked", stderr.getvalue())
            self.assertIn("missing_para_directory: Areas/", stderr.getvalue())

    def test_validator_only_depends_on_vault_structure(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault_root = tmp_path / "vault"
            vault_config = tmp_path / "workspace" / "config" / "vault.yml"
            initialize_para_vault(vault_root, vault_config)
            (vault_root / "Resources").rmdir()

            violations = validate_para_layout(vault_root)

            self.assertTrue(any(item.type == "missing_para_directory" for item in violations))


if __name__ == "__main__":
    unittest.main()
