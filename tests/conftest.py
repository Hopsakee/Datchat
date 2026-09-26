"""A tiny synthetic CBS table served through httpx.MockTransport (no network)."""

from __future__ import annotations

import io
import json
import zipfile

import httpx
import pytest

from datchat.cbs import V4_BASE, CbsClient

T = "TEST01NED"

DIMENSIONS = [
    {
        "Identifier": "Groep",
        "Title": "Groep",
        "Kind": "Dimension",
        "ContainsGroups": False,
        "ContainsCodes": True,
        "CodesUrl": f"{V4_BASE}/{T}/GroepCodes",
        "GroupsUrl": None,
    },
    {
        "Identifier": "Perioden",
        "Title": "Perioden",
        "Kind": "TimeDimension",
        "ContainsGroups": False,
        "ContainsCodes": True,
        "CodesUrl": f"{V4_BASE}/{T}/PeriodenCodes",
        "GroupsUrl": None,
    },
]
GROEP_CODES = [
    {"Identifier": "T001", "Index": 1, "Title": "Totaal"},
    {"Identifier": "G1", "Index": 2, "Title": "Groep 1"},
]
PERIODEN_CODES = [
    {"Identifier": "2023JJ00", "Index": 1, "Title": "2023", "Status": "Definitief"},
    {"Identifier": "2024JJ00", "Index": 2, "Title": "2024", "Status": "Voorlopig"},
]
MEASURES = [
    {"Identifier": "M1", "Index": 3, "Title": "Aantal", "Unit": "x 1 000", "Decimals": 1},
    {"Identifier": "M2", "Index": 4, "Title": "Bedrag", "Unit": "mld euro", "Decimals": 1},
]


def _obs(i, m, g, p, v):
    return {
        "Id": i,
        "Measure": m,
        "ValueAttribute": "None",
        "Value": v,
        "StringValue": None,
        "Groep": g,
        "Perioden": p,
    }


OBSERVATIONS = [
    _obs(0, "M1", "T001", "2023JJ00", 10.0),
    _obs(1, "M2", "T001", "2023JJ00", 1.5),
    _obs(2, "M1", "G1", "2023JJ00", 4.0),
    _obs(3, "M2", "G1", "2023JJ00", 0.5),
    _obs(4, "M1", "T001", "2024JJ00", 11.0),
    _obs(5, "M2", "T001", "2024JJ00", 1.7),
    _obs(6, "M1", "G1", "2024JJ00", 4.2),
]
PROPERTIES = {
    "Identifier": T,
    "Title": "Testtabel",
    "Version": "202601010000",
    "Modified": "2026-01-01T00:00:00+01:00",
    "ObservationCount": len(OBSERVATIONS),
    "LongDescription": "Toelichting",
}
V3_PROPS = [
    {"ID": 0, "Type": "Dimension", "Key": "Groep", "Title": "Groep"},
    {"ID": 1, "Type": "TimeDimension", "Key": "Perioden", "Title": "Perioden"},
    {"ID": 3, "Type": "Topic", "Key": "Aantal_1", "Title": "Aantal", "Unit": "x 1 000"},
    {"ID": 4, "Type": "Topic", "Key": "Bedrag_2", "Title": "Bedrag", "Unit": "mld euro"},
]
# v3 pads keys and returns empty cells as null (G1/2024 has no Bedrag).
V3_WIDE = [
    {"Groep": "T001  ", "Perioden": "2023JJ00", "Aantal_1": 10.0, "Bedrag_2": 1.5},
    {"Groep": "G1    ", "Perioden": "2023JJ00", "Aantal_1": 4.0, "Bedrag_2": 0.5},
    {"Groep": "T001  ", "Perioden": "2024JJ00", "Aantal_1": 11.0, "Bedrag_2": 1.7},
    {"Groep": "G1    ", "Perioden": "2024JJ00", "Aantal_1": 4.2, "Bedrag_2": None},
]


def _csv_zip() -> bytes:
    lines = ["Id;Measure;Groep;Perioden;Value;StringValue;ValueAttribute"]
    for o in OBSERVATIONS:
        value = str(o["Value"]).replace(".", ",")
        lines.append(f"{o['Id']};{o['Measure']};{o['Groep']};{o['Perioden']};{value};;None")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Observations.csv", "﻿" + "\n".join(lines))
    return buf.getvalue()


class FakeCbs:
    """Routes requests; flags let tests simulate CBS quirks."""

    def __init__(self):
        self.v4_observations_404 = False
        self.v3_broken = False
        self.page_size: int | None = None
        self.properties = dict(PROPERTIES)
        self.requests: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        path = request.url.path
        self.requests.append(url)
        v4 = f"/odata/v1/CBS/{T}"
        routes = {
            v4: {
                "value": [
                    {"name": n}
                    for n in (
                        "MeasureCodes",
                        "Dimensions",
                        "GroepCodes",
                        "PeriodenCodes",
                        "Observations",
                        "Properties",
                    )
                ]
            },
            f"{v4}/Properties": self.properties,
            f"{v4}/Dimensions": {"value": DIMENSIONS},
            f"{v4}/GroepCodes": {"value": GROEP_CODES},
            f"{v4}/PeriodenCodes": {"value": PERIODEN_CODES},
            f"{v4}/MeasureCodes": {"value": MEASURES},
            f"/ODataApi/odata/{T}/DataProperties": {"value": V3_PROPS},
            f"/ODataFeed/odata/{T}/TypedDataSet": {"value": V3_WIDE},
        }
        if self.v3_broken and "/ODataFeed/" in path:
            return httpx.Response(500)
        if path == f"{v4}/Observations":
            if self.v4_observations_404:
                return httpx.Response(404)
            skip = int(request.url.params.get("$skip", 0))
            size = self.page_size or len(OBSERVATIONS)
            page = {"value": OBSERVATIONS[skip : skip + size]}
            if skip + size < len(OBSERVATIONS):
                page["@odata.nextLink"] = f"{V4_BASE}/{T}/Observations?$skip={skip + size}"
            return httpx.Response(200, json=page)
        if path == f"/csv/CBS/nl/{T}":
            return httpx.Response(200, content=_csv_zip())
        if path in routes:
            return httpx.Response(200, content=json.dumps(routes[path]))
        return httpx.Response(404)


@pytest.fixture
def fake_cbs() -> FakeCbs:
    return FakeCbs()


@pytest.fixture
def client(fake_cbs: FakeCbs) -> CbsClient:
    return CbsClient(httpx.Client(transport=httpx.MockTransport(fake_cbs.handler)), retries=1)
