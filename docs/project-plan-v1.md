# Dutch Statistics Explorer — Project Plan

Sep 25, 2026 · @Jelle

A personal Claude Code application for exploring Dutch (and later European or global) statistics conversationally, with on-demand dashboards and charts, backed by a locally cached database.

## Goal and scope

Build a personal Claude Code application for exploring statistics, primarily Dutch, with room to expand to European or global data later. The core use case: ask a question in plain language (for example, how does the wealth of the richest 1 percent in the Netherlands compare to the bottom 50 percent, with and without home equity), then dig into the underlying numbers, sources, and time range interactively rather than getting a single number back.

The tool should support two modes side by side: conversational querying through Claude Code, and dashboard or chart generation from those same questions, so a question can turn into a visual you keep exploring.

## Architecture

Claude Code acts as the conversational front end: it interprets questions, queries the local database, and generates Plotly charts and dashboard views on demand rather than maintaining a single fixed dashboard.

### UI framework comparison

| Framework | Strengths | Watch-outs |
| --- | --- | --- |
| Panel (HoloViz) | Built for exploratory, drill-down data analysis with cross-filtering; plotting-library agnostic (works well with Plotly); handles larger, more complex apps; strong fit for digging into numbers interactively | Less polished default look out of the box; slightly steeper learning curve for its more powerful declarative API |
| Streamlit | Fastest to get something running; very easy to share; huge community | Rerun-the-whole-script model makes deep, stateful drill-down interactions clunkier |
| NiceGUI | Ready-made GUI widgets (buttons, sliders, layout) with little code; built on FastAPI; good for admin-panel or form-style apps; easy to self-host and share | More geared to application-style UIs than to exploratory cross-filtered analysis |

**Decision: building this in Panel.** It fits the interactive, drill-down nature of the wealth and inequality questions best, and it's a new tool worth learning hands-on.

## Data sources

**Start with CBS only.** Statistics Netherlands (CBS) publishes wealth, income, and agricultural data (including household wealth by wealth class, and figures like cattle feed or nutrient imports) through its StatLine OData API. The unofficial `cbsodata` Python package wraps this cleanly, and there's also a raw OData v4 API for direct queries. Build and prove the full pipeline (sync, store, query, visualize) against CBS before adding anything else.

**Later sources, once the pattern is proven:**

- Eurostat, for European comparisons
- BRO (Basisregistratie Ondergrond), for soil and groundwater data — geospatial, has its own API
- PDOK, the Dutch national geodata portal — geospatial (OGC APIs, WFS/WMS), likely needed alongside BRO

The geospatial sources (BRO, PDOK) are structurally different from CBS's tabular data (they carry geometry) and larger in volume, so they'll likely need their own handling (possibly PostGIS or a spatial extension) rather than fitting the same simple table pattern as CBS.

## Storage

**Decision: DuckDB.** It's an embedded, in-process analytical (OLAP) database, purpose-built for the kind of group-by and aggregation queries this project needs (e.g. top 1 percent versus bottom 50 percent, filtered by year). No server to manage, and far faster than a row-oriented database for this workload. Its single-writer model is not a concern here, since only a periodic sync job writes while Panel reads.

Runs on the Hetzner server alongside the sync jobs; Panel queries it directly.

## Build phases

1. **Pipeline proof-of-concept with CBS.** Sync job pulling wealth/income tables via `cbsodata` into DuckDB on the Hetzner server; verify the data lands cleanly and matches StatLine.
2. **Conversational querying.** Claude Code reads from DuckDB and answers questions in plain language, including drill-down follow-ups (source table, year range, methodology).
3. **Panel dashboards.** Build interactive, cross-filterable Panel views (e.g. wealth share by group over time, with/without housing equity) driven by the same underlying questions/queries.
4. **Sharing.** Host the Panel app on the Hetzner server so it's reachable beyond just local use.
5. **Expand sources.** Add Eurostat, then BRO/PDOK as separate connectors once the CBS pipeline is stable.

## Open questions

