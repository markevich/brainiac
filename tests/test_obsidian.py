from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from brainiac.obsidian import TASKS_PLUGIN_ID, inspect_tasks_plugin


class TasksPluginStatusTests(unittest.TestCase):
    def test_plugin_is_ready_only_when_installed_and_enabled(self):
        with TemporaryDirectory() as tmp:
            vault_root = Path(tmp)
            plugin_directory = vault_root / ".obsidian" / "plugins" / TASKS_PLUGIN_ID
            plugin_directory.mkdir(parents=True)
            (plugin_directory / "manifest.json").write_text(
                json.dumps({"id": TASKS_PLUGIN_ID}),
                encoding="utf-8",
            )
            (vault_root / ".obsidian" / "community-plugins.json").write_text(
                json.dumps([TASKS_PLUGIN_ID]),
                encoding="utf-8",
            )

            status = inspect_tasks_plugin(vault_root)

            self.assertTrue(status.manifest_exists)
            self.assertTrue(status.enabled)
            self.assertTrue(status.ready)

    def test_missing_or_invalid_plugin_configuration_is_not_ready(self):
        with TemporaryDirectory() as tmp:
            vault_root = Path(tmp)
            obsidian_directory = vault_root / ".obsidian"
            obsidian_directory.mkdir()
            (obsidian_directory / "community-plugins.json").write_text("not json", encoding="utf-8")

            status = inspect_tasks_plugin(vault_root)

            self.assertFalse(status.manifest_exists)
            self.assertFalse(status.enabled)
            self.assertFalse(status.ready)

    def test_wrong_manifest_id_is_not_installed(self):
        with TemporaryDirectory() as tmp:
            vault_root = Path(tmp)
            plugin_directory = vault_root / ".obsidian" / "plugins" / TASKS_PLUGIN_ID
            plugin_directory.mkdir(parents=True)
            (plugin_directory / "manifest.json").write_text(
                json.dumps({"id": "other-plugin"}),
                encoding="utf-8",
            )
            (vault_root / ".obsidian" / "community-plugins.json").write_text(
                json.dumps([TASKS_PLUGIN_ID]),
                encoding="utf-8",
            )

            status = inspect_tasks_plugin(vault_root)

            self.assertFalse(status.manifest_exists)
            self.assertTrue(status.enabled)
            self.assertFalse(status.ready)
