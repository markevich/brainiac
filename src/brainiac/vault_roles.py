from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROLE_ROOT_SECTIONS = {
    "area_roots": "area",
    "project_roots": "project",
    "resource_roots": "resource",
    "synthesis_roots": "synthesis",
    "generated_roots": "generated",
    "queue_roots": "queue",
    "archive_roots": "archive",
    "inbox_roots": "inbox",
}


@dataclass(frozen=True)
class RoleRoot:
    role: str
    path: str
    source: str


def load_role_roots(path: Path) -> tuple[RoleRoot, ...]:
    current_section: str | None = None
    roots: list[RoleRoot] = []
    if not path.exists():
        return ()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if not line.startswith(" ") and stripped.endswith(":"):
            current_section = stripped[:-1]
            continue
        if current_section not in ROLE_ROOT_SECTIONS or not stripped.startswith("- "):
            continue
        value = _unquote(stripped[2:].strip())
        if value:
            roots.append(RoleRoot(role=ROLE_ROOT_SECTIONS[current_section], path=_folder_path(value), source="config"))
    return tuple(roots)


def classify_path_role(path: str, roots: tuple[RoleRoot, ...]) -> str | None:
    matches = [root for root in roots if path == root.path.rstrip("/") or path.startswith(root.path)]
    if not matches:
        return None
    best = max(matches, key=lambda root: len(root.path))
    return best.role


def _folder_path(value: str) -> str:
    normalized = value.strip().strip("/")
    return normalized + "/" if normalized else normalized


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
