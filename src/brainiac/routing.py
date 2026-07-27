from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from math import log
from pathlib import Path


TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
UNSAFE_FILENAME_RE = re.compile(r"[\\/:*?\"<>|]+")


@dataclass(frozen=True)
class RoutingDestination:
    key: str
    section: str
    path: str


@dataclass(frozen=True)
class DuplicateCandidate:
    path: str
    score: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class WriteSuggestion:
    action: str
    path: str
    title: str
    link: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RouteCandidate:
    destination: RoutingDestination
    score: int
    reasons: tuple[str, ...]
    suggestion: WriteSuggestion


@dataclass(frozen=True)
class RouteResult:
    title: str
    candidates: tuple[RouteCandidate, ...]
    duplicates: tuple[DuplicateCandidate, ...]
    confidence: str
    recommendation: str


def route_content(
    index_path: Path,
    content: str,
    *,
    limit: int = 5,
    duplicate_limit: int = 5,
) -> RouteResult:
    """Dry-run route content into a canonical PARA profile or Inbox."""
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")

    title = extract_title(content)
    terms = _terms(content)
    with closing(sqlite3.connect(index_path)) as connection:
        rows = connection.execute("SELECT path, title, headings, tags, tasks, body FROM search_index").fetchall()
        document_terms = {
            path: _terms(" ".join(value or "" for value in values))
            for path, *values in rows
        }
        total = max(1, len(rows))
        frequencies = {term: sum(term in row_terms for row_terms in document_terms.values()) for term in terms}
        weights = {term: log((total + 1) / (frequencies[term] + 1)) + 1 for term in terms}
        query_weight = sum(weights.values()) or 1
        evidence: dict[str, list[tuple[float, str, int]]] = {}
        for path, row_terms in document_terms.items():
            shared = terms & row_terms
            if len(shared) < 2:
                continue
            score = sum(weights[term] for term in shared) / query_weight
            for candidate, depth in _para_ancestors(path):
                evidence.setdefault(candidate, []).append((score, path, depth))

        duplicates = tuple(
            candidate
            for candidate in find_duplicates(index_path, content, limit=duplicate_limit)
            if "same title" in candidate.reasons or "same note name" in candidate.reasons
        )
        markdown_paths = _markdown_paths(connection)
        existing_titles = _existing_titles(connection)
        existing_basenames = {Path(path).stem.casefold(): path for path in markdown_paths}
        candidates: list[RouteCandidate] = []
        for path, items in evidence.items():
            ranked = sorted(items, reverse=True)[:3]
            support = ranked[0][0] + sum(item[0] * 0.25 for item in ranked[1:])
            score = round((support + min(ranked[0][2], 3) * 0.03) * 100)
            if score < 35:
                continue
            destination = RoutingDestination(path.rstrip("/").split("/")[-1], "profile", path)
            suggestion = _suggest_write(
                connection, destination, title, existing_titles, existing_basenames, markdown_paths
            )
            candidates.append(
                RouteCandidate(
                    destination,
                    score,
                    (f"profile evidence: {', '.join(item[1] for item in ranked)}",),
                    suggestion,
                )
            )

        candidates = _prefer_specific_para_candidates(candidates)
        inbox = RoutingDestination("default", "inbox", "Inbox/")
        candidates.append(
            RouteCandidate(
                inbox,
                5,
                ("PARA fallback destination",),
                _suggest_write(connection, inbox, title, existing_titles, existing_basenames, markdown_paths),
            )
        )

    ordered = tuple(
        sorted(candidates, key=lambda item: (-item.score, -len(Path(item.destination.path).parts), item.destination.path))[:limit]
    )
    confidence = "high" if ordered[0].destination.path != "Inbox/" and ordered[0].score >= 35 else "low"
    recommendation = "Profile evidence supports the top destination." if confidence == "high" else "No clear profile match. Capture this in Inbox."
    return RouteResult(title, ordered, duplicates, confidence, recommendation)


