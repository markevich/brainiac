from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from .index import require_fts5


TOKEN_RE = re.compile(r"[\w/-]+", re.UNICODE)


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
) -> tuple[SearchResult, ...]:
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found: {index_path}. Run `brainiac scan` first.")
    if limit <= 0:
        return ()
    match_query = _to_fts_query(query)
    if not match_query:
        return ()

    with closing(sqlite3.connect(index_path)) as connection:
        require_fts5(connection)
        rows = _fetch_search_rows(connection, match_query, limit=limit)
    return tuple(SearchResult(path=row[0], score=float(row[1]), snippet=row[2]) for row in rows)


def _fetch_search_rows(
    connection: sqlite3.Connection,
    match_query: str,
    *,
    limit: int,
) -> list[tuple[str, float, str]]:
    return connection.execute(
        """
        SELECT
          search_index.path,
          bm25(search_index) AS score,
          snippet(search_index, 6, '[', ']', '...', 18) AS snippet
        FROM search_index
        WHERE search_index MATCH ?
        ORDER BY
          score ASC,
          search_index.path ASC
        LIMIT ?
        """,
        (match_query, limit),
    ).fetchall()


def _to_fts_query(query: str) -> str:
    tokens = [token for token in TOKEN_RE.findall(query.lower()) if token.strip("-_/")]
    return " ".join(_quote_fts_token(token) for token in tokens)


def _quote_fts_token(token: str) -> str:
    return '"' + token.replace('"', '""') + '"'
