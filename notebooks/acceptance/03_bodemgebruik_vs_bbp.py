import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import plotly.graph_objects as go

    from datchat import charts, nb

    LAND_TABLES = ["37105", "86210NED", "86211NED"]
    BBP_TABLES = ["84088NED", "84087NED"]
    TABLES = LAND_TABLES + BBP_TABLES
    nb.require(TABLES)
    return BBP_TABLES, LAND_TABLES, TABLES, charts, go, mo, nb


@app.cell
def _(mo):
    mo.md(
        r"""
        # Bodemgebruik tegenover aandeel in het bbp

        **Vraag:** How has the area of the 5 largest land-use types in the Netherlands developed
        over the last 20 years, compared to their share of Dutch GDP (bbp)?
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
        | 37105 Bodemgebruik; verkorte gebruiksvorm, per provincie, vanaf 1900 | Oppervlakte per hoofdgroep bodemgebruik, Nederland, t/m 2017 | ja | Langste reeks volgens de oude methode (BBG). Na 2017 alleen de totale oppervlakte. |
        | 86210NED / 86211NED Bodemgebruik, wijk- en buurtcijfers 2020 / 2022 | Oppervlakte per hoofdgroep, Nederland (NL01), 2020 en 2022 | ja | Enige recentere bodemgebruikcijfers; **nieuwe methode (NBBG)**, volgens CBS een trendbreuk met beperkte vergelijkbaarheid. |
        | 70262ned Bodemgebruik; uitgebreide gebruiksvorm, per gemeente | Zelfde BBG-reeks tot 2017, meer detail | nee | Voegt voor Nederland als geheel niets toe aan 37105. |
        | 84088NED Productie- en inkomenscomponenten bbp; bedrijfstak; nr, 1995-2022 | Bruto toegevoegde waarde per SBI-sectie (A–U) | ja | Nodig voor losse secties (bijv. R Cultuur, sport en recreatie). |
        | 84087NED Opbouw binnenlands product (bbp); nr, 1995-2022 | Bruto binnenlands product | ja | Noemer voor "aandeel in het bbp"; zelfde reeks als 84088NED (totale toegevoegde waarde is in elk jaar gelijk, zie controle). |
        | 85867NED / 85865NED (2021-2025) | Opvolgers van 84088NED / 84087NED | nee | Bodemgebruik gaat niet verder dan 2022; 84087/84088 dekken 2003–2022 in één consistente reeks. |
        """
    )
    return


@app.cell
def _():
    # ── Aanname, niet CBS ───────────────────────────────────────────────────────────────
    # CBS classifies land use and the economy separately. This mapping of land-use main
    # groups to SBI sections is OUR assumption. Edit it and every chart below updates.
    # Sections not listed (e.g. B Delfstoffenwinning, H Vervoer en opslag) count as
    # "niet toegewezen", as do product taxes minus subsidies (the gap between value added
    # and bbp).
    LANDGEBRUIK_NAAR_SBI = {
        "Agrarisch terrein": ["A"],
        "Bebouwd terrein": list("CDEFGIJKLMNOPQSTU"),
        "Recreatieterrein": ["R"],
        "Bos en open natuurlijk terrein": [],
        "Water": [],
        "Verkeersterrein": ["H"],
        "Semi-bebouwd terrein": [],
    }
    return (LANDGEBRUIK_NAAR_SBI,)


@app.cell
def _(LANDGEBRUIK_NAAR_SBI, mo):
    _rows = "\n".join(
        f"| {k} | {', '.join(v) if v else '(geen sector)'} |"
        for k, v in LANDGEBRUIK_NAAR_SBI.items()
    )
    mo.callout(
        mo.md(
            "**Aanname, niet CBS:** koppeling bodemgebruik → SBI-secties "
            "(aan te passen in de cel hierboven)\n\n| Bodemgebruik | SBI-secties |\n|---|---|\n"
            + _rows
        ),
        kind="warn",
    )
    return


