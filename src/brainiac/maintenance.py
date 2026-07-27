from __future__ import annotations

import hashlib
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from .config import VaultConfig
from .duplicates import list_exact_duplicate_groups
from .para import CANONICAL_ROOTS, validate_para_layout
from .scanner import walk_source_files
from .structure import analyze_structure
from .vault_roles import (
    RoleRoot,
    classify_note_role,
    classify_path_role,
    has_explicit_role_marker,
    invalid_explicit_role_marker_values,
    para_role_roots,
)


TOOLING_SEGMENTS = {
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".git",
    ".hg",
    ".svn",
}
WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


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
    def ambiguous_wikilink_count(self) -> int:
        return sum(1 for finding in self.findings if finding.type == "ambiguous_wikilink")

    @property
    def missing_wikilink_count(self) -> int:
        return sum(1 for finding in self.findings if finding.type == "missing_wikilink")

    @property
    def semantic_duplicate_count(self) -> int:
        return sum(1 for finding in self.findings if finding.type == "semantic_duplicate")

    @property
    def missing_role_marker_count(self) -> int:
        return sum(1 for finding in self.findings if finding.type == "missing_role_marker")

    @property
    def invalid_role_marker_count(self) -> int:
        return sum(1 for finding in self.findings if finding.type == "invalid_role_marker")


@dataclass(frozen=True)
class _SemanticDocument:
    path: str
    stem: str
    title_key: str
    terms: frozenset[str]
    sha256: str


@dataclass(frozen=True)
class _SemanticCandidate:
    path: str
    score: int
    reasons: tuple[str, ...]


def maintenance_report(
    index_path: Path,
    *,
    config: VaultConfig,
) -> MaintenanceReport:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    if config.root is None:
        raise ValueError("Vault root is not configured. Pass --vault-root or set vault.root.")

    role_roots = para_role_roots()
    with closing(sqlite3.connect(index_path)) as connection:
        findings = list(_para_layout_findings(config))
        findings.extend(
            _empty_directory_findings(
                connection,
                config,
                role_roots,
            )
        )
        findings.extend(
            _exact_duplicate_findings(
                index_path,
            )
        )
        findings.extend(_ambiguous_wikilink_findings(connection))
        findings.extend(_missing_wikilink_findings(connection))
        findings.extend(_invalid_role_marker_findings(index_path))
        findings.extend(_missing_role_marker_findings(index_path, role_roots))
        findings.extend(_semantic_duplicate_findings(index_path))
    ordered = tuple(sorted(findings, key=lambda item: (_severity_rank(item.severity), item.path)))
    return MaintenanceReport(findings=ordered)


def _para_layout_findings(config: VaultConfig) -> tuple[MaintenanceFinding, ...]:
    if config.root is None:
        return ()
    return tuple(
        MaintenanceFinding(
            id=f"para_layout:{violation.type}:{violation.path.rstrip('/')}",
            type=violation.type,
            severity="high",
            path=violation.path,
            summary=violation.summary,
            reasons=("vault.layout is para",),
            suggested_action=violation.suggested_action,
        )
        for violation in validate_para_layout(config.root)
    )


def _exact_duplicate_findings(
    index_path: Path,
) -> tuple[MaintenanceFinding, ...]:
    findings: list[MaintenanceFinding] = []
    for group in list_exact_duplicate_groups(index_path, limit=200):
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


def _invalid_role_marker_findings(index_path: Path) -> tuple[MaintenanceFinding, ...]:
    findings: list[MaintenanceFinding] = []
    with closing(sqlite3.connect(index_path)) as connection:
        rows = connection.execute(
            """
            SELECT path
            FROM search_index
            ORDER BY path
            """
        ).fetchall()
        for (path,) in rows:
            invalid_values = invalid_explicit_role_marker_values(connection, path)
            if not invalid_values:
                continue
            findings.append(
                MaintenanceFinding(
                    id=f"invalid_role_marker:{path}",
                    type="invalid_role_marker",
                    severity="medium",
                    path=path,
                    summary="Invalid explicit role marker",
                    reasons=(
                        f"unsupported brainiac_role value(s): {', '.join(invalid_values)}",
                        "valid values: source, umbrella",
                    ),
                    suggested_action="Replace brainiac_role with one of: source, umbrella.",
                )
            )
    return tuple(findings)


