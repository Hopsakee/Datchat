"""Curated analysis views in the ``core`` schema.

Codes are CBS v4 identifiers and are only meaningful *within* one table: the same measure
code can mean different things in different tables, so every view is pinned to one table.

Methodological caveat carried into the views as ``note``: the 10%-groups in 83834NED are
ranked on total wealth *including* the owner-occupied home. "Excl. eigen woning" figures
per group are therefore the non-housing wealth of households ranked on total wealth, not a
re-ranking on non-housing wealth.
"""

from __future__ import annotations

import duckdb

# 83834NED / 83835NED
HOUSEHOLDS = "1050010"  # measure: Particuliere huishoudens (x 1 000); also the "all" category
TOTAL_WEALTH = "M006782"  # Totaal vermogen (mld euro)
MEAN_WEALTH = "M006767"  # Gemiddeld vermogen (1 000 euro)
MEDIAN_WEALTH = "M000939"  # Mediaan vermogen (1 000 euro)
COMPONENT_TOTAL = "T001126"  # Vermogen
COMPONENT_EXCL_HOME = "1021480"  # Vermogen exclusief eigen woning

EXCL_HOME_NOTE = (
    "10%-groepen gerangschikt op totaal vermogen incl. eigen woning; "
    "excl.-woning-bedragen zijn niet opnieuw gerangschikt"
)

