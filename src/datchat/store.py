"""DuckDB storage: three schemas.

- ``raw``  : one table per CBS table (``raw.t83834ned``), observations exactly as served,
             dimension columns keep their CBS identifiers.
- ``meta`` : table properties (incl. methodology text), dimensions, codes, groups, measures,
             and the sync log. Shared across all CBS tables, keyed by ``table_id``.
- ``core`` : labelled views per table (``core.t83834ned``): every observation with code
             titles, measure title and unit, and period status. Question-specific SQL lives
             in the notebooks that answer questions.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pandas as pd

from datchat.cbs import Observations, TableMetadata

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS meta.tables (
    table_id              VARCHAR PRIMARY KEY,
    title                 VARCHAR,
    description           VARCHAR,
    long_description      VARCHAR,
    temporal_coverage     VARCHAR,
    frequency             VARCHAR,
    status                VARCHAR,
    modified              TIMESTAMPTZ,
    observations_modified TIMESTAMPTZ,
    version               VARCHAR,
    observation_count     BIGINT,
    source_api            VARCHAR,
    statline_url          VARCHAR,
    properties_json       JSON,
    synced_at             TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS meta.dimensions (
    table_id     VARCHAR,
    dimension_id VARCHAR,
    position     INTEGER,
    title        VARCHAR,
    description  VARCHAR,
    kind         VARCHAR,
    PRIMARY KEY (table_id, dimension_id)
);

CREATE TABLE IF NOT EXISTS meta.dimension_codes (
    table_id     VARCHAR,
    dimension_id VARCHAR,
    code         VARCHAR,
    idx          INTEGER,
    title        VARCHAR,
    description  VARCHAR,
    group_id     VARCHAR,
    status       VARCHAR,  -- Perioden only: Definitief / Voorlopig / ...
    PRIMARY KEY (table_id, dimension_id, code)
);

CREATE TABLE IF NOT EXISTS meta.dimension_groups (
    table_id     VARCHAR,
    dimension_id VARCHAR,
    group_id     VARCHAR,
    idx          INTEGER,
    title        VARCHAR,
    description  VARCHAR,
    parent_id    VARCHAR,
    PRIMARY KEY (table_id, dimension_id, group_id)
);

CREATE TABLE IF NOT EXISTS meta.measures (
    table_id    VARCHAR,
    measure_id  VARCHAR,
    idx         INTEGER,
    title       VARCHAR,
    description VARCHAR,
    group_id    VARCHAR,
    unit        VARCHAR,
    decimals    INTEGER,
    data_type   VARCHAR,
    PRIMARY KEY (table_id, measure_id)
);

CREATE TABLE IF NOT EXISTS meta.measure_groups (
    table_id    VARCHAR,
    group_id    VARCHAR,
    idx         INTEGER,
    title       VARCHAR,
    description VARCHAR,
    parent_id   VARCHAR,
    PRIMARY KEY (table_id, group_id)
);

CREATE SEQUENCE IF NOT EXISTS meta.sync_log_seq;
CREATE TABLE IF NOT EXISTS meta.sync_log (
    run_id      BIGINT DEFAULT nextval('meta.sync_log_seq'),
    table_id    VARCHAR,
    started_at  TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    outcome     VARCHAR,   -- loaded / unchanged / failed
    source_api  VARCHAR,
    rows_loaded BIGINT,
    modified    TIMESTAMPTZ,
    message     VARCHAR
);
"""

META_TABLES = (
    "meta.tables",
    "meta.dimensions",
    "meta.dimension_codes",
    "meta.dimension_groups",
    "meta.measures",
    "meta.measure_groups",
)


def raw_table(table_id: str) -> str:
    return f"raw.t{table_id.lower()}"


def core_table(table_id: str) -> str:
    return f"core.t{table_id.lower()}"


class DatabaseLocked(RuntimeError):
    pass