def _missing_role_marker_findings(
    index_path: Path,
    role_roots: tuple[RoleRoot, ...],
) -> tuple[MaintenanceFinding, ...]:
    findings: list[MaintenanceFinding] = []
    with closing(sqlite3.connect(index_path)) as connection:
        rows = connection.execute(
            """
            SELECT path, title, headings, tags, tasks, body
            FROM search_index
            ORDER BY path
            """
        ).fetchall()
        for path, title, headings, tags, tasks, body in rows:
            if has_explicit_role_marker(connection, path):
                continue
            note_role = classify_note_role(connection, path, role_roots)
            umbrella_like = _is_umbrella_like_note(title, headings, tags, tasks, body)
            if umbrella_like:
                role_hint = "umbrella"
            else:
                role_hint = "source"
            reasons = [f"no explicit brainiac_role marker on {path}"]
            if umbrella_like:
                reasons.append("note is list-like and may be a master list/index note")
            elif role_hint == "source":
                reasons.append("default role: source")
            findings.append(
                MaintenanceFinding(
                    id=f"missing_role_marker:{path}",
                    type="missing_role_marker",
                    severity="medium" if role_hint == "umbrella" else "low",
                    path=path,
                    summary="Missing explicit role marker",
                    reasons=tuple(reasons),
                    suggested_action=f"Add brainiac_role: {role_hint or 'source'} to frontmatter.",
                )
            )
    return tuple(findings)