@app.cell
def _(nb):
    # Area per land-use main group as a share of total area (land + water), per table.
    # Codes are table-specific; the label list only names CBS's own main groups.
    # The wijk- en buurttabellen have no Perioden dimension: their year is the table's period.
    opp = nb.sql(
        """
        WITH labels(bron, code, bodemgebruik) AS (VALUES
            ('37105', 'A045820_2', 'Agrarisch terrein'),
            ('37105', 'A045801_2', 'Bebouwd terrein'),
            ('37105', 'A045814_2', 'Recreatieterrein'),
            ('37105', 'A045823_2', 'Bos en open natuurlijk terrein'),
            ('37105', 'A047040_2', 'Water'),
            ('37105', 'A045797_2', 'Verkeersterrein'),
            ('37105', 'A045807_2', 'Semi-bebouwd terrein'),
            ('nbbg',  'A045820_2', 'Agrarisch terrein'),
            ('nbbg',  'A045801_2', 'Bebouwd terrein'),
            ('nbbg',  'A045814_2', 'Recreatieterrein'),
            ('nbbg',  'A045823_2', 'Bos en open natuurlijk terrein'),
            ('nbbg',  'A047040',   'Water'),
            ('nbbg',  'A045797_2', 'Verkeersterrein'),
            ('nbbg',  'A045807_2', 'Semi-bebouwd terrein')
        ),
        bbg AS (
            SELECT '37105' AS tabel, 'BBG (oude methode)' AS methode, year, measure, value
            FROM core.t37105 WHERE RegioS = 'NL01' AND value IS NOT NULL
        ),
        nbbg AS (
            SELECT t.table_id AS tabel, 'NBBG (nieuwe methode)' AS methode,
                   CAST(t.temporal_coverage AS INTEGER) AS year, o.measure, o.value
            FROM meta.tables t
            JOIN (SELECT '86210NED' AS tid, measure, value FROM raw.t86210ned WHERE AlleRegioIndelingen = 'NL01'
                  UNION ALL
                  SELECT '86211NED', measure, value FROM raw.t86211ned WHERE AlleRegioIndelingen = 'NL01') o
              ON o.tid = t.table_id
        ),
        alles AS (SELECT * FROM bbg UNION ALL SELECT * FROM nbbg),
        totaal AS (SELECT tabel, year, value AS totaal FROM alles WHERE measure = 'T001455')
        SELECT a.tabel, a.methode, a.year, l.bodemgebruik, a.value AS oppervlakte,
               100 * a.value / t.totaal AS aandeel_oppervlakte_pct
        FROM alles a
        JOIN labels l ON l.code = a.measure
                     AND l.bron = CASE WHEN a.tabel = '37105' THEN '37105' ELSE 'nbbg' END
        JOIN totaal t ON t.tabel = a.tabel AND t.year = a.year
        WHERE a.year >= (SELECT max(year) FROM alles) - 20
        ORDER BY a.year, aandeel_oppervlakte_pct DESC
        """
    )
    laatste_jaar = int(opp["year"].max())
    top5 = (
        opp[opp["year"] == laatste_jaar]
        .nlargest(5, "aandeel_oppervlakte_pct")["bodemgebruik"]
        .tolist()
    )
    opp
    return laatste_jaar, opp, top5


@app.cell
def _(LANDGEBRUIK_NAAR_SBI, nb, opp):
    # Share of bbp of the SBI sections mapped to each land-use type (84088NED value added,
    # 84087NED bbp), for the years the land-use series covers.
    _types, _secs = [], []
    for _k, _v in LANDGEBRUIK_NAAR_SBI.items():
        for _s in _v:
            _types.append(_k)
            _secs.append(_s)
    bbp = nb.sql(
        """
        WITH mapping AS (
            SELECT unnest(?::VARCHAR[]) AS bodemgebruik, unnest(?::VARCHAR[]) AS sectie
        ),
        btw AS (
            SELECT year, period_status,
                   regexp_extract(BedrijfstakkenBranchesSBI2008_title, '^([A-U]) ', 1) AS sectie,
                   value AS btw
            FROM core.t84088ned
            WHERE measure = 'M006324_1'   -- Bruto toegevoegde waarde basisprijzen, werkelijke prijzen
              AND regexp_matches(BedrijfstakkenBranchesSBI2008_title, '^[A-U] ')
        ),
        bbp AS (
            SELECT year, value AS bbp FROM core.t84087ned WHERE measure = 'M002782_1'
        )
        SELECT b.year, b.period_status, m.bodemgebruik,
               100 * sum(b.btw) / max(p.bbp) AS aandeel_bbp_pct
        FROM btw b JOIN mapping m USING (sectie) JOIN bbp p USING (year)
        WHERE b.year BETWEEN ? AND ?
        GROUP BY ALL
        ORDER BY b.year
        """,
        [_types, _secs, int(opp["year"].min()), int(opp["year"].max())],
    )
    bbp
    return (bbp,)


