"""datchat: CBS StatLine cache for question-driven marimo notebooks.

catalog            load/refresh the StatLine table catalog
search TERMS       find tables in the catalog
sync ID...         download tables (data, metadata, labels)
describe ID        what a synced table contains
query SQL          run a read-only query
verify [ID...]     check synced tables against CBS
check NOTEBOOK...   run notebooks headless (marimo export); fails if any cell errors
status             what is in the database
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from datchat import config, store


def _synced(con) -> list[str]:
    return [r[0] for r in con.execute("SELECT table_id FROM meta.tables ORDER BY 1").fetchall()]


def _print_df(df: pd.DataFrame, max_rows: int) -> None:
    with pd.option_context(
        "display.max_rows",
        max_rows,
        "display.max_columns",
        None,
        "display.width",
        200,
        "display.max_colwidth",
        80,
    ):
        print(df.to_string(index=False, max_rows=max_rows))
    if len(df) > max_rows:
        print(f"… {len(df)} rows total")


def cmd_catalog(args: argparse.Namespace) -> int:
    from datchat.catalog import sync_catalog

    con = store.connect(config.db_path())
    n = sync_catalog(con)
    stopped = con.execute(
        "SELECT count(*) FROM meta.catalog WHERE frequency = 'Stopgezet'"
    ).fetchone()[0]
    print(f"Catalog: {n} tables ({n - stopped} active, {stopped} discontinued)")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    from datchat.catalog import search

    con = store.connect(config.db_path(), read_only=True)
    df = search(con, " ".join(args.terms), limit=args.limit)
    if df.empty:
        print("No matching tables.")
        return 1
    _print_df(df, args.limit)
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    from datchat.sync import sync

    con = store.connect(config.db_path())
    ids = [store.canonical_id(con, t) for t in args.tables] or _synced(con)
    if not ids:
        sys.exit("Nothing to sync: give table ids (find them with `datchat search`).")
    results = sync(con, ids, force=args.force)
    for r in results:
        extra = f" rows={r.rows} via {r.source_api}" if r.outcome == "loaded" else ""
        note = f"  ({r.message})" if r.message else ""
        print(f"{r.table_id:10} {r.outcome:9}{extra}{note}")
    return 1 if any(r.outcome == "failed" for r in results) else 0


def cmd_describe(args: argparse.Namespace) -> int:
    from datchat.describe import describe

    con = store.connect(config.db_path(), read_only=True)
    print(describe(con, args.table, max_codes=10_000 if args.all else 40))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    con = store.connect(config.db_path(), read_only=True)
    _print_df(con.execute(args.sql).df(), args.max_rows)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    from datchat.verify import run_checks

    con = store.connect(config.db_path(), read_only=True)
    ids = [store.canonical_id(con, t) for t in args.tables] or _synced(con)
    checks = run_checks(con, ids, cross_check_v3=args.cross_check)
    width = max(len(c.name) for c in checks)
    for c in checks:
        label = "FAIL" if not c.ok else "NOTE" if c.note else "PASS"
        print(f"[{label}] {c.name:{width}}  {c.detail}")
    failed = [c for c in checks if not c.ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    return 1 if failed else 0


def cmd_check(args: argparse.Namespace) -> int:
    import subprocess
    import tempfile
    from pathlib import Path

    failed = []
    with tempfile.TemporaryDirectory() as tmp:
        for nb in args.notebooks:
            out = Path(tmp) / (Path(nb).stem + ".html")
            proc = subprocess.run(
                [sys.executable, "-m", "marimo", "export", "html", nb, "-o", str(out)],
                capture_output=True,
                text=True,
            )
            ok = proc.returncode == 0
            print(f"[{'PASS' if ok else 'FAIL'}] {nb}")
            if not ok:
                failed.append(nb)
                print("  " + (proc.stdout + proc.stderr).strip()[-2000:].replace("\n", "\n  "))
    return 1 if failed else 0


def cmd_render(args: argparse.Namespace) -> int:
    import importlib.util
    from pathlib import Path

    nb_path = Path(args.notebook)
    out_dir = Path(args.out or f"data/renders/{nb_path.stem}")
    out_dir.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location(nb_path.stem, nb_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _, defs = module.app.run()
    figs = {k: v for k, v in defs.items() if k.startswith("fig_")}
    if not figs:
        print("No variables named fig_* in the notebook.")
        return 1
    for name, fig in figs.items():
        path = out_dir / f"{name}.png"
        fig.write_image(path, width=1100, height=640)
        print(path)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    path = config.db_path()
    con = store.connect(path, read_only=True)
    print(f"Database: {path}")
    has_catalog = con.execute(
        "SELECT count(*) FROM information_schema.tables"
        " WHERE table_schema = 'meta' AND table_name = 'catalog'"
    ).fetchone()[0]
    if has_catalog:
        n, loaded = con.execute(
            "SELECT count(*), max(loaded_at)::TIMESTAMP(0) FROM meta.catalog"
        ).fetchone()
        print(f"Catalog: {n} tables, loaded {loaded}")
    else:
        print("Catalog: not loaded (run `datchat catalog`)")
    rows = con.execute(
        "SELECT table_id, title, temporal_coverage, source_api,"
        " synced_at::TIMESTAMP(0) FROM meta.tables ORDER BY table_id"
    ).fetchall()
    print(f"Synced tables: {len(rows)}")
    for t, title, coverage, source, synced in rows:
        n = con.execute(f"SELECT count(*) FROM {store.raw_table(t)}").fetchone()[0]
        print(
            f"  {t:10} {coverage:>14}  {n:>7} rows via {source}  synced {synced}  {title.strip()}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="datchat", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("catalog", help="load/refresh the StatLine table catalog")
    p.set_defaults(func=cmd_catalog)

    p = sub.add_parser("search", help="find tables in the catalog")
    p.add_argument("terms", nargs="+")
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("sync", help="download tables (skips tables whose CBS version is unchanged)")
    p.add_argument("tables", nargs="*", help="table ids (default: re-check all synced tables)")
    p.add_argument("--force", action="store_true", help="reload even if CBS version is unchanged")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("describe", help="measures, dimensions, codes and periods of a table")
    p.add_argument("table")
    p.add_argument("--all", action="store_true", help="list every dimension code")
    p.set_defaults(func=cmd_describe)

    p = sub.add_parser("query", help="run a read-only SQL query")
    p.add_argument("sql")
    p.add_argument("--max-rows", type=int, default=60)
    p.set_defaults(func=cmd_query)

    p = sub.add_parser("verify", help="check synced tables for completeness (and against CBS)")
    p.add_argument("tables", nargs="*", help="table ids (default: all synced)")
    p.add_argument(
        "--cross-check",
        action="store_true",
        help="re-download every cell via an independent CBS channel and compare",
    )
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("check", help="run notebooks headless; fails if any cell errors")
    p.add_argument("notebooks", nargs="+")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("render", help="write the notebook's charts (fig_*) to PNG files")
    p.add_argument("notebook")
    p.add_argument("--out", help="output directory (default: data/renders/<notebook>)")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("status", help="what is in the database")
    p.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (store.DatabaseLocked, FileNotFoundError) as e:
        print(e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