def _semantic_duplicate_findings(index_path: Path) -> tuple[MaintenanceFinding, ...]:
    findings: list[MaintenanceFinding] = []
    important_terms = frozenset()
    stopwords = frozenset()
    role_roots = para_role_roots()
    archive_roots = ("Archive/",)
    seen_pairs: set[tuple[str, str]] = set()
    with closing(sqlite3.connect(index_path)) as connection:
        rows = connection.execute(
            """
            SELECT search_index.path, title, headings, tags, tasks, body, files.sha256
            FROM search_index
            JOIN files ON files.path = search_index.path
            ORDER BY search_index.path
            """
        ).fetchall()
        documents: list[_SemanticDocument] = []
        for path, title, headings, tags, tasks, body, sha256 in rows:
            if _is_under_roots(path, archive_roots) or _is_archived_path(path):
                continue
            note_role = classify_note_role(connection, path, role_roots)
            if note_role == "umbrella":
                continue
            if note_role == "source" and _is_umbrella_like_note(title, headings, tags, tasks, body):
                continue
            documents.append(
                _SemanticDocument(
                    path=path,
                    stem=Path(path).stem,
                    title_key=_semantic_title_key(title or "", important_terms),
                    terms=frozenset(
                        _semantic_terms(
                            _semantic_text(path, title, headings, tags, tasks, body),
                            important_terms,
                            stopwords,
                        )
                    ),
                    sha256=sha256,
                )
            )

        by_path = {document.path: document for document in documents}
        by_title: dict[str, set[str]] = {}
        by_term: dict[str, set[str]] = {}
        for document in documents:
            if document.title_key:
                by_title.setdefault(document.title_key, set()).add(document.path)
            for term in document.terms:
                by_term.setdefault(term, set()).add(document.path)
        high_frequency_limit = min(200, max(25, len(documents) // 20))

        for document in documents:
            candidate_paths: set[str] = set()
            if document.title_key:
                candidate_paths.update(by_title.get(document.title_key, set()))
            for term in document.terms:
                term_paths = by_term.get(term, set())
                if len(term_paths) <= high_frequency_limit or term in important_terms:
                    candidate_paths.update(term_paths)
            candidates = sorted(
                (
                    _score_semantic_candidate(document, by_path[candidate_path])
                    for candidate_path in candidate_paths
                    if candidate_path != document.path
                    and candidate_path in by_path
                    and by_path[candidate_path].sha256 != document.sha256
                ),
                key=lambda candidate: (-candidate.score, candidate.path),
            )
            for candidate in candidates[:3]:
                if candidate.score < 55:
                    continue
                pair = tuple(sorted((document.path, candidate.path)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                findings.append(
                    MaintenanceFinding(
                        id=f"semantic_duplicate:{hashlib.sha1('|'.join(pair).encode('utf-8')).hexdigest()[:12]}",
                        type="semantic_duplicate",
                        severity="low",
                        path=pair[0],
                        summary=f"Semantic duplicate candidate ({pair[1]})",
                        reasons=tuple(dict.fromkeys((f"similar note: {candidate.path}",) + candidate.reasons)),
                        suggested_action="Review both notes, preserve unique details, then consider a merge or retirement with review.",
                    )
                )
                break
    return tuple(findings)


def _semantic_text(path: str, title: str, headings: str, tags: str, tasks: str, body: str) -> str:
    return "\n".join(
        part
        for part in (
            title,
            headings,
            tags,
            tasks,
            _strip_frontmatter(body),
        )
        if part
    )


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1 :]).lstrip("\n")
    return text


def _score_semantic_candidate(seed: _SemanticDocument, candidate: _SemanticDocument) -> _SemanticCandidate:
    reasons: list[str] = []
    if _same_parent_folder(seed.path, candidate.path):
        score = _score_sibling_candidate(seed, candidate, reasons)
        return _SemanticCandidate(path=candidate.path, score=score, reasons=tuple(dict.fromkeys(reasons)))

    score = 0
    if seed.title_key and seed.title_key == candidate.title_key:
        score += 70
        reasons.append("same title")
    if seed.title_key and seed.title_key == candidate.stem.casefold():
        score += 50
        reasons.append("same note name")
    overlap = seed.terms & candidate.terms
    if overlap:
        coefficient = len(overlap) / max(1, min(len(seed.terms), len(candidate.terms)))
        score += min(60, round(coefficient * 100))
        reasons.append(f"shared terms: {', '.join(sorted(overlap)[:5])}")
    return _SemanticCandidate(path=candidate.path, score=score, reasons=tuple(dict.fromkeys(reasons)))


def _score_sibling_candidate(
    seed: _SemanticDocument,
    candidate: _SemanticDocument,
    reasons: list[str],
) -> int:
    basename_similarity = _name_similarity(seed.stem, candidate.stem)
    title_similarity = _name_similarity(seed.title_key, candidate.title_key)
    best_name_similarity = max(basename_similarity, title_similarity)
    reasons.append(f"same-folder sibling similarity: {best_name_similarity:.2f}")
    if best_name_similarity < 0.85:
        return 0
    score = round(best_name_similarity * 100)
    if seed.title_key and seed.title_key == candidate.title_key:
        score += 20
        reasons.append("same title")
    if seed.stem.casefold() == candidate.stem.casefold():
        score += 15
        reasons.append("same note name")
    return score


def _semantic_title_key(title: str, important_terms: frozenset[str]) -> str:
    return " ".join(sorted(_semantic_terms(title, important_terms, frozenset()))).casefold()


def _same_parent_folder(path_a: str, path_b: str) -> bool:
    return Path(path_a).parent.as_posix() == Path(path_b).parent.as_posix()


def _name_similarity(left: str, right: str) -> float:
    left_tokens = _name_tokens(left)
    right_tokens = _name_tokens(right)
    if left_tokens and right_tokens:
        overlap = len(left_tokens & right_tokens)
        if not overlap:
            return 0.0
        return max(
            overlap / len(left_tokens),
            overlap / len(right_tokens),
        )
    left_normalized = _normalize_name(left)
    right_normalized = _normalize_name(right)
    if not left_normalized or not right_normalized:
        return 0.0
    return 1.0 if left_normalized == right_normalized else 0.0


def _name_tokens(text: str) -> set[str]:
    return {
        token.casefold()
        for token in WORD_RE.findall(text)
        if any(char.isalpha() for char in token)
    }


def _normalize_name(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _semantic_terms(
    text: str,
    important_terms: frozenset[str],
    stopwords: frozenset[str],
) -> set[str]:
    return {
        token.casefold().strip("-_/")
        for token in WORD_RE.findall(text)
        if _keep_semantic_token(token, important_terms, stopwords)
    }


def _keep_semantic_token(
    token: str,
    important_terms: frozenset[str],
    stopwords: frozenset[str],
) -> bool:
    normalized = token.casefold().strip("-_/")
    if normalized in important_terms:
        return True
    if normalized in stopwords:
        return False
    return len(normalized) > 2


def _is_under_roots(path: str, roots: tuple[str, ...]) -> bool:
    return any(path == root.rstrip("/") or path.startswith(root) for root in roots)


def _is_archived_path(path: str) -> bool:
    return any(part.casefold() in {"archive", "archives"} for part in Path(path).parts[:-1])


def _is_umbrella_like_note(title: str, headings: str, tags: str, tasks: str, body: str) -> bool:
    text = "\n".join(part for part in (title, headings, tags, tasks, body) if part)
    if "[[" not in text:
        return False
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        return False
    prose_lines = 0
    link_lines = 0
    for line in lines:
        if line.startswith("#"):
            continue
        if line.startswith(("-", "*", "+")) and "[[" in line:
            link_lines += 1
            continue
        if re.fullmatch(r"\[\[[^\]]+\]\]", line):
            link_lines += 1
            continue
        prose_lines += 1
    if prose_lines > 1 or link_lines == 0:
        return False
    word_count = len(WORD_RE.findall(text.replace("[[", " ").replace("]]", " ")))
    return word_count <= 20


def _empty_directory_findings(
    connection: sqlite3.Connection,
    config: VaultConfig,
    role_roots: tuple[RoleRoot, ...],
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
    indexed_paths: set[str],
    direct_source_count: int,
) -> MaintenanceFinding | None:
    if dir_key in CANONICAL_ROOTS.values():
        return None

    role = classify_path_role(dir_key, role_roots)
    reasons = ["directory has no source files under configured scan rules"]
    severity = "low"
    summary = "Empty directory"
    suggested_action = "Delete if obsolete, or add source notes if this folder should stay active."

    if role in {"area", "project", "resource"}:
        severity = "medium"
        summary = f"Empty {role} directory"
        reasons.append(f"directory sits under the {role} role")
        suggested_action = "Delete if abandoned, or add the source notes that should live here."
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
