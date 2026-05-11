from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
UNSAFE_FILENAME_RE = re.compile(r"[\\/:*?\"<>|]+")
GENERIC_DESTINATIONS = {"default", "root"}
CONFIG_SECTIONS = {
    "area_roots",
    "archive_roots",
    "disabled_destination_sections",
    "important_terms",
    "generated_roots",
    "inbox_roots",
    "project_roots",
    "queue_roots",
    "resource_roots",
    "rules",
    "sensitive_destination_keys",
    "sensitive_path_prefixes",
    "stopwords",
    "synthesis_roots",
}
DUPLICATE_ROUTE_BOOST_MIN_SCORE = 30
LOW_CONFIDENCE_ROUTE_SCORE = 20


@dataclass(frozen=True)
class RoutingDestination:
    key: str
    section: str
    path: str


@dataclass(frozen=True)
class RoutingConfig:
    destinations: tuple[RoutingDestination, ...]
    disabled_destination_sections: frozenset[str]
    important_terms: frozenset[str]
    stopwords: frozenset[str]
    sensitive_destination_keys: frozenset[str]
    sensitive_path_prefixes: tuple[str, ...]


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
    policy: str
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


def load_routing_destinations(path: Path) -> tuple[RoutingDestination, ...]:
    return load_routing_config(path).destinations


def load_routing_config(path: Path) -> RoutingConfig:
    if not path.exists():
        raise FileNotFoundError(f"Routing config not found: {path}")

    current_section: str | None = None
    destinations: list[RoutingDestination] = []
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
            if current_section is not None:
                lists.setdefault(current_section, []).append(_unquote(stripped[2:].strip()))
            continue
        if current_section is None or current_section in CONFIG_SECTIONS:
            continue
        if ":" not in stripped or stripped.startswith("- "):
            continue

        key, value = stripped.split(":", 1)
        value = _unquote(value.strip())
        if value:
            destinations.append(
                RoutingDestination(key=key.strip(), section=current_section, path=value)
            )

    return RoutingConfig(
        destinations=tuple(destinations),
        disabled_destination_sections=frozenset(
            section.casefold().strip() for section in lists.get("disabled_destination_sections", [])
        ),
        important_terms=frozenset(_normalize_term(term) for term in lists.get("important_terms", [])),
        stopwords=frozenset(_normalize_term(term) for term in lists.get("stopwords", [])),
        sensitive_destination_keys=frozenset(
            _normalize_destination_key(key) for key in lists.get("sensitive_destination_keys", [])
        ),
        sensitive_path_prefixes=tuple(lists.get("sensitive_path_prefixes", [])),
    )


def route_content(
    index_path: Path,
    routing_config_path: Path,
    content: str,
    *,
    limit: int = 5,
    duplicate_limit: int = 5,
) -> RouteResult:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    routing_config = load_routing_config(routing_config_path)
    if not routing_config.destinations:
        raise ValueError(f"No routing destinations found in {routing_config_path}")

    title = extract_title(content)
    content_terms = _terms(content, routing_config.important_terms)
    duplicates = find_duplicates(
        index_path,
        content,
        limit=duplicate_limit,
        important_terms=routing_config.important_terms,
    )

    with closing(sqlite3.connect(index_path)) as connection:
        markdown_paths = _markdown_paths(connection)
        existing_titles = _existing_titles(connection, routing_config.important_terms)
        existing_basenames = {Path(path).stem.casefold(): path for path in markdown_paths}
        document_terms = _document_terms(connection, routing_config.important_terms)

        candidates: list[RouteCandidate] = []
        for destination in routing_config.destinations:
            if destination.section.casefold() in routing_config.disabled_destination_sections:
                continue
            score, reasons = _score_destination(
                destination,
                content_terms,
                document_terms,
                routing_config.important_terms,
            )
            duplicate_path = _duplicate_under_destination(destination.path, duplicates)
            if duplicate_path:
                score += 35
                reasons.append(f"likely duplicate under destination: {duplicate_path}")
            suggestion = _suggest_write(
                connection,
                destination,
                title,
                existing_titles,
                existing_basenames,
                markdown_paths,
                routing_config,
            )
            score += _suggestion_score(suggestion)
            candidates.append(
                RouteCandidate(
                    destination=destination,
                    score=score,
                    reasons=tuple(dict.fromkeys(reasons + list(suggestion.reasons))),
                    suggestion=suggestion,
                )
            )

    ordered = sorted(candidates, key=lambda item: (-item.score, item.destination.section, item.destination.key))
    selected = tuple(ordered[:limit])
    confidence, recommendation = _route_confidence(selected, duplicates)
    return RouteResult(
        title=title,
        candidates=selected,
        duplicates=duplicates,
        confidence=confidence,
        recommendation=recommendation,
    )


