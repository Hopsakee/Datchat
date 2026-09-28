"""Minimal client for the CBS StatLine OData APIs.

Primary source is OData v4 (datasets.cbs.nl): it serves observations in long format and
carries per-cell ``ValueAttribute`` flags and per-period ``Status`` (Definitief/Voorlopig).

Some discontinued tables expose their v4 metadata but 404 on ``Observations``. For those we
fall back to the v3 API (opendata.cbs.nl), fetch the wide ``TypedDataSet`` and reshape it
into the same long, v4-shaped rows. v3 topics are mapped onto v4 measure codes via
``DataProperties.ID == MeasureCodes.Index``; title and unit must agree or we refuse.
"""

from __future__ import annotations

import csv
import io
import time
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx

V4_BASE = "https://datasets.cbs.nl/odata/v1/CBS"
V4_CSV_BASE = "https://datasets.cbs.nl/csv/CBS/nl"
V3_CATALOG_URL = "https://opendata.cbs.nl/ODataCatalog/Tables"
V3_FEED_BASE = "https://opendata.cbs.nl/ODataFeed/odata"
V3_API_BASE = "https://opendata.cbs.nl/ODataApi/odata"

V3_NON_TOPIC_TYPES = {"Dimension", "TimeDimension", "GeoDimension", "GeoDetail", "TopicGroup"}


class CbsError(RuntimeError):
    pass


class ObservationsUnavailable(CbsError):
    """v4 serves metadata for the table but not its observations."""


@dataclass
class TableMetadata:
    table_id: str
    properties: dict[str, Any]
    dimensions: list[dict[str, Any]]
    dimension_codes: dict[str, list[dict[str, Any]]]
    dimension_groups: dict[str, list[dict[str, Any]]]
    measure_codes: list[dict[str, Any]]
    measure_groups: list[dict[str, Any]]

    @property
    def dimension_ids(self) -> list[str]:
        return [d["Identifier"] for d in self.dimensions]


@dataclass
class Observations:
    rows: list[dict[str, Any]]
    source_api: str  # "v4" or "v3"
    notes: list[str] = field(default_factory=list)


class CbsClient:
    def __init__(self, client: httpx.Client | None = None, retries: int = 3):
        self._http = client or httpx.Client(timeout=httpx.Timeout(120.0, connect=15.0))
        self._retries = retries

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> CbsClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- HTTP ---------------------------------------------------------------------------------

    def _get_json(self, url: str, params: dict[str, str] | None = None) -> Any:
        last: Exception | None = None
        for attempt in range(self._retries):
            try:
                resp = self._http.get(url, params=params)
            except httpx.TransportError as e:
                last = e
            else:
                if resp.status_code == 404:
                    raise httpx.HTTPStatusError(
                        "404 Not Found", request=resp.request, response=resp
                    )
                if resp.status_code < 500:
                    resp.raise_for_status()
                    return resp.json()
                last = httpx.HTTPStatusError(
                    f"{resp.status_code} from CBS", request=resp.request, response=resp
                )
            if attempt < self._retries - 1:
                time.sleep(2**attempt)
        raise CbsError(f"GET {url} failed after {self._retries} attempts: {last}") from last

    def _get_paged(self, url: str, params: dict[str, str] | None = None) -> Iterator[dict]:
        """Yield all entities, following ``@odata.nextLink`` (v4) / ``odata.nextLink`` (v3)."""
        next_url: str | None = url
        while next_url:
            page = self._get_json(next_url, params)
            params = None  # nextLink already carries the query
            yield from page["value"]
            next_url = page.get("@odata.nextLink") or page.get("odata.nextLink")

    # -- catalog ------------------------------------------------------------------------------

    def catalog(self) -> list[dict[str, Any]]:
        """All tables in the CBS StatLine catalog (v3 ODataCatalog, incl. discontinued)."""
        return list(self._get_paged(V3_CATALOG_URL, {"$format": "json"}))

    # -- v4 -----------------------------------------------------------------------------------

    def properties(self, table_id: str) -> dict[str, Any]:
        props = self._get_json(f"{V4_BASE}/{table_id}/Properties")
        props.pop("@odata.context", None)
        return props

    def entity_sets(self, table_id: str) -> set[str]:
        """Names in the table's v4 service document (not every table has e.g. MeasureGroups)."""
        return {e["name"] for e in self._get_json(f"{V4_BASE}/{table_id}")["value"]}

    def metadata(self, table_id: str) -> TableMetadata:
        base = f"{V4_BASE}/{table_id}"
        available = self.entity_sets(table_id)
        dimensions = list(self._get_paged(f"{base}/Dimensions"))
        codes: dict[str, list[dict]] = {}
        groups: dict[str, list[dict]] = {}
        for dim in dimensions:
            if dim.get("ContainsCodes", True) and dim.get("CodesUrl"):
                codes[dim["Identifier"]] = list(self._get_paged(dim["CodesUrl"]))
            if dim.get("ContainsGroups") and dim.get("GroupsUrl"):
                groups[dim["Identifier"]] = list(self._get_paged(dim["GroupsUrl"]))
        return TableMetadata(
            table_id=table_id,
            properties=self.properties(table_id),
            dimensions=dimensions,
            dimension_codes=codes,
            dimension_groups=groups,
            measure_codes=list(self._get_paged(f"{base}/MeasureCodes")),
            measure_groups=(
                list(self._get_paged(f"{base}/MeasureGroups"))
                if "MeasureGroups" in available
                else []
            ),
        )

    def observations_v4(self, table_id: str) -> list[dict[str, Any]]:
        try:
            return list(self._get_paged(f"{V4_BASE}/{table_id}/Observations"))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ObservationsUnavailable(
                    f"{table_id}: v4 Observations endpoint returns 404"
                ) from e
            raise

    def observation_count_v4(self, table_id: str) -> int:
        resp = self._http.get(f"{V4_BASE}/{table_id}/Observations/$count")
        resp.raise_for_status()
        return int(resp.text.strip().lstrip("﻿"))

    def observations_v4_csv(self, table_id: str) -> list[dict[str, Any]]:
        """Observations from the v4 bulk download (zip of CSVs); used as a cross-check source."""
        resp = self._http.get(f"{V4_CSV_BASE}/{table_id}")
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            text = zf.read("Observations.csv").decode("utf-8-sig")
        rows = []
        for r in csv.DictReader(io.StringIO(text), delimiter=";"):
            value = r.pop("Value")
            rows.append(
                {
                    **{k: v.strip() for k, v in r.items()},
                    "Id": int(r["Id"]),
                    "Value": float(value.replace(",", ".")) if value not in ("", None) else None,
                    "StringValue": r["StringValue"] or None,
                }
            )
        return rows

    # -- v3 fallback --------------------------------------------------------------------------

    def observations_v3(self, meta: TableMetadata) -> list[dict[str, Any]]:
        t = meta.table_id
        props = list(self._get_paged(f"{V3_API_BASE}/{t}/DataProperties", {"$format": "json"}))
        wide = list(self._get_paged(f"{V3_FEED_BASE}/{t}/TypedDataSet", {"$format": "json"}))
        return v3_wide_to_long(meta, props, wide)

    def observations(self, meta: TableMetadata) -> Observations:
        try:
            return Observations(self.observations_v4(meta.table_id), "v4")
        except ObservationsUnavailable as e:
            rows = self.observations_v3(meta)
            return Observations(rows, "v3", [f"{e}; used v3 TypedDataSet instead"])