@app.cell
def _(LAND_TABLES, charts, go, laatste_jaar, opp, top5):
    _c = charts.colors(len(top5), accent=0)
    fig_opp = go.Figure()
    _labels = []
    for _i, _t in enumerate(top5):
        _d = opp[opp["bodemgebruik"] == _t]
        _old = _d[_d["methode"].str.startswith("BBG")]
        _new = _d[_d["methode"].str.startswith("NBBG")]
        fig_opp.add_trace(
            go.Scatter(
                x=_old["year"],
                y=_old["aandeel_oppervlakte_pct"],
                name=_t,
                mode="lines+markers",
                line={"color": _c[_i], "width": 2},
            )
        )
        fig_opp.add_trace(
            go.Scatter(
                x=_new["year"],
                y=_new["aandeel_oppervlakte_pct"],
                name=_t + " (NBBG)",
                mode="markers",
                marker={"color": _c[_i], "size": 9, "symbol": "diamond"},
            )
        )
        _last = _new.iloc[-1] if len(_new) else _old.iloc[-1]
        _labels.append((_last["year"], _last["aandeel_oppervlakte_pct"], _t, _c[_i]))
    charts.direct_labels(fig_opp, _labels)
    _brk = opp.loc[opp["methode"].str.startswith("NBBG"), "year"].min()
    fig_opp.add_vline(x=_brk - 1.5, line_dash="dot", line_color="#999", line_width=1.5)
    fig_opp.add_annotation(
        x=_brk - 1.5,
        y=1.02,
        yref="paper",
        text="trendbreuk: nieuwe methode",
        showarrow=False,
        font={"size": 11, "color": "#666"},
    )
    _agr = opp[(opp["bodemgebruik"] == top5[0]) & (opp["year"] == laatste_jaar)].iloc[0]
    charts.style(
        fig_opp,
        title=f"{top5[0]} beslaat {_agr['aandeel_oppervlakte_pct']:.0f}% van Nederland ({laatste_jaar})",
        x_title="Jaar",
        y_title="Aandeel in totale oppervlakte land en water (%)",
        tables=LAND_TABLES,
        note="Lijnen: BBG t/m 2017; ruiten: NBBG 2020 en 2022, beperkt vergelijkbaar",
    )
    fig_opp.update_yaxes(rangemode="tozero")
    charts.checked(fig_opp)
    return (fig_opp,)


@app.cell
def _(BBP_TABLES, bbp, charts, go, top5):
    _mapped = [t for t in top5 if t in set(bbp["bodemgebruik"])]
    _c = charts.colors(len(_mapped), accent=0 if _mapped and _mapped[0] == top5[0] else None)
    fig_bbp = go.Figure()
    _labels = []
    for _i, _t in enumerate(_mapped):
        _d = bbp[bbp["bodemgebruik"] == _t]
        _final = _d[_d["period_status"] != "Voorlopig"]
        _prov = _d[_d["period_status"] == "Voorlopig"]
        fig_bbp.add_trace(
            go.Scatter(
                x=_final["year"],
                y=_final["aandeel_bbp_pct"],
                name=_t,
                mode="lines",
                line={"color": _c[_i], "width": 2},
            )
        )
        if len(_prov):
            _join = _final.tail(1)
            fig_bbp.add_trace(
                go.Scatter(
                    x=list(_join["year"]) + list(_prov["year"]),
                    y=list(_join["aandeel_bbp_pct"]) + list(_prov["aandeel_bbp_pct"]),
                    name=_t + " (voorlopig)",
                    mode="lines",
                    line={"color": _c[_i], "width": 2, "dash": charts.PROVISIONAL_DASH},
                )
            )
        _last = _d.iloc[-1]
        _labels.append((_last["year"], _last["aandeel_bbp_pct"], _t, _c[_i]))
    charts.direct_labels(fig_bbp, _labels)
    charts.style(
        fig_bbp,
        title="Aandeel in het bbp van de gekoppelde sectoren",
        x_title="Jaar",
        y_title="Aandeel in het bbp (%)",
        tables=BBP_TABLES,
        note="Koppeling bodemgebruik → SBI is een aanname, niet CBS. Stippellijn = voorlopig",
    )
    fig_bbp.update_yaxes(rangemode="tozero")
    charts.checked(fig_bbp)
    return (fig_bbp,)


