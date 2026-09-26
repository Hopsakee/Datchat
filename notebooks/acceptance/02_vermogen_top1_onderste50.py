import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import plotly.graph_objects as go

    from datchat import charts, nb

    TABLES = ["84476NED", "83834NED"]
    nb.require(TABLES)
    return TABLES, charts, go, mo, nb


@app.cell
def _(mo):
    mo.md(
        r"""
        # Vermogen: top 1% tegenover de onderste 50%, met en zonder eigen woning

        **Vraag:** How does the wealth of the richest 1% in the Netherlands compare to the
        bottom 50%, with and without home equity?
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
        | 84476NED Ongelijkheid in inkomen en vermogen | Totaal vermogen van alle huishoudens en van de top 10%, 1% en 0,1% (mld euro), 2011– | ja | Enige tabel met de **top 1%**. Alleen vermogen **incl.** eigen woning. |
        | 83834NED Vermogen; vermogensbestanddelen | Vermogen per 10%-groep, uitgesplitst naar bestanddeel, incl. *Vermogen exclusief eigen woning*, 2006– | ja | Onderste 50% = 10%-groepen 1–5, met en zonder eigen woning. Geen groep kleiner dan 10%. |
        | 83835NED Vermogen; vermogensklassen | Aantal huishoudens per vermogensklasse (euro-banden) | nee | Klassen in euro's, geen top 1%. |
        | 83934NED Grenzen 10%-groepen | Grensbedragen van de 10%-groepen | nee | Alleen grenzen, geen totalen per groep. |
        | 85889NED / 84104NED / 82960NED Vermogensverdeling; nationale rekeningen | Vermogenssaldo incl. pensioenaanspraken per 10%- of 20%-groep | nee | Ander vermogensbegrip (incl. pensioenen); geen top 1%. Niet te mengen met de tabellen hierboven. |
        """
    )
    return


@app.cell
def _(nb):
    # Top 1% (84476NED) and bottom 50% (sum of 10%-groups 1-5, 83834NED), incl. eigen woning.
    # Shares are of total household wealth in the same table.
    incl = nb.sql(
        """
        WITH top AS (
            SELECT year, period_status,
                   max(value) FILTER (WHERE measure = 'D006055') AS top1_mld,
                   max(value) FILTER (WHERE measure = 'D006053') AS totaal_mld
            FROM core.t84476ned
            WHERE InkomensEnVermogensbegrippen = 'A047664'   -- Vermogen
              AND KenmerkenVanHuishoudens = '1050010'        -- Particuliere huishoudens
            GROUP BY ALL
        ),
        bottom AS (
            SELECT d.year, d.period_status, sum(d.value) AS onderste50_mld, t.value AS totaal_mld
            FROM core.t83834ned d
            JOIN core.t83834ned t
              ON t.year = d.year AND t.measure = d.measure
             AND t.Vermogensbestanddelen = d.Vermogensbestanddelen
             AND t.KenmerkenVanHuishoudens = '1050010'
            WHERE d.measure = 'M006782'                        -- Totaal vermogen (mld euro)
              AND d.Vermogensbestanddelen = 'T001126'          -- Vermogen
              AND d.KenmerkenVanHuishoudens IN
                  ('1021060', '1021070', '1021080', '1021090', '1021100')  -- 1e..5e 10%-groep
            GROUP BY d.year, d.period_status, t.value
        )
        SELECT coalesce(b.year, t.year) AS year,
               coalesce(b.period_status, t.period_status) AS period_status,
               100 * t.top1_mld / t.totaal_mld AS top1_pct,
               100 * b.onderste50_mld / b.totaal_mld AS onderste50_pct,
               t.top1_mld, b.onderste50_mld
        FROM bottom b FULL JOIN top t ON t.year = b.year
        ORDER BY year
        """
    )
    incl
    return (incl,)


