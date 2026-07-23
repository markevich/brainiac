from __future__ import annotations

import sqlite3
from contextlib import closing
from functools import lru_cache
from dataclasses import dataclass
from pathlib import Path

from .routing import DuplicateCandidate, find_duplicates
from .vault_roles import RoleRoot, classify_path_role, load_role_roots


@dataclass(frozen=True)
class CanonicalDuplicateDetails:
    path: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ExactDuplicateGroup:
    group_id: str
    sha256: str
    paths: tuple[str, ...]
    canonical: CanonicalDuplicateDetails


@dataclass(frozen=True)
class DuplicateInspection:
    query: str
    exact_group: ExactDuplicateGroup | None
    semantic_duplicates: tuple[DuplicateCandidate, ...]


@dataclass(frozen=True)
class _DuplicatePathAssessment:
    path: str
    role: str | None
    generated_like: bool
    queue_like: bool
    inbox_like: bool
    outgoing_links: int
    backlinks: int
    mtime: float
    role_rank: int
    path_preference: str

    @property
    def connectivity(self) -> int:
        return self.backlinks + self.outgoing_links

    @property
    def sort_key(self) -> tuple[int, int, int, float, int, str]:
        return (
            0 if self.generated_like else 1,
            0 if self.queue_like else 1,
            0 if self.inbox_like else 1,
            float(self.connectivity),
            float(self.mtime),
            self.role_rank,
            self.path_preference,
        )


def exact_duplicate_paths(connection: sqlite3.Connection, path: str) -> tuple[str, ...]:
    row = connection.execute(
        "SELECT sha256 FROM files WHERE path = ? AND is_markdown = 1",
        (path,),
    ).fetchone()
    if row is None:
        return ()
    rows = connection.execute(
        """
        SELECT path
        FROM files
        WHERE is_markdown = 1 AND sha256 = ?
        ORDER BY path
        """,
        (row[0],),
    ).fetchall()
    if len(rows) <= 1:
        return ()
    return tuple(item[0] for item in rows)


def canonical_duplicate_path(
    connection: sqlite3.Connection,
    path: str,
    role_roots: tuple[RoleRoot, ...],
) -> str:
    duplicates = exact_duplicate_paths(connection, path)
    if not duplicates:
        return path
    return choose_canonical_path(connection, duplicates, role_roots)


def choose_canonical_path(
    connection: sqlite3.Connection,
    paths: tuple[str, ...],
    role_roots: tuple[RoleRoot, ...],
) -> str:
    return canonical_duplicate_details(connection, paths, role_roots).path


def canonical_duplicate_details(
    connection: sqlite3.Connection,
    paths: tuple[str, ...],
    role_roots: tuple[RoleRoot, ...],
) -> CanonicalDuplicateDetails:
    assessments = _assess_duplicate_paths(connection, paths, role_roots)
    winner = max(assessments, key=lambda item: item.sort_key)
    return CanonicalDuplicateDetails(
        path=winner.path,
        reasons=_canonical_reasons(winner, assessments),
    )


