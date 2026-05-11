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
                generated_root=tmp_path / "generated",
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
                generated_root=tmp_path / "generated",
            )

            write_index(config.index_path, scan_vault(config))

            inspection = inspect_path(config.index_path, "A/Source.md")
            related = related_paths(config.index_path, "A/Source.md", limit=5)

            self.assertEqual(inspection.outgoing_links[0].resolution_status, "ambiguous")
            self.assertEqual(inspection.outgoing_links[0].preferred_path, "A/Duplicate.md")
            self.assertEqual(inspection.outgoing_links[0].candidate_paths, ("A/Duplicate.md", "B/Duplicate.md"))
            self.assertEqual(related[0].path, "A/Duplicate.md")
            self.assertIn("ambiguous link preferred candidate", related[0].reasons)


if __name__ == "__main__":
    unittest.main()