@app.cell
def _(TABLES, charts, go, incl):
    def _series(df, col, name, color):
        final = df[df["period_status"] != "Voorlopig"]
        prov = df[df["period_status"] == "Voorlopig"]
        traces = [
            go.Scatter(
                x=final["year"],
                y=final[col],
                name=name,
                mode="lines",
                line={"color": color, "width": 2.5},
            )
        ]
        if len(prov):
            last = final.tail(1)
            traces.append(
                go.Scatter(
                    x=list(last["year"]) + list(prov["year"]),
                    y=list(last[col]) + list(prov[col]),
                    name=name + " (voorlopig)",
                    mode="lines+markers",
                    line={"color": color, "width": 2.5, "dash": charts.PROVISIONAL_DASH},
                    showlegend=False,
                )
            )
        return traces

    _c = charts.colors(2, accent=0)
    _d = incl.dropna(subset=["top1_pct"])
    fig_incl = go.Figure(
        _series(_d, "top1_pct", "Top 1%", _c[0])
        + _series(_d, "onderste50_pct", "Onderste 50%", _c[1])
    )
    _def = _d[_d["period_status"] == "Definitief"].iloc[-1]
    if _def["onderste50_pct"] > 0:
        _title = (
            f"In {int(_def['year'])} bezat de top 1% "
            f"{_def['top1_pct'] / _def['onderste50_pct']:.0f} keer zoveel als de hele onderste 50%"
        )
    else:
        _title = f"In {int(_def['year'])} had de onderste 50% per saldo meer schulden dan bezit"
    charts.style(
        fig_incl,
        title=_title,
        x_title="Jaar (stand op 1 januari)",
        y_title="Aandeel in totaal vermogen (%)",
        tables=TABLES,
        note="Vermogen incl. eigen woning. Stippellijn = voorlopige cijfers",
    )
    # Bottom 50% was negative (more debt than assets) in 2010-2019: keep zero visible.
    fig_incl.update_yaxes(zeroline=True, zerolinecolor="#999", zerolinewidth=1)
    # Label each series once, at its last point.
    for _name, _col, _color in [
        ("Top 1%", "top1_pct", _c[0]),
        ("Onderste 50%", "onderste50_pct", _c[1]),
    ]:
        _last = _d.iloc[-1]
        fig_incl.add_annotation(
            x=_last["year"],
            y=_last[_col],
            text=_name,
            xanchor="left",
            xshift=8,
            showarrow=False,
            font={"color": _color, "size": 12},
        )
    charts.checked(fig_incl)
    return (fig_incl,)


@app.cell
def _(nb):
    # With and without eigen woning, by 10%-group totals (83834NED).
    # Groups are ranked on total wealth INCLUDING the home in both columns.
    beide = nb.sql(
        """
        WITH g AS (
            SELECT year, period_status, Vermogensbestanddelen_title AS begrip,
                   sum(value) FILTER (WHERE KenmerkenVanHuishoudens IN
                       ('1021060', '1021070', '1021080', '1021090', '1021100')) AS onderste50_mld,
                   max(value) FILTER (WHERE KenmerkenVanHuishoudens = '1050010') AS totaal_mld
            FROM core.t83834ned
            WHERE measure = 'M006782'
              AND Vermogensbestanddelen IN ('T001126', '1021480')
            GROUP BY ALL
        )
        SELECT year, period_status, begrip, onderste50_mld, totaal_mld,
               100 * onderste50_mld / totaal_mld AS onderste50_pct
        FROM g ORDER BY year, begrip
        """
    )
    beide
    return (beide,)


