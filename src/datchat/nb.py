"""Helpers for generated marimo notebooks.

Every query opens its own read-only connection and closes it again, so a notebook never
holds the database file and a sync can run in between. Everything a notebook shows comes
from ``sql()`` (CBS data), or from a cell explicitly labelled as an assumption.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from datchat import config, store

ASSUMPTION_LABEL = "Aanname, niet CBS"


def sql(query: str, params: list | None = None) -> pd.DataFrame:
    """Run a read-only query against the local CBS cache and return a DataFrame."""
    con = store.connect(config.db_path(), read_only=True)
    try:
        return con.execute(query, params or []).df()
    finally:
        con.close()


def require(table_ids: Iterable[str]) -> None:
    """Fail with a clear instruction when a table the notebook needs is not synced."""
    wanted = list(table_ids)
    have = {t.lower() for t in sql("SELECT table_id FROM meta.tables")["table_id"]}
    missing = [t for t in wanted if t.lower() not in have]
    if missing:
        raise RuntimeError(
            f"Tables not synced: {', '.join(missing)}. Run: uv run datchat sync {' '.join(missing)}"
        )


def sources(table_ids: Iterable[str]) -> pd.DataFrame:
    """Provenance per table: title, coverage, which periods are provisional, sync time."""
    ids = [t.lower() for t in table_ids]
    return sql(
        """
        SELECT t.table_id, trim(t.title) AS title, t.temporal_coverage,
               string_agg(c.title, ', ' ORDER BY c.idx)
                   FILTER (WHERE c.status = 'Voorlopig') AS voorlopig,
               t.modified::DATE AS cbs_gewijzigd, t.synced_at::TIMESTAMP(0) AS gesynchroniseerd,
               t.statline_url
        FROM meta.tables t
        LEFT JOIN meta.dimension_codes c
          ON c.table_id = t.table_id AND c.dimension_id = 'Perioden'
        WHERE lower(t.table_id) IN (SELECT unnest(?::VARCHAR[]))
        GROUP BY ALL ORDER BY t.table_id
        """,
        [ids],
    )


def source_line(table_ids: Iterable[str]) -> str:
    """One-line caption for charts, e.g. 'Bron: CBS StatLine 84476NED, 83834NED'."""
    return "Bron: CBS StatLine " + ", ".join(table_ids)