- **Sync schedule:** left open for now — update on demand rather than a fixed schedule, since usage frequency isn't yet known.
- **Spatial storage for BRO/PDOK: DuckDB's spatial extension, not PostGIS.** DuckDB Spatial has geometry types and spatial functions, but is still maturing compared to PostGIS (e.g. no SRID stored on the geometry itself, no geography type). PostGIS fits long-lived, shared, multi-user spatial systems better; DuckDB Spatial fits local, personal analytical work better, which matches this project. Decision: use DuckDB's spatial extension when BRO/PDOK are added, and only move to PostGIS if an actual wall is hit.
- **Database location: confirmed on Hetzner.** The DuckDB file lives on the Hetzner server; both Claude Code and the Panel app query it there.

## Inspiration: agent-skill patterns worth learning from

Two agent skills from [hugobowne/show-us-your-agent-skills](https://github.com/hugobowne/show-us-your-agent-skills) are useful as reference material for how to structure our own approach — not to install or adapt directly, just to learn the patterns and reimplement our own version where it fits:

- **[marimo-pair](https://github.com/hugobowne/show-us-your-agent-skills/tree/main/skills/marimo-pair)** (Apache 2.0) — pattern worth studying: a bash bridge lets the agent execute code directly in a running notebook kernel and see results live, rather than just generating code blindly. Good reference for the interactive, human-in-the-loop drill-down phase ("dig into the numbers") before anything gets formalized into a Panel view — even if we don't use Marimo itself.
- **[high-signal-chart-workflow](https://github.com/hugobowne/show-us-your-agent-skills/tree/main/skills/high-signal-chart-workflow)** (CC BY-NC-ND — personal reference only, do not copy or fork the code) — pattern worth studying: a design checklist plus a verifier loop that keeps regenerating a chart until it meets Tufte-style standards (no default gridlines, direct labels instead of legends, axis titles with units, muted palette with one accent color, dpi=300). Worth adopting as *our own* design checklist for Plotly/Panel charts, written in our own words.

## Cold-start prompt for the Claude Code VM

I'm building a personal data-exploration app: ask questions in plain language about Dutch statistics (CBS StatLine first — household wealth, income, agriculture/nutrient data), and get back both conversational answers and interactive Panel dashboards, drilling into source tables, time ranges, and methodology.

Stack:

- Storage: DuckDB, single file, living on my Hetzner server. No other writers, so no concurrency concerns for now.
- Data source: CBS StatLine via the `cbsodata` Python package (or the raw OData v4 API directly if needed).
- UI: Panel (HoloViz), chosen for its strength in exploratory, cross-filterable drill-down analysis — not Streamlit or NiceGUI. Charts via Plotly.
- Deployment: Panel app hosted on the Hetzner server so I can access and share it.

Build phase 1 first: a sync pipeline that pulls the relevant CBS StatLine tables (household wealth by wealth class, including a split that separates out housing equity) into DuckDB, and verify the data lands cleanly and matches what StatLine shows on its own site. Don't build the Panel UI or add other data sources yet — prove this pipeline end to end first.

Two design patterns to take inspiration from (do not copy, install, or fork any code from these — just read them for how they structure the problem, then write our own version in our own words if a pattern fits):

1. marimo-pair (https://github.com/hugobowne/show-us-your-agent-skills/tree/main/skills/marimo-pair) — the idea of an agent executing code directly in a live kernel and observing results before writing the next step, rather than generating code blind. Relevant for how we do interactive, human-in-the-loop exploration before something gets formalized into the Panel app.
2. high-signal-chart-workflow (https://github.com/hugobowne/show-us-your-agent-skills/tree/main/skills/high-signal-chart-workflow) — the idea of a written design checklist (no default gridlines, direct labels instead of legends, axis titles with units, muted palette with one accent color, dpi=300) paired with a verification step that checks a chart against it. Worth writing our own checklist along these lines for our Plotly/Panel charts.

Start by checking what CBS StatLine tables actually exist for household wealth by percentile/wealth class (I'm especially interested in top 1% vs bottom 50%, and versions with/without housing equity), and propose the sync approach before writing the full pipeline.
