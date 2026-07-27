import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from brainiac.config import VaultConfig
from brainiac.index import write_index
from brainiac.retrieval import inspect_path, read_path, related_paths
from brainiac.scanner import scan_vault


class RetrievalTest(unittest.TestCase):
    def test_inspects_and_reads_bounded_sections(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            vault.mkdir()
            (vault / "Source.md").write_text(
                """# Source

[[Target]]
#topic
- [ ] follow up

## Details

Important section text.

## Later

Other text.
""",
                encoding="utf-8",
            )
            (vault / "Target.md").write_text("# Target\n", encoding="utf-8")
            (vault / "Peer.md").write_text("# Peer\n\n#topic\n", encoding="utf-8")

            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
            )

            write_index(config.index_path, scan_vault(config))

            inspection = inspect_path(config.index_path, "Source.md")
            section = read_path(config.index_path, "Source.md", section="Details")
            truncated = read_path(config.index_path, "Source.md", max_chars=12)
            related = related_paths(config.index_path, "Source.md", limit=5)

            self.assertEqual(inspection.path, "Source.md")
            self.assertEqual(inspection.tags, ("#topic",))
            self.assertEqual(inspection.tasks[0].text, "follow up")
            self.assertEqual(inspection.outgoing_links[0].resolved_path, "Target.md")
            target_inspection = inspect_path(config.index_path, "Target.md")
            self.assertEqual(target_inspection.backlinks[0].file_path, "Source.md")
            self.assertIn("Important section text.", section)
            self.assertNotIn("Other text.", section)
            self.assertTrue(truncated.endswith("...[truncated]"))
            self.assertEqual([result.path for result in related], ["Target.md", "Peer.md"])
            self.assertIn("outgoing link", related[0].reasons)

    def test_inspect_surfaces_ambiguous_preferred_path(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "A").mkdir(parents=True)
            (vault / "B").mkdir()
            (vault / "A" / "Source.md").write_text("[[Duplicate]]", encoding="utf-8")
            (vault / "A" / "Duplicate.md").write_text("# A\n", encoding="utf-8")
            (vault / "B" / "Duplicate.md").write_text("# B\n", encoding="utf-8")

            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
            )

            write_index(config.index_path, scan_vault(config))

            inspection = inspect_path(config.index_path, "A/Source.md")
            related = related_paths(config.index_path, "A/Source.md", limit=5)

            self.assertEqual(inspection.outgoing_links[0].resolution_status, "ambiguous")
            self.assertEqual(inspection.outgoing_links[0].preferred_path, "A/Duplicate.md")
            self.assertEqual(inspection.outgoing_links[0].candidate_paths, ("A/Duplicate.md", "B/Duplicate.md"))
            target_inspection = inspect_path(config.index_path, "A/Duplicate.md")
            self.assertEqual(target_inspection.backlinks[0].file_path, "A/Source.md")
            self.assertEqual(related[0].path, "A/Duplicate.md")
            self.assertIn("ambiguous link preferred candidate", related[0].reasons)

    def test_related_does_not_return_same_folder_noise_only(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            flat = vault / "ibooks-highlights"
            flat.mkdir(parents=True)
            (flat / "Testing Elixir.md").write_text("## Annotations\n\nExcerpt one.\n", encoding="utf-8")
            (flat / "Random Book.md").write_text("## Annotations\n\nExcerpt two.\n", encoding="utf-8")
            (flat / "Another Book.md").write_text("## Annotations\n\nExcerpt three.\n", encoding="utf-8")

            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
            )

            write_index(config.index_path, scan_vault(config))
            related = related_paths(config.index_path, "ibooks-highlights/Testing Elixir.md", limit=5)

            self.assertEqual(related, ())

    def test_inspect_surfaces_exact_duplicate_group_and_canonical_path(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "0_Inbox").mkdir(parents=True)
            (vault / "2_Areas" / "Work").mkdir(parents=True)
            text = "# Shared\n\nSame content.\n"
            (vault / "0_Inbox" / "Shared.md").write_text(text, encoding="utf-8")
            (vault / "2_Areas" / "Work" / "Shared.md").write_text(text, encoding="utf-8")

            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
            )

            write_index(config.index_path, scan_vault(config))
            inspection = inspect_path(config.index_path, "0_Inbox/Shared.md")

            self.assertEqual(
                inspection.exact_duplicates,
                ("0_Inbox/Shared.md", "2_Areas/Work/Shared.md"),
            )
            self.assertEqual(inspection.canonical_path, "2_Areas/Work/Shared.md")

    def test_inspect_identifies_umbrella_backlinks(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "Sources").mkdir(parents=True)
            (vault / "Sources" / "Raw.md").write_text("# Raw\n\nEvidence.\n", encoding="utf-8")
            (vault / "Umbrella.md").write_text(
                "---\nbrainiac_role: umbrella\n---\n# Topic\n\n[[Sources/Raw]]\n",
                encoding="utf-8",
            )
            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
            )

            write_index(config.index_path, scan_vault(config))
            inspection = inspect_path(config.index_path, "Sources/Raw.md")

            self.assertEqual(inspection.role, "source")
            self.assertEqual(inspection.umbrella_backlinks, ("Umbrella.md",))

if __name__ == "__main__":
    unittest.main()