def find_duplicates(
    index_path: Path,
    content: str,
    *,
    limit: int = 5,
    min_score: int = 20,
    important_terms: frozenset[str] = frozenset(),
) -> tuple[DuplicateCandidate, ...]:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")

    title = extract_title(content)
    title_key = _title_key(title, important_terms)
    content_terms = _terms(content, important_terms)
    if not content_terms and not title_key:
        return ()

    candidates: list[DuplicateCandidate] = []
    with closing(sqlite3.connect(index_path)) as connection:
        for path, path_text, existing_title, headings, tags, tasks, body in connection.execute(
            """
            SELECT path, path_text, title, headings, tags, tasks, body
            FROM search_index
            """
        ).fetchall():
            reasons: list[str] = []
            score = 0
            existing_title_key = _title_key(existing_title, important_terms)
            if title_key and title_key == existing_title_key:
                score += 70
                reasons.append("same title")
            if title_key and title_key == Path(path).stem.casefold():
                score += 50
                reasons.append("same note name")

            row_terms = _terms(
                " ".join(value or "" for value in (path_text, existing_title, headings, tags, tasks, body)),
                important_terms,
            )
            overlap = content_terms & row_terms
            if overlap:
                coefficient = len(overlap) / max(1, min(len(content_terms), len(row_terms)))
                overlap_score = min(60, round(coefficient * 100))
                score += overlap_score
                sample = ", ".join(sorted(overlap)[:5])
                reasons.append(f"shared terms: {sample}")

            if score >= min_score:
                candidates.append(
                    DuplicateCandidate(path=path, score=score, reasons=tuple(dict.fromkeys(reasons)))
                )

    ordered = sorted(candidates, key=lambda item: (-item.score, item.path))[:limit]
    return tuple(ordered)


def extract_title(content: str) -> str:
    heading_match = HEADING_RE.search(content)
    if heading_match:
        return heading_match.group(1).strip()
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped.lstrip("#").strip()[:80]
    return "Untitled"


def _score_destination(
    destination: RoutingDestination,
    content_terms: set[str],
    document_terms: dict[str, set[str]],
    important_terms: frozenset[str],
) -> tuple[int, list[str]]:
    destination_terms = _terms(" ".join((destination.section, destination.key, destination.path)), important_terms)
    overlap = content_terms & destination_terms
    score = 0
    reasons: list[str] = []
    if overlap:
        score += min(60, 20 * len(overlap))
        reasons.append(f"matches routing terms: {', '.join(sorted(overlap))}")
    if destination.key in GENERIC_DESTINATIONS:
        score += 5
        reasons.append("generic fallback destination")

    related_scores: list[tuple[int, str]] = []
    for path, terms in document_terms.items():
        if not _path_belongs_to_destination(path, destination.path):
            continue
        shared = content_terms & terms
        if shared:
            related_scores.append((len(shared), path))
    if related_scores:
        shared_count, path = max(related_scores, key=lambda item: (item[0], item[1]))
        score += min(40, shared_count * 4)
        reasons.append(f"similar indexed note under destination: {path}")
    return score, reasons


def _path_belongs_to_destination(path: str, destination_path: str) -> bool:
    if destination_path.endswith("/"):
        return path.startswith(destination_path)
    return path == destination_path


def _duplicate_under_destination(
    destination_path: str,
    duplicates: tuple[DuplicateCandidate, ...],
) -> str | None:
    for duplicate in duplicates:
        if duplicate.score < DUPLICATE_ROUTE_BOOST_MIN_SCORE:
            continue
        if _path_belongs_to_destination(duplicate.path, destination_path):
            return duplicate.path
    return None


def _route_confidence(
    candidates: tuple[RouteCandidate, ...],
    duplicates: tuple[DuplicateCandidate, ...],
) -> tuple[str, str]:
    if not candidates:
        return "none", "No configured route candidates. Capture to inbox or configure vault roles first."
    top = candidates[0]
    strong_duplicate = any(duplicate.score >= DUPLICATE_ROUTE_BOOST_MIN_SCORE for duplicate in duplicates)
    if top.score < LOW_CONFIDENCE_ROUTE_SCORE and not strong_duplicate:
        return (
            "low",
            "No strong existing destination matched. Treat this as an inbox capture or candidate for a new area.",
        )
    if top.score < LOW_CONFIDENCE_ROUTE_SCORE:
        return "medium", "Route is weak, but duplicate candidates may point to the right neighborhood."
    return "high", "Top route has enough structural or lexical support for a dry-run suggestion."


