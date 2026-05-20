from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .duplicates import canonical_duplicate_path
from .routing_config import ensure_routing_config
from .routing import shortest_unique_link
from .search import search_index
from .vault_roles import classify_note_role, classify_path_role, load_role_roots


SOURCE_SNAPSHOT_KEYS = {"source_snapshots", "source-snapshots"}
UNSAFE_FILENAME_CHARS = set('\\/:*?"<>|')


@dataclass(frozen=True)
class SynthesisNote:
    path: str
    title: str
    topic: str
    source_count: int
    stale_source_count: int
    open_question_count: int


@dataclass(frozen=True)
class SynthesisSource:
    path: str
    link_target: str
    status: str
    current_sha256: str | None
    snapshot_sha256: str | None
    current_mtime: float | None
    snapshot_mtime: float | None


@dataclass(frozen=True)
class SynthesisInspection:
    note: SynthesisNote
    metadata: dict[str, tuple[str, ...]]
    sources: tuple[SynthesisSource, ...]


@dataclass(frozen=True)
class StaleSynthesisNote:
    path: str
    stale_sources: tuple[SynthesisSource, ...]


@dataclass(frozen=True)
class SynthesisSourceCandidate:
    path: str
    title: str
    score: int
    reasons: tuple[str, ...]
    sha256: str
    mtime: float


@dataclass(frozen=True)
class SynthesisSuggestion:
    topic: str
    action: str
    path: str
    sources: tuple[SynthesisSourceCandidate, ...]
    draft: str


def list_synthesis_notes(
    index_path: Path,
    routing_config_path: Path,
    *,
    limit: int = 50,
) -> tuple[SynthesisNote, ...]:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    roots = load_synthesis_roots(routing_config_path)
    role_roots = load_role_roots(routing_config_path)
    with closing(sqlite3.connect(index_path)) as connection:
        paths = _synthesis_paths(connection, roots, role_roots)
        notes = [_synthesis_note(connection, path) for path in paths]
    return tuple(sorted(notes, key=lambda note: note.path)[:limit])


def inspect_synthesis(
    index_path: Path,
    routing_config_path: Path,
    topic_or_path: str,
) -> SynthesisInspection:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    roots = load_synthesis_roots(routing_config_path)
    role_roots = load_role_roots(routing_config_path)
    with closing(sqlite3.connect(index_path)) as connection:
        path = _resolve_synthesis_path(connection, roots, role_roots, topic_or_path)
        return SynthesisInspection(
            note=_synthesis_note(connection, path),
            metadata=_metadata(connection, path),
            sources=_sources(connection, path),
        )


def stale_synthesis_notes(
    index_path: Path,
    routing_config_path: Path,
    *,
    limit: int = 50,
) -> tuple[StaleSynthesisNote, ...]:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    roots = load_synthesis_roots(routing_config_path)
    role_roots = load_role_roots(routing_config_path)
    stale: list[StaleSynthesisNote] = []
    with closing(sqlite3.connect(index_path)) as connection:
        for path in _synthesis_paths(connection, roots, role_roots):
            stale_sources = tuple(source for source in _sources(connection, path) if source.status == "stale")
            if stale_sources:
                stale.append(StaleSynthesisNote(path=path, stale_sources=stale_sources))
    return tuple(sorted(stale, key=lambda note: note.path)[:limit])


def suggest_synthesis(
    index_path: Path,
    routing_config_path: Path,
    topic_or_path: str,
    *,
    limit: int = 8,
) -> SynthesisSuggestion:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    roots = load_synthesis_roots(routing_config_path)
    role_roots = load_role_roots(routing_config_path)
    with closing(sqlite3.connect(index_path)) as connection:
        exact_path = _indexed_markdown_path(connection, topic_or_path)
        if exact_path and is_synthesis_path(connection, exact_path, roots):
            return _update_suggestion(connection, exact_path, limit)
        if exact_path is None:
            try:
                synthesis_path = _resolve_synthesis_path(connection, roots, role_roots, topic_or_path)
                return _update_suggestion(connection, synthesis_path, limit)
            except FileNotFoundError:
                pass

        topic = _topic_for_input(connection, topic_or_path, exact_path)
        path = _suggested_synthesis_path(connection, roots, topic)
        action = "update" if _indexed_markdown_path(connection, path) else "create"
        candidates = _source_candidates(connection, index_path, routing_config_path, roots, role_roots, topic, exact_path, limit)
        return SynthesisSuggestion(
            topic=topic,
            action=action,
            path=path,
            sources=candidates,
            draft=_draft_note(connection, topic, candidates),
        )


def is_synthesis_path(connection: sqlite3.Connection, path: str, roots: tuple[str, ...] = ()) -> bool:
    if any(path.startswith(root) for root in roots):
        return True
    return classify_note_role(connection, path, ()) == "synthesis"


