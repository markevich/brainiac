from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


CURRENT_CONFIG_VERSION = 1


@dataclass(frozen=True)
class VaultConfig:
    name: str
    root: Path | None
    exclude: tuple[str, ...]
    source_patterns: tuple[str, ...]
    index_path: Path
    layout: str = "para"
    config_version: int = 1


def load_vault_config(path: Path) -> VaultConfig:
    """Load the small YAML subset used by config/brainiac.yml.

    Brainiac intentionally has no runtime dependency yet. This parser supports
    the current config shape: nested scalar keys and string lists.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Brainiac config not found: {path}. "
            "Run `brainiac init --vault-root /path/to/new-vault` for a new PARA vault, "
            "or provide config/brainiac.yml."
        )

    current_section: str | None = None
    values: dict[str, str] = {}
    lists: dict[str, list[str]] = {}

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        stripped = line.strip()
        if not line.startswith(" ") and stripped.endswith(":"):
            current_section = stripped[:-1]
            lists.setdefault(current_section, [])
            continue

        if stripped.startswith("- "):
            if current_section is None:
                raise ValueError(f"List item outside a section in {path}: {raw_line}")
            lists.setdefault(current_section, []).append(_unquote(stripped[2:].strip()))
            continue

        if ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        full_key = f"{current_section}.{key.strip()}" if current_section else key.strip()
        values[full_key] = _unquote(value.strip())

    project_root = path.parent.parent
    config_version_value = values.get("brainiac.config_version", "")
    if not config_version_value.isdigit() or int(config_version_value) != CURRENT_CONFIG_VERSION:
        raise ValueError(
            f"Brainiac requires brainiac.config_version: {CURRENT_CONFIG_VERSION} in {path}. "
            "Use the LLM upgrade flow before running CLI commands."
        )
    vault_root_value = values.get("vault.root", "")
    vault_root = Path(vault_root_value).expanduser() if vault_root_value else None
    layout = values.get("vault.layout", "").casefold().strip()
    if layout != "para":
        raise ValueError(f"Brainiac requires vault.layout: para in {path}.")

    return VaultConfig(
        name=values.get("vault.name", vault_root.name if vault_root else "Unknown vault"),
        root=vault_root,
        exclude=tuple(lists.get("exclude", [])),
        source_patterns=tuple(lists.get("source_formats", [])),
        index_path=_resolve_workspace_path(project_root, values["index.path"]),
        layout=layout,
        config_version=int(config_version_value),
    )


def with_vault_overrides(
    config: VaultConfig,
    *,
    root: Path | None = None,
    exclude: tuple[str, ...] | None = None,
) -> VaultConfig:
    selected_root = root if root is not None else config.root
    return VaultConfig(
        name=selected_root.name if selected_root is not None else config.name,
        root=selected_root,
        exclude=exclude if exclude is not None else config.exclude,
        source_patterns=config.source_patterns,
        index_path=config.index_path,
        layout=config.layout,
        config_version=config.config_version,
    )


def _resolve_workspace_path(project_root: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    return project_root / candidate


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
