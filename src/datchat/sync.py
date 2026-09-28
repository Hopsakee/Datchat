"""On-demand, idempotent sync of CBS tables into DuckDB."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from datchat import store
from datchat.cbs import CbsClient


@dataclass
class SyncResult:
    table_id: str
    outcome: str  # loaded / unchanged / failed
    rows: int | None = None
    source_api: str | None = None
    message: str | None = None


def sync_table(
    con: duckdb.DuckDBPyConnection, client: CbsClient, table_id: str, force: bool = False
) -> SyncResult:
    started = store.now()
    try:
        props = client.properties(table_id)
        if not force and store.stored_version(con, table_id) == props.get("Version"):
            store.log_sync(con, table_id, started, "unchanged", modified=props.get("Modified"))
            return SyncResult(table_id, "unchanged", message=f"version {props.get('Version')}")
        meta = client.metadata(table_id)
        obs = client.observations(meta)
        rows = store.load_table(con, meta, obs)
        message = "; ".join(obs.notes) or None
        store.log_sync(
            con,
            table_id,
            started,
            "loaded",
            obs.source_api,
            rows,
            meta.properties.get("Modified"),
            message,
        )
        return SyncResult(table_id, "loaded", rows, obs.source_api, message)
    except Exception as e:  # logged and reported; other tables still sync
        store.log_sync(con, table_id, started, "failed", message=f"{type(e).__name__}: {e}")
        return SyncResult(table_id, "failed", message=f"{type(e).__name__}: {e}")


def sync(
    con: duckdb.DuckDBPyConnection,
    table_ids: list[str],
    force: bool = False,
    client: CbsClient | None = None,
) -> list[SyncResult]:
    own_client = client is None
    client = client or CbsClient()
    try:
        results = [sync_table(con, client, t, force) for t in table_ids]
    finally:
        if own_client:
            client.close()
    return results