@app.cell
def _(beide, incl, mo):
    _final = incl[(incl["period_status"] == "Definitief") & incl["top1_pct"].notna()].iloc[-1]
    _y = int(_final["year"])
    _b = beide[beide["year"] == _y].set_index("begrip")
    _neg_years = incl.loc[incl["onderste50_pct"] < 0, "year"].astype(int).tolist()
    _neg = (
        f"In {_neg_years[0]}–{_neg_years[-1]} had de onderste 50% samen een **negatief** vermogen "
        f"(meer schulden dan bezittingen); het laagste punt was {incl['onderste50_mld'].min():,.1f} mld euro "
        f"in {int(incl.loc[incl['onderste50_mld'].idxmin(), 'year'])}."
        if _neg_years
        else ""
    )
    mo.md(
        f"""
        **Antwoord (1 januari {_y}, definitieve cijfers):** de rijkste 1% van de huishoudens
        bezat **{_final["top1_pct"]:.1f}%** van het totale vermogen ({_final["top1_mld"]:,.1f} mld euro),
        de onderste 50% samen **{_final["onderste50_pct"]:.1f}%** ({_final["onderste50_mld"]:,.1f} mld euro).

        **Zonder eigen woning** had de onderste 50% {_b.loc["Vermogen exclusief eigen woning", "onderste50_mld"]:,.1f} mld euro,
        {_b.loc["Vermogen exclusief eigen woning", "onderste50_pct"]:.1f}% van al het vermogen exclusief eigen woning.
        Het aandeel van de **top 1% zonder eigen woning publiceert CBS niet** (zie *Niet beschikbaar*).

        {_neg}
        """
    )
    return


@app.cell
def _(beide, mo):
    _tbl = beide.pivot(
        index=["year", "period_status"], columns="begrip", values="onderste50_pct"
    ).reset_index()
    mo.vstack(
        [
            mo.md("### Onderste 50%: aandeel met en zonder eigen woning (%)"),
            _tbl.round(1),
            mo.md(
                "*Let op:* de 10%-groepen zijn in beide kolommen gerangschikt op totaal vermogen "
                "**inclusief** eigen woning. 'Zonder eigen woning' is dus het overige vermogen van "
                "diezelfde huishoudens; zij worden niet opnieuw gerangschikt."
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Niet beschikbaar

        **Top 1% zonder eigen woning.** CBS publiceert het vermogen van de top 1% alleen
        inclusief eigen woning (84476NED). De tabel met *Vermogen exclusief eigen woning*
        (83834NED) kent geen groep kleiner dan 10%. De vergelijking top 1% tegenover onderste
        50% **zonder** eigen woning is daarom niet te maken uit CBS StatLine. Er is bewust
        geen benadering (zoals de top 10%) gebruikt.

        Overwogen en afgewezen: 83835NED (euro-klassen), 83934NED (alleen grenzen) en de
        nationale-rekeningentabellen 85889NED/84104NED/82960NED (ander vermogensbegrip, geen top 1%).
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
        | Totaal bedrag top 1% 2023 = 681,4 mld euro | 84476NED · Vermogen · Particuliere huishoudens · 2023 · *Totaal bedrag top 1%* | Definitief | https://opendata.cbs.nl/#/CBS/nl/dataset/84476NED/table | 2026-09-26: `datchat verify 84476NED --cross-check`, alle 18.453 cellen gelijk aan v3-API |
        | Totaal vermogen 2023 = 2.713,8 mld euro | 84476NED · idem · *Totaal bedrag* | Definitief | idem | idem |
        | Aandeel top 1% 2011–2022 | berekend uit 84476NED | Definitief | — | Vergeleken met CBS-nieuwsbericht 15-1-2025 ("56 procent vermogen in handen van 10 procent huishoudens"): max. verschil 0,06 procentpunt (CBS rekent met onafgeronde bedragen) |
        | Vermogen excl. eigen woning, alle huishoudens 2023 = 1.364,1 mld euro | 83834NED · Particuliere huishoudens · Vermogen exclusief eigen woning · 2023 · *Totaal vermogen* | Definitief | https://opendata.cbs.nl/#/CBS/nl/dataset/83834NED/table | 2026-09-26: `datchat verify 83834NED --cross-check`, alle 86.085 cellen gelijk aan v3-API |
        """
    )
    return


if __name__ == "__main__":
    app.run()