VIEWS: dict[str, tuple[tuple[str, ...], str]] = {
    # name: (required tables, SQL)
    "core.wealth_by_decile": (
        ("83834NED",),
        f"""
        SELECT o.year, o.period_status,
               CAST(regexp_extract(o.KenmerkenVanHuishoudens_title, '(\\d+)e 10%-groep', 1)
                    AS INTEGER) AS decile,
               o.Vermogensbestanddelen AS component_code,
               o.Vermogensbestanddelen_title AS component,
               max(o.value) FILTER (WHERE o.measure = '{HOUSEHOLDS}') AS households_k,
               max(o.value) FILTER (WHERE o.measure = '{TOTAL_WEALTH}') AS total_bn_eur,
               max(o.value) FILTER (WHERE o.measure = '{MEAN_WEALTH}') AS mean_k_eur,
               max(o.value) FILTER (WHERE o.measure = '{MEDIAN_WEALTH}') AS median_k_eur,
               '83834NED' AS source_table
        FROM core.t83834ned o
        WHERE o.KenmerkenVanHuishoudens_title LIKE 'Vermogen: %e 10\\%-groep' ESCAPE '\\'
        GROUP BY ALL
        """,
    ),
    "core.wealth_top_shares": (
        ("84476NED",),
        """
        SELECT year, period_status,
               max(value) FILTER (WHERE measure = '1050010') AS households_k,
               max(value) FILTER (WHERE measure = 'D006053') AS total_bn_eur,
               max(value) FILTER (WHERE measure = 'D006056') AS top10_bn_eur,
               max(value) FILTER (WHERE measure = 'D006055') AS top1_bn_eur,
               max(value) FILTER (WHERE measure = 'D006054') AS top01_bn_eur,
               top10_bn_eur / total_bn_eur AS top10_share,
               top1_bn_eur / total_bn_eur AS top1_share,
               top01_bn_eur / total_bn_eur AS top01_share,
               max(value) FILTER (WHERE measure = 'M000960') AS gini,
               max(value) FILTER (WHERE measure = 'M003229') AS mean_k_eur,
               max(value) FILTER (WHERE measure = 'D005607') AS median_k_eur,
               '84476NED' AS source_table
        FROM core.t84476ned
        WHERE InkomensEnVermogensbegrippen = 'A047664'   -- Vermogen
          AND KenmerkenVanHuishoudens = '1050010'        -- Particuliere huishoudens
        GROUP BY year, period_status
        """,
    ),
    "core.wealth_group_shares": (
        ("83834NED", "84476NED"),
        f"""
        WITH d AS (
            SELECT * FROM core.wealth_by_decile
            WHERE component_code IN ('{COMPONENT_TOTAL}', '{COMPONENT_EXCL_HOME}')
        ),
        totals AS (
            SELECT year, Vermogensbestanddelen AS component_code, value AS total_bn_eur
            FROM core.t83834ned
            WHERE KenmerkenVanHuishoudens = '{HOUSEHOLDS}' AND measure = '{TOTAL_WEALTH}'
              AND Vermogensbestanddelen IN ('{COMPONENT_TOTAL}', '{COMPONENT_EXCL_HOME}')
        ),
        groups AS (
            SELECT year, period_status, component_code, 'Onderste 50%' AS wealth_group, 1 AS ord,
                   sum(total_bn_eur) AS total_bn_eur, count(*) AS n_deciles
            FROM d WHERE decile <= 5 GROUP BY ALL
            UNION ALL
            SELECT year, period_status, component_code, 'Middelste 40%', 2,
                   sum(total_bn_eur), count(*)
            FROM d WHERE decile BETWEEN 6 AND 9 GROUP BY ALL
            UNION ALL
            SELECT year, period_status, component_code, 'Top 10%', 3, sum(total_bn_eur), count(*)
            FROM d WHERE decile = 10 GROUP BY ALL
        )
        SELECT g.year, g.period_status,
               CASE g.component_code WHEN '{COMPONENT_TOTAL}' THEN 'incl. eigen woning'
                    ELSE 'excl. eigen woning' END AS basis,
               g.wealth_group, g.ord, g.total_bn_eur,
               g.total_bn_eur / t.total_bn_eur AS share,
               '83834NED' AS source_table,
               CASE WHEN g.component_code = '{COMPONENT_EXCL_HOME}' THEN '{EXCL_HOME_NOTE}'
               END AS note
        FROM groups g JOIN totals t USING (year, component_code)
        UNION ALL
        SELECT year, period_status, 'incl. eigen woning', 'Top 1%', 4, top1_bn_eur, top1_share,
               '84476NED', 'Top 1% excl. eigen woning wordt door CBS niet gepubliceerd'
        FROM core.wealth_top_shares
        """,
    ),
    "core.wealth_percentile_boundaries": (
        ("83934NED",),
        """
        SELECT year, period_status, Populatie_title AS population,
               CAST(regexp_extract(Percentielen_title, '(\\d+)e percentiel', 1) AS INTEGER)
                   AS percentile,
               value AS boundary_k_eur, '83934NED' AS source_table
        FROM core.t83934ned
        WHERE measure = 'M006083'   -- Percentiel vermogen
        """,
    ),
    "core.nr_wealth_groups": (
        ("84104NED", "85889NED"),
        """
        -- National accounts (incl. pension entitlements). 84104NED has 20%-groups (2015-2021),
        -- 85889NED has 10%-groups (2021-2023); both publish 2021, kept apart by source_table.
        SELECT year, period_status, source_table, group_size, wealth_group_rank,
               Huishoudenskenmerken_title AS wealth_group, vermogenssaldo_mln_eur,
               vermogenssaldo_mln_eur / sum(vermogenssaldo_mln_eur)
                   OVER (PARTITION BY source_table, year) AS share
        FROM (
            SELECT year, period_status, '84104NED' AS source_table, '20%' AS group_size,
                   CAST(regexp_extract(Huishoudenskenmerken_title, '(\\d+)e 20%-groep', 1)
                        AS INTEGER) AS wealth_group_rank,
                   Huishoudenskenmerken_title, value AS vermogenssaldo_mln_eur
            FROM core.t84104ned
            WHERE measure = 'M006629_1'
              AND Huishoudenskenmerken_title LIKE 'Vermogenssaldo %e 20\\%-groep' ESCAPE '\\'
            UNION ALL
            SELECT year, period_status, '85889NED', '10%',
                   CAST(regexp_extract(Huishoudenskenmerken_title, '(\\d+)e 10%-groep', 1)
                        AS INTEGER),
                   Huishoudenskenmerken_title, value
            FROM core.t85889ned
            WHERE measure = 'M006629_1'
              AND Huishoudenskenmerken_title LIKE 'Vermogenssaldo %e 10\\%-groep' ESCAPE '\\'
        )
        """,
    ),
}


def _tables_present(con: duckdb.DuckDBPyConnection) -> set[str]:
    return {r[0] for r in con.execute("SELECT table_id FROM meta.tables").fetchall()}


def create_views(con: duckdb.DuckDBPyConnection) -> list[str]:
    present = _tables_present(con)
    created = []
    for name, (required, sql) in VIEWS.items():
        if set(required) <= present:
            con.execute(f"CREATE OR REPLACE VIEW {name} AS {sql}")
            created.append(name)
    return created
