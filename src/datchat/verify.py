"""Verification: does the database hold exactly what CBS publishes, for any synced table?

1. Completeness & integrity (offline): row counts vs CBS ``ObservationCount``, every code
   resolvable in the metadata, no duplicate cells, every period has a status.
2. Cross-check (online, ``--cross-check``): every cell re-downloaded from an independent CBS
   channel (v3 API for v4-sourced tables, v4 bulk CSV for v3-sourced ones) and compared.

Question-specific checks (sums, identities, published figures) live with the notebook that
answers the question, not here.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from datchat import store
from datchat.cbs import CbsClient, CbsError, TableMetadata

# Documented discrepancies in CBS's own metadata. Shown as NOTE, never silently passed.
KNOWN_COUNT_DISCREPANCIES = {
    "82960NED": (
        14721,
        14720,
        "CBS Properties.ObservationCount says 14721, but both the v4 bulk CSV and the v3 API "
        "contain 14720 observations",
    ),
}


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    note: bool = False  # passed, but with a documented caveat


def _q(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None) -> list[tuple]:
    return con.execute(sql, params or []).fetchall()


def _dims(con: duckdb.DuckDBPyConnection, t: str) -> list[str]:
    return [
        r[0]
        for r in _q(
            con,
            "SELECT dimension_id FROM meta.dimensions WHERE table_id = ? ORDER BY position",
            [t],
        )
    ]


# -- 1. completeness & integrity ------------------------------------------------------------


def check_table_integrity(con: duckdb.DuckDBPyConnection, t: str) -> list[Check]:
    checks: list[Check] = []
    rt = store.raw_table(t)
    meta_row = _q(con, "SELECT observation_count FROM meta.tables WHERE table_id = ?", [t])
    if not meta_row:
        return [Check(f"{t} present", False, "not in database; run `datchat sync`")]
    expected = meta_row[0][0]
    rows = _q(con, f"SELECT count(*) FROM {rt}")[0][0]
    if rows == expected:
        checks.append(Check(f"{t} row count", True, f"{rows} = CBS ObservationCount"))
    elif t in KNOWN_COUNT_DISCREPANCIES and KNOWN_COUNT_DISCREPANCIES[t][:2] == (expected, rows):
        checks.append(Check(f"{t} row count", True, KNOWN_COUNT_DISCREPANCIES[t][2], note=True))
    else:
        checks.append(Check(f"{t} row count", False, f"{rows} rows, CBS says {expected}"))

    dims = _dims(con, t)
    for d in dims:
        missing = _q(
            con,
            f'SELECT DISTINCT o."{d}" FROM {rt} o LEFT JOIN meta.dimension_codes c'
            f' ON c.table_id = ? AND c.dimension_id = ? AND c.code = o."{d}"'
            " WHERE c.code IS NULL LIMIT 5",
            [t, d],
        )
        checks.append(
            Check(
                f"{t} codes {d}",
                not missing,
                "all codes resolve" if not missing else f"unknown codes {missing}",
            )
        )
    missing_m = _q(
        con,
        f"SELECT DISTINCT o.measure FROM {rt} o LEFT JOIN meta.measures m"
        " ON m.table_id = ? AND m.measure_id = o.measure WHERE m.measure_id IS NULL LIMIT 5",
        [t],
    )
    checks.append(
        Check(
            f"{t} measures",
            not missing_m,
            "all measures resolve" if not missing_m else f"unknown {missing_m}",
        )
    )

    key = ", ".join(["measure"] + [f'"{d}"' for d in dims])
    dupes = _q(
        con, f"SELECT count(*) FROM (SELECT {key} FROM {rt} GROUP BY ALL HAVING count(*) > 1)"
    )
    checks.append(Check(f"{t} unique cells", dupes[0][0] == 0, f"{dupes[0][0]} duplicated cells"))

    periods = _q(
        con,
        "SELECT status, count(*), min(code), max(code) FROM meta.dimension_codes"
        " WHERE table_id = ? AND dimension_id = 'Perioden' GROUP BY status ORDER BY 3",
        [t],
    )
    no_status = [p for p in periods if not p[0]]
    summary = ", ".join(f"{p[0] or 'geen status'}: {p[2][:4]}-{p[3][:4]}" for p in periods)
    if no_status:
        summary += (
            " (CBS supplies no period status; read 'Status van de cijfers' in the toelichting)"
        )
    checks.append(Check(f"{t} period status", True, summary, note=bool(no_status)))
    return checks


def _has(con: duckdb.DuckDBPyConnection, t: str) -> bool:
    return bool(_q(con, "SELECT 1 FROM meta.tables WHERE table_id = ?", [t]))


# -- 2. online cross-check ------------------------------------------------------------------


def _stored_metadata(con: duckdb.DuckDBPyConnection, t: str) -> TableMetadata:
    dims = _dims(con, t)
    measures = _q(
        con,
        "SELECT measure_id, idx, title, unit FROM meta.measures WHERE table_id = ? ORDER BY idx",
        [t],
    )
    return TableMetadata(
        table_id=t,
        properties={},
        dimensions=[{"Identifier": d} for d in dims],
        dimension_codes={},
        dimension_groups={},
        measure_codes=[
            {"Identifier": m[0], "Index": m[1], "Title": m[2], "Unit": m[3]} for m in measures
        ],
        measure_groups=[],
    )


def cross_check_table(con: duckdb.DuckDBPyConnection, client: CbsClient, t: str) -> list[Check]:
    source, version = _q(
        con, "SELECT source_api, version FROM meta.tables WHERE table_id = ?", [t]
    )[0]
    checks = []
    live_version = client.properties(t).get("Version")
    checks.append(
        Check(
            f"{t} up to date",
            live_version == version,
            f"stored version {version}, CBS now {live_version}",
        )
    )
    meta = _stored_metadata(con, t)
    dims = meta.dimension_ids
    if source == "v4":
        try:
            other = client.observations_v3(meta)
            other_name = "v3 API"
        except CbsError as e:
            # v3 and v4 can carry different labels (CBS renamed categories in v4 only), so the
            # v3 topics can't be paired safely; the v4 bulk CSV is the other independent channel.
            other = client.observations_v4_csv(t)
            other_name = f"v4 bulk CSV (v3 not comparable: {e})"
    else:
        other_name = "v4 bulk CSV"
        other = client.observations_v4_csv(t)

    # Compare values. Empty cells (e.g. ValueAttribute 'Impossible', CBS symbol '.') are part
    # of v4 but simply absent from v3, so they are compared as "no value" on both sides.
    theirs = {
        (r["Measure"], *(r[d] for d in dims)): r["Value"] for r in other if r["Value"] is not None
    }
    cols = ", ".join(["measure"] + [f'"{d}"' for d in dims] + ["value"])
    rows = _q(con, f"SELECT {cols} FROM {store.raw_table(t)}")
    mine = {tuple(r[:-1]): r[-1] for r in rows if r[-1] is not None}
    empty = len(rows) - len(mine)

    only_mine = mine.keys() - theirs.keys()
    only_theirs = theirs.keys() - mine.keys()
    diffs = [k for k in mine.keys() & theirs.keys() if abs(mine[k] - theirs[k]) >= 1e-9]
    ok = not only_mine and not only_theirs and not diffs
    empty_note = f" (+{empty} cells without a number: 'Impossible' or text)" if empty else ""
    detail = (
        f"{len(mine)} values identical to {other_name}{empty_note}"
        if ok
        else f"vs {other_name}: {len(only_mine)} only ours, {len(only_theirs)} only theirs, "
        f"{len(diffs)} differ (e.g. {(diffs or list(only_mine) or list(only_theirs))[:2]})"
    )
    checks.append(Check(f"{t} cross-check", ok, detail))
    return checks


def run_checks(
    con: duckdb.DuckDBPyConnection, tables: list[str], cross_check_v3: bool = False
) -> list[Check]:
    checks: list[Check] = []
    for t in tables:
        checks += check_table_integrity(con, t)
    if cross_check_v3:
        with CbsClient() as client:
            for t in tables:
                if _has(con, t):
                    checks += cross_check_table(con, client, t)
    return checks
