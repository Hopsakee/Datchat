"""Verification: does the database hold exactly what CBS publishes?

Three layers:

1. Completeness & integrity (offline): row counts vs CBS ``ObservationCount``, every code
   resolvable in the metadata, no duplicate cells, every period has a status.
2. Internal consistency (offline): identities CBS's figures must satisfy, within the rounding
   of the published numbers (e.g. 10%-groups add up to the total; bezittingen - schulden =
   vermogen; 'excl. eigen woning' = vermogen - eigen woning + hypotheekschuld).
3. External agreement:
   - offline: shares recomputed from our data vs figures CBS printed in its own publication;
   - online (``--cross-check``): every cell re-downloaded from an independent CBS channel
     (v3 API for v4-sourced tables, v4 bulk CSV for the v3-sourced one) and compared.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import duckdb

from datchat import store
from datchat.cbs import CbsClient, TableMetadata
from datchat.reference import PUBLISHED_TOP_SHARES

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
    checks.append(
        Check(
            f"{t} period status",
            not no_status,
            ", ".join(f"{p[0]}: {p[2][:4]}-{p[3][:4]}" for p in periods),
        )
    )
    return checks


# -- 2. internal consistency ----------------------------------------------------------------


def _max_gap(con: duckdb.DuckDBPyConnection, sql: str) -> tuple[float, int]:
    gap, n = _q(con, f"SELECT coalesce(max(abs(gap)), 0), count(*) FROM ({sql})")[0]
    return float(gap), int(n)


def _identity(con: duckdb.DuckDBPyConnection, name: str, sql: str, tol: float, what: str) -> Check:
    gap, n = _max_gap(con, sql)
    return Check(
        name, n > 0 and gap <= tol, f"{what}: max gap {gap:.3g} over {n} rows (tol {tol:.3g})"
    )


# Tolerance for a sum of n published figures, each rounded to one decimal, compared with a
# separately rounded total: (n + 1) * 0.05.
def _tol(n_terms: int, decimals: int = 1) -> float:
    return (n_terms + 1) * 0.5 * 10**-decimals + 1e-9


def consistency_83834(con: duckdb.DuckDBPyConnection) -> list[Check]:
    wide = """
        (PIVOT (SELECT year, Vermogensbestanddelen AS c, value FROM core.t83834ned
                WHERE KenmerkenVanHuishoudens = '1050010' AND measure = 'M006782')
         ON c USING first(value))
    """
    deciles = """
        SELECT d.year, d.component_code, t.measure,
               CASE t.measure WHEN '1050010' THEN d.hh ELSE d.tot END - t.value AS gap
        FROM (SELECT year, component_code, sum(households_k) hh, sum(total_bn_eur) tot
              FROM core.wealth_by_decile GROUP BY ALL) d
        JOIN core.t83834ned t ON t.year = d.year AND t.Vermogensbestanddelen = d.component_code
         AND t.KenmerkenVanHuishoudens = '1050010' AND t.measure IN ('1050010', 'M006782')
    """
    return [
        _identity(
            con,
            "83834NED deciles sum to total",
            deciles,
            _tol(10),
            "sum of 10%-groups vs all households (households, total wealth)",
        ),
        _identity(
            con,
            "83834NED vermogen = bezit - schuld",
            f'SELECT "T001126" - ("1021410" - "1021460") AS gap FROM {wide}',
            _tol(2),
            "Vermogen vs Bezittingen - Schulden",
        ),
        _identity(
            con,
            "83834NED bezittingen components",
            'SELECT "1021410" - ("1021420" + "1021430" + "1021450" + "1021424" + "1021440")'
            f" AS gap FROM {wide}",
            _tol(5),
            "Bezittingen vs sum of 1.1-1.5",
        ),
        _identity(
            con,
            "83834NED schulden components",
            f'SELECT "1021460" - ("1021461" + "1021426" + "1021462") AS gap FROM {wide}',
            _tol(3),
            "Schulden vs sum of 2.1-2.3",
        ),
        _identity(
            con,
            "83834NED excl. eigen woning",
            f'SELECT "1021480" - ("T001126" - "1021431" + "1021461") AS gap FROM {wide}',
            _tol(3),
            "Vermogen excl. eigen woning vs Vermogen - Eigen woning + Hypotheek",
        ),
    ]


def consistency_83835(con: duckdb.DuckDBPyConnection) -> list[Check]:
    sql = """
        SELECT c.year, c.s - t.value AS gap
        FROM (SELECT year, sum(value) s FROM core.t83835ned
              WHERE KenmerkenVanHuishoudens = '1050010' AND measure = '1050010'
                AND Vermogensklassen_title LIKE 'Vermogen%euro%' GROUP BY year) c
        JOIN core.t83835ned t ON t.year = c.year AND t.KenmerkenVanHuishoudens = '1050010'
         AND t.measure = '1050010' AND t.Vermogensklassen = 'T001125'
    """
    return [
        _identity(
            con,
            "83835NED wealth classes sum to total",
            sql,
            _tol(12),
            "households over 12 euro classes vs total",
        )
    ]


def consistency_84476(con: duckdb.DuckDBPyConnection) -> list[Check]:
    ordered = _q(
        con,
        """
        SELECT count(*) FILTER (WHERE NOT (top01_bn_eur <= top1_bn_eur
                                           AND top1_bn_eur <= top10_bn_eur
                                           AND top10_bn_eur <= total_bn_eur)), count(*)
        FROM core.wealth_top_shares""",
    )[0]
    checks = [
        Check(
            "84476NED top 0.1% <= 1% <= 10% <= total",
            ordered[0] == 0 and ordered[1] > 0,
            f"{ordered[0]} violations over {ordered[1]} years",
        )
    ]
    if _has(con, "83834NED"):
        # Not a pure rounding identity: top-10% amounts in 84476NED are whole billions from
        # 2018 on and deviate up to ~0.1% from the 10e 10%-groep in 83834NED.
        rel = """
            SELECT (s.top10_bn_eur - d.total_bn_eur) / d.total_bn_eur AS gap
            FROM core.wealth_top_shares s JOIN core.wealth_by_decile d
              ON d.year = s.year AND d.decile = 10 AND d.component_code = 'T001126'
        """
        tot = """
            SELECT s.total_bn_eur - t.value AS gap FROM core.wealth_top_shares s
            JOIN core.t83834ned t ON t.year = s.year AND t.KenmerkenVanHuishoudens = '1050010'
             AND t.Vermogensbestanddelen = 'T001126' AND t.measure = 'M006782'
        """
        checks += [
            _identity(
                con,
                "84476NED total = 83834NED total",
                tot,
                _tol(1),
                "total household wealth in both tables",
            ),
            _identity(
                con,
                "84476NED top 10% ~ 83834NED 10e groep",
                rel,
                0.001,
                "relative gap, top 10% vs 10e 10%-groep",
            ),
        ]
    return checks


def consistency_83934(con: duckdb.DuckDBPyConnection) -> list[Check]:
    bad = _q(
        con,
        """
        SELECT count(*) FROM (
            SELECT boundary_k_eur < lag(boundary_k_eur) OVER
                   (PARTITION BY year, population ORDER BY percentile) AS dec
            FROM core.wealth_percentile_boundaries) WHERE dec""",
    )[0][0]
    return [Check("83934NED percentiles increase", bad == 0, f"{bad} decreasing steps")]


def consistency_nr(con: duckdb.DuckDBPyConnection) -> list[Check]:
    sql = """
        SELECT g.s - t.value AS gap
        FROM (SELECT source_table, year, sum(vermogenssaldo_mln_eur) s
              FROM core.nr_wealth_groups GROUP BY ALL) g
        JOIN (SELECT year, '84104NED' AS st, value FROM core.t84104ned
              WHERE Huishoudenskenmerken = 'T001139' AND measure = 'M006629_1'
              UNION ALL
              SELECT year, '85889NED', value FROM core.t85889ned
              WHERE Huishoudenskenmerken = 'T001139' AND measure = 'M006629_1') t
          ON t.year = g.year AND t.st = g.source_table
    """
    return [
        _identity(
            con,
            "NR wealth groups sum to total",
            sql,
            _tol(10, decimals=0),
            "Vermogenssaldo (mln euro) over groups vs Totaal, 84104NED + 85889NED",
        )
    ]


def check_published_shares(con: duckdb.DuckDBPyConnection) -> list[Check]:
    ref = PUBLISHED_TOP_SHARES
    ours = {
        r[0]: r[1:]
        for r in _q(
            con, "SELECT year, top10_share, top1_share, top01_share FROM core.wealth_top_shares"
        )
    }
    worst, where, n = 0.0, "", 0
    for year, published in ref["values"].items():
        if year not in ours:
            continue
        for label, pub, mine in zip(
            ("top10", "top1", "top0.1"), published, ours[year], strict=True
        ):
            gap = abs(mine * 100 - pub)
            n += 1
            if gap > worst:
                worst, where = gap, f"{year} {label}: ours {mine * 100:.2f}% vs published {pub}%"
    tol = ref["tolerance_pp"]
    return [
        Check(
            "84476NED shares vs CBS publication",
            n > 0 and worst <= tol,
            f"{n} values, max gap {worst:.2f} pp (tol {tol}; {where}) - {ref['source']}",
        )
    ]


def _has(con: duckdb.DuckDBPyConnection, t: str) -> bool:
    return bool(_q(con, "SELECT 1 FROM meta.tables WHERE table_id = ?", [t]))


CONSISTENCY: list[tuple[tuple[str, ...], Callable[[duckdb.DuckDBPyConnection], list[Check]]]] = [
    (("83834NED",), consistency_83834),
    (("83835NED",), consistency_83835),
    (("84476NED",), consistency_84476),
    (("84476NED",), check_published_shares),
    (("83934NED",), consistency_83934),
    (("84104NED", "85889NED"), consistency_nr),
]


# -- 3. online cross-check ------------------------------------------------------------------


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
        other_name = "v3 API"
        other = client.observations_v3(meta)
    else:
        other_name = "v4 bulk CSV"
        other = client.observations_v4_csv(t)

    theirs = {(r["Measure"], *(r[d] for d in dims)): r["Value"] for r in other}
    cols = ", ".join(["measure"] + [f'"{d}"' for d in dims] + ["value"])
    mine = {tuple(r[:-1]): r[-1] for r in _q(con, f"SELECT {cols} FROM {store.raw_table(t)}")}

    only_mine = mine.keys() - theirs.keys()
    only_theirs = theirs.keys() - mine.keys()
    diffs = [
        k
        for k in mine.keys() & theirs.keys()
        if not (
            mine[k] == theirs[k]
            or (mine[k] is not None and theirs[k] is not None and abs(mine[k] - theirs[k]) < 1e-9)
        )
    ]
    ok = not only_mine and not only_theirs and not diffs
    detail = (
        f"{len(mine)} cells identical to {other_name}"
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
    for required, fn in CONSISTENCY:
        if set(required) <= set(tables) and all(_has(con, t) for t in required):
            checks += fn(con)
    if cross_check_v3:
        with CbsClient() as client:
            for t in tables:
                if _has(con, t):
                    checks += cross_check_table(con, client, t)
    return checks