def synthesis_references_for_source(
    connection: sqlite3.Connection,
    source_path: str,
    roots: tuple[str, ...] = (),
) -> tuple[str, ...]:
    rows = connection.execute(
        """
        SELECT DISTINCT file_path
        FROM wikilinks
        WHERE resolved_path = ? OR preferred_path = ?
        ORDER BY file_path
        """,
        (source_path, source_path),
    ).fetchall()
    return tuple(path for (path,) in rows if is_synthesis_path(connection, path, roots))


def load_synthesis_roots(path: Path) -> tuple[str, ...]:
    if path.name == "routing.yml":
        path = ensure_routing_config(path)
    current_section: str | None = None
    roots: list[str] = []
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
        if current_section != "synthesis_roots" or not stripped.startswith("- "):
            continue
        value = _unquote(stripped[2:].strip())
        if value:
            roots.append(_folder_path(value))
    return tuple(roots)


def _update_suggestion(connection: sqlite3.Connection, synthesis_path: str, limit: int) -> SynthesisSuggestion:
    topic = _synthesis_note(connection, synthesis_path).topic
    sources = tuple(
        _candidate_from_source(connection, source.path, 100, ("existing source",))
        for source in _sources(connection, synthesis_path)
        if _indexed_markdown_path(connection, source.path)
    )
    sources = tuple(candidate for candidate in sources if candidate is not None)[:limit]
    return SynthesisSuggestion(
        topic=topic,
        action="update",
        path=synthesis_path,
        sources=sources,
        draft=_draft_note(connection, topic, sources),
    )


def _source_candidates(
    connection: sqlite3.Connection,
    index_path: Path,
    routing_config_path: Path,
    roots: tuple[str, ...],
    role_roots,
    topic: str,
    seed_path: str | None,
    limit: int,
) -> tuple[SynthesisSourceCandidate, ...]:
    candidates: dict[str, SynthesisSourceCandidate] = {}
    seen_hashes: set[str] = set()
    expected_role = classify_path_role(seed_path, role_roots) if seed_path else None
    topic_terms = _topic_terms(topic)
    if seed_path is not None:
        seed = _candidate_from_source(connection, seed_path, 120, ("seed source",))
        if seed is not None:
            canonical_seed = _canonical_candidate(connection, seed, role_roots, ("canonical exact duplicate",))
            candidates[canonical_seed.path] = canonical_seed
            seen_hashes.add(canonical_seed.sha256)

    for position, result in enumerate(
        search_index(index_path, topic, limit=max(limit * 3, 10), routing_config_path=routing_config_path),
        start=1,
    ):
        if result.path == seed_path or is_synthesis_path(connection, result.path, roots):
            continue
        candidate = _candidate_from_source(
            connection,
            result.path,
            max(10, 90 - position * 5),
            ("lexical topic match",),
        )
        if candidate is not None:
            enriched = _topic_adjusted_candidate(connection, candidate, topic_terms, expected_role, role_roots)
            canonical = _canonical_candidate(connection, enriched, role_roots, ("canonical exact duplicate",))
            if canonical.sha256 in seen_hashes:
                continue
            if canonical.score >= 20:
                seen_hashes.add(canonical.sha256)
                candidates.setdefault(canonical.path, canonical)
            elif canonical.path not in candidates and canonical.score >= 10:
                candidates.setdefault(canonical.path, canonical)
                seen_hashes.add(canonical.sha256)

    ordered = sorted(candidates.values(), key=lambda item: (-item.score, item.path))
    return tuple(ordered[:limit])


def _candidate_from_source(
    connection: sqlite3.Connection,
    path: str,
    score: int,
    reasons: tuple[str, ...],
) -> SynthesisSourceCandidate | None:
    row = connection.execute(
        """
        SELECT files.path, search_index.title, files.sha256, files.mtime
        FROM files
        JOIN search_index ON search_index.path = files.path
        WHERE files.path = ? AND files.is_markdown = 1
        """,
        (path,),
    ).fetchone()
    if row is None:
        return None
    return SynthesisSourceCandidate(
        path=row[0],
        title=row[1] or Path(row[0]).stem,
        score=score,
        reasons=reasons,
        sha256=row[2],
        mtime=float(row[3]),
    )


