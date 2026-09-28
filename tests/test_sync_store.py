from datchat import store, verify
from datchat.sync import sync
from tests.conftest import OBSERVATIONS, T


def _con(tmp_path):
    return store.connect(tmp_path / "t.duckdb")


def test_sync_loads_and_labels(tmp_path, client):
    con = _con(tmp_path)
    [r] = sync(con, [T], client=client)
    assert (r.outcome, r.rows, r.source_api) == ("loaded", len(OBSERVATIONS), "v4")
    row = con.execute(
        "SELECT Groep_title, year, period_status, measure_title, unit, value FROM core.ttest01ned"
        " WHERE Groep = 'G1' AND Perioden = '2024JJ00'"
    ).fetchone()
    assert row == ("Groep 1", 2024, "Voorlopig", "Aantal", "x 1 000", 4.2)
    assert con.execute("SELECT long_description FROM meta.tables").fetchone()[0] == "Toelichting"


def test_second_sync_is_skipped_until_cbs_version_changes(tmp_path, client, fake_cbs):
    con = _con(tmp_path)
    sync(con, [T], client=client)
    assert sync(con, [T], client=client)[0].outcome == "unchanged"
    fake_cbs.properties["Version"] = "202602010000"
    assert sync(con, [T], client=client)[0].outcome == "loaded"
    assert con.execute(f"SELECT count(*) FROM {store.raw_table(T)}").fetchone()[0] == len(
        OBSERVATIONS
    )
    outcomes = [
        r[0] for r in con.execute("SELECT outcome FROM meta.sync_log ORDER BY run_id").fetchall()
    ]
    assert outcomes == ["loaded", "unchanged", "loaded"]


def test_failed_sync_is_logged_and_keeps_old_data(tmp_path, client, fake_cbs):
    con = _con(tmp_path)
    sync(con, [T], client=client)
    fake_cbs.properties["Version"] = "new"
    fake_cbs.properties["ObservationCount"] = 999
    fake_cbs.v4_observations_404 = True
    fake_cbs.v3_broken = True
    [r] = sync(con, [T], client=client)
    assert r.outcome == "failed"
    assert con.execute(f"SELECT count(*) FROM {store.raw_table(T)}").fetchone()[0] == len(
        OBSERVATIONS
    )


def test_integrity_checks_pass_and_catch_count_mismatch(tmp_path, client):
    con = _con(tmp_path)
    sync(con, [T], client=client)
    assert all(c.ok for c in verify.check_table_integrity(con, T))
    con.execute("UPDATE meta.tables SET observation_count = 99")
    [count] = [c for c in verify.check_table_integrity(con, T) if c.name.endswith("row count")]
    assert not count.ok


def test_cross_check_detects_changed_value(tmp_path, client):
    con = _con(tmp_path)
    sync(con, [T], client=client)
    [_, cross] = verify.cross_check_table(con, client, T)
    assert cross.ok, cross.detail
    con.execute(f"UPDATE {store.raw_table(T)} SET value = 99 WHERE id = 0")
    [_, cross] = verify.cross_check_table(con, client, T)
    assert not cross.ok and "1 differ" in cross.detail


def test_cross_check_treats_impossible_cells_as_no_value(tmp_path, client, fake_cbs):
    import tests.conftest as c

    extra = c._obs(99, "M2", "G1", "2024JJ00", None)
    extra["ValueAttribute"] = "Impossible"  # v4 lists it; v3 has null and drops it
    c.OBSERVATIONS.append(extra)
    fake_cbs.properties["ObservationCount"] = len(c.OBSERVATIONS)
    try:
        con = _con(tmp_path)
        sync(con, [T], client=client)
        [_, cross] = verify.cross_check_table(con, client, T)
        assert cross.ok, cross.detail
        assert "+1 cells without a number" in cross.detail
    finally:
        c.OBSERVATIONS.remove(extra)
