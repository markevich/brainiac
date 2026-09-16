from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


TASKS_PLUGIN_ID = "obsidian-tasks-plugin"


@dataclass(frozen=True)
class TasksPluginStatus:
    manifest_exists: bool
    enabled: bool

    @property
    def ready(self) -> bool:
        return self.manifest_exists and self.enabled


def inspect_tasks_plugin(vault_root: Path) -> TasksPluginStatus:
    """Inspect, without changing, whether the required Obsidian Tasks plugin is ready."""
    obsidian_directory = vault_root / ".obsidian"
    manifest_path = obsidian_directory / "plugins" / TASKS_PLUGIN_ID / "manifest.json"
    enabled_plugins_path = obsidian_directory / "community-plugins.json"
    return TasksPluginStatus(
        manifest_exists=_has_tasks_manifest(manifest_path),
        enabled=_plugin_is_enabled(enabled_plugins_path),
    )


def _has_tasks_manifest(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return isinstance(manifest, dict) and manifest.get("id") == TASKS_PLUGIN_ID


def _plugin_is_enabled(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        plugins = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return isinstance(plugins, list) and TASKS_PLUGIN_ID in plugins
