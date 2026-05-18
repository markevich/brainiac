from __future__ import annotations

from pathlib import Path
from shutil import copyfile


def ensure_routing_config(path: Path) -> Path:
    if path.exists():
        return path
    if path.name != "routing.yml":
        raise FileNotFoundError(f"Routing config not found: {path}")
    example_path = path.with_name("routing.example.yml")
    if not example_path.exists():
        raise FileNotFoundError(
            f"Routing config not found: {path}. Template not found: {example_path}."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    copyfile(example_path, path)
    return path
