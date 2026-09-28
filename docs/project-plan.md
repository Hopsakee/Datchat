# Dutch Statistics Explorer — Project Plan v2

Sep 25, 2026 · @Jelle · supersedes v1 (same folder), after a grilling session

## Goal

A Claude Code skill that turns a plain-language question about Dutch statistics into a Marimo notebook built from CBS StatLine data — and says plainly when the data to answer it does not exist. It never invents data.

Example questions it must handle:

- "How does the wealth of the richest 1% in the Netherlands compare to the bottom 50%, with and without home equity?"
- "How has the area of the 5 largest land-use types in the Netherlands developed over the last 20 years, compared to their share of Dutch GDP (bbp)?"

## How it works (decided)

- **The user's own Claude Code session is the conversational front end.** There is no LLM inside the app, and no API key.
- **Each question produces one Marimo notebook** (a plain `.py` file) that the user keeps, re-runs, and edits. Marimo replaces Panel from v1: reactive cells give the drill-down, and the SQL cell that produced each chart sits right above it.
- **DuckDB is local storage**, next to wherever Claude Code runs. It is a file, not a server.
- **Discovery through a catalog.** A sync command loads the StatLine table catalog (IDs, titles, descriptions, periods) into DuckDB. The skill searches the catalog, picks tables, syncs only those, and records why it picked each one.
- **Joins across classifications are allowed only as a visible assumption.** Example: land-use categories mapped to SBI sectors in the national accounts. The mapping lives in its own clearly labelled cell or file ("aanname, niet CBS"), the user can edit it, and the charts update.
- **Writes are rare.** Blocking reads while a sync runs is acceptable, even for an hour. Notebooks open a connection per query rather than holding the file, and a sync that finds the file locked says so.

## Ideal state — what done means

Each criterion names how it is falsified.

1. **No invented numbers.** Every number in a generated notebook traces to a CBS table ID and the query that produced it, or to a labelled assumption cell. *Falsifier:* any displayed value without that trace.
2. **Unanswerable means "niet beschikbaar".** When no CBS table covers the question, the skill says so, lists the tables it considered and why each fell short, and produces no chart. *Falsifier:* a chart or number for acceptance question 4.
3. **The catalog sync works.** One command loads the StatLine catalog into DuckDB, and can re-run it idempotently. *Falsifier:* a second run that duplicates rows or fails.
4. **The table sync works on demand.** Given table IDs, the data, metadata, and dimension labels land in DuckDB. *Falsifier:* a synced table whose row count or a sampled value differs from StatLine.
5. **Notebooks run headless.** Every generated notebook passes `marimo export` (or equivalent) without errors. *Falsifier:* one that fails.
6. **All four acceptance questions below pass**, each with a spot check against StatLine recorded in the repo.

## Acceptance questions

1. **Exact:** "Hoeveel inwoners had Nederland op 1 januari 2024?" — must match StatLine exactly.
2. **Headline:** top 1% vs bottom 50% wealth, with and without home equity, over time. If CBS does not publish this split, the correct outcome is criterion 2, not an approximation.
3. **Two tables plus a mapping:** the five largest land-use types over 20 years vs their sector share of bbp. The land-use-to-sector mapping must appear as an assumption.
4. **Must fail honestly:** "Vermogen van de top 0,01% per gemeente in 1950" → niet beschikbaar.

## Out of scope for this goal

- Publishing or hosting notebooks (Hetzner, Marimo hosting services, anything else).
- Any source besides CBS: Eurostat, BRO, PDOK.
- A fixed dashboard, or an LLM chat inside the app.

## Constraints and known gotchas

- **Python, with `uv` as the only package manager.** A `pyproject.toml` plus a committed `uv.lock`; every command runs as `uv run …`; no `pip`, `requirements.txt`, conda, or poetry. Generated notebooks must run from the project environment with `uv run marimo edit <notebook>.py`. The DuckDB file is gitignored.
- **CBS API version: verify, don't assume.** The unofficial `cbsodata` package targets the older OData v3 API; CBS also has an OData v4 API. Pick whichever actually serves the needed tables, and record why in the repo.
- **DuckDB concurrency:** one read-write process *or* several read-only processes, never both. See "Writes are rare" above.
- The cloud environment needs network access to the CBS API hosts. The agent must confirm that before building on it.

## Roadmap after this goal (the user's call, not the agent's)

1. Use the skill on real questions.
2. When a question fails because the data is missing, that question picks the next source to add.
3. Then decide which frustration is bigger: missing sources, or not being able to publish notebooks. The bigger one goes next.
