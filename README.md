# Datchat

A personal explorer for Dutch statistics. You ask questions in plain language, get
conversational answers, and turn them into interactive Panel dashboards. Everything is backed
by a local DuckDB cache of CBS StatLine.

**Status: phase 1, the sync pipeline.** CBS household-wealth tables sync into DuckDB and are
verified against CBS itself. There is no UI yet. See the
[project plan](docs/project-plan.md) for the phases.

## Quick start

```bash
uv sync                          # Python 3.12 + deps (uv downloads Python if needed)
uv run datchat sync              # download all configured CBS tables (≈20 s first time)
uv run datchat verify            # offline checks: completeness, integrity, consistency
uv run datchat verify --cross-check   # + re-download every cell via a second CBS channel
uv run datchat status            # what is in the database
uv run datchat spotcheck         # values to compare by hand on the StatLine website
```

The database lives at `data/datchat.duckdb`. Override the location with `DATCHAT_DB`, for
example `DATCHAT_DB=/srv/datchat/datchat.duckdb` on the server.

`sync` runs on demand and is idempotent. A table is only downloaded again when CBS's
`Version` for it changes; `--force` reloads it anyway. Each table is replaced in a single
transaction, so a failed download keeps the previous data. Every run is recorded in
`meta.sync_log`.

## What gets synced

| Table | Content | Years |
|---|---|---|
| 83834NED | Wealth by 10%-group and component, incl. *Vermogen exclusief eigen woning* | 2006–2024 |
| 84476NED | Inequality (Gini etc.) and total wealth of the top 10% / 1% / 0.1% | 2011–2024 |
| 83835NED | Households by wealth class (euro bands) and 10%-group | 2006–2024 |
| 83934NED | Percentile boundaries of the 10%-groups | 2011–2024 |
| 85889NED | National accounts wealth distribution (incl. pensions), 10%-groups | 2021–2023 |
| 84104NED | National accounts, 20%-groups, housing split out | 2015–2021 |
| 82960NED | National accounts, by household type/income (no wealth groups) | 2005–2014 |

See [docs/data-sources.md](docs/data-sources.md) for what each table can and cannot answer.
It covers the top 1% vs bottom 50% question and the caveat on "excluding housing".

## Database layout

| Schema | Contents |
|---|---|
| `raw` | `raw.t<id>`: observations exactly as CBS serves them (long format, CBS codes) |
| `meta` | `tables` (incl. methodology text), `dimensions`, `dimension_codes` (incl. period status), `dimension_groups`, `measures` (title, unit), `measure_groups`, `sync_log` |
| `core` | `core.t<id>`: labelled view per table · `wealth_by_decile` · `wealth_top_shares` · `wealth_group_shares` (bottom 50% / middle 40% / top 10% / top 1%, incl. and excl. housing) · `wealth_percentile_boundaries` · `nr_wealth_groups` |

```sql
-- Top 1% vs bottom 50%, with and without the owner-occupied home
SELECT year, period_status, basis, wealth_group, round(share * 100, 1) AS pct, note
FROM core.wealth_group_shares
WHERE wealth_group IN ('Onderste 50%', 'Top 1%', 'Top 10%')
ORDER BY year, basis, ord;
```

## Data access

- **OData v4** (`datasets.cbs.nl`) is the primary source. It delivers observations in long
  format with per-cell flags and a *Definitief*/*Voorlopig* status per period.
- **OData v3** (`opendata.cbs.nl`) is the fallback, used for 82960NED. v4 serves that
  table's metadata but its `Observations` endpoint returns 404. The v3 rows are reshaped to
  the v4 format. v3 topics map to v4 measure codes by `DataProperties.ID ==
  MeasureCodes.Index`, and title and unit must match, otherwise the sync fails loudly.
- We don't use the `cbsodata` package. It wraps v3 only, returns wide tables, and drops the
  period status.

## Verification

`datchat verify` answers the question: does the database hold exactly what CBS publishes?

1. **Completeness:** row counts match CBS's `ObservationCount`, every code and measure
   resolves, there are no duplicate cells, and every period has a status.
2. **Consistency:** identities that must hold, within the rounding of the published
   figures. The 10%-groups add up to the total. Bezittingen − schulden = vermogen. Excl.
   eigen woning = vermogen − eigen woning + hypotheekschuld. Wealth classes add up.
   84476NED and 83834NED agree with each other.
3. **Agreement with CBS:**
   - Top shares are recomputed and compared with the figures CBS printed in its
     January 2025 news release (2011–2022, max gap 0.06 pp).
   - `--cross-check` compares every cell (226,719) with an independent CBS channel: the v3
     API, or for 82960NED the v4 bulk CSV.
   - `datchat spotcheck` lists values to compare by eye on the StatLine website.

Known discrepancy: CBS's metadata for 82960NED claims 14,721 observations. The v3 API and
the v4 bulk CSV both contain 14,720. `verify` reports this as a `NOTE`.

## Development

```bash
uv run pytest            # offline tests (mocked CBS)
uv run pytest -m live    # end-to-end against the real CBS API
uv run ruff check src tests && uv run ruff format --check src tests
```

Network: sync needs `datasets.cbs.nl` and `opendata.cbs.nl`, nothing else.

## Deploying to the Hetzner server

```bash
git clone … && cd Datchat
uv sync --no-dev
export DATCHAT_DB=/srv/datchat/datchat.duckdb
uv run datchat sync && uv run datchat verify
```

DuckDB allows one writing process at a time. While a sync runs, other processes cannot open
the file. When the Panel app arrives (phase 3), it should open the database read-only and the
sync should run when the app is idle. Alternatively, the sync can write to a copy and swap
the files atomically.

## Docs

- [docs/project-plan.md](docs/project-plan.md): goals, stack and phases
- [docs/data-sources.md](docs/data-sources.md): CBS table survey, answerable questions, caveats
- [docs/chart-checklist.md](docs/chart-checklist.md): our design checklist for Plotly/Panel charts
- [docs/exploration-workflow.md](docs/exploration-workflow.md): how interactive exploration turns into Panel views
