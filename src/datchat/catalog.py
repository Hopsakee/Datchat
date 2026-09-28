"""The StatLine table catalog in DuckDB, so questions can be matched to tables.

``sync_catalog`` replaces ``meta.catalog`` in one transaction (idempotent: re-running never
duplicates rows). ``search`` ranks tables by how many search terms they match, title matches
first; discontinued tables are included because historic questions may need them.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import duckdb
import pandas as pd

from datchat import store
from datchat.cbs import CbsClient

CATALOG_SQL = """
CREATE TABLE IF NOT EXISTS meta.catalog (
    table_id          VARCHAR PRIMARY KEY,
    title             VARCHAR,
    short_title       VARCHAR,
    short_description VARCHAR,
    summary           VARCHAR,
    period            VARCHAR,
    frequency         VARCHAR,   -- 'Stopgezet' = discontinued
    modified          TIMESTAMPTZ,
    record_count      BIGINT,
    language          VARCHAR,
    catalog           VARCHAR,
    search_text       VARCHAR,   -- lower-cased, accents stripped
    loaded_at         TIMESTAMPTZ
);
"""

COLUMNS = {
    "Identifier": "table_id",
    "Title": "title",
    "ShortTitle": "short_title",
    "ShortDescription": "short_description",
    "Summary": "summary",
    "Period": "period",
    "Frequency": "frequency",
    "Modified": "modified",
    "RecordCount": "record_count",
    "Language": "language",
    "Catalog": "catalog",
}


def normalize(text: str | None) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(CATALOG_SQL)


def sync_catalog(con: duckdb.DuckDBPyConnection, client: CbsClient | None = None) -> int:
    own = client is None
    client = client or CbsClient()
    try:
        entries = client.catalog()
    finally:
        if own:
            client.close()
    return load_catalog(con, entries)


def load_catalog(con: duckdb.DuckDBPyConnection, entries: list[dict[str, Any]]) -> int:
    rows = []
    seen: set[str] = set()
    for e in entries:
        table_id = (e.get("Identifier") or "").strip()
        if not table_id or table_id in seen:
            continue
        seen.add(table_id)
        row = {col: e.get(key) for key, col in COLUMNS.items()}
        row["table_id"] = table_id
        row["title"] = (row["title"] or "").strip()
        row["search_text"] = normalize(
            " ".join(
                str(row[c] or "")
                for c in ("table_id", "title", "short_title", "short_description", "summary")
            )
        )
        row["loaded_at"] = store.now()
        rows.append(row)
    df = pd.DataFrame(rows, columns=[*COLUMNS.values(), "search_text", "loaded_at"])
    ensure_schema(con)
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute("DELETE FROM meta.catalog")
        con.register("_catalog", df)
        con.execute("INSERT INTO meta.catalog BY NAME SELECT * FROM _catalog")
        con.unregister("_catalog")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return len(df)


def search(con: duckdb.DuckDBPyConnection, query: str, limit: int = 25) -> pd.DataFrame:
    """Tables matching any term, ranked by (#terms in title, #terms anywhere, recency)."""
    terms = [t for t in re.split(r"\s+", normalize(query)) if t]
    if not terms:
        raise ValueError("empty search")
    title_hits = " + ".join("(strip_accents(lower(title)) LIKE ?)::INT" for _ in terms)
    any_hits = " + ".join("(search_text LIKE ?)::INT" for _ in terms)
    like = [f"%{t}%" for t in terms]
    synced = "EXISTS (SELECT 1 FROM meta.tables t WHERE t.table_id = c.table_id)"
    return con.execute(
        f"""
        SELECT table_id, title, period, frequency, modified::DATE AS modified,
               {synced} AS synced,
               {title_hits} AS title_hits, {any_hits} AS hits
        FROM meta.catalog c
        WHERE {any_hits} > 0
        ORDER BY title_hits DESC, hits DESC, (frequency = 'Stopgezet'), modified DESC
        LIMIT ?
        """,
        [*like, *like, *like, limit],
    ).df()


def describe_entry(con: duckdb.DuckDBPyConnection, table_id: str) -> dict[str, Any] | None:
    row = con.execute(
        "SELECT * EXCLUDE (search_text) FROM meta.catalog WHERE table_id = ?", [table_id]
    ).fetchone()
    if row is None:
        return None
    cols = [d[0] for d in con.description]
    return dict(zip(cols, row, strict=True))
