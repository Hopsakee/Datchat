---
name: cbs-question
description: Turn a plain-language question about Dutch statistics into a marimo notebook built only from CBS StatLine data, or say "niet beschikbaar" when CBS has no data for it. Use whenever the user asks a statistical question about the Netherlands (population, wealth, income, land use, economy, agriculture, housing, …) or asks to explore CBS data.
---

# CBS question → marimo notebook

You turn one question into **one marimo notebook** (`notebooks/<slug>.py`) that the user keeps,
re-runs and edits. The only data source is CBS StatLine, via the local DuckDB cache that
`uv run datchat …` manages. **You never invent numbers.** If CBS does not publish what the
question needs, the correct answer is **"niet beschikbaar"**, with the tables you considered and
why each one fell short. An approximation is not an acceptable substitute.

All commands run from the repo root with `uv run`. Nothing else is installed or used.

## Rules

1. **Every number traces to CBS.** Each value shown in a chart, a table or text comes from a
   `nb.sql(...)` result on a synced CBS table, in a cell whose SQL is visible directly above
   the chart. Numbers in prose are rendered from query results with f-strings, never typed in
   by hand. The one exception is an assumption cell labelled `Aanname, niet CBS` (rule 4).
2. **No proxies.** If the question asks for X and CBS publishes only something close to X
   (another group, another year, another area), then X is *niet beschikbaar*. You may show
   the close thing as a separate, clearly named fact, but only if it answers part of the
   question in its own right. Never present it as X.
3. **Partial answers are split explicitly.** Answer the parts CBS covers, and give the parts
   it doesn't cover their own "Niet beschikbaar" section, with the tables considered.
4. **Joining across classifications is only allowed as a visible assumption.** Example:
   land-use categories mapped to SBI sectors. The mapping lives in its own cell titled
   `Aanname, niet CBS`, as plain editable Python data. Every chart that depends on it says so
   in its caption. In marimo the charts re-run automatically when the user edits the mapping.
5. **State provenance and status.** Show the table ids, periods and whether figures are
   *Voorlopig* (`nb.sources([...])`). Mark provisional years in every chart.
6. **CBS codes are table-specific.** Never reuse a measure or dimension code from one table in
   another. Always look the codes up with `datchat describe` for the table at hand.
7. **When blocked** (network, CBS outage, a locked database, a missing tool), stop and tell the
   user what is blocking. Don't work around it.

## Workflow

### 1. Make sure the catalog is there
```bash
uv run datchat status            # catalog loaded? which tables are synced?
uv run datchat catalog           # (re)load the StatLine catalog, ≈6,000 tables; idempotent
```

### 2. Take the question apart
Write down, for yourself, what a complete answer needs:
- **quantities** (e.g. wealth, number of inhabitants, hectares, value added)
- **breakdown** (group, sector, region, age)
- **time** (a point in time, a range, "last 20 years")
- **unit and definition** (e.g. "with/without home equity", "share of bbp")

### 3. Find candidate tables
Search in Dutch; CBS titles are Dutch. Try several phrasings and synonyms:
```bash
uv run datchat search vermogen huishoudens
uv run datchat search bodemgebruik
uv run datchat search bevolking kerncijfers
```
The results show each table's period, whether it is discontinued (`Stopgezet`), and whether
it is already synced. Discontinued tables can still be the right source for older years.

### 4. Inspect candidates before deciding
```bash
uv run datchat sync 83834NED 84476NED       # only the candidates you need
uv run datchat describe 83834NED            # measures, dimensions, codes, period status, methodology
```
For every quantity from step 2, decide which table covers it, and keep a record per table:
*provides / falls short because*. That record goes into the notebook's "Tabelkeuze" cell.
Read the methodology text (`TOELICHTING`) for definitions and breaks in series.

If nothing covers a required quantity, that part is **niet beschikbaar**. Still write the
notebook (step 6), with the explanation and the tables considered, and no chart for that part.

