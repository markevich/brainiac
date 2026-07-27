from __future__ import annotations

import sqlite3
from dataclasses import dataclass


ROLE_MARKER_VALUES = {"source", "umbrella"}
PARA_ROLE_ROOTS = (
    ("inbox", "Inbox/"),
    ("project", "Projects/"),
    ("area", "Areas/"),
    ("resource", "Resources/"),
)


@dataclass(frozen=True)
class RoleRoot:
    role: str
    path: str
    source: str = "canonical_para"


def para_role_roots() -> tuple[RoleRoot, ...]:
    return tuple(RoleRoot(role, path) for role, path in PARA_ROLE_ROOTS)


def classify_path_role(path: str, roots: tuple[RoleRoot, ...]) -> str | None:
    matches = [root for root in roots if path == root.path.rstrip("/") or path.startswith(root.path)]
    return max(matches, key=lambda root: len(root.path)).role if matches else None


def classify_note_role(connection: sqlite3.Connection, path: str, roots: tuple[RoleRoot, ...] = ()) -> str:
    for value in explicit_role_marker_values(connection, path):
        if value.casefold().strip() in ROLE_MARKER_VALUES:
            return value.casefold().strip()
    path_role = classify_path_role(path, roots)
    return path_role if path_role in ROLE_MARKER_VALUES else "source"


def has_explicit_role_marker(connection: sqlite3.Connection, path: str) -> bool:
    return bool(explicit_role_marker_values(connection, path))


def explicit_role_marker_values(connection: sqlite3.Connection, path: str) -> tuple[str, ...]:
    return tuple(row[0] for row in connection.execute("SELECT value FROM markdown_metadata WHERE file_path = ? AND lower(key) = 'brainiac_role' ORDER BY value", (path,)).fetchall())


def invalid_explicit_role_marker_values(connection: sqlite3.Connection, path: str) -> tuple[str, ...]:
    return tuple(value for value in explicit_role_marker_values(connection, path) if value.casefold().strip() not in ROLE_MARKER_VALUES)
