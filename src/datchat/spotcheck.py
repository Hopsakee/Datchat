"""Values to compare by hand against the StatLine website.

The automated checks compare every cell against CBS's other API channels; this list closes
the last gap: what a person sees on https://opendata.cbs.nl. Each entry names the table, the
selection to make in StatLine, and the value our database holds.
"""

from __future__ import annotations

import duckdb

from datchat import store

# (table, {dimension: code}, measure)
SPOTS: list[tuple[str, dict[str, str], str]] = [
    (
        "84476NED",
        {
            "InkomensEnVermogensbegrippen": "A047664",
            "KenmerkenVanHuishoudens": "1050010",
            "Perioden": "2023JJ00",
        },
        "D006053",
    ),
    (
        "84476NED",
        {
            "InkomensEnVermogensbegrippen": "A047664",
            "KenmerkenVanHuishoudens": "1050010",
            "Perioden": "2023JJ00",
        },
        "D006055",
    ),
    (
        "84476NED",
        {
            "InkomensEnVermogensbegrippen": "A047664",
            "KenmerkenVanHuishoudens": "1050010",
            "Perioden": "2024JJ00",
        },
        "M000960",
    ),
    (
        "83834NED",
        {
            "KenmerkenVanHuishoudens": "1021150",
            "Vermogensbestanddelen": "T001126",
            "Perioden": "2023JJ00",
        },
        "M006782",
    ),
    (
        "83834NED",
        {
            "KenmerkenVanHuishoudens": "1050010",
            "Vermogensbestanddelen": "1021480",
            "Perioden": "2023JJ00",
        },
        "M006782",
    ),
    (
        "83834NED",
        {
            "KenmerkenVanHuishoudens": "1021060",
            "Vermogensbestanddelen": "T001126",
            "Perioden": "2024JJ00",
        },
        "M006767",
    ),
    (
        "83835NED",
        {
            "KenmerkenVanHuishoudens": "1050010",
            "Vermogensklassen": "1021390",
            "Perioden": "2024JJ00",
        },
        "1050010",
    ),
    (
        "83934NED",
        {"Populatie": "1050010", "Percentielen": "A044098", "Perioden": "2024JJ00"},
        "M006083",
    ),
    ("85889NED", {"Huishoudenskenmerken": "A053411", "Perioden": "2023JJ00"}, "M006629_1"),
    ("84104NED", {"Huishoudenskenmerken": "T001139", "Perioden": "2021JJ00"}, "M006629_1"),
    ("82960NED", {"HuishoudensKenmerken": "1000000", "Perioden": "2014JJ00"}, "X088152"),
]


def spot_values(con: duckdb.DuckDBPyConnection) -> list[dict]:
    out = []
    for table_id, selection, measure in SPOTS:
        where = " AND ".join(f'"{d}" = ?' for d in selection)
        row = con.execute(
            f"SELECT value, measure_title, unit, period_status FROM {store.core_table(table_id)}"
            f" WHERE measure = ? AND {where}",
            [measure, *selection.values()],
        ).fetchone()
        labels = []
        for dim, code in selection.items():
            title = con.execute(
                "SELECT title FROM meta.dimension_codes"
                " WHERE table_id = ? AND dimension_id = ? AND code = ?",
                [table_id, dim, code],
            ).fetchone()
            labels.append(f"{dim} = {title[0] if title else code + ' (?)'}")
        out.append(
            {
                "table_id": table_id,
                "url": f"https://opendata.cbs.nl/#/CBS/nl/dataset/{table_id}/table",
                "selection": labels,
                "measure": f"{row[1]} [{row[2]}]" if row else measure,
                "value": row[0] if row else None,
                "status": row[3] if row else None,
            }
        )
    return out
