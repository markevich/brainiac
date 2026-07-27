from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from brainiac.bootstrap import initialize_para_vault
from brainiac.config import VaultConfig, load_vault_config
from brainiac.index import write_index
from brainiac.maintenance import maintenance_report
from brainiac.scanner import scan_vault


class MaintenanceTests(unittest.TestCase):
    def test_fresh_initialized_vault_is_maintenance_clean(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            vault_config = tmp_path / "workspace" / "config" / "brainiac.yml"
            initialize_para_vault(vault, vault_config)
            config = load_vault_config(vault_config)
            write_index(config.index_path, scan_vault(config))

            report = maintenance_report(config.index_path, config=config)

            self.assertEqual(report.findings, ())

    def test_reports_missing_source_marker_and_invalid_marker(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            vault_config = tmp_path / "workspace" / "config" / "brainiac.yml"
            initialize_para_vault(vault, vault_config)
            (vault / "Resources" / "Food").mkdir()
            (vault / "Resources" / "Food" / "Coffee.md").write_text(
                "# Coffee\n\nBeans and brewing notes.\n", encoding="utf-8"
            )
            (vault / "Resources" / "Food" / "Broken.md").write_text(
                "---\nbrainiac_role: summary\n---\n# Broken\n", encoding="utf-8"
            )
            config = load_vault_config(vault_config)
            write_index(config.index_path, scan_vault(config))

            report = maintenance_report(config.index_path, config=config)
            finding_types = {(finding.type, finding.path) for finding in report.findings}

            self.assertIn(("missing_role_marker", "Resources/Food/Coffee.md"), finding_types)
            self.assertIn(("invalid_role_marker", "Resources/Food/Broken.md"), finding_types)


if __name__ == "__main__":
    unittest.main()
