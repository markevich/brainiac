from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from .config import VaultConfig
from .duplicates import list_exact_duplicate_groups
from .routing import load_routing_config
from .scanner import walk_source_files
from .structure import analyze_structure
from .synthesis import stale_synthesis_notes
from .vault_roles import RoleRoot, classify_path_role, load_role_roots


TOOLING_SEGMENTS = {
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".git",
    ".hg",
    ".svn",
}


@dataclass(frozen=True)
class MaintenanceFinding:
    id: str
    type: str
    severity: str
    path: str
    summary: str
    reasons: tuple[str, ...]
    suggested_action: str


@dataclass(frozen=True)
class MaintenanceReport:
    findings: tuple[MaintenanceFinding, ...]

    @property
    def empty_directory_count(self) -> int:
        return sum(1 for finding in self.findings if finding.type == "empty_directory")

    @property
    def exact_duplicate_count(self) -> int:
        return sum(1 for finding in self.findings if finding.type == "exact_duplicate_group")

    @property
    def stale_synthesis_count(self) -> int:
        return sum(1 for finding in self.findings if finding.type == "stale_synthesis")

    @property
    def ambiguous_wikilink_count(self) -> int:
        return sum(1 for finding in self.findings if finding.type == "ambiguous_wikilink")

    @property
    def missing_wikilink_count(self) -> int:
        return sum(1 for finding in self.findings if finding.type == "missing_wikilink")

    @property
    def unconfigured_profile_count(self) -> int:
        return sum(1 for finding in self.findings if finding.type == "unconfigured_structure_profile")


def maintenance_report(
    index_path: Path,
    *,
    config: VaultConfig,
    routing_config_path: Path,
) -> MaintenanceReport:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    if config.root is None:
        raise ValueError("Vault root is not configured. Pass --vault-root or set vault.root.")

    role_roots = load_role_roots(routing_config_path)
    routing_config = load_routing_config(routing_config_path)
    with closing(sqlite3.connect(index_path)) as connection:
        findings = list(
            _empty_directory_findings(
                connection,
                config,
                role_roots,
                configured_folder_paths={
                    destination.path
                    for destination in routing_config.destinations
                    if destination.path.endswith("/")
                },
            )
        )
        findings.extend(
            _exact_duplicate_findings(
                index_path,
                routing_config_path,
            )
        )
        findings.extend(
            _stale_synthesis_findings(
                index_path,
                routing_config_path,
            )
        )
        findings.extend(_ambiguous_wikilink_findings(connection))
        findings.extend(_missing_wikilink_findings(connection))
        findings.extend(_unconfigured_profile_findings(index_path, routing_config_path))
    ordered = tuple(sorted(findings, key=lambda item: (_severity_rank(item.severity), item.path)))
    return MaintenanceReport(findings=ordered)


def _exact_duplicate_findings(
    index_path: Path,
    routing_config_path: Path,
) -> tuple[MaintenanceFinding, ...]:
    findings: list[MaintenanceFinding] = []
    for group in list_exact_duplicate_groups(index_path, routing_config_path=routing_config_path, limit=200):
        reasons = [
            f"{len(group.paths)} files share the same Markdown content hash",
            f"canonical path: {group.canonical.path}",
        ]
        reasons.extend(group.canonical.reasons)
        findings.append(
            MaintenanceFinding(
                id=f"exact_duplicate_group:{group.group_id}",
                type="exact_duplicate_group",
                severity="medium",
                path=group.canonical.path,
                summary=f"Exact duplicate cluster ({len(group.paths)} files)",
                reasons=tuple(reasons),
                suggested_action=(
                    "Keep the canonical path for retrieval and future writes; review non-canonical copies for relink or deletion."
                ),
            )
        )
    return tuple(findings)


def _stale_synthesis_findings(
    index_path: Path,
    routing_config_path: Path,
) -> tuple[MaintenanceFinding, ...]:
    findings: list[MaintenanceFinding] = []
    for note in stale_synthesis_notes(index_path, routing_config_path, limit=200):
        stale_paths = tuple(source.path for source in note.stale_sources)
        findings.append(
            MaintenanceFinding(
                id=f"stale_synthesis:{note.path}",
                type="stale_synthesis",
                severity="medium",
                path=note.path,
                summary=f"Stale synthesis note ({len(note.stale_sources)} changed sources)",
                reasons=tuple(
                    [f"{len(note.stale_sources)} referenced sources changed since last synthesis snapshot"]
                    + [f"stale source: {path}" for path in stale_paths[:5]]
                ),
                suggested_action="Refresh this synthesis note against current canonical source notes.",
            )
        )
    return tuple(findings)


