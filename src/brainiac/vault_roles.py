from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .routing_config import ensure_routing_config


ROLE_ROOT_SECTIONS = {
    "area_roots": "area",
    "project_roots": "project",
    "resource_roots": "resource",
    "generated_roots": "generated",
    "queue_roots": "queue",
    "inbox_roots": "inbox",
}
ROLE_MARKER_VALUES = {
    "source",
    "umbrella",
}


@dataclass(frozen=True)
class RoleRoot:
    role: str
    path: str
    source: str


def load_role_roots(path: Path) -> tuple[RoleRoot, ...]:
    return _load_roots(path, ROLE_ROOT_SECTIONS)


def load_archive_roots(path: Path) -> tuple[str, ...]:
    return _load_root_paths(path, {"archive_roots"})


def _load_roots(path: Path, sections: dict[str, str]) -> tuple[RoleRoot, ...]:
    roots = [
        RoleRoot(role=sections[section], path=value, source="config")
        for section, value in _iter_root_values(path, set(sections))
    ]
    return tuple(roots)


def _load_root_paths(path: Path, sections: set[str]) -> tuple[str, ...]:
    return tuple(value for _, value in _iter_root_values(path, sections))


def _iter_root_values(path: Path, sections: set[str]):
    if path.name == "routing.yml":
        path = ensure_routing_config(path)
    current_section: str | None = None
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if not line.startswith(" ") and stripped.endswith(":"):
            current_section = stripped[:-1]
            continue
        if current_section not in sections or not stripped.startswith("- "):
            continue
        value = _unquote(stripped[2:].strip())
        if value:
            yield current_section, _folder_path(value)


def classify_path_role(path: str, roots: tuple[RoleRoot, ...]) -> str | None:
    matches = [root for root in roots if path == root.path.rstrip("/") or path.startswith(root.path)]
    if not matches:
        return None
    best = max(matches, key=lambda root: len(root.path))
    return best.role


def classify_note_role(
    connection: sqlite3.Connection,
    path: str,
    roots: tuple[RoleRoot, ...] = (),
) -> str:
    for value in explicit_role_marker_values(connection, path):
        normalized = value.casefold().strip()
        if normalized in ROLE_MARKER_VALUES:
            return normalized
    role = classify_path_role(path, roots)
    if role in ROLE_MARKER_VALUES:
        return role
    return "source"


def has_explicit_role_marker(connection: sqlite3.Connection, path: str) -> bool:
    return bool(explicit_role_marker_values(connection, path))


def explicit_role_marker_values(connection: sqlite3.Connection, path: str) -> tuple[str, ...]:
    return tuple(
        row[0]
        for row in connection.execute(
            """
            SELECT value
            FROM markdown_metadata
            WHERE file_path = ? AND lower(key) = 'brainiac_role'
            ORDER BY value
            """,
            (path,),
        ).fetchall()
    )


def invalid_explicit_role_marker_values(connection: sqlite3.Connection, path: str) -> tuple[str, ...]:
    return tuple(
        value
        for value in explicit_role_marker_values(connection, path)
        if value.casefold().strip() not in ROLE_MARKER_VALUES
    )


def _folder_path(value: str) -> str:
    normalized = value.strip().strip("/")
    return normalized + "/" if normalized else normalized


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
