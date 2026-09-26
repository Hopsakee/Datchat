# Datchat

Ask a question about Dutch statistics in your own Claude Code session and get back **one
marimo notebook** built from CBS StatLine data. When CBS doesn't publish what the question
needs, the answer is **"niet beschikbaar"**, with the tables that were considered. Numbers are
never invented. See [docs/project-plan.md](docs/project-plan.md) (plan v2).

## How it works

- **The front end is your Claude Code session.** The project skill
  [`.claude/skills/cbs-question`](.claude/skills/cbs-question/SKILL.md) does the work:
  1. searches the CBS catalog
  2. picks tables and records why
  3. syncs only those tables
  4. probes the data
  5. writes `notebooks/<slug>.py`
  6. runs it headless
  7. spot-checks it against CBS
- **DuckDB is a local file** (`data/datchat.duckdb`, gitignored), next to wherever Claude Code
  runs.
- **There is no LLM or API key inside the app.**

```bash
uv sync
uv run datchat catalog                        # load the StatLine catalog (~6,000 tables)
# then, in Claude Code: "Hoeveel inwoners had Nederland op 1 januari 2024?"
uv run marimo edit notebooks/<slug>.py        # open the notebook it wrote
```

## The `datchat` command

| Command | What it does |
|---|---|
| `catalog` | Load or refresh the StatLine table catalog into `meta.catalog`. It is idempotent. |
| `search TERMS…` | Find tables. Results are ranked with title matches first; accents don't matter. |
| `sync ID…` | Download tables on demand: data, metadata, labels and period status. A table is skipped when its CBS version hasn't changed. |
| `describe ID` | Show a table's measures (with units), dimensions and codes, which periods are final or provisional, and its methodology text. |
| `query SQL` | Run a read-only query, for probing. |
| `verify [ID…] [--cross-check]` | Check row counts, codes and duplicates. `--cross-check` also compares every cell with an independent CBS channel. |
| `check NOTEBOOK…` | Run notebooks headless (`marimo export`). It fails if any cell errors or a chart breaks the checklist. |
| `status` | Show the catalog and the synced tables. |

## Database layout

| Schema | Contents |
|---|---|
| `meta` | `catalog`, `tables` (properties, methodology text), `dimensions`, `dimension_codes` (incl. period status), `dimension_groups`, `measures` (title, unit), `measure_groups`, `sync_log` |
| `raw` | `raw.t<id>`: observations exactly as CBS serves them (long format, CBS codes) |
| `core` | `core.t<id>`: every observation with code titles, `year`, `period_status`, `measure_title`, `unit` |

Question-specific SQL lives in the notebooks, directly above the chart it feeds.

## CBS API choice (plan v2: "verify, don't assume")

We checked this against the live APIs in September 2026:

- **OData v4 (`datasets.cbs.nl`) is the primary source.** It serves observations in long
  format with per-cell flags and a *Definitief*/*Voorlopig* status per period. We need that
  status to mark provisional figures.
- **OData v3 (`opendata.cbs.nl`) is the automatic fallback.** Some discontinued tables expose
  v4 metadata but return 404 on v4 `Observations`; 82960NED is an example. v3 topics are
  mapped to v4 measure codes by `DataProperties.ID == MeasureCodes.Index`, and the sync
  refuses to continue if title or unit disagree. v3 also provides the table catalog.
- **The `cbsodata` package is not used.** It wraps v3 only, returns wide tables and drops the
  period status.

Tested: for 6 wealth tables, every one of 207,999 v4 cells is identical to v3. For 82960NED,
all 14,720 v3 cells are identical to the v4 bulk CSV.

## Concurrency

DuckDB allows one read-write process *or* several read-only processes. Notebooks open a
short-lived read-only connection per query (`datchat.nb.sql`), so they never hold the file.
A sync that finds the file in use says so and stops. It doesn't wait or retry.

## Acceptance questions (plan v2)

| # | Question | Notebook | Status |
|---|---|---|---|
| 1 | Inwoners op 1 januari 2024 (exact) | `notebooks/acceptance/01_…` | pending |
| 2 | Top 1% vs onderste 50%, met/zonder eigen woning | [`02_vermogen_top1_onderste50.py`](notebooks/acceptance/02_vermogen_top1_onderste50.py) | done, runs headless; top 1% excl. woning = niet beschikbaar |
| 3 | 5 grootste bodemgebruiksvormen vs aandeel bbp | `notebooks/acceptance/03_…` | pending |
| 4 | Vermogen top 0,01% per gemeente in 1950 | `notebooks/acceptance/04_…` | pending (expected: niet beschikbaar) |

## Development

```bash
uv run pytest            # offline tests (mocked CBS)
uv run pytest -m live    # real CBS: sync + every notebook headless
uv run ruff check src tests notebooks && uv run ruff format --check src tests notebooks
```

Network: `datasets.cbs.nl` and `opendata.cbs.nl`, plus PyPI for `uv sync`.

## Docs

- [docs/project-plan.md](docs/project-plan.md): plan v2, the current plan
  ([v1](docs/project-plan-v1.md) is kept for history)
- [docs/chart-checklist.md](docs/chart-checklist.md): chart rules, enforced by `datchat.charts`
- [docs/wealth-tables.md](docs/wealth-tables.md): survey of the CBS wealth tables behind question 2
