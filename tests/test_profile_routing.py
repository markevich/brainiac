import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from contextlib import redirect_stdout
from io import StringIO

from brainiac.cli import main
from brainiac.config import VaultConfig
from brainiac.index import write_index
from brainiac.routing import route_content
from brainiac.scanner import scan_vault


class ProfileRoutingTests(unittest.TestCase):
    def _index(self, tmp_path: Path) -> VaultConfig:
        vault = tmp_path / "vault"
        (vault / "Inbox").mkdir(parents=True)
        (vault / "Projects").mkdir()
        (vault / "Areas").mkdir()
        (vault / "Resources" / "Food" / "Cafes" / "Tbilisi").mkdir(parents=True)
        (vault / "Resources" / "Food" / "Meat").mkdir(parents=True)
        (vault / "Resources" / "Food" / "Cafes" / "Tbilisi" / "Entree.md").write_text(
            "# Entree\n\nTbilisi coffee breakfast pastries.\n", encoding="utf-8"
        )
        (vault / "Resources" / "Food" / "Cafes" / "Tbilisi" / "Santini.md").write_text(
            "# Santini\n\nTbilisi breakfast with good coffee.\n", encoding="utf-8"
        )
        (vault / "Resources" / "Food" / "Meat" / "Shop.md").write_text(
            "# Meat shop\n\nFood, meat, and grill.\n", encoding="utf-8"
        )
        config = VaultConfig(
            name="Test vault", root=vault, exclude=(), source_patterns=("*.md",),
            index_path=tmp_path / "brainiac.sqlite", layout="para",
        )
        write_index(config.index_path, scan_vault(config))
        return config

    def test_routes_to_deepest_profile_using_idf_weighted_evidence(self):
        with TemporaryDirectory() as tmp:
            config = self._index(Path(tmp))
            result = route_content(
                config.index_path, "# Coffee tomorrow\n\nTbilisi coffee and breakfast pastries.",
            )

            self.assertEqual(result.candidates[0].destination.path, "Resources/Food/Cafes/Tbilisi/")
            self.assertEqual(result.confidence, "high")
            self.assertFalse(any(item.destination.path == "Resources/Food/Cafes/" for item in result.candidates))
            self.assertFalse(any("Meat/Shop.md" in item.path for item in result.duplicates))

    def test_routes_weak_evidence_to_inbox(self):
        with TemporaryDirectory() as tmp:
            config = self._index(Path(tmp))
            result = route_content(
                config.index_path, "# New thought\n\nUnrelated astronomy telescope.",
            )

            self.assertEqual(result.candidates[0].destination.path, "Inbox/")
            self.assertEqual(result.confidence, "low")

    def test_ignores_nested_legacy_named_para_roots(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            for directory in ("Inbox", "Projects", "Areas", "Resources", "Archive"):
                (vault / directory).mkdir(parents=True, exist_ok=True)
            legacy_profile = vault / "Old" / "Resources" / "Coffee"
            legacy_profile.mkdir(parents=True)
            (legacy_profile / "Note.md").write_text(
                "# Note\n\nTbilisi coffee breakfast pastries.\n", encoding="utf-8"
            )
            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
            )
            write_index(config.index_path, scan_vault(config))

            result = route_content(
                config.index_path, "# Coffee tomorrow\n\nTbilisi coffee breakfast pastries.",
            )

            self.assertEqual(result.candidates[0].destination.path, "Inbox/")
            self.assertFalse(any(candidate.destination.path.startswith("Old/") for candidate in result.candidates))

    def test_new_vault_cli_routes_without_a_routing_config(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            workspace = tmp_path / "workspace"
            workspace.mkdir()
            previous_directory = Path.cwd()
            try:
                os.chdir(workspace)
                self.assertEqual(main(["init", "--vault-root", str(vault)]), 0)
                config = workspace / "config" / "brainiac.yml"
                self.assertFalse((config.parent / "routing.yml").exists())
                destination = vault / "Resources" / "Food" / "Cafes" / "Tbilisi"
                destination.mkdir(parents=True)
                (destination / "Entree.md").write_text(
                    "# Entree\n\nTbilisi coffee breakfast pastries.\n", encoding="utf-8"
                )

                self.assertEqual(main(["scan"]), 0)
                output = StringIO()
                with redirect_stdout(output):
                    self.assertEqual(
                        main(["route", "# Coffee tomorrow\n\nTbilisi coffee breakfast pastries."]),
                        0,
                    )
            finally:
                os.chdir(previous_directory)
            self.assertIn("Resources/Food/Cafes/Tbilisi/", output.getvalue())


if __name__ == "__main__":
    unittest.main()