def list_exact_duplicate_groups(
    index_path: Path,
    *,
    routing_config_path: Path = Path("config/routing.yml"),
    limit: int = 50,
) -> tuple[ExactDuplicateGroup, ...]:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    with closing(sqlite3.connect(index_path)) as connection:
        role_roots = load_role_roots(routing_config_path)
        rows = connection.execute(
            """
            SELECT sha256
            FROM files
            WHERE is_markdown = 1
            GROUP BY sha256
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC, sha256 ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        groups = []
        for row in rows:
            group = _duplicate_group(connection, row[0], role_roots)
            if group is None:
                continue
            groups.append(group)
        return tuple(groups)


def inspect_duplicates(
    index_path: Path,
    path_or_group: str,
    *,
    routing_config_path: Path = Path("config/routing.yml"),
    semantic_limit: int = 5,
) -> DuplicateInspection:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    with closing(sqlite3.connect(index_path)) as connection:
        role_roots = load_role_roots(routing_config_path)
        exact_group = _resolve_duplicate_group(connection, path_or_group, role_roots)
        seed_path = exact_group.canonical.path if exact_group is not None else _resolve_indexed_path(connection, path_or_group)
        semantic_candidates = find_duplicates(
            index_path,
            _indexed_duplicate_seed(connection, seed_path),
            limit=max(semantic_limit * 3, 10),
            routing_config_path=routing_config_path,
        )
        excluded_paths = {seed_path}
        if exact_group is not None:
            excluded_paths.update(exact_group.paths)
        semantic_duplicates = _canonicalize_semantic_candidates(
            connection,
            semantic_candidates,
            excluded_paths,
            role_roots,
            limit=semantic_limit,
        )
        return DuplicateInspection(
            query=path_or_group,
            exact_group=exact_group,
            semantic_duplicates=semantic_duplicates,
        )


def _assess_duplicate_paths(
    connection: sqlite3.Connection,
    paths: tuple[str, ...],
    role_roots: tuple[RoleRoot, ...],
) -> tuple[_DuplicatePathAssessment, ...]:
    cache = _duplicate_stats_cache(connection)
    return tuple(_build_assessment(path, role_roots, cache) for path in paths)


def _build_assessment(path: str, role_roots: tuple[RoleRoot, ...], cache) -> _DuplicatePathAssessment:
    role = classify_path_role(path, role_roots)
    generated_like = _contains_folder(path, "generated")
    queue_like = _contains_folder(path, "queue")
    inbox_like = role == "inbox"
    role_rank = {
        "resource": 4,
        "project": 4,
        "queue": 1,
        "inbox": 2,
        "generated": 1,
        "area": 4,
        "unknown": 3,
        None: 3,
    }.get(role, 3)
    outgoing, backlinks, mtime = cache(path)
    return _DuplicatePathAssessment(
        path=path,
        role=role,
        generated_like=generated_like,
        queue_like=queue_like,
        inbox_like=inbox_like,
        outgoing_links=outgoing,
        backlinks=backlinks,
        mtime=mtime,
        role_rank=role_rank,
        path_preference=_path_preference(path),
    )


def _canonical_reasons(
    winner: _DuplicatePathAssessment,
    assessments: tuple[_DuplicatePathAssessment, ...],
) -> tuple[str, ...]:
    others = [item for item in assessments if item.path != winner.path]
    if not others:
        return ("only exact duplicate candidate in group",)

    reasons: list[str] = []
    if not winner.generated_like and any(item.generated_like for item in others):
        reasons.append("preferred over generated paths")
    if not winner.queue_like and any(item.queue_like for item in others):
        reasons.append("preferred over queue-like paths")
    if not winner.inbox_like and any(item.inbox_like for item in others):
        reasons.append("preferred over inbox paths")
    if winner.connectivity > max(item.connectivity for item in others):
        reasons.append(
            f"most connected duplicate ({winner.backlinks} backlinks, {winner.outgoing_links} outgoing links)"
        )
    if winner.mtime > max(item.mtime for item in others):
        reasons.append("newest duplicate copy")
    if winner.role_rank > max(item.role_rank for item in others):
        role = winner.role or "unclassified"
        reasons.append(f"stronger vault role ({role})")
    if winner.path_preference > max(item.path_preference for item in others):
        reasons.append("shorter, more stable path tie-break")
    if not reasons:
        reasons.append("stable lexical tie-break on path")
    return tuple(reasons)


def _duplicate_group(
    connection: sqlite3.Connection,
    sha256: str,
    role_roots: tuple[RoleRoot, ...],
) -> ExactDuplicateGroup | None:
    rows = connection.execute(
        """
        SELECT path
        FROM files
        WHERE is_markdown = 1 AND sha256 = ?
        ORDER BY path
        """,
        (sha256,),
    ).fetchall()
    paths = tuple(row[0] for row in rows)
    if len(paths) < 2:
        return None
    canonical = canonical_duplicate_details(connection, paths, role_roots)
    return ExactDuplicateGroup(
        group_id=_duplicate_group_id(sha256),
        sha256=sha256,
        paths=paths,
        canonical=canonical,
    )


def _duplicate_group_id(sha256: str) -> str:
    return f"sha256:{sha256[:12]}"


def _resolve_duplicate_group(
    connection: sqlite3.Connection,
    path_or_group: str,
    role_roots: tuple[RoleRoot, ...],
) -> ExactDuplicateGroup | None:
    sha256 = _resolve_duplicate_group_sha(connection, path_or_group)
    if sha256 is None:
        return None
    return _duplicate_group(connection, sha256, role_roots)


def _resolve_duplicate_group_sha(connection: sqlite3.Connection, path_or_group: str) -> str | None:
    if connection.execute("SELECT 1 FROM files WHERE path = ? AND is_markdown = 1", (path_or_group,)).fetchone():
        row = connection.execute("SELECT sha256 FROM files WHERE path = ?", (path_or_group,)).fetchone()
        if row is None:
            return None
        count = int(
            connection.execute(
                "SELECT COUNT(*) FROM files WHERE is_markdown = 1 AND sha256 = ?",
                (row[0],),
            ).fetchone()[0]
        )
        return row[0] if count > 1 else None
    if not path_or_group.startswith("sha256:"):
        return None
    prefix = path_or_group.split(":", 1)[1].strip().casefold()
    if not prefix:
        raise ValueError("Duplicate group id is empty.")
    rows = connection.execute(
        """
        SELECT sha256
        FROM files
        WHERE is_markdown = 1
        GROUP BY sha256
        HAVING COUNT(*) > 1
        """,
    ).fetchall()
    matches = [row[0] for row in rows if row[0].casefold().startswith(prefix)]
    if not matches:
        raise ValueError(f"Exact duplicate group not found: {path_or_group}")
    if len(matches) > 1:
        group_ids = ", ".join(_duplicate_group_id(item) for item in matches[:10])
        raise ValueError(f"Ambiguous duplicate group: {path_or_group}. Matches: {group_ids}")
    return matches[0]


def _resolve_indexed_path(connection: sqlite3.Connection, note_path: str) -> str:
    if connection.execute("SELECT 1 FROM files WHERE path = ? AND is_markdown = 1", (note_path,)).fetchone():
        return note_path
    raise FileNotFoundError(f"Path not found in index: {note_path}")


def _indexed_duplicate_seed(connection: sqlite3.Connection, path: str) -> str:
    row = connection.execute(
        """
        SELECT title, headings, tags, tasks, body
        FROM search_index
        WHERE path = ?
        """,
        (path,),
    ).fetchone()
    if row is None:
        raise FileNotFoundError(f"Path not found in search index: {path}")
    title, headings, tags, tasks, body = row
    title_line = f"# {title}\n\n" if title else ""
    extra = "\n".join(part for part in (headings, tags, tasks, body) if part)
    return title_line + extra


def _canonicalize_semantic_candidates(
    connection: sqlite3.Connection,
    candidates: tuple[DuplicateCandidate, ...],
    excluded_paths: set[str],
    role_roots: tuple[RoleRoot, ...],
    *,
    limit: int,
) -> tuple[DuplicateCandidate, ...]:
    merged: dict[str, DuplicateCandidate] = {}
    for candidate in candidates:
        canonical = canonical_duplicate_path(connection, candidate.path, role_roots)
        if canonical in excluded_paths:
            continue
        reasons = list(candidate.reasons)
        if canonical != candidate.path:
            reasons.append(f"exact duplicate canonicalized from {candidate.path}")
        previous = merged.get(canonical)
        if previous is None:
            merged[canonical] = DuplicateCandidate(
                path=canonical,
                score=candidate.score,
                reasons=tuple(dict.fromkeys(reasons)),
            )
            continue
        merged[canonical] = DuplicateCandidate(
            path=canonical,
            score=max(previous.score, candidate.score),
            reasons=tuple(dict.fromkeys(previous.reasons + tuple(reasons))),
        )
    ordered = sorted(merged.values(), key=lambda item: (-item.score, item.path))
    return tuple(ordered[:limit])


def _contains_folder(path: str, folder: str) -> bool:
    normalized = "/" + path.casefold().strip("/") + "/"
    return f"/{folder.casefold()}/" in normalized


def _path_preference(path: str) -> str:
    return "\uffff" * max(0, 20 - len(Path(path).parts)) + path


def _duplicate_stats_cache(connection: sqlite3.Connection):
    @lru_cache(maxsize=None)
    def load(path: str) -> tuple[int, int, float]:
        outgoing = int(
            connection.execute("SELECT COUNT(*) FROM wikilinks WHERE file_path = ?", (path,)).fetchone()[0]
        )
        backlinks = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM wikilinks
                WHERE resolved_path = ? OR preferred_path = ?
                """,
                (path, path),
            ).fetchone()[0]
        )
        mtime = float(connection.execute("SELECT mtime FROM files WHERE path = ?", (path,)).fetchone()[0])
        return outgoing, backlinks, mtime

    return load
