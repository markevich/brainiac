from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from .index import require_fts5
from .vault_roles import load_role_roots


TOKEN_RE = re.compile(r"[\w/-]+", re.UNICODE)
SYNTHESIS_SCORE_BOOST = 1.0


@dataclass(frozen=True)
class SearchResult:
    path: str
    score: float
    snippet: str


def search_index(
    index_path: Path,
    query: str,
    *,
    limit: int = 10,
    routing_config_path: Path = Path("config/routing.yml"),
) -> tuple[SearchResult, ...]:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    if limit <= 0:
        return ()
    match_query = _to_fts_query(query)
    if not match_query:
        return ()

    with closing(sqlite3.connect(index_path)) as connection:
        role_roots = load_role_roots(routing_config_path)
        require_fts5(connection)
        synthesis_roots = tuple(root.path for root in role_roots if root.role == "synthesis")
        rows = _fetch_search_rows(connection, match_query, synthesis_roots=synthesis_roots, limit=limit)
    return tuple(SearchResult(path=row[0], score=float(row[1]), snippet=row[2]) for row in rows)


def _fetch_search_rows(
    connection: sqlite3.Connection,
    match_query: str,
    *,
    synthesis_roots: tuple[str, ...],
    limit: int,
) -> list[tuple[str, float, str]]:
    synthesis_condition, synthesis_args = _synthesis_condition(synthesis_roots)
    return connection.execute(
        f"""
        SELECT
          search_index.path,
          bm25(search_index)
            - CASE WHEN {synthesis_condition} THEN ? ELSE 0 END
            AS score,
          snippet(search_index, 6, '[', ']', '...', 18) AS snippet
        FROM search_index
        WHERE search_index MATCH ?
        ORDER BY
          score ASC,
          search_index.path ASC
        LIMIT ?
        """,
        (*synthesis_args, SYNTHESIS_SCORE_BOOST, match_query, limit),
    ).fetchall()


def _synthesis_condition(synthesis_roots: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    root_clauses = tuple("search_index.path LIKE ?" for _root in synthesis_roots)
    clauses = root_clauses + (
        """
        EXISTS (
          SELECT 1
          FROM markdown_metadata
          WHERE markdown_metadata.file_path = search_index.path
            AND lower(markdown_metadata.key) = 'brainiac_role'
            AND lower(markdown_metadata.value) = 'synthesis'
        )
        """,
    )
    return " OR ".join(clauses), tuple(root + "%" for root in synthesis_roots)


def _to_fts_query(query: str) -> str:
    tokens = [token for token in TOKEN_RE.findall(query.lower()) if token.strip("-_/")]
    return " ".join(_quote_fts_token(token) for token in tokens)


def _quote_fts_token(token: str) -> str:
    return '"' + token.replace('"', '""') + '"'
