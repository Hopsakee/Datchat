# Exploration workflow: from question to Panel view

The pattern we adopt is that Claude works against a **live, stateful session**. It runs a
step, looks at the actual result, and only then decides the next step. The alternative,
writing a whole analysis blind and hoping it runs, is what we want to avoid. The human sees
the same intermediate results and can redirect at any point.

## How this maps onto Datchat

1. **Ask.** A question in plain language, e.g. "hoe verhoudt de top 1% zich tot de onderste
   50%, met en zonder eigen woning?"
2. **Locate.** Claude looks in `meta.tables`, `meta.measures` and `meta.dimension_codes`, and
   in the `core` views, for which table and codes answer it, and reads the methodology text
   (`meta.tables.long_description`) for caveats.
3. **Probe in a live session.** Claude runs small queries against DuckDB, one step at a time,
   and inspects the output before writing the next query: row counts, a few values, the period
   status. It runs read-only against the database file.
4. **Answer with provenance.** The answer names the table ids, years, period status and caveats.
5. **Sketch.** A first chart in the same session, checked against
   [chart-checklist.md](chart-checklist.md).
6. **Formalise.** Once a question and chart prove useful, the query becomes a `core` view or a
   function, with a test, and the chart becomes a Panel view. Only formalised steps go into
   the app.

## Tooling decision (for phase 2)

Open question: which live session to use for step 3. The options are a marimo notebook
running on the server, a Jupyter kernel, or simply a persistent DuckDB/Python REPL that
Claude drives. marimo's reactive cells suit the "human sees every step" goal. A plain REPL
has the fewest moving parts. We'll decide when phase 2 starts.
