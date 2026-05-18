import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from brainiac.config import VaultConfig
from brainiac.duplicates import inspect_duplicates, list_exact_duplicate_groups
from brainiac.index import write_index
from brainiac.scanner import scan_vault


class DuplicatesTest(unittest.TestCase):
    def test_lists_exact_duplicate_groups_with_canonical_reason(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "0_Inbox").mkdir(parents=True)
            (vault / "2_Areas" / "Work").mkdir(parents=True)
            (vault / "2_Areas" / "Travel").mkdir(parents=True)
            shared = "# Shared\n\nSame content.\n"
            (vault / "0_Inbox" / "Shared.md").write_text(shared, encoding="utf-8")
            (vault / "2_Areas" / "Work" / "Shared.md").write_text(shared, encoding="utf-8")
            (vault / "2_Areas" / "Travel" / "Trips.md").write_text(
                "# Trips\n\ntravel itinerary flights hotels\n",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
inbox_roots:
  - "0_Inbox/"
area_roots:
  - "2_Areas/"
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
            groups = list_exact_duplicate_groups(config.index_path, routing_config_path=routing_config)

            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0].canonical.path, "2_Areas/Work/Shared.md")
            self.assertIn("preferred over inbox paths", groups[0].canonical.reasons)
            self.assertTrue(groups[0].group_id.startswith("sha256:"))

    def test_inspect_duplicates_supports_path_and_group_id_and_separates_semantic_ideas(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "0_Inbox").mkdir(parents=True)
            (vault / "2_Areas" / "Work").mkdir(parents=True)
            exact = "# Shared\n\nSame content.\n"
            (vault / "0_Inbox" / "Shared.md").write_text(exact, encoding="utf-8")
            (vault / "2_Areas" / "Work" / "Shared.md").write_text(exact, encoding="utf-8")
            (vault / "2_Areas" / "Work" / "Shared notes.md").write_text(
                "# Shared\n\nSame content summary and follow-up actions.\n",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
inbox_roots:
  - "0_Inbox/"
area_roots:
  - "2_Areas/"
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
            by_path = inspect_duplicates(
                config.index_path,
                "0_Inbox/Shared.md",
                routing_config_path=routing_config,
                semantic_limit=3,
            )

            self.assertIsNotNone(by_path.exact_group)
            self.assertEqual(by_path.exact_group.canonical.path, "2_Areas/Work/Shared.md")
            self.assertEqual([item.path for item in by_path.semantic_duplicates], ["2_Areas/Work/Shared notes.md"])

            by_group = inspect_duplicates(
                config.index_path,
                by_path.exact_group.group_id,
                routing_config_path=routing_config,
                semantic_limit=3,
            )

            self.assertIsNotNone(by_group.exact_group)
            self.assertEqual(by_group.exact_group.group_id, by_path.exact_group.group_id)
            self.assertEqual(by_group.semantic_duplicates, by_path.semantic_duplicates)


if __name__ == "__main__":
    unittest.main()