def _topic_adjusted_candidate(
    connection: sqlite3.Connection,
    candidate: SynthesisSourceCandidate,
    topic_terms: tuple[str, ...],
    expected_role: str | None,
    role_roots,
) -> SynthesisSourceCandidate:
    row = connection.execute(
        """
        SELECT path_text, title, headings, tags, body
        FROM search_index
        WHERE path = ?
        """,
        (candidate.path,),
    ).fetchone()
    if row is None:
        return candidate

    path_text, title, headings, tags, body = (value or "" for value in row)
    score = candidate.score
    reasons = list(candidate.reasons)
    in_primary_fields = {term for term in topic_terms if _contains_term(" ".join((path_text, title, headings, tags)), term)}
    in_body = {term for term in topic_terms if _contains_term(body, term)}
    if in_primary_fields:
        score += 20
        reasons.append("topic in path/title/headings/tags")
    elif in_body:
        score -= 30
        reasons.append("body-only lexical match")

    candidate_role = classify_path_role(candidate.path, role_roots)
    if expected_role and candidate_role:
        if candidate_role == expected_role:
            score += 12
            reasons.append(f"same role {candidate_role}")
        else:
            score -= 10
            reasons.append(f"different role {candidate_role}")

    return SynthesisSourceCandidate(
        path=candidate.path,
        title=candidate.title,
        score=score,
        reasons=tuple(dict.fromkeys(reasons)),
        sha256=candidate.sha256,
        mtime=candidate.mtime,
    )


def _canonical_candidate(
    connection: sqlite3.Connection,
    candidate: SynthesisSourceCandidate,
    role_roots,
    extra_reasons: tuple[str, ...] = (),
) -> SynthesisSourceCandidate:
    canonical_path = canonical_duplicate_path(connection, candidate.path, role_roots)
    if canonical_path == candidate.path:
        return candidate
    canonical = _candidate_from_source(connection, canonical_path, candidate.score, candidate.reasons + extra_reasons)
    if canonical is None:
        return candidate
    return SynthesisSourceCandidate(
        path=canonical.path,
        title=canonical.title,
        score=max(candidate.score, canonical.score),
        reasons=tuple(dict.fromkeys(candidate.reasons + extra_reasons + (f"canonicalized from {candidate.path}",))),
        sha256=canonical.sha256,
        mtime=canonical.mtime,
    )


def _draft_note(
    connection: sqlite3.Connection,
    topic: str,
    sources: tuple[SynthesisSourceCandidate, ...],
) -> str:
    snapshot_lines = "\n".join(
        f'  - "{source.path}|{source.sha256}|{source.mtime}"' for source in sources
    )
    source_lines = "\n".join(f"- {shortest_unique_link(connection, source.path)}" for source in sources)
    if not snapshot_lines:
        snapshot_lines = "  - "
    if not source_lines:
        source_lines = "- "
    return f"""---
brainiac_role: synthesis
topic: {topic}
last_reviewed: {date.today().isoformat()}
source_snapshots:
{snapshot_lines}
---
# {topic}

## Current stance

## Key points

## Decisions

## Contradictions

## Open questions

## Sources

{source_lines}
"""


def _topic_for_input(connection: sqlite3.Connection, topic_or_path: str, exact_path: str | None) -> str:
    if exact_path is None:
        return topic_or_path.strip() or "Untitled synthesis"
    row = connection.execute("SELECT title FROM search_index WHERE path = ?", (exact_path,)).fetchone()
    title = row[0] if row and row[0] else Path(exact_path).stem
    return title.strip() or Path(exact_path).stem


def _suggested_synthesis_path(connection: sqlite3.Connection, roots: tuple[str, ...], topic: str) -> str:
    root = roots[0] if roots else "memory/synthesis/"
    base = _safe_stem(topic)
    candidate = f"{root}{base}.synthesis.md"
    counter = 2
    while _indexed_markdown_path(connection, candidate):
        candidate = f"{root}{base}.synthesis {counter}.md"
        counter += 1
    return candidate


def _indexed_markdown_path(connection: sqlite3.Connection, path: str) -> str | None:
    row = connection.execute(
        "SELECT path FROM files WHERE path = ? AND is_markdown = 1",
        (path,),
    ).fetchone()
    return row[0] if row else None


def _safe_stem(value: str) -> str:
    cleaned = "".join("-" if char in UNSAFE_FILENAME_CHARS else char for char in value)
    cleaned = cleaned.strip().strip(".")
    return cleaned or "Untitled synthesis"


def _synthesis_paths(
    connection: sqlite3.Connection,
    roots: tuple[str, ...],
    role_roots,
) -> tuple[str, ...]:
    paths = {
        row[0]
        for row in connection.execute("SELECT path FROM files WHERE is_markdown = 1 ORDER BY path").fetchall()
        if is_synthesis_path(connection, row[0], roots)
    }
    return tuple(sorted(paths))


