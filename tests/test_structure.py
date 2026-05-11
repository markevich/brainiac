import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from brainiac.config import VaultConfig
from brainiac.index import write_index
from brainiac.scanner import scan_vault
from brainiac.structure import analyze_structure


class StructureTest(unittest.TestCase):
    def test_detects_configured_and_unconfigured_area_profiles(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "2_Areas" / "Food").mkdir(parents=True)
            (vault / "2_Areas" / "Music").mkdir()
            (vault / "2_Areas" / "Health").mkdir()
            (vault / "2_Areas" / "Food" / "Rice.md").write_text(
                "# Rice\n\nRisotto and jasmine rice.\n#food\n",
                encoding="utf-8",
            )
            (vault / "2_Areas" / "Music" / "Songs.md").write_text(
                "# Songs\n\nLyrics, melody, and vocal ideas.\n#music\n",
                encoding="utf-8",
            )
            (vault / "2_Areas" / "Health" / "Sleep.md").write_text(
                "# Sleep\n\nRecovery and energy.\n#health\n",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
areas:
  food: "2_Areas/Food/"
area_roots:
  - "2_Areas/"
sensitive_path_prefixes:
  - "2_Areas/Health/"
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

            analysis = analyze_structure(config.index_path, routing_config)
            profiles = {profile.path: profile for profile in analysis.profiles}
            unconfigured = {profile.path for profile in analysis.unconfigured_profiles}

            self.assertTrue(profiles["2_Areas/Food/"].configured)
            self.assertFalse(profiles["2_Areas/Music/"].configured)
            self.assertTrue(profiles["2_Areas/Health/"].sensitive)
            self.assertIn("2_Areas/Music/", unconfigured)
            self.assertIn("Configure area destination for 2_Areas/Music/", analysis.recommendations)

    def test_requires_configured_role_roots_for_profiles(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "0_Inbox").mkdir(parents=True)
            (vault / "0_Inbox" / "Capture.md").write_text("# Capture\n", encoding="utf-8")
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text("inbox:\n  default: \"0_Inbox/\"\n", encoding="utf-8")
            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
                generated_root=tmp_path / "generated",
            )

            write_index(config.index_path, scan_vault(config))

            analysis = analyze_structure(config.index_path, routing_config)

            self.assertEqual(analysis.role_roots, ())
            self.assertEqual(analysis.profiles, ())
            self.assertIn(
                "Configure role roots so Brainiac can build area/project/resource profiles.",
                analysis.recommendations,
            )


if __name__ == "__main__":
    unittest.main()