def connect(path: Path, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Open the database. DuckDB allows one writer *or* several readers, never both."""
    if read_only and not path.exists():
        raise FileNotFoundError(f"No database at {path}; run `uv run datchat catalog` first.")
    if not read_only:
        path.parent.mkdir(parents=True, exist_ok=True)
    try:
        con = duckdb.connect(str(path), read_only=read_only)
    except duckdb.IOException as e:
        if "lock" in str(e).lower():
            mode = "read" if read_only else "write to"
            raise DatabaseLocked(
                f"Cannot {mode} {path}: another process holds it"
                f" ({'a sync is running' if read_only else 'e.g. a notebook or another sync'})."
                " Try again when it has finished."
            ) from e
        raise
    if not read_only:
        con.execute(SCHEMA_SQL)
    return con


def now() -> datetime:
    return datetime.now(UTC)


def stored_version(con: duckdb.DuckDBPyConnection, table_id: str) -> str | None:
    row = con.execute("SELECT version FROM meta.tables WHERE table_id = ?", [table_id]).fetchone()
    return row[0] if row else None


def log_sync(
    con: duckdb.DuckDBPyConnection,
    table_id: str,
    started_at: datetime,
    outcome: str,
    source_api: str | None = None,
    rows_loaded: int | None = None,
    modified: str | None = None,
    message: str | None = None,
) -> None:
    con.execute(
        "INSERT INTO meta.sync_log (table_id, started_at, finished_at, outcome, source_api,"
        " rows_loaded, modified, message) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [table_id, started_at, now(), outcome, source_api, rows_loaded, modified, message],
    )


def _df(rows: list[dict], columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=columns)


def load_table(con: duckdb.DuckDBPyConnection, meta: TableMetadata, obs: Observations) -> int:
    """Replace everything we hold for ``meta.table_id`` in one transaction."""
    t = meta.table_id
    p = meta.properties
    dim_ids = meta.dimension_ids

    tables_df = _df(
        [
            {
                "table_id": t,
                "title": p.get("Title"),
                "description": p.get("Description"),
                "long_description": p.get("LongDescription"),
                "temporal_coverage": p.get("TemporalCoverage"),
                "frequency": p.get("Frequency"),
                "status": p.get("Status"),
                "modified": p.get("Modified"),
                "observations_modified": p.get("ObservationsModified"),
                "version": p.get("Version"),
                "observation_count": p.get("ObservationCount"),
                "source_api": obs.source_api,
                "statline_url": f"https://opendata.cbs.nl/#/CBS/nl/dataset/{t}/table",
                "properties_json": json.dumps(p, ensure_ascii=False),
                "synced_at": now(),
            }
        ],
        [
            "table_id",
            "title",
            "description",
            "long_description",
            "temporal_coverage",
            "frequency",
            "status",
            "modified",
            "observations_modified",
            "version",
            "observation_count",
            "source_api",
            "statline_url",
            "properties_json",
            "synced_at",
        ],
    )
    dims_df = _df(
        [
            {
                "table_id": t,
                "dimension_id": d["Identifier"],
                "position": i,
                "title": d.get("Title"),
                "description": d.get("Description"),
                "kind": d.get("Kind"),
            }
            for i, d in enumerate(meta.dimensions)
        ],
        ["table_id", "dimension_id", "position", "title", "description", "kind"],
    )
    codes_df = _df(
        [
            {
                "table_id": t,
                "dimension_id": dim,
                "code": c["Identifier"],
                "idx": c.get("Index"),
                "title": c.get("Title"),
                "description": c.get("Description"),
                "group_id": c.get("DimensionGroupId"),
                "status": c.get("Status"),
            }
            for dim, codes in meta.dimension_codes.items()
            for c in codes
        ],
        ["table_id", "dimension_id", "code", "idx", "title", "description", "group_id", "status"],
    )
    groups_df = _df(
        [
            {
                "table_id": t,
                "dimension_id": dim,
                "group_id": g["Id"],
                "idx": g.get("Index"),
                "title": g.get("Title"),
                "description": g.get("Description"),
                "parent_id": g.get("ParentId"),
            }
            for dim, groups in meta.dimension_groups.items()
            for g in groups
        ],
        ["table_id", "dimension_id", "group_id", "idx", "title", "description", "parent_id"],
    )
    measures_df = _df(
        [
            {
                "table_id": t,
                "measure_id": m["Identifier"],
                "idx": m.get("Index"),
                "title": m.get("Title"),
                "description": m.get("Description"),
                "group_id": m.get("MeasureGroupId"),
                "unit": m.get("Unit"),
                "decimals": m.get("Decimals"),
                "data_type": m.get("DataType"),
            }
            for m in meta.measure_codes
        ],
        [
            "table_id",
            "measure_id",
            "idx",
            "title",
            "description",
            "group_id",
            "unit",
            "decimals",
            "data_type",
        ],
    )
    mgroups_df = _df(
        [
            {
                "table_id": t,
                "group_id": g["Id"],
                "idx": g.get("Index"),
                "title": g.get("Title"),
                "description": g.get("Description"),
                "parent_id": g.get("ParentId"),
            }
            for g in meta.measure_groups
        ],
        ["table_id", "group_id", "idx", "title", "description", "parent_id"],
    )
    obs_df = pd.DataFrame(
        {
            "id": pd.array([r["Id"] for r in obs.rows], dtype="Int64"),
            "measure": [r["Measure"] for r in obs.rows],
            "value_attribute": [r["ValueAttribute"] for r in obs.rows],
            "value": pd.array([r["Value"] for r in obs.rows], dtype="Float64"),
            "string_value": [r["StringValue"] for r in obs.rows],
            **{d: [r[d] for r in obs.rows] for d in dim_ids},
        }
    )
    dim_cols = ", ".join(f'"{d}" VARCHAR' for d in dim_ids)

    con.execute("BEGIN TRANSACTION")
    try:
        for mt in META_TABLES:
            con.execute(f"DELETE FROM {mt} WHERE table_id = ?", [t])
        for mt, df in [
            ("meta.tables", tables_df),
            ("meta.dimensions", dims_df),
            ("meta.dimension_codes", codes_df),
            ("meta.dimension_groups", groups_df),
            ("meta.measures", measures_df),
            ("meta.measure_groups", mgroups_df),
        ]:
            con.register("_df", df)
            con.execute(f"INSERT INTO {mt} BY NAME SELECT * FROM _df")
            con.unregister("_df")

        rt = raw_table(t)
        con.execute(f"DROP TABLE IF EXISTS {rt}")
        con.execute(
            f"CREATE TABLE {rt} (id BIGINT, measure VARCHAR, value_attribute VARCHAR,"
            f" value DOUBLE, string_value VARCHAR, {dim_cols})"
        )
        con.register("_obs", obs_df)
        con.execute(f"INSERT INTO {rt} BY NAME SELECT * FROM _obs")
        con.unregister("_obs")
        _create_labeled_view(con, t, dim_ids)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return len(obs_df)


def _create_labeled_view(con: duckdb.DuckDBPyConnection, table_id: str, dim_ids: list[str]) -> None:
    """``core.t<id>``: every observation with code titles, measure title/unit, period status."""
    selects = ['o."' + d + '"' for d in dim_ids]
    joins = []
    for i, d in enumerate(dim_ids):
        a = f"c{i}"
        selects.append(f'{a}.title AS "{d}_title"')
        if d == "Perioden":
            selects.append(f"{a}.status AS period_status")
            selects.append('TRY_CAST(substr(o."Perioden", 1, 4) AS INTEGER) AS year')
        joins.append(
            f"LEFT JOIN meta.dimension_codes {a} ON {a}.table_id = '{table_id}'"
            f" AND {a}.dimension_id = '{d}' AND {a}.code = o.\"{d}\""
        )
    view = f"""
        CREATE OR REPLACE VIEW {core_table(table_id)} AS
        SELECT {", ".join(selects)},
               o.measure, m.title AS measure_title, m.unit, mg.title AS measure_group,
               o.value, o.value_attribute
        FROM {raw_table(table_id)} o
        {" ".join(joins)}
        LEFT JOIN meta.measures m ON m.table_id = '{table_id}' AND m.measure_id = o.measure
        LEFT JOIN meta.measure_groups mg ON mg.table_id = '{table_id}' AND mg.group_id = m.group_id
    """
    con.execute(view)
