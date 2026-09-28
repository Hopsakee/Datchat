"""Hits the real CBS API. Run with: uv run pytest -m live"""

import pytest

from datchat import store, verify
from datchat.sync import sync

pytestmark = pytest.mark.live


def test_small_table_end_to_end(tmp_path):
    con = store.connect(tmp_path / "live.duckdb")
    [r] = sync(con, ["83934NED"])
    assert r.outcome == "loaded", r.message
    checks = verify.run_checks(con, ["83934NED"], cross_check_v3=True)
    assert all(c.ok for c in checks), [c for c in checks if not c.ok]