def _suggest_write(
    connection: sqlite3.Connection,
    destination: RoutingDestination,
    title: str,
    existing_titles: dict[str, str],
    existing_basenames: dict[str, str],
    markdown_paths: set[str],
    routing_config: RoutingConfig,
) -> WriteSuggestion:
    if destination.path.endswith("/"):
        note_name = _unique_note_name(title, destination.path, markdown_paths)
        path = destination.path + note_name
        action = "create"
        reasons = ["dry-run create suggestion"]
        title_match = existing_titles.get(_title_key(title, routing_config.important_terms))
        basename_match = existing_basenames.get(Path(note_name).stem.casefold())
        if title_match:
            action = "review"
            path = title_match
            reasons.append("existing note has same title")
        elif basename_match:
            action = "review"
            path = basename_match
            reasons.append("note-name collision exists")
    else:
        path = destination.path
        action = "update" if path in markdown_paths else "create"
        reasons = [f"dry-run {action} suggestion"]

    return WriteSuggestion(
        action=action,
        path=path,
        title=title,
        link=shortest_unique_link(connection, path),
        policy=_write_policy(destination, path, routing_config),
        reasons=tuple(reasons),
    )


def shortest_unique_link(connection: sqlite3.Connection, note_path: str) -> str:
    stem = Path(note_path).stem
    all_matches = {
        row[0]
        for row in connection.execute("SELECT path FROM files WHERE is_markdown = 1").fetchall()
        if Path(row[0]).stem.casefold() == stem.casefold()
    }
    if not all_matches or all_matches == {note_path}:
        return f"[[{stem}]]"
    return f"[[{Path(note_path).with_suffix('').as_posix()}]]"


def _write_policy(destination: RoutingDestination, path: str, routing_config: RoutingConfig) -> str:
    destination_keys = {
        destination.key.casefold(),
        f"{destination.section}.{destination.key}".casefold(),
    }
    if destination_keys & routing_config.sensitive_destination_keys:
        return "review_required"
    if any(path.startswith(prefix) for prefix in routing_config.sensitive_path_prefixes):
        return "review_required"
    return "dry_run_only"


def _suggestion_score(suggestion: WriteSuggestion) -> int:
    if suggestion.action == "update":
        return 6
    if suggestion.action == "review":
        return 4
    return 2


def _unique_note_name(title: str, folder: str, markdown_paths: set[str]) -> str:
    base = _safe_note_stem(title)
    candidate = f"{base}.md"
    counter = 2
    while folder + candidate in markdown_paths:
        candidate = f"{base} {counter}.md"
        counter += 1
    return candidate


def _safe_note_stem(title: str) -> str:
    stem = UNSAFE_FILENAME_RE.sub("-", title).strip().strip(".")
    return stem or "Untitled"


def _existing_titles(connection: sqlite3.Connection, important_terms: frozenset[str]) -> dict[str, str]:
    titles: dict[str, str] = {}
    for path, title in connection.execute("SELECT path, title FROM search_index").fetchall():
        key = _title_key(title, important_terms)
        if key:
            titles.setdefault(key, path)
    return titles


def _markdown_paths(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute("SELECT path FROM files WHERE is_markdown = 1").fetchall()
    }


def _document_terms(connection: sqlite3.Connection, important_terms: frozenset[str]) -> dict[str, set[str]]:
    return {
        path: _terms(
            " ".join(value or "" for value in (path_text, title, headings, tags, tasks, body)),
            important_terms,
        )
        for path, path_text, title, headings, tags, tasks, body in connection.execute(
            """
            SELECT path, path_text, title, headings, tags, tasks, body
            FROM search_index
            """
        ).fetchall()
    }


def _terms(text: str, important_terms: frozenset[str] = frozenset()) -> set[str]:
    return {
        token.lower().strip("-_/")
        for token in TOKEN_RE.findall(text)
        if _keep_token(token, important_terms)
    }


def _keep_token(token: str, important_terms: frozenset[str]) -> bool:
    normalized = _normalize_term(token)
    return len(normalized) > 2 or normalized in important_terms


def _title_key(title: str, important_terms: frozenset[str]) -> str:
    return " ".join(sorted(_terms(title, important_terms))).casefold()


def _normalize_term(term: str) -> str:
    return term.lower().strip("-_/")


def _normalize_destination_key(key: str) -> str:
    return key.casefold().strip()


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