def _ambiguous_wikilink_findings(connection: sqlite3.Connection) -> tuple[MaintenanceFinding, ...]:
    findings: list[MaintenanceFinding] = []
    rows = connection.execute(
        """
        SELECT file_path, line, target, preferred_path, candidate_paths
        FROM wikilinks
        WHERE resolution_status = 'ambiguous'
        ORDER BY file_path, line, target
        """
    ).fetchall()
    for file_path, line, target, preferred_path, candidate_paths in rows:
        candidates = tuple(candidate_paths.splitlines()) if candidate_paths else ()
        reasons = [f"wikilink `[[{target}]]` has multiple indexed candidates"]
        if preferred_path:
            reasons.append(f"preferred candidate: {preferred_path}")
        if candidates:
            reasons.append(f"candidates: {', '.join(candidates[:5])}")
        findings.append(
            MaintenanceFinding(
                id=f"ambiguous_wikilink:{file_path}:{line}:{target}",
                type="ambiguous_wikilink",
                severity="medium",
                path=file_path,
                summary=f"Ambiguous wikilink at line {line}",
                reasons=tuple(reasons),
                suggested_action="Rewrite this wikilink to the shortest unique target path or rename duplicate note basenames.",
            )
        )
    return tuple(findings)


def _missing_wikilink_findings(connection: sqlite3.Connection) -> tuple[MaintenanceFinding, ...]:
    findings: list[MaintenanceFinding] = []
    rows = connection.execute(
        """
        SELECT file_path, line, target
        FROM wikilinks
        WHERE resolution_status = 'missing'
        ORDER BY file_path, line, target
        """
    ).fetchall()
    for file_path, line, target in rows:
        findings.append(
            MaintenanceFinding(
                id=f"missing_wikilink:{file_path}:{line}:{target}",
                type="missing_wikilink",
                severity="medium",
                path=file_path,
                summary=f"Missing wikilink at line {line}",
                reasons=(f"wikilink `[[{target}]]` does not resolve to any indexed note",),
                suggested_action="Create the missing note, fix the target, or remove the broken link.",
            )
        )
    return tuple(findings)


def _unconfigured_profile_findings(
    index_path: Path,
    routing_config_path: Path,
) -> tuple[MaintenanceFinding, ...]:
    findings: list[MaintenanceFinding] = []
    analysis = analyze_structure(index_path, routing_config_path, max_profiles=500)
    for profile in analysis.unconfigured_profiles:
        reasons = [f"{profile.note_count} indexed Markdown notes under {profile.path}"]
        if profile.top_tags:
            reasons.append(f"top tags: {', '.join(profile.top_tags[:5])}")
        if profile.top_terms:
            reasons.append(f"top terms: {', '.join(profile.top_terms[:5])}")
        findings.append(
            MaintenanceFinding(
                id=f"unconfigured_structure_profile:{profile.role}:{profile.path.rstrip('/')}",
                type="unconfigured_structure_profile",
                severity="medium",
                path=profile.path,
                summary=f"Unconfigured {profile.role} profile",
                reasons=tuple(reasons),
                suggested_action=f"Add a routing destination or explicit structure mapping for {profile.path}.",
            )
        )
    return tuple(findings)


