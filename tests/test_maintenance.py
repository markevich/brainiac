import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from brainiac.config import VaultConfig
from brainiac.index import write_index
from brainiac.maintenance import maintenance_report
from brainiac.scanner import scan_vault


class MaintenanceTest(unittest.TestCase):
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

    def test_aggregates_exact_duplicates_and_stale_synthesis(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vault = tmp_path / "vault"
            (vault / "A").mkdir(parents=True)
            (vault / "B").mkdir()
            (vault / "Brainiac" / "memory" / "synthesis").mkdir(parents=True)
            duplicate_text = "# Shared\n\nSame content.\n"
            (vault / "A" / "Same.md").write_text(duplicate_text, encoding="utf-8")
            (vault / "B" / "Same.md").write_text(duplicate_text, encoding="utf-8")
            source_path = vault / "A" / "Topic.md"
            source_path.write_text("# Topic\n\nVersion one.\n", encoding="utf-8")
            routing_config = tmp_path / "routing.yml"
            routing_config.write_text(
                """
area_roots:
  - "A/"
resource_roots:
  - "B/"
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
            with sqlite3.connect(config.index_path) as connection:
                source_sha, source_mtime = connection.execute(
                    "SELECT sha256, mtime FROM files WHERE path = ?",
                    ("A/Topic.md",),
                ).fetchone()

            synthesis_path = vault / "Brainiac" / "memory" / "synthesis" / "Topic synthesis.md"
            synthesis_path.write_text(
                (
                    "---\n"
                    "brainiac_type: synthesis\n"
                    "topic: Topic\n"
                    "source_snapshots:\n"
                    f'  - "A/Topic.md|{source_sha}|{source_mtime}"\n'
                    "---\n"
                    "# Topic synthesis\n\n"
                    "[[Topic]]\n"
                ),
                encoding="utf-8",
            )
            source_path.write_text("# Topic\n\nVersion two.\n", encoding="utf-8")
            write_index(config.index_path, scan_vault(config))
            report = maintenance_report(config.index_path, config=config, routing_config_path=routing_config)

            duplicate_findings = [finding for finding in report.findings if finding.type == "exact_duplicate_group"]
            stale_findings = [finding for finding in report.findings if finding.type == "stale_synthesis"]

            self.assertEqual(report.exact_duplicate_count, 1)
            self.assertEqual(report.stale_synthesis_count, 1)
            self.assertEqual(len(duplicate_findings), 1)
            self.assertIn("canonical path:", duplicate_findings[0].reasons[1])
            self.assertEqual(len(stale_findings), 1)
            self.assertEqual(stale_findings[0].path, "Brainiac/memory/synthesis/Topic synthesis.md")
            self.assertIn("stale source: A/Topic.md", stale_findings[0].reasons)

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

if __name__ == "__main__":
    unittest.main()
