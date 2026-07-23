import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from brainiac.config import VaultConfig
from brainiac.index import write_index
from brainiac.routing import find_duplicates, route_content
from brainiac.scanner import scan_vault


class RoutingTest(unittest.TestCase):
    def test_routes_content_and_finds_duplicates(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "2_Areas" / "Food").mkdir(parents=True)
            (vault / "2_Areas" / "Travel").mkdir(parents=True)
            (vault / "2_Areas" / "Food" / "Fermentation.md").write_text(
                "# Fermentation\n\nKimchi, pickles, and sourdough notes.\n#food\n",
                encoding="utf-8",
            )
            (vault / "2_Areas" / "Travel" / "Flights.md").write_text(
                "# Flights\n\nAirport and ticket notes.\n#travel\n",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
areas:
  food: "2_Areas/Food/"
  travel: "2_Areas/Travel/"
inbox:
  default: "0_Inbox/"
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

            content = "# Fermentation\n\nKimchi experiments and sourdough schedule.\n#food"
            route = route_content(config.index_path, routing_config, content, limit=3)
            duplicates = find_duplicates(config.index_path, content, limit=3)

            self.assertEqual(route.title, "Fermentation")
            self.assertEqual(route.candidates[0].destination.key, "food")
            self.assertEqual(route.candidates[0].suggestion.action, "review")
            self.assertEqual(route.candidates[0].suggestion.path, "2_Areas/Food/Fermentation.md")
            self.assertEqual(duplicates[0].path, "2_Areas/Food/Fermentation.md")
            self.assertIn("same title", duplicates[0].reasons)

    def test_archive_section_is_not_a_route_destination(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "Notes").mkdir(parents=True)
            (vault / "Notes" / "Status.md").write_text("# Status\n\nsource copy\n", encoding="utf-8")
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
areas:
  notes: "Notes/"
archive:
  old: "Archive/"
archive_roots:
  - "Archive/"
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

            route = route_content(
                config.index_path,
                routing_config,
                "# Status\n\nsource copy",
                limit=5,
            )

            self.assertEqual([candidate.destination.section for candidate in route.candidates], ["areas"])

    def test_create_suggestion_uses_shortest_unique_link(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "A").mkdir(parents=True)
            (vault / "B").mkdir()
            (vault / "A" / "Status.md").write_text("# Status\n\nA status note.\n", encoding="utf-8")
            (vault / "B" / "Status.md").write_text("# Status B\n\nB status note.\n", encoding="utf-8")
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
areas:
  status: "A/"
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

            route = route_content(
                config.index_path,
                routing_config,
                "# New Status\n\n- [[Topic One]]\n- [[Topic Two]]",
                limit=1,
            )

            self.assertEqual(route.candidates[0].suggestion.action, "create")
            self.assertEqual(route.candidates[0].suggestion.path, "A/New Status.md")
            self.assertEqual(route.candidates[0].suggestion.link, "[[New Status]]")
            self.assertIn("suggested frontmatter role: source", route.candidates[0].suggestion.reasons)

    def test_existing_collision_uses_path_link_for_ambiguous_basename(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "A").mkdir(parents=True)
            (vault / "B").mkdir()
            (vault / "A" / "Status.md").write_text("# A Status\n", encoding="utf-8")
            (vault / "B" / "Status.md").write_text("# B Status\n", encoding="utf-8")
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
areas:
  status: "A/"
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

            route = route_content(config.index_path, routing_config, "# Status\n\nstatus update", limit=1)

            self.assertEqual(route.candidates[0].suggestion.action, "review")
            self.assertEqual(route.candidates[0].suggestion.path, "A/Status.md")
            self.assertEqual(route.candidates[0].suggestion.link, "[[A/Status]]")
            self.assertIn("suggested frontmatter role: source", route.candidates[0].suggestion.reasons)

    def test_file_destination_does_not_score_parent_folder_notes(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "2_Areas" / "Food").mkdir(parents=True)
            (vault / "2_Areas" / "Social.md").write_text("# Social\n\nPeople notes.\n", encoding="utf-8")
            (vault / "2_Areas" / "Food" / "Rice.md").write_text(
                "# Rice\n\nRisotto, jasmine rice, and cooking notes.\n",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
areas:
  food: "2_Areas/Food/"
  social: "2_Areas/Social.md"
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

            route = route_content(config.index_path, routing_config, "# Risotto\n\nRice cooking notes", limit=2)

            self.assertEqual(route.candidates[0].destination.key, "food")
            self.assertLess(route.candidates[1].score, route.candidates[0].score)

    def test_duplicate_under_destination_boosts_route_candidate(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "1_Projects" / "Investor").mkdir(parents=True)
            (vault / "2_Areas" / "Family").mkdir(parents=True)
            (vault / "1_Projects" / "Investor" / "Ideas.md").write_text(
                "# Investment Ideas\n\nportfolio risk horizon thesis\n",
                encoding="utf-8",
            )
            (vault / "2_Areas" / "Family" / "Values.md").write_text(
                "# Values\n\nrisk and decisions\n",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
projects:
  root: "1_Projects/"
areas:
  family: "2_Areas/Family/"
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

            route = route_content(
                config.index_path,
                routing_config,
                "# Investment Ideas\n\nportfolio risk horizon thesis",
                limit=2,
            )

            self.assertEqual(route.candidates[0].destination.section, "projects")

    def test_sensitive_destinations_require_review_before_write(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "2_Areas" / "Здоровье").mkdir(parents=True)
            (vault / "2_Areas" / "Здоровье" / "Анализы.md").write_text(
                "# Анализы\n\nвитамин D ферритин\n",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
areas:
  health: "2_Areas/Здоровье/"
sensitive_destination_keys:
  - "areas.health"
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

            route = route_content(
                config.index_path,
                routing_config,
                "# Анализы крови\n\nвитамин D ферритин",
                limit=1,
            )

            self.assertEqual(route.candidates[0].suggestion.policy, "review_required")

    def test_configured_important_short_terms_are_kept(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "3_Resources" / "AI").mkdir(parents=True)
            (vault / "3_Resources" / "AI" / "Design.md").write_text(
                "# Design\n\nAI UI workflow notes.\n",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
areas:
  ai: "3_Resources/AI/"
inbox:
  default: "0_Inbox/"
important_terms:
  - "ai"
  - "ui"
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

            route = route_content(config.index_path, routing_config, "# UI prompt\n\nAI design flow", limit=2)

            self.assertEqual(route.candidates[0].destination.key, "ai")

    def test_disabled_destination_sections_are_not_routed_to(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            vault.mkdir()
            (vault / "Existing.md").write_text("# Existing\n", encoding="utf-8")
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
generated:
  root: "Brainiac/memory/generated/"
inbox:
  default: "0_Inbox/"
disabled_destination_sections:
  - "generated"
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

            route = route_content(config.index_path, routing_config, "# Unknown topic\n\nNo match", limit=2)

            self.assertEqual(route.candidates[0].destination.section, "inbox")
            self.assertEqual(route.confidence, "low")


if __name__ == "__main__":
    unittest.main()
