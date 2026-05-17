import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from brainiac.config import VaultConfig
from brainiac.index import write_index
from brainiac.retrieval import inspect_path, related_paths
from brainiac.scanner import scan_vault
from brainiac.search import search_index
from brainiac.synthesis import (
    inspect_synthesis,
    list_synthesis_notes,
    stale_synthesis_notes,
    suggest_synthesis,
)


class SynthesisTest(unittest.TestCase):
    def test_lists_inspects_and_detects_stale_sources(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "Brainiac" / "memory" / "synthesis").mkdir(parents=True)
            (vault / "Sources").mkdir()
            (vault / "Sources" / "Raw.md").write_text(
                "# Raw Evidence\n\nFermentation source detail.\n",
                encoding="utf-8",
            )
            (vault / "Brainiac" / "memory" / "synthesis" / "Fermentation.md").write_text(
                """---
brainiac_type: synthesis
topic: Fermentation
last_reviewed: 2026-05-11
source_snapshots:
  - "Sources/Raw.md|not-the-current-hash|0"
---
# Fermentation

## Key points

Current understanding cites [[Sources/Raw]].

## Open questions

- [ ] question: verify salt ratio
""",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
synthesis_roots:
  - "Brainiac/memory/synthesis/"
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

            notes = list_synthesis_notes(config.index_path, routing_config)
            inspection = inspect_synthesis(config.index_path, routing_config, "Fermentation")
            stale = stale_synthesis_notes(config.index_path, routing_config)
            source_inspection = inspect_path(config.index_path, "Sources/Raw.md")
            related = related_paths(config.index_path, "Sources/Raw.md")
            search_results = search_index(config.index_path, "fermentation")

            self.assertEqual([note.path for note in notes], ["Brainiac/memory/synthesis/Fermentation.md"])
            self.assertEqual(inspection.note.topic, "Fermentation")
            self.assertEqual(inspection.sources[0].path, "Sources/Raw.md")
            self.assertEqual(inspection.sources[0].status, "stale")
            self.assertEqual([note.path for note in stale], ["Brainiac/memory/synthesis/Fermentation.md"])
            self.assertEqual(
                source_inspection.synthesis_references,
                ("Brainiac/memory/synthesis/Fermentation.md",),
            )
            self.assertEqual(related[0].path, "Brainiac/memory/synthesis/Fermentation.md")
            self.assertEqual(search_results[0].path, "Brainiac/memory/synthesis/Fermentation.md")

    def test_suggests_dry_run_synthesis_drafts(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "Brainiac" / "memory" / "synthesis").mkdir(parents=True)
            (vault / "Sources").mkdir()
            (vault / "Sources" / "Fermentation.md").write_text(
                "# Fermentation\n\nKimchi brine and lacto fermentation notes.\n",
                encoding="utf-8",
            )
            (vault / "Sources" / "Pickles.md").write_text(
                "# Pickles\n\nFermentation timing and salt ratio.\n",
                encoding="utf-8",
            )
            (vault / "Brainiac" / "memory" / "synthesis" / "Fermentation.md").write_text(
                """---
brainiac_type: synthesis
topic: Fermentation
---
# Fermentation

## Sources

[[Sources/Fermentation]]
""",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
synthesis_roots:
  - "Brainiac/memory/synthesis/"
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

            topic_suggestion = suggest_synthesis(config.index_path, routing_config, "pickles", limit=3)
            source_suggestion = suggest_synthesis(
                config.index_path,
                routing_config,
                "Sources/Fermentation.md",
                limit=3,
            )
            update_suggestion = suggest_synthesis(
                config.index_path,
                routing_config,
                "Brainiac/memory/synthesis/Fermentation.md",
                limit=3,
            )
            topic_update_suggestion = suggest_synthesis(
                config.index_path,
                routing_config,
                "Fermentation",
                limit=3,
            )

            self.assertEqual(topic_suggestion.action, "create")
            self.assertEqual(topic_suggestion.path, "Brainiac/memory/synthesis/pickles.md")
            self.assertIn("Sources/Pickles.md", [source.path for source in topic_suggestion.sources])
            self.assertIn("source_snapshots:", topic_suggestion.draft)
            self.assertIn("[[Pickles]]", topic_suggestion.draft)
            self.assertEqual(source_suggestion.sources[0].path, "Sources/Fermentation.md")
            self.assertIn("seed source", source_suggestion.sources[0].reasons)
            self.assertEqual(update_suggestion.action, "update")
            self.assertEqual(update_suggestion.path, "Brainiac/memory/synthesis/Fermentation.md")
            self.assertEqual(update_suggestion.sources[0].path, "Sources/Fermentation.md")
            self.assertEqual(topic_update_suggestion.action, "update")
            self.assertEqual(topic_update_suggestion.path, "Brainiac/memory/synthesis/Fermentation.md")

    def test_suggest_prefers_title_and_path_matches_over_body_only_mentions(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "Brainiac" / "memory" / "synthesis").mkdir(parents=True)
            (vault / "3_Resources" / "Travel").mkdir(parents=True)
            (vault / "2_Areas" / "Family").mkdir(parents=True)
            (vault / "3_Resources" / "Travel" / "Georgia.md").write_text(
                "# Georgia\n\nTrip notes.\n",
                encoding="utf-8",
            )
            (vault / "2_Areas" / "Family" / "Values.md").write_text(
                "# Values\n\nWe may one day move to Georgia.\n",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
resource_roots:
  - "3_Resources/"
area_roots:
  - "2_Areas/"
synthesis_roots:
  - "Brainiac/memory/synthesis/"
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
            suggestion = suggest_synthesis(config.index_path, routing_config, "Georgia", limit=5)

            self.assertEqual(suggestion.sources[0].path, "3_Resources/Travel/Georgia.md")
            weaker = next(source for source in suggestion.sources if source.path == "2_Areas/Family/Values.md")
            self.assertIn("body-only lexical match", weaker.reasons)

    def test_suggest_dedupes_exact_duplicate_sources_by_canonical_path(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "0_Inbox").mkdir(parents=True)
            (vault / "2_Areas" / "Work").mkdir(parents=True)
            (vault / "Brainiac" / "memory" / "synthesis").mkdir(parents=True)
            text = "# Schema change чеки\n\nSame content.\n"
            (vault / "0_Inbox" / "Schema change чеки.md").write_text(text, encoding="utf-8")
            (vault / "2_Areas" / "Work" / "Schema change чеки.md").write_text(text, encoding="utf-8")
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
inbox_roots:
  - "0_Inbox/"
area_roots:
  - "2_Areas/"
synthesis_roots:
  - "Brainiac/memory/synthesis/"
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
            suggestion = suggest_synthesis(config.index_path, routing_config, "0_Inbox/Schema change чеки.md", limit=5)

            self.assertEqual([source.path for source in suggestion.sources], ["2_Areas/Work/Schema change чеки.md"])
            self.assertIn("canonicalized from 0_Inbox/Schema change чеки.md", suggestion.sources[0].reasons)


if __name__ == "__main__":
    unittest.main()