def _resolve_synthesis_path(
    connection: sqlite3.Connection,
    roots: tuple[str, ...],
    role_roots,
    topic_or_path: str,
) -> str:
    row = connection.execute(
        "SELECT path FROM files WHERE is_markdown = 1 AND path = ?",
        (topic_or_path,),
    ).fetchone()
    if row is not None:
        path = row[0]
        if not is_synthesis_path(connection, path, roots):
            raise ValueError(f"Indexed path is not a synthesis note: {topic_or_path}")
        return path

    query = topic_or_path.casefold()
    matches = [
        path
        for path in _synthesis_paths(connection, roots, role_roots)
        if query in Path(path).stem.casefold()
        or any(query in value.casefold() for value in _metadata(connection, path).get("topic", ()))
    ]
    if not matches:
        raise FileNotFoundError(f"Synthesis note not found: {topic_or_path}")
    if len(matches) > 1:
        raise ValueError(f"Ambiguous synthesis topic: {topic_or_path}. Matches: {', '.join(matches[:10])}")
    return matches[0]


def _synthesis_note(connection: sqlite3.Connection, path: str) -> SynthesisNote:
    title = connection.execute("SELECT title FROM search_index WHERE path = ?", (path,)).fetchone()
    metadata = _metadata(connection, path)
    sources = _sources(connection, path)
    return SynthesisNote(
        path=path,
        title=title[0] if title else Path(path).stem,
        topic=metadata.get("topic", (Path(path).stem,))[0],
        source_count=len(sources),
        stale_source_count=sum(1 for source in sources if source.status == "stale"),
        open_question_count=_open_question_count(connection, path),
    )


def _sources(connection: sqlite3.Connection, synthesis_path: str) -> tuple[SynthesisSource, ...]:
    snapshots = _source_snapshots(connection, synthesis_path)
    rows = connection.execute(
        """
        SELECT target, resolved_path, preferred_path, resolution_status
        FROM wikilinks
        WHERE file_path = ?
        ORDER BY line, target
        """,
        (synthesis_path,),
    ).fetchall()
    sources: list[SynthesisSource] = []
    seen: set[str] = set()
    for target, resolved_path, preferred_path, resolution_status in rows:
        path = resolved_path or preferred_path
        if path is None:
            sources.append(
                SynthesisSource(
                    path=target,
                    link_target=target,
                    status=resolution_status,
                    current_sha256=None,
                    snapshot_sha256=None,
                    current_mtime=None,
                    snapshot_mtime=None,
                )
            )
            continue
        if path in seen:
            continue
        seen.add(path)
        file_row = connection.execute(
            "SELECT sha256, mtime FROM files WHERE path = ?",
            (path,),
        ).fetchone()
        current_sha = file_row[0] if file_row else None
        current_mtime = float(file_row[1]) if file_row else None
        snapshot = snapshots.get(path)
        status = "current"
        if snapshot and snapshot[0] and current_sha and snapshot[0] != current_sha:
            status = "stale"
        sources.append(
            SynthesisSource(
                path=path,
                link_target=target,
                status=status,
                current_sha256=current_sha,
                snapshot_sha256=snapshot[0] if snapshot else None,
                current_mtime=current_mtime,
                snapshot_mtime=snapshot[1] if snapshot else None,
            )
        )
    return tuple(sources)


def _source_snapshots(connection: sqlite3.Connection, synthesis_path: str) -> dict[str, tuple[str | None, float | None]]:
    snapshots: dict[str, tuple[str | None, float | None]] = {}
    metadata = _metadata(connection, synthesis_path)
    for key, values in metadata.items():
        if key.casefold() not in SOURCE_SNAPSHOT_KEYS:
            continue
        for value in values:
            parts = [part.strip() for part in value.split("|")]
            if not parts or not parts[0]:
                continue
            sha = parts[1] if len(parts) > 1 and parts[1] else None
            mtime = _float_or_none(parts[2]) if len(parts) > 2 else None
            snapshots[parts[0]] = (sha, mtime)
    return snapshots


def _metadata(connection: sqlite3.Connection, path: str) -> dict[str, tuple[str, ...]]:
    values: dict[str, list[str]] = {}
    for key, value in connection.execute(
        "SELECT key, value FROM markdown_metadata WHERE file_path = ? ORDER BY key, value",
        (path,),
    ).fetchall():
        values.setdefault(key, []).append(value)
    return {key: tuple(items) for key, items in values.items()}


def _open_question_count(connection: sqlite3.Connection, path: str) -> int:
    row = connection.execute(
        """
        SELECT COUNT(*)
        FROM tasks
        WHERE file_path = ? AND done = 0 AND lower(text) LIKE '%question%'
        """,
        (path,),
    ).fetchone()
    return int(row[0]) if row else 0


def _folder_path(value: str) -> str:
    normalized = value.strip().strip("/")
    return normalized + "/" if normalized else normalized


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _float_or_none(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _topic_terms(topic: str) -> tuple[str, ...]:
    return tuple(
        token.casefold()
        for token in Path(topic).stem.replace("/", " ").split()
        if len(token.strip("-_/")) > 2
    )


def _contains_term(text: str, term: str) -> bool:
    return term.casefold() in text.casefold()
