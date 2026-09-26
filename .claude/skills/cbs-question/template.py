# Template for a CBS question notebook. Copy to notebooks/<slug>.py and replace every TODO.
# Structure and rules: .claude/skills/cbs-question/SKILL.md

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import plotly.graph_objects as go

    from datchat import charts, nb

    TABLES = ["TODO_TABLE_ID"]  # every CBS table this notebook reads
    nb.require(TABLES)
    return TABLES, charts, go, mo, nb


@app.cell
def _(mo):
    mo.md(
        r"""
        # TODO: title (the finding, not the topic)

        **Vraag:** TODO: the question, verbatim.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Tabelkeuze

        | Tabel | Levert | Gebruikt? | Waarom |
        |---|---|---|---|
        | TODO_TABLE_ID | TODO | ja | TODO |
        | TODO_REJECTED_ID | TODO | nee | TODO: why it falls short |
        """
    )
    return


@app.cell
def _(nb):
    # SQL for the chart below. Every number shown comes from a query like this.
    df = nb.sql(
        """
        SELECT year, period_status, value
        FROM core.tTODO
        WHERE measure = 'TODO'
        ORDER BY year
        """
    )
    df
    return (df,)


@app.cell
def _(TABLES, charts, df, go):
    _c = charts.colors(1)
    fig = go.Figure(
        go.Scatter(
            x=df["year"], y=df["value"], name="TODO", mode="lines+markers", line={"color": _c[0]}
        )
    )
    charts.style(
        fig,
        title="TODO: the finding",
        x_title="Jaar (1 januari)",
        y_title="TODO (unit)",
        tables=TABLES,
    )
    charts.label_ends(fig)
    charts.checked(fig)
    return


@app.cell
def _(df, mo):
    # Answer text: numbers are interpolated from query results, never typed.
    _last = df.iloc[-1]
    mo.md(
        f"**Antwoord:** TODO {_last['value']:,.1f} in {int(_last['year'])} ({_last['period_status']})."
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Niet beschikbaar

        TODO (delete this cell if everything is answered): what CBS doesn't publish, and the
        tables considered.
        """
    )
    return


@app.cell
def _(TABLES, mo, nb):
    mo.vstack([mo.md("## Bronnen"), nb.sources(TABLES)])
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Controle

        | Waarde | Tabel en selectie | Status | StatLine | Gecontroleerd |
        |---|---|---|---|---|
        | TODO | TODO | TODO | https://opendata.cbs.nl/#/CBS/nl/dataset/TODO/table | TODO: date, `datchat verify --cross-check` result |
        """
    )
    return


if __name__ == "__main__":
    app.run()
