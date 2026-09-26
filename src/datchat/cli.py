"""Command line entry point: ``datchat sync | verify | status``."""

from __future__ import annotations

import argparse
import sys

from datchat import config, store


def _tables(args: argparse.Namespace) -> list[str]:
    ids = [t.upper() for t in args.tables] or list(config.TABLE_IDS)
    unknown = [t for t in ids if t not in config.TABLE_IDS]
    if unknown:
        sys.exit(f"Unknown table(s) {unknown}; configured: {', '.join(config.TABLE_IDS)}")
    return ids


def cmd_sync(args: argparse.Namespace) -> int:
    from datchat.sync import sync

    con = store.connect(config.db_path())
    results = sync(con, _tables(args), force=args.force)
    for r in results:
        extra = f" rows={r.rows} via {r.source_api}" if r.outcome == "loaded" else ""
        note = f"  ({r.message})" if r.message else ""
        print(f"{r.table_id:10} {r.outcome:9}{extra}{note}")
    return 1 if any(r.outcome == "failed" for r in results) else 0


def cmd_verify(args: argparse.Namespace) -> int:
    from datchat.verify import run_checks

    con = store.connect(config.db_path(), read_only=True)
    checks = run_checks(con, _tables(args), cross_check_v3=args.cross_check)
    width = max(len(c.name) for c in checks)
    for c in checks:
        label = "FAIL" if not c.ok else "NOTE" if c.note else "PASS"
        print(f"[{label}] {c.name:{width}}  {c.detail}")
    failed = [c for c in checks if not c.ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    return 1 if failed else 0


def cmd_spotcheck(args: argparse.Namespace) -> int:
    from datchat.spotcheck import spot_values

    con = store.connect(config.db_path(), read_only=True)
    for i, s in enumerate(spot_values(con), 1):
        status = f" ({s['status']})" if s["status"] else ""
        print(f"{i:2}. {s['table_id']}  {s['url']}")
        for label in s["selection"]:
            print(f"      {label}")
        print(f"      {s['measure']}: {s['value']}{status}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    path = config.db_path()
    if not path.exists():
        print(f"No database at {path}; run `datchat sync` first.")
        return 1
    con = store.connect(path, read_only=True)
    rows = con.execute(
        """
        SELECT table_id, title, temporal_coverage, modified::DATE, source_api,
               synced_at::TIMESTAMP(0)
        FROM meta.tables ORDER BY table_id
        """
    ).fetchall()
    print(f"Database: {path}")
    for t, title, coverage, modified, source, synced in rows:
        n = con.execute(f"SELECT count(*) FROM {store.raw_table(t)}").fetchone()[0]
        print(
            f"{t:10} {coverage:>12}  modified {modified}  {n:>6} rows via {source}  synced {synced}"
        )
        print(f"{'':10} {title.strip()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="datchat", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("sync", help="download CBS tables into DuckDB (skips unchanged tables)")
    p.add_argument("tables", nargs="*", help="table ids (default: all configured)")
    p.add_argument("--force", action="store_true", help="reload even if CBS version is unchanged")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("verify", help="check the stored data for completeness and consistency")
    p.add_argument("tables", nargs="*", help="table ids (default: all configured)")
    p.add_argument(
        "--cross-check",
        action="store_true",
        help="also re-download every table via the independent v3 API and compare all values",
    )
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("spotcheck", help="print values to compare by hand on the StatLine site")
    p.set_defaults(func=cmd_spotcheck)

    p = sub.add_parser("status", help="show what is in the database")
    p.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