def _empty_directory_findings(
    connection: sqlite3.Connection,
    config: VaultConfig,
    role_roots: tuple[RoleRoot, ...],
    *,
    configured_folder_paths: set[str],
) -> tuple[MaintenanceFinding, ...]:
    source_files = walk_source_files(config)
    descendant_source_counts: dict[str, int] = {}
    direct_source_counts: dict[str, int] = {}
    indexed_paths = {
        row[0]
        for row in connection.execute("SELECT path FROM files").fetchall()
    }

    for _path, relative_path in source_files:
        direct_parent = Path(relative_path).parent.as_posix()
        if direct_parent != ".":
            direct_key = _dir_key(direct_parent)
            direct_source_counts[direct_key] = direct_source_counts.get(direct_key, 0) + 1
        for parent in Path(relative_path).parents:
            parent_text = parent.as_posix()
            if parent_text == ".":
                continue
            dir_key = _dir_key(parent_text)
            descendant_source_counts[dir_key] = descendant_source_counts.get(dir_key, 0) + 1

    findings: list[MaintenanceFinding] = []
    root = config.root.resolve()
    for path in root.rglob("*"):
        if not path.is_dir():
            continue
        relative_dir = path.relative_to(root).as_posix()
        if _is_excluded(relative_dir, config.exclude):
            continue
        dir_key = _dir_key(relative_dir)
        if _is_tooling_directory(dir_key):
            continue
        if descendant_source_counts.get(dir_key, 0) > 0:
            continue
        children = list(path.iterdir())
        if children:
            continue
        finding = _empty_directory_finding(
            dir_key,
            role_roots,
            configured_folder_paths=configured_folder_paths,
            indexed_paths=indexed_paths,
            direct_source_count=direct_source_counts.get(dir_key, 0),
        )
        if finding is not None:
            findings.append(finding)
    return tuple(findings)


def _empty_directory_finding(
    dir_key: str,
    role_roots: tuple[RoleRoot, ...],
    *,
    configured_folder_paths: set[str],
    indexed_paths: set[str],
    direct_source_count: int,
) -> MaintenanceFinding | None:
    role = classify_path_role(dir_key, role_roots)
    reasons = ["directory has no source files under configured scan rules"]
    severity = "low"
    summary = "Empty directory"
    suggested_action = "Delete if obsolete, or add source notes if this folder should stay active."

    if dir_key in configured_folder_paths:
        severity = "high"
        summary = "Empty configured destination"
        reasons.append("directory is configured as a routing destination")
        suggested_action = "Either populate this destination with source notes or remove/retarget it in routing config."
    elif any(dir_key == root.path for root in role_roots):
        role_name = next(root.role for root in role_roots if dir_key == root.path)
        severity = "high"
        summary = f"Empty configured {role_name} root"
        reasons.append("directory is a configured role root")
        suggested_action = "Either populate this role root or remove it from routing config."
    elif role in {"area", "project", "resource"}:
        severity = "medium"
        summary = f"Empty {role} directory"
        reasons.append(f"directory sits under the {role} role")
        suggested_action = "Delete if abandoned, or add the source notes that should live here."
    elif role == "archive":
        severity = "low"
        summary = "Empty archive directory"
        reasons.append("directory sits under the archive role")
        suggested_action = "Delete if it is only leftover structure."
    elif role in {"generated", "queue", "synthesis"}:
        return None
    elif _looks_user_facing(dir_key):
        summary = "Empty unclassified directory"
        suggested_action = "Delete if obsolete, or classify and populate it if it should become part of the vault structure."
    else:
        return None

    if direct_source_count == 0 and dir_key not in indexed_paths:
        reasons.append("directory itself is not represented in the file index")

    finding_id = f"empty_directory:{dir_key.rstrip('/')}"
    return MaintenanceFinding(
        id=finding_id,
        type="empty_directory",
        severity=severity,
        path=dir_key,
        summary=summary,
        reasons=tuple(reasons),
        suggested_action=suggested_action,
    )


def _looks_user_facing(path: str) -> bool:
    parts = Path(path.rstrip("/")).parts
    return bool(parts and not any(part.startswith(".") for part in parts))


def _is_tooling_directory(path: str) -> bool:
    parts = Path(path.rstrip("/")).parts
    return any(part.startswith(".") or part in TOOLING_SEGMENTS for part in parts)


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _dir_key(path: str) -> str:
    normalized = path.strip().strip("/")
    return normalized + "/" if normalized else normalized


def _is_excluded(relative_path: str, exclude: tuple[str, ...]) -> bool:
    for pattern in exclude:
        normalized = pattern.strip("/")
        if not normalized:
            continue
        if relative_path == normalized or relative_path.startswith(normalized + "/"):
            return True
    return False
