import pytest

from datchat.cbs import CbsError, v3_wide_to_long
from tests.conftest import OBSERVATIONS, V3_PROPS, V3_WIDE, T


def test_metadata_skips_entity_sets_the_table_lacks(client, fake_cbs):
    meta = client.metadata(T)
    assert meta.dimension_ids == ["Groep", "Perioden"]
    assert meta.measure_groups == []  # no MeasureGroups in the service document
    assert not any(u.endswith("/MeasureGroups") for u in fake_cbs.requests)
    assert meta.dimension_codes["Perioden"][1]["Status"] == "Voorlopig"


def test_v4_observations_follow_next_link(client, fake_cbs):
    fake_cbs.page_size = 3
    obs = client.observations(client.metadata(T))
    assert obs.source_api == "v4"
    assert [r["Id"] for r in obs.rows] == [o["Id"] for o in OBSERVATIONS]


def test_falls_back_to_v3_when_v4_observations_404(client, fake_cbs):
    fake_cbs.v4_observations_404 = True
    obs = client.observations(client.metadata(T))
    assert obs.source_api == "v3"
    assert "404" in obs.notes[0]
    got = {(r["Measure"], r["Groep"], r["Perioden"]): r["Value"] for r in obs.rows}
    want = {(o["Measure"], o["Groep"], o["Perioden"]): o["Value"] for o in OBSERVATIONS}
    assert got == want  # padded keys stripped, null cells dropped, topics mapped to M-codes


def test_v3_mapping_refuses_mismatched_measures(client):
    meta = client.metadata(T)
    props = [dict(p) for p in V3_PROPS]
    props[3]["Unit"] = "mln euro"
    with pytest.raises(CbsError, match="does not match"):
        v3_wide_to_long(meta, props, V3_WIDE)


def test_csv_bundle_parses_decimal_commas(client):
    rows = client.observations_v4_csv(T)
    assert [r["Value"] for r in rows] == [o["Value"] for o in OBSERVATIONS]


def test_v3_text_values_become_string_values(client):
    meta = client.metadata(T)
    wide = [dict(r) for r in V3_WIDE]
    wide[0]["Aantal_1"] = "Nederland   "
    rows = v3_wide_to_long(meta, V3_PROPS, wide)
    text = [r for r in rows if r["StringValue"] is not None]
    assert len(text) == 1 and text[0]["StringValue"] == "Nederland" and text[0]["Value"] is None
