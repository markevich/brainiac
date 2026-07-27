from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from brainiac.config import VaultConfig
from brainiac.index import write_index
from brainiac.scanner import scan_vault
from brainiac.structure import analyze_structure


class StructureTests(unittest.TestCase):
    def test_reports_profiles_only_under_canonical_para_roots(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "Inbox").mkdir(parents=True)
            (vault / "Projects" / "Launch").mkdir(parents=True)
            (vault / "Areas" / "Food").mkdir(parents=True)
            (vault / "Resources" / "Coffee").mkdir(parents=True)
            (vault / "Archive" / "Old").mkdir(parents=True)
            (vault / "Old" / "Resources" / "Legacy").mkdir(parents=True)
            (vault / "Inbox" / "Capture.md").write_text("# Capture\n", encoding="utf-8")
            (vault / "Projects" / "Launch" / "Plan.md").write_text("# Plan\n", encoding="utf-8")
            (vault / "Areas" / "Food" / "Recipes.md").write_text("# Recipes\n", encoding="utf-8")
            (vault / "Resources" / "Coffee" / "Beans.md").write_text("# Beans\n", encoding="utf-8")
            (vault / "Archive" / "Old" / "Note.md").write_text("# Old\n", encoding="utf-8")
            (vault / "Old" / "Resources" / "Legacy" / "Note.md").write_text("# Legacy\n", encoding="utf-8")
            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=("Archive/",),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
            )
            write_index(config.index_path, scan_vault(config))

            analysis = analyze_structure(config.index_path)
            profiles = {(profile.role, profile.path) for profile in analysis.profiles}

            self.assertIn(("inbox", "Inbox/"), profiles)
            self.assertIn(("project", "Projects/Launch/"), profiles)
            self.assertIn(("area", "Areas/Food/"), profiles)
            self.assertIn(("resource", "Resources/Coffee/"), profiles)
            self.assertFalse(any(path.startswith("Old/") for _, path in profiles))


if __name__ == "__main__":
    unittest.main()
