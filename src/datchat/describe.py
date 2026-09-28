"""Human- and Claude-readable description of a synced table: what it can answer."""

from __future__ import annotations

import duckdb

from datchat import store


def describe(con: duckdb.DuckDBPyConnection, table_id: str, max_codes: int = 40) -> str:
    t = store.canonical_id(con, table_id)
    meta = con.execute(
        "SELECT title, temporal_coverage, status, frequency, modified::DATE, source_api,"
        " long_description FROM meta.tables WHERE table_id = ?",
        [t],
    ).fetchone()
    if meta is None:
        return f"{t} is not synced; run `uv run datchat sync {t}`."
    title, coverage, status, frequency, modified, source, long_desc = meta
    out = [
        f"{t}: {title.strip()}",
        f"  periode {coverage} · {frequency} · status {status} · gewijzigd {modified}"
        f" · via {source}",
        f"  labelled view: {store.core_table(t)}   raw: {store.raw_table(t)}",
        "",
        "MEASURES (column `measure`; `measure_title`, `unit` in the core view)",
    ]
    for mid, mtitle, unit, group in con.execute(
        """
        SELECT m.measure_id, m.title, m.unit, g.title FROM meta.measures m
        LEFT JOIN meta.measure_groups g ON g.table_id = m.table_id AND g.group_id = m.group_id
        WHERE m.table_id = ? ORDER BY m.idx
        """,
        [t],
    ).fetchall():
        prefix = f"{group} / " if group else ""
        out.append(f"  {mid:<14} {prefix}{mtitle.strip()} [{unit}]")

    for dim, _dtitle, kind in con.execute(
        "SELECT dimension_id, title, kind FROM meta.dimensions WHERE table_id = ?"
        " ORDER BY position",
        [t],
    ).fetchall():
        codes = con.execute(
            "SELECT code, title, status FROM meta.dimension_codes"
            " WHERE table_id = ? AND dimension_id = ? ORDER BY idx",
            [t, dim],
        ).fetchall()
        out += ["", f'DIMENSION "{dim}" ({kind}, {len(codes)} codes; `{dim}_title` in core view)']
        if dim == "Perioden":
            by_status: dict[str, list[str]] = {}
            for _, ptitle, pstatus in codes:
                by_status.setdefault(pstatus or "?", []).append(ptitle)
            for pstatus, titles in by_status.items():
                out.append(f"  {pstatus}: {titles[0]} .. {titles[-1]} ({len(titles)})")
            continue
        for code, ctitle, _ in codes[:max_codes]:
            out.append(f"  {code:<12} {ctitle}")
        if len(codes) > max_codes:
            out.append(f"  … {len(codes) - max_codes} more (use --all)")

    if long_desc:
        out += ["", "TOELICHTING (first 1500 chars; full text in meta.tables.long_description)"]
        out.append("  " + long_desc.strip()[:1500].replace("\n", "\n  "))
    return "\n".join(out)