def v3_wide_to_long(
    meta: TableMetadata, v3_props: list[dict], wide_rows: list[dict]
) -> list[dict[str, Any]]:
    """Reshape v3 TypedDataSet rows into v4-shaped observation rows.

    v4 omits empty cells while v3 returns them as null, so null cells are dropped to keep
    row counts comparable with ``Properties.ObservationCount``. v3 has no per-cell
    ValueAttribute, so it is left as None for these rows.
    """
    dim_ids = meta.dimension_ids
    v3_dim_keys = [
        p["Key"] for p in v3_props if p["Type"] in ("Dimension", "TimeDimension", "GeoDimension")
    ]
    if sorted(v3_dim_keys) != sorted(dim_ids):
        raise CbsError(f"{meta.table_id}: v3 dimensions {v3_dim_keys} != v4 dimensions {dim_ids}")

    by_index = {m["Index"]: m for m in meta.measure_codes}
    topic_map: dict[str, str] = {}
    for p in v3_props:
        if p["Type"] in V3_NON_TOPIC_TYPES:
            continue
        m = by_index.get(p["ID"])
        if m is None:
            raise CbsError(f"{meta.table_id}: v3 topic {p['Key']} (ID {p['ID']}) has no v4 measure")
        if (p["Title"].strip(), (p.get("Unit") or "").strip()) != (
            m["Title"].strip(),
            (m.get("Unit") or "").strip(),
        ):
            raise CbsError(
                f"{meta.table_id}: v3 topic {p['Key']!r} ({p['Title']}, {p.get('Unit')}) does not "
                f"match v4 measure {m['Identifier']} ({m['Title']}, {m.get('Unit')})"
            )
        topic_map[p["Key"]] = m["Identifier"]
    if len(topic_map) != len(meta.measure_codes):
        raise CbsError(
            f"{meta.table_id}: mapped {len(topic_map)} v3 topics but v4 has "
            f"{len(meta.measure_codes)} measures"
        )

    out: list[dict[str, Any]] = []
    for row in wide_rows:
        dims = {d: str(row[d]).strip() for d in dim_ids}
        for key, measure in topic_map.items():
            value = row.get(key)
            if value is None:
                continue
            is_text = isinstance(value, str)
            out.append(
                {
                    "Id": None,
                    "Measure": measure,
                    "ValueAttribute": None,
                    "Value": None if is_text else float(value),
                    "StringValue": value.strip() if is_text else None,
                    **dims,
                }
            )
    return out