### 5. Probe the data before writing the notebook
Look at real values one step at a time, and decide the next step only after seeing the output:
```bash
uv run datchat query "SELECT year, period_status, KenmerkenVanHuishoudens_title, measure_title, unit, value
                      FROM core.t84476ned WHERE KenmerkenVanHuishoudens = '1050010' ORDER BY year LIMIT 20"
```
`core.t<id>` is the labelled view of each table. It holds every CBS code column, a
`<Dimension>_title` column per dimension, `year` and `period_status` (from `Perioden`), and
`measure`, `measure_title`, `unit`, `value`. Check the things that go wrong in practice:
- the totals and subgroups you expect actually exist
- the units (x 1 000, mln, mld)
- gaps in years
- provisional periods

### Pitfalls found while building the acceptance notebooks
- **Table ids are case-sensitive at CBS** (`37296ned` works, `37296NED` is a 404). `datchat`
  resolves ids through the catalog, but always write them in notebooks exactly as `datchat
  search` shows them.
- **`period_status` can be empty.** Some tables (e.g. 7461bev, 37105) have no period status in
  their metadata. Read "Status van de cijfers" in the toelichting and quote it; don't guess.
- **Empty cells:** `value` is NULL with `value_attribute = 'Impossible'` (CBS symbol ".")
  where a combination can't exist (e.g. married 4-year-olds). Some measures are text
  (`string_value`), not numbers.
- **Not every table has a `Perioden` dimension.** One-year tables (e.g. the wijk- en
  buurtcijfers) are a single period; take the year from `meta.tables.temporal_coverage`.
- **Method breaks.** Search the toelichting for *breuk*, *trendbreuk* and *vergelijkbaar*.
  Across a break, never draw one connected line. Show the series separately and say so.
  Rankings (e.g. "the five largest") can differ on either side of a break.
- **Negative values** (e.g. the wealth of the bottom 50%) need a visible zero line, and titles
  computed from ratios must handle a denominator ≤ 0.
- **Two tables, one number:** before combining tables (e.g. value added from one and bbp from
  another), assert in the notebook that their shared totals are identical.

### 6. Write the notebook
Copy `.claude/skills/cbs-question/template.py` to `notebooks/<slug>.py` and fill it in. The
structure:
1. **Vraag**: the question, verbatim, and a one-paragraph answer rendered from query results
2. **Tabelkeuze**: the per-table record from step 4, including rejected tables
3. **Aanname, niet CBS** (only if needed): the mapping, as editable data
4. Per chart: **a SQL cell** (`df = nb.sql("""…""")`) and directly below it **a chart cell**
   that follows `docs/chart-checklist.md`. Use `charts.direct_labels` for line-end labels
   (it keeps them from overlapping) and end with `charts.checked(fig_…)`
5. **Niet beschikbaar** (if any part isn't covered): what is missing and which tables were
   considered
6. **Bronnen**: `nb.sources([...])`
7. **Controle**: the spot checks from step 8

Notebooks call `nb.require([...])` first, so they fail with a clear message when a table
isn't synced. Each query opens and closes its own read-only connection (`nb.sql`), so an open
notebook never blocks a sync for longer than a query takes.

### 7. The notebook must run headless
```bash
uv run datchat check notebooks/<slug>.py     # marimo export; fails if any cell errors
```
Fix the notebook until this passes. A notebook that fails this check is not done.

Then **look at every chart**. The checker can't see overlap or clipping.
```bash
uv run datchat render notebooks/<slug>.py     # PNGs in data/renders/<slug>/
```
Open the PNGs, then fix overlapping or clipped labels, a hidden zero line, or a title that
doesn't match the data. Charts must be assigned to variables named `fig_…` for `render` to
find them. Rendering needs Chrome. If kaleido can't find it, set `BROWSER_PATH` to a
Chrome or Chromium binary, or run `uv run plotly_get_chrome` once.

### 8. Spot check against CBS and record it
```bash
uv run datchat verify <ids> --cross-check    # every cell vs an independent CBS channel
```
Pick one to three values that the notebook displays. For each, record in the **Controle**
cell: the value, the table, the exact selection (codes and titles), the period status, the
StatLine URL (`https://opendata.cbs.nl/#/CBS/nl/dataset/<id>/table`), the date, and the
cross-check result. Where CBS has published the figure in an article, cite it as well.

### 9. Report back
Tell the user, briefly:
- the answer, or which parts are niet beschikbaar
- the notebook path, and how to open it: `uv run marimo edit notebooks/<slug>.py`
- the tables used and the caveats that matter