def find_duplicates(index_path: Path, content: str, *, limit: int = 5, min_score: int = 20) -> tuple[DuplicateCandidate, ...]:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    title = extract_title(content)
    title_key = _title_key(title)
    content_terms = _terms(content)
    if not content_terms and not title_key:
        return ()

    candidates: list[DuplicateCandidate] = []
    with closing(sqlite3.connect(index_path)) as connection:
        rows = connection.execute("SELECT path, path_text, title, headings, tags, tasks, body FROM search_index").fetchall()
    for path, path_text, existing_title, headings, tags, tasks, body in rows:
        reasons: list[str] = []
        score = 0
        if title_key and title_key == _title_key(existing_title):
            score += 70
            reasons.append("same title")
        if title_key and title_key == Path(path).stem.casefold():
            score += 50
            reasons.append("same note name")
        row_terms = _terms(" ".join(value or "" for value in (path_text, existing_title, headings, tags, tasks, body)))
        overlap = content_terms & row_terms
        if overlap:
            score += min(60, round(len(overlap) / max(1, min(len(content_terms), len(row_terms))) * 100))
            reasons.append(f"shared terms: {', '.join(sorted(overlap)[:5])}")
        if score >= min_score:
            candidates.append(DuplicateCandidate(path, score, tuple(dict.fromkeys(reasons))))
    return tuple(sorted(candidates, key=lambda item: (-item.score, item.path))[:limit])


def extract_title(content: str) -> str:
    heading_match = HEADING_RE.search(content)
    if heading_match:
        return heading_match.group(1).strip()
    for line in content.splitlines():
        if line.strip():
            return line.strip().lstrip("#").strip()[:80]
    return "Untitled"


def _para_ancestors(path: str) -> tuple[tuple[str, int], ...]:
    parent = Path(path).parent
    if not parent.parts or parent.parts[0] not in {"Projects", "Areas", "Resources"}:
        return ()
    candidates = []
    for end in range(2, len(parent.parts) + 1):
        candidates.append((Path(*parent.parts[:end]).as_posix() + "/", end - 1))
    return tuple(candidates)


def _prefer_specific_para_candidates(candidates: list[RouteCandidate]) -> list[RouteCandidate]:
    return [
        candidate
        for candidate in candidates
        if not any(
            other.destination.path.startswith(candidate.destination.path)
            and other.destination.path != candidate.destination.path
            and other.score >= candidate.score * 0.8
            for other in candidates
        )
    ]


def _suggest_write(
    connection: sqlite3.Connection,
    destination: RoutingDestination,
    title: str,
    existing_titles: dict[str, str],
    existing_basenames: dict[str, str],
    markdown_paths: set[str],
) -> WriteSuggestion:
    note_name = _unique_note_name(title, destination.path, markdown_paths)
    path = destination.path + note_name
    action = "create"
    reasons = ["dry-run create suggestion"]
    if title_match := existing_titles.get(_title_key(title)):
        action, path = "review", title_match
        reasons.append("existing note has same title")
    elif basename_match := existing_basenames.get(Path(note_name).stem.casefold()):
        action, path = "review", basename_match
        reasons.append("note-name collision exists")
    reasons.append("suggested frontmatter role: source")
    return WriteSuggestion(action, path, title, shortest_unique_link(connection, path), tuple(reasons))


def shortest_unique_link(connection: sqlite3.Connection, note_path: str) -> str:
    stem = Path(note_path).stem
    matches = {row[0] for row in connection.execute("SELECT path FROM files WHERE is_markdown = 1").fetchall() if Path(row[0]).stem.casefold() == stem.casefold()}
    return f"[[{stem}]]" if not matches or matches == {note_path} else f"[[{Path(note_path).with_suffix('').as_posix()}]]"


def _unique_note_name(title: str, folder: str, markdown_paths: set[str]) -> str:
    base = UNSAFE_FILENAME_RE.sub("-", title).strip().strip(".") or "Untitled"
    candidate, counter = f"{base}.md", 2
    while folder + candidate in markdown_paths:
        candidate, counter = f"{base} {counter}.md", counter + 1
    return candidate


def _existing_titles(connection: sqlite3.Connection) -> dict[str, str]:
    titles: dict[str, str] = {}
    for path, title in connection.execute("SELECT path, title FROM search_index").fetchall():
        if key := _title_key(title):
            titles.setdefault(key, path)
    return titles


def _markdown_paths(connection: sqlite3.Connection) -> set[str]:
    return {row[0] for row in connection.execute("SELECT path FROM files WHERE is_markdown = 1").fetchall()}


def _terms(text: str) -> set[str]:
    return {token.casefold().strip("-_/") for token in TOKEN_RE.findall(text) if len(token.strip("-_ /")) > 2}


def _title_key(title: str) -> str:
    return " ".join(sorted(_terms(title))).casefold()
