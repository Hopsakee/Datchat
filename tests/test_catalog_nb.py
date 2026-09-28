import subprocess
import sys

import plotly.graph_objects as go
import pytest

from datchat import catalog, charts, nb, store
from datchat.sync import sync
from tests.conftest import CATALOG, T


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "t.duckdb"
    monkeypatch.setenv("DATCHAT_DB", str(path))
    return path


def test_catalog_sync_is_idempotent(db, client, fake_cbs):
    con = store.connect(db)
    assert catalog.sync_catalog(con, client) == len(CATALOG)
    fake_cbs.catalog.append(dict(CATALOG[0]))  # CBS listing the same table twice
    assert catalog.sync_catalog(con, client) == len(CATALOG)
    assert con.execute("SELECT count(*) FROM meta.catalog").fetchone()[0] == len(CATALOG)


def test_search_ranks_title_matches_and_ignores_accents(db, client):
    con = store.connect(db)
    catalog.sync_catalog(con, client)
    hits = catalog.search(con, "Bévolking")
    assert hits["table_id"].tolist()[0] == "37296ned"
    hits = catalog.search(con, "eigen woning vermogen")
    assert hits["table_id"].tolist() == ["83834NED"]
    assert catalog.search(con, "bodemgebruik")["frequency"].tolist() == ["Stopgezet"]


def test_nb_reads_with_short_lived_read_only_connections(db, client):
    con = store.connect(db)
    sync(con, [T], client=client)
    con.close()
    df = nb.sql(f"SELECT count(*) AS n FROM {store.raw_table(T)}")
    assert df["n"][0] > 0
    # nb.sql released the file: a writer can open it right away
    store.connect(db).close()
    nb.require([T])
    with pytest.raises(RuntimeError, match="uv run datchat sync 99999NED"):
        nb.require([T, "99999NED"])
    src = nb.sources([T])
    assert src["voorlopig"][0] == "2024"


def test_clear_message_when_another_process_holds_the_file(db):
    store.connect(db).close()
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            f"import duckdb, sys, time; c = duckdb.connect({str(db)!r}); print('ok', flush=True);"
            " sys.stdin.read()",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout.readline().strip() == "ok"
        with pytest.raises(store.DatabaseLocked, match="another process holds it"):
            store.connect(db)
        with pytest.raises(store.DatabaseLocked, match="a sync is running"):
            store.connect(db, read_only=True)
    finally:
        holder.stdin.close()
        holder.wait(timeout=10)


def test_chart_checker():
    bare = go.Figure(go.Scatter(x=[1, 2], y=[3, 4], name="a"))
    assert {"title_missing", "source_caption_missing", "default_colours"} <= set(
        charts.check_figure(bare)
    )
    c = charts.colors(2)
    fig = go.Figure(
        [
            go.Scatter(x=[1, 2], y=[3, 4], name="a", line={"color": c[0]}),
            go.Scatter(x=[1, 2], y=[1, 2], name="b", line={"color": c[1]}),
        ]
    )
    charts.style(fig, title="t", x_title="Jaar", y_title="Aandeel (%)", tables=["X"])
    charts.label_ends(fig)
    assert charts.check_figure(fig) == []
    fig.update_yaxes(title_text="Aandeel")
    with pytest.raises(charts.ChartCheckError, match="yaxis_unit_missing"):
        charts.checked(fig)


def test_table_ids_resolve_to_cbs_spelling(db, client):
    con = store.connect(db)
    assert store.canonical_id(con, "37296NED") == "37296NED"  # unknown: passed through
    catalog.sync_catalog(con, client)
    assert store.canonical_id(con, "37296NED") == "37296ned"  # v4 ids are case-sensitive
    assert store.canonical_id(con, " 83834ned ") == "83834NED"