@app.cell
def _(TABLES, bbp, charts, go, laatste_jaar, opp, top5):
    # Latest year with both: land use and bbp.
    _jaar = min(laatste_jaar, int(bbp["year"].max()))
    _o = opp[opp["year"] == _jaar].set_index("bodemgebruik")["aandeel_oppervlakte_pct"]
    _b = bbp[bbp["year"] == _jaar].set_index("bodemgebruik")["aandeel_bbp_pct"]
    _types = list(reversed(top5))
    _area = [_o.get(t) for t in _types]
    _gdp = [_b.get(t, 0.0) for t in _types]
    _gdp_text = [
        f"{_b[t]:.1f}".replace(".", ",") + "% bbp" if t in _b.index else "geen sector"
        for t in _types
    ]
    _area_text = [f"{a:.1f}".replace(".", ",") + "% opp." for a in _area]
    fig_cmp = go.Figure(
        [
            go.Bar(
                y=_types,
                x=_area,
                orientation="h",
                name="oppervlakte",
                marker={"color": charts.GREYS[2]},
                text=_area_text,
                textposition="outside",
                cliponaxis=False,
            ),
            go.Bar(
                y=_types,
                x=_gdp,
                orientation="h",
                name="bbp",
                marker={"color": charts.ACCENT},
                text=_gdp_text,
                textposition="outside",
                cliponaxis=False,
            ),
        ]
    )
    fig_cmp.update_layout(barmode="group")
    charts.style(
        fig_cmp,
        title=f"Oppervlakte en bbp lopen sterk uiteen ({_jaar})",
        x_title="Aandeel (%)",
        y_title="Bodemgebruik",
        tables=TABLES,
        note="Grijs = aandeel oppervlakte, rood = aandeel bbp via de aangenomen koppeling (aanname, niet CBS)",
    )
    fig_cmp.update_xaxes(range=[0, 100])
    charts.checked(fig_cmp, value_axis="x")
    return (fig_cmp,)


@app.cell
def _(bbp, laatste_jaar, mo, opp, top5):
    _jaar = min(laatste_jaar, int(bbp["year"].max()))
    _first = int(opp["year"].min())
    _o = opp.set_index(["bodemgebruik", "year"])["aandeel_oppervlakte_pct"]
    _b = bbp[bbp["year"] == _jaar].set_index("bodemgebruik")["aandeel_bbp_pct"]
    _lines = []
    for _t in top5:
        _bb = f"{_b[_t]:.1f}% van het bbp" if _t in _b.index else "geen sector gekoppeld"
        _lines.append(
            f"- **{_t}**: {_o[(_t, _first)]:.1f}% van de oppervlakte in {_first}, "
            f"{_o[(_t, laatste_jaar)]:.1f}% in {laatste_jaar}; {_bb} in {_jaar}"
        )
    mo.md(
        f"""
        **Antwoord.** De vijf grootste vormen van bodemgebruik in {laatste_jaar} en hun
        ontwikkeling sinds {_first}, tegenover het bbp-aandeel van de sectoren die wij eraan
        koppelen (aanname, niet CBS):

        {chr(10).join(_lines)}

        *Let op:* de cijfers vóór en na 2020 zijn volgens CBS beperkt vergelijkbaar (nieuwe
        methode). Onder de oude methode was Verkeersterrein groter dan Recreatieterrein; onder
        de nieuwe methode is het andersom. De top 5 is daarom bepaald op het laatste jaar.
        """
    )
    return


@app.cell
def _(mo, nb):
    # Consistency of the two national-accounts tables: total value added must be identical.
    _chk = nb.sql(
        """
        SELECT a.year, a.value AS btw_84087, b.value AS btw_84088
        FROM core.t84087ned a JOIN core.t84088ned b
          ON b.year = a.year AND b.measure = 'M006324_1' AND b.BedrijfstakkenBranchesSBI2008 = 'T001081'
        WHERE a.measure = 'T001081_1'
        """
    )
    assert (_chk["btw_84087"] == _chk["btw_84088"]).all(), "84087NED and 84088NED disagree"
    mo.md(
        f"Controle: totale bruto toegevoegde waarde gelijk in 84087NED en 84088NED voor alle "
        f"{len(_chk)} jaren ({_chk['year'].min()}–{_chk['year'].max()})."
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
        | Agrarisch terrein 2017 = 22.304 km² | 37105 · Nederland · Totaal agrarisch terrein · 2017 | geen periodestatus in metadata | https://opendata.cbs.nl/#/CBS/nl/dataset/37105/table | 2026-09-28: `datchat verify 37105 --cross-check` |
        | Agrarisch terrein 2022 = 2.159.516 ha | 86211NED · Nederland (NL01) · Totaal Agrarisch terrein | tabel 2022 | https://opendata.cbs.nl/#/CBS/nl/dataset/86211NED/table | 2026-09-28: `datchat verify 86211NED --cross-check` |
        | Bbp en toegevoegde waarde per sectie | 84087NED · Bruto binnenlands product; 84088NED · Bruto toegevoegde waarde basisprijzen per SBI-sectie | Definitief t/m 2021, 2022 voorlopig | https://opendata.cbs.nl/#/CBS/nl/dataset/84088NED/table | 2026-09-28: `datchat verify 84087NED 84088NED --cross-check`; secties A–U tellen op tot het totaal; totalen gelijk in beide tabellen |
        """
    )
    return


if __name__ == "__main__":
    app.run()
