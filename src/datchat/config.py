"""Tables we sync and where the database lives."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TableSpec:
    table_id: str
    purpose: str


# Phase 1: household wealth. Order is the default sync order.
TABLES: tuple[TableSpec, ...] = (
    TableSpec(
        "83834NED", "Wealth by 10%-group and component, incl. 'Vermogen exclusief eigen woning'"
    ),
    TableSpec("84476NED", "Inequality measures and total wealth of top 10% / 1% / 0.1%"),
    TableSpec("83835NED", "Households by wealth class (euro bands) and 10%-group"),
    TableSpec("83934NED", "Percentile boundaries of the 10%-groups for income and wealth"),
    TableSpec("85889NED", "National accounts wealth distribution (incl. pensions), 2021-"),
    TableSpec("84104NED", "National accounts wealth distribution (incl. pensions), 2015-2021"),
    TableSpec("82960NED", "National accounts wealth distribution (incl. pensions), 2005-2014"),
)

TABLE_IDS: tuple[str, ...] = tuple(t.table_id for t in TABLES)


def db_path() -> Path:
    """DuckDB file location; override with DATCHAT_DB (e.g. on the Hetzner server)."""
    return Path(os.environ.get("DATCHAT_DB", "data/datchat.duckdb"))
