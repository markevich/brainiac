from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from brainiac.config import VaultConfig
from brainiac.index import write_index
from brainiac.maintenance import maintenance_report
from brainiac.scanner import scan_vault


class MaintenanceReportTest(unittest.TestCase):
    def test_reports_meaningful_empty_directories(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "0_Inbox").mkdir(parents=True)
            (vault / "1_Projects" / "Investor").mkdir(parents=True)
            (vault / "2_Areas" / "Health").mkdir(parents=True)
            (vault / "2_Areas" / "Food").mkdir(parents=True)
            (vault / "2_Areas" / "Food" / "Rice.md").write_text("# Rice\n", encoding="utf-8")
            (vault / "Untitled").mkdir()
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
inbox:
  default: "0_Inbox/"
projects:
  investor: "1_Projects/Investor/"
areas:
  food: "2_Areas/Food/"
  health: "2_Areas/Health/"
inbox_roots:
  - "0_Inbox/"
project_roots:
  - "1_Projects/"
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
            report = maintenance_report(config.index_path, config=config, routing_config_path=routing_config)
            findings = {finding.path: finding for finding in report.findings}

            self.assertEqual(findings["0_Inbox/"].severity, "high")
            self.assertEqual(findings["0_Inbox/"].summary, "Empty configured destination")
            self.assertEqual(findings["1_Projects/Investor/"].severity, "high")
            self.assertEqual(findings["2_Areas/Health/"].severity, "high")
            self.assertEqual(findings["Untitled/"].severity, "low")
            self.assertNotIn("2_Areas/Food/", findings)

    def test_ignores_hidden_tooling_and_excluded_directories(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "Softswiss" / "Jarvis" / ".git" / "objects").mkdir(parents=True)
            (vault / "Softswiss" / "Jarvis" / ".venv" / "lib").mkdir(parents=True)
            (vault / "Ignored").mkdir()
            (vault / "UserFacing").mkdir()
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text("", encoding="utf-8")
            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=("Ignored/", "Softswiss/Jarvis/"),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
                generated_root=tmp_path / "generated",
            )

            write_index(config.index_path, scan_vault(config))
            report = maintenance_report(config.index_path, config=config, routing_config_path=routing_config)
            paths = {finding.path for finding in report.findings}

            self.assertEqual(paths, {"UserFacing/"})

    def test_ignores_frontmatter_role_markers_in_semantic_duplicate_scoring(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "A").mkdir(parents=True)
            (vault / "B").mkdir()
            (vault / "A" / "One.md").write_text(
                "---\nbrainiac_role: source\n---\n# One\n\nAlpha content.\n",
                encoding="utf-8",
            )
            (vault / "B" / "Two.md").write_text(
                "---\nbrainiac_role: source\n---\n# Two\n\nBeta content.\n",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
area_roots:
  - "A/"
resource_roots:
  - "B/"
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
            report = maintenance_report(config.index_path, config=config, routing_config_path=routing_config)

            semantic_findings = [finding for finding in report.findings if finding.type == "semantic_duplicate"]

            self.assertEqual(report.semantic_duplicate_count, 0)
            self.assertEqual(len(semantic_findings), 0)

    def test_does_not_classify_umbrella_list_notes_as_semantic_duplicates(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "A").mkdir(parents=True)
            source_path = vault / "A" / "Topic.md"
            source_path.write_text("# Topic\n\nVersion one.\n", encoding="utf-8")
            umbrella_path = vault / "A" / "Topic list.md"
            umbrella_path.write_text("# Topic list\n\n- [[Topic]]\n", encoding="utf-8")
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
area_roots:
  - "A/"
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
            report = maintenance_report(config.index_path, config=config, routing_config_path=routing_config)

            semantic_findings = [finding for finding in report.findings if finding.type == "semantic_duplicate"]

            self.assertEqual(report.semantic_duplicate_count, 0)
            self.assertEqual(len(semantic_findings), 0)

    def test_does_not_flag_sibling_cards_in_the_same_folder_as_semantic_duplicates(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "Catalog").mkdir(parents=True)
            (vault / "Catalog" / "Alpha.md").write_text(
                "# Alpha\n\n- Rating: 9/10\n- Top items: one, two, three\n",
                encoding="utf-8",
            )
            (vault / "Catalog" / "Beta.md").write_text(
                "# Beta\n\n- Rating: 8/10\n- Top items: four, five, six\n",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
resource_roots:
  - "Catalog/"
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
            report = maintenance_report(config.index_path, config=config, routing_config_path=routing_config)

            semantic_findings = [finding for finding in report.findings if finding.type == "semantic_duplicate"]

            self.assertEqual(report.semantic_duplicate_count, 0)
            self.assertEqual(len(semantic_findings), 0)

    def test_archive_excludes_keep_notes_out_of_maintenance(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "Archive").mkdir(parents=True)
            (vault / "Source").mkdir(parents=True)
            shared = "# Shared\n\nSame content.\n"
            (vault / "Archive" / "Shared.md").write_text(shared, encoding="utf-8")
            (vault / "Source" / "Shared.md").write_text(shared, encoding="utf-8")
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
archive_roots:
  - "Archive/"
""",
                encoding="utf-8",
            )
            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=("Archive/",),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
                generated_root=tmp_path / "generated",
            )

            write_index(config.index_path, scan_vault(config))
            report = maintenance_report(config.index_path, config=config, routing_config_path=routing_config)

            self.assertEqual(report.exact_duplicate_count, 0)
            self.assertEqual(report.semantic_duplicate_count, 0)
            self.assertTrue(all(finding.path != "Archive/Shared.md" for finding in report.findings))

    def test_reports_notes_missing_explicit_role_markers_and_invalid_values(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "Notes").mkdir(parents=True)
            (vault / "Notes" / "Plain.md").write_text("# Plain\n\nregular source note\n", encoding="utf-8")
            (vault / "Notes" / "Marked.md").write_text(
                "---\nBrainiac_Role: source\n---\n# Marked\n\nregular source note\n",
                encoding="utf-8",
            )
            (vault / "Notes" / "Broken role.md").write_text(
                "---\nbrainiac_role: banana\n---\n# Broken role\n\nregular source note\n",
                encoding="utf-8",
            )
            (vault / "Notes" / "Master list.md").write_text(
                "# Master list\n\n- [[Topic One]]\n- [[Topic Two]]\n",
                encoding="utf-8",
            )
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text("", encoding="utf-8")
            config = VaultConfig(
                name="Test vault",
                root=vault,
                exclude=(),
                source_patterns=("*.md",),
                index_path=tmp_path / "brainiac.sqlite",
                generated_root=tmp_path / "generated",
            )

            write_index(config.index_path, scan_vault(config))
            report = maintenance_report(config.index_path, config=config, routing_config_path=routing_config)

            missing_role = [finding for finding in report.findings if finding.type == "missing_role_marker"]
            invalid_role = [finding for finding in report.findings if finding.type == "invalid_role_marker"]

            self.assertEqual(report.missing_role_marker_count, 2)
            self.assertEqual(report.invalid_role_marker_count, 1)
            self.assertEqual(
                {finding.path for finding in missing_role},
                {"Notes/Plain.md", "Notes/Master list.md"},
            )
            self.assertEqual([finding.path for finding in invalid_role], ["Notes/Broken role.md"])
            self.assertTrue(any("master list/index note" in " ".join(finding.reasons) for finding in missing_role))
            self.assertTrue(any("default role: source" in finding.reasons for finding in missing_role))

    def test_aggregates_ambiguous_missing_links_and_unconfigured_profiles(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "2_Areas" / "Food").mkdir(parents=True)
            (vault / "2_Areas" / "Music").mkdir()
            (vault / "A").mkdir()
            (vault / "B").mkdir()
            (vault / "2_Areas" / "Food" / "Rice.md").write_text("# Rice\n", encoding="utf-8")
            (vault / "2_Areas" / "Music" / "Songs.md").write_text("# Songs\n#music\n", encoding="utf-8")
            (vault / "A" / "Duplicate.md").write_text("# A\n", encoding="utf-8")
            (vault / "B" / "Duplicate.md").write_text("# B\n", encoding="utf-8")
            (vault / "Source.md").write_text("[[Duplicate]] [[Missing]]\n", encoding="utf-8")
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
areas:
  food: "2_Areas/Food/"
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
            report = maintenance_report(config.index_path, config=config, routing_config_path=routing_config)

            self.assertEqual(report.ambiguous_wikilink_count, 1)
            self.assertEqual(report.missing_wikilink_count, 1)
            self.assertEqual(report.unconfigured_profile_count, 1)

            ambiguous = [finding for finding in report.findings if finding.type == "ambiguous_wikilink"]
            missing = [finding for finding in report.findings if finding.type == "missing_wikilink"]
            unconfigured = [finding for finding in report.findings if finding.type == "unconfigured_structure_profile"]

            self.assertEqual(ambiguous[0].path, "Source.md")
            self.assertIn("preferred candidate:", ambiguous[0].reasons[1])
            self.assertEqual(missing[0].path, "Source.md")
            self.assertIn("does not resolve", missing[0].reasons[0])
            self.assertEqual(unconfigured[0].path, "2_Areas/Music/")
            self.assertIn("indexed Markdown notes", unconfigured[0].reasons[0])
