import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import math

    import marimo as mo
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    from datchat import charts, nb

    TABLES = ["70262ned", "86210NED", "86211NED"]
    nb.require(TABLES)
    return TABLES, charts, go, make_subplots, math, mo, nb


@app.cell
def _(mo):
    mo.md(
        r"""
        # De grootste bodemgebruiksvormen van Nederland, 20 jaar lang

        **Vraag:** the development of the area used by the 6 largest usages of area in the
        Netherlands over the last 20 years. If it changes in those 20 years which the 6 largest
        space occupiers are, then add those. So we might get more than 6 we track the space
        used for.

        **Uitwerking:** "bodemgebruiksvorm" is het fijnste niveau dat CBS voor heel Nederland
        publiceert (de *uitgebreide gebruiksvorm*, zoals woonterrein, bos of Waddenzee), niet de
        negen hoofdgroepen. Per peiljaar bepaalt dit notebook de zes grootste; elke vorm die in
        minstens één peiljaar bij de zes grootste hoort, wordt over de hele periode gevolgd.
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
        | 70262ned Bodemgebruik; uitgebreide gebruiksvorm, per gemeente | Oppervlakte per uitgebreide gebruiksvorm, Nederland (NL01), 1996–2017 | ja | Enige reeks met het fijne niveau volgens de oude methode (BBG); peiljaren 2003–2017 vallen in de periode. |
        | 86210NED / 86211NED Bodemgebruik, wijk- en buurtcijfers 2020 / 2022 | Zelfde niveau, Nederland (NL01), 2020 en 2022 | ja | Enige cijfers na 2017; **nieuwe methode (NBBG)**. CBS: "trendbreuk en beperkte vergelijkbaarheid" met eerdere publicaties. |
        | 37105 Bodemgebruik; verkorte gebruiksvorm, per provincie | Alleen de negen hoofdgroepen, t/m 2017 | nee | Te grof: een top 6 uit negen hoofdgroepen is bijna alles. Zelfde BBG-bron als 70262ned. |
        | 85217NED Bodemgebruik, wijk- en buurtcijfers 2017 | BBG 2017 per wijk en buurt | nee | Alleen 2017, en dat jaar staat voor Nederland al in 70262ned. |
        | 7041BBOD Bodemgebruik in Nederland: 1989; 1993; 1996 | Oudere peiljaren | nee | Stopgezet, valt buiten de laatste 20 jaar. |
        """
    )
    return


@app.cell
def _(mo):
    water = mo.ui.switch(value=True, label="Binnen- en buitenwater meetellen als bodemgebruik")
    mo.vstack(
        [
            mo.md(
                "CBS rekent water (IJsselmeer, Waddenzee, Noordzee binnen de gemeentegrenzen) "
                "tot het bodemgebruik. Zet dit uit om alleen land te rangschikken."
            ),
            water,
        ]
    )
    return (water,)


@app.cell
def _():
    # ── Aanname, niet CBS ───────────────────────────────────────────────────────────────
    # CBS codes are table-specific, and the method changed in 2020 (BBG → NBBG). Which
    # BBG category counts as "the same" NBBG category is OUR assumption: it only decides
    # whether an old line and new points share one panel. Edit it and the charts update.
    #
    # Default: a code present in both tables is the same category, except the one whose
    # CBS definition changed with the method (compare meta.measures.description):
    NIET_ZELFDE_NA_BREUK = {
        # BBG: "niet in gebruik voor glastuinbouw, zoals grasland, tuinland, bouwland".
        # NBBG: "voor zover niet toegerekend aan ... Akker en meerjarige teelt en Agrarisch
        # grasland" -- a residual next to two new categories.
        "A045822": "BBG: bijna alle landbouwgrond; NBBG: restpost naast grasland en akker",
    }
    # A045799 is titled "Wegverkeersterrein" (BBG) and "Hoofdweg" (NBBG), but both tables
    # define it as transport "over het hoofdwegennetwerk", so it is treated as the same.
    return (NIET_ZELFDE_NA_BREUK,)


@app.cell
def _(nb):
    # Every leaf category (not the "Totaal" subtotals), Nederland, both methods. The group
    # comes from CBS metadata: measure titles in core.t<id> carry no group prefix.
    # The wijk- en buurttabellen have no Perioden dimension: their year is the table's period.
    blad = nb.sql(
        """
        WITH bbg AS (
            SELECT '70262ned' AS tabel, 'BBG' AS methode, year, measure, value
            FROM core.t70262ned WHERE RegioS = 'NL01'
        ),
        nbbg AS (
            SELECT o.tabel, 'NBBG' AS methode, CAST(t.temporal_coverage AS INTEGER) AS year,
                   o.measure, o.value
            FROM (SELECT '86210NED' AS tabel, measure, value
                  FROM core.t86210ned WHERE AlleRegioIndelingen = 'NL01'
                  UNION ALL
                  SELECT '86211NED', measure, value
                  FROM core.t86211ned WHERE AlleRegioIndelingen = 'NL01') o
            JOIN meta.tables t ON t.table_id = o.tabel
        ),
        alles AS (SELECT * FROM bbg UNION ALL SELECT * FROM nbbg)
        SELECT a.tabel, a.methode, a.year, a.measure AS code,
               g.title AS groep, trim(m.title) AS naam, a.value AS ha
        FROM alles a
        JOIN meta.measures m ON lower(m.table_id) = lower(a.tabel) AND m.measure_id = a.measure
        JOIN meta.measure_groups g ON g.table_id = m.table_id AND g.group_id = m.group_id
        WHERE a.value IS NOT NULL
          AND g.title <> 'Regioaanduiding'
          AND NOT starts_with(trim(m.title), 'Totaal')
          AND a.year >= (SELECT max(year) FROM alles) - 20
        ORDER BY a.year, a.value DESC
        """
    )
    blad
    return (blad,)


@app.cell
def _(nb):
    # Totals per table and year, to check that the leaves add up (Controle below).
    totalen = nb.sql(
        """
        SELECT '70262ned' AS tabel, year, measure, value FROM core.t70262ned
        WHERE RegioS = 'NL01' AND measure IN ('T001455', 'A045820_2')
        UNION ALL
        SELECT o.tabel, CAST(t.temporal_coverage AS INTEGER), o.measure, o.value
        FROM (SELECT '86210NED' AS tabel, measure, value FROM core.t86210ned
              WHERE AlleRegioIndelingen = 'NL01' AND measure IN ('T001455', 'A045820_2')
              UNION ALL
              SELECT '86211NED', measure, value FROM core.t86211ned
              WHERE AlleRegioIndelingen = 'NL01' AND measure IN ('T001455', 'A045820_2')) o
        JOIN meta.tables t ON t.table_id = o.tabel
        """
    )
    return (totalen,)


@app.cell
def _(blad, totalen):
    # The leaves must add up to CBS's own totals in every year, or the ranking is wrong.
    # CBS rounds every figure to whole hectares, so the sum may drift by at most half a
    # hectare per rounded leaf.
    for (_tab, _yr), _d in blad.groupby(["tabel", "year"]):
        _t = totalen[(totalen.tabel == _tab) & (totalen.year == _yr)].set_index("measure")["value"]
        assert abs(_d["ha"].sum() - _t["T001455"]) <= 0.5 * len(_d), (_tab, _yr, "totaal")
        _agr = _d[_d["groep"] == "Agrarisch terrein"]["ha"]
        assert abs(_agr.sum() - _t["A045820_2"]) <= 0.5 * len(_agr), (_tab, _yr, "agrarisch")
    return


@app.cell
def _(NIET_ZELFDE_NA_BREUK, blad, water):
    # Category key: one panel per key. Shared codes use the NBBG name; the rest are kept apart.
    _codes = {m: set(blad.loc[blad.methode == m, "code"]) for m in ("BBG", "NBBG")}
    _zelfde = (_codes["BBG"] & _codes["NBBG"]) - set(NIET_ZELFDE_NA_BREUK)
    _nieuw_naam = blad[blad.methode == "NBBG"].drop_duplicates("code").set_index("code")["naam"]
    _is_water = blad["groep"].isin(["Binnenwater", "Buitenwater"])

    reeks = blad[~_is_water | water.value].copy()
    reeks["categorie"] = [
        _nieuw_naam[c] if c in _zelfde else f"{n} ({m})"
        for c, n, m in zip(reeks["code"], reeks["naam"], reeks["methode"], strict=True)
    ]
    reeks["rang"] = reeks.groupby("year")["ha"].rank(ascending=False, method="first").astype(int)

    _top = reeks[reeks["rang"] <= 6]
    gevolgd = _top.groupby("categorie")["ha"].max().sort_values(ascending=False).index.tolist()
    top6_jaren = _top.groupby("categorie")["year"].apply(lambda s: sorted(s)).to_dict()
    gevolgd_df = reeks[reeks["categorie"].isin(gevolgd)]
    return gevolgd, gevolgd_df, reeks, top6_jaren


@app.cell
def _(gevolgd_df, mo):
    # Rank per year: which categories were a top-6, and when.
    _rang = gevolgd_df.pivot_table(
        index="categorie", columns="year", values="rang", aggfunc="first"
    )
    _rang = _rang.loc[_rang.min(axis=1).sort_values().index]
    _rang.columns = [str(c) for c in _rang.columns]
    mo.vstack(
        [
            mo.md("### Rang per peiljaar (1 = grootste)"),
            mo.ui.table(_rang.reset_index(), selection=None, show_column_summaries=False),
        ]
    )
    return


@app.cell
def _(TABLES, charts, gevolgd, gevolgd_df, go, make_subplots, math, top6_jaren):
    _n = len(gevolgd)
    _cols = 2
    _rows = math.ceil(_n / _cols)
    _c = charts.colors(1)[0]

    # Grid starts bottom-left so the first axis pair (the one the checker reads) is the
    # bottom-left panel, which carries both axis titles. Panels still read top-left first.
    def _pos(i):
        return _rows - i // _cols, i % _cols + 1

    _titles = [""] * (_rows * _cols)
    for _i, _k in enumerate(gevolgd):
        _r, _col = _pos(_i)
        _titles[(_r - 1) * _cols + _col - 1] = (
            f"{_k}<br><sup>top 6 in {', '.join(str(y) for y in top6_jaren[_k])}</sup>"
        )
    fig_panelen = make_subplots(
        rows=_rows,
        cols=_cols,
        start_cell="bottom-left",
        shared_xaxes=True,
        vertical_spacing=0.11,
        horizontal_spacing=0.12,
        subplot_titles=_titles,
    )
    for _i, _k in enumerate(gevolgd):
        _r, _col = _pos(_i)
        _d = gevolgd_df[gevolgd_df["categorie"] == _k]
        for _m, _mode, _mk in (("BBG", "lines+markers", "circle"), ("NBBG", "markers", "diamond")):
            _s = _d[_d["methode"] == _m]
            if len(_s):
                fig_panelen.add_trace(
                    go.Scatter(
                        x=_s["year"],
                        y=_s["ha"] / 1000,
                        name=f"{_k} ({_m})",
                        mode=_mode,
                        line={"color": _c, "width": 2},
                        marker={"color": _c, "size": 8 if _m == "BBG" else 10, "symbol": _mk},
                        customdata=_s[["tabel"]],
                        hovertemplate="%{x}: %{y:,.1f} duizend ha<br>%{customdata[0]}<extra></extra>",
                    ),
                    row=_r,
                    col=_col,
                )
    _brk = int(gevolgd_df.loc[gevolgd_df["methode"] == "NBBG", "year"].min())
    for _i in range(_n):
        _r, _col = _pos(_i)
        fig_panelen.add_vline(
            x=_brk - 1.5, line_dash="dot", line_color="#999", line_width=1.5, row=_r, col=_col
        )

    _bbg = gevolgd_df[gevolgd_df["methode"] == "BBG"]
    _y0, _y1 = int(_bbg["year"].min()), int(_bbg["year"].max())
    _groei = (
        _bbg.pivot_table(index="categorie", columns="year", values="ha")[[_y0, _y1]]
        .dropna()
        .assign(pct=lambda t: 100 * (t[_y1] - t[_y0]) / t[_y0])
    )
    _hard = _groei["pct"].idxmax()
    charts.style(
        fig_panelen,
        title=(
            f"{_n} vormen waren ooit een top 6; {_hard} groeide het hardst "
            f"({_groei.loc[_hard, 'pct']:+.0f}%, {_y0}–{_y1})"
        ),
        x_title="Peiljaar",
        y_title="Oppervlakte (duizend ha)",
        tables=TABLES,
        note=(
            f"Lijnen: oude methode (BBG) t/m {_y1}; ruiten: nieuwe methode (NBBG) {_brk} en later. "
            "Stippellijn: trendbreuk, beperkt vergelijkbaar. Elk paneel heeft een eigen schaal."
        ),
    )
    fig_panelen.update_layout(height=300 * _rows + 220, margin={"l": 90, "r": 40, "t": 120})
    fig_panelen.update_yaxes(rangemode="tozero", title_text="", nticks=4)
    fig_panelen.update_yaxes(title_text="Oppervlakte (duizend ha)", row=1, col=1)
    fig_panelen.update_xaxes(title_text="")
    fig_panelen.update_xaxes(title_text="Peiljaar", row=1)
    fig_panelen.update_annotations(font_size=12, selector={"xref": "x domain"})
    charts.checked(fig_panelen)
    return (fig_panelen,)


@app.cell
def _(TABLES, charts, gevolgd_df, go):
    # Change within one method only: BBG first to last peiljaar, NBBG first to last.
    _rows = []
    for (_k, _m), _d in gevolgd_df.groupby(["categorie", "methode"]):
        _d = _d.sort_values("year")
        if len(_d) >= 2:
            _a, _b = _d.iloc[0], _d.iloc[-1]
            _rows.append(
                (_k, _m, int(_a.year), int(_b.year), 100 * (_b.ha - _a.ha) / _a.ha, _b.ha - _a.ha)
            )
    _bbg = sorted([r for r in _rows if r[1] == "BBG"], key=lambda r: r[4])
    _grootst = max(_bbg, key=lambda r: abs(r[4]))
    fig_groei = go.Figure()
    for _sel, _kleur in (
        (lambda r: r is not _grootst, charts.GREYS[1]),
        (lambda r: r is _grootst, charts.ACCENT),
    ):
        _d = [r for r in _bbg if _sel(r)]
        fig_groei.add_trace(
            go.Bar(
                x=[r[4] for r in _d],
                y=[r[0] for r in _d],
                orientation="h",
                marker={"color": _kleur},
                text=[f"{r[4]:+.1f}% ({r[5] / 1000:+,.1f} duizend ha)" for r in _d],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="%{y}: %{x:+.1f}%<extra></extra>",
            )
        )
    fig_groei.update_yaxes(categoryorder="array", categoryarray=[r[0] for r in _bbg])
    _y0, _y1 = _bbg[0][2], _bbg[0][3]
    charts.style(
        fig_groei,
        title=(f"{_grootst[0]} veranderde het meest: {_grootst[4]:+.0f}% tussen {_y0} en {_y1}"),
        x_title=f"Verandering in oppervlakte {_y0}–{_y1} (%)",
        y_title="",
        tables=TABLES[:1],
        note="Oude methode (BBG) 70262ned; alleen vormen die ooit een top 6 waren en in beide jaren bestaan.",
    )
    fig_groei.update_layout(height=120 + 45 * len(_bbg), margin={"l": 220, "r": 60})
    _lo = min(0, min(r[4] for r in _bbg))
    _hi = max(0, max(r[4] for r in _bbg))
    _pad = 0.9 * (_hi - _lo)  # room for the outside labels on both sides
    fig_groei.update_xaxes(zeroline=True, zerolinecolor="#999", range=[_lo - _pad, _hi + _pad])
    fig_groei.update_yaxes(title_text="Bodemgebruiksvorm (ha, BBG)")
    groei_rijen = _rows
    charts.checked(fig_groei, value_axis="x")
    return fig_groei, groei_rijen


@app.cell
def _(gevolgd, gevolgd_df, mo, top6_jaren):
    # Answer text: every number interpolated from the query results above.
    _regels = []
    for _k in gevolgd:
        _d = gevolgd_df[gevolgd_df["categorie"] == _k].sort_values("year")
        _parts = []
        for _m in ("BBG", "NBBG"):
            _s = _d[_d["methode"] == _m]
            if len(_s) >= 2:
                _a, _b = _s.iloc[0], _s.iloc[-1]
                _parts.append(
                    f"{_m} {int(_a.year)}–{int(_b.year)}: {_a.ha / 1000:,.0f} → {_b.ha / 1000:,.0f} "
                    f"duizend ha ({100 * (_b.ha - _a.ha) / _a.ha:+.1f}%)"
                )
            elif len(_s) == 1:
                _parts.append(
                    f"{_m} {int(_s.iloc[0].year)}: {_s.iloc[0].ha / 1000:,.0f} duizend ha"
                )
        _regels.append(
            f"- **{_k}** (top 6 in {len(top6_jaren[_k])} peiljaren): " + "; ".join(_parts)
        )
    mo.md(
        f"**Antwoord:** {len(gevolgd)} bodemgebruiksvormen hoorden in minstens één peiljaar bij "
        "de zes grootste. Veranderingen zijn alleen binnen één methode vergelijkbaar:\n\n"
        + "\n".join(_regels)
    )
    return


@app.cell
def _(NIET_ZELFDE_NA_BREUK, mo):
    _rows = "\n".join(f"| `{k}` | {v} |" for k, v in NIET_ZELFDE_NA_BREUK.items())
    mo.md(
        "## Let op bij de trendbreuk\n\n"
        "Vanaf peiljaar 2020 maakt CBS het Bestand Bodemgebruik met een herziene methode "
        "(NBBG); CBS noemt de cijfers daardoor beperkt vergelijkbaar. Een sprong tussen 2017 en "
        "2020 is dus niet als verandering in het landgebruik te lezen. Deze codes zijn bewust "
        "niet als één reeks behandeld:\n\n"
        "| Code | Verschil |\n|---|---|\n" + _rows + "\n\n"
        "Vooral de landbouw verandert van indeling: de oude 'Overig agrarisch terrein' is in "
        "de nieuwe methode opgesplitst in agrarisch grasland, akker en meerjarige teelt, en "
        "een kleine restpost. De ranglijst is daarom per methode te lezen, niet over de breuk heen."
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

        De bladcategorieën tellen per tabel en peiljaar op tot CBS' eigen totale oppervlakte
        (`T001455`) en totaal agrarisch terrein (`A045820_2`); het notebook stopt als dat niet
        klopt.

        | Waarde | Tabel en selectie | Status | StatLine | Gecontroleerd |
        |---|---|---|---|---|
        | Woonterrein 2003: 223.891 ha | 70262ned, RegioS NL01 Nederland, A045802 Bebouwd terrein / Woonterrein, 2003 | definitief | https://opendata.cbs.nl/#/CBS/nl/dataset/70262ned/table | 2026-09-28, `datchat verify 70262ned 86210NED 86211NED --cross-check`: 22/22 checks geslaagd; alle waarden in de drie tabellen identiek aan de v3-API |
        | Agrarisch grasland 2022: 949.080 ha | 86211NED, NL01 Nederland, M008355 Agrarisch terrein / Agrarisch grasland | definitief | https://opendata.cbs.nl/#/CBS/nl/dataset/86211NED/table | idem |
        | Bos 2020: 335.895 ha | 86210NED, NL01 Nederland, A045824 Natuurlijk terrein / Bos | definitief | https://opendata.cbs.nl/#/CBS/nl/dataset/86210NED/table | idem |
        """
    )
    return


if __name__ == "__main__":
    app.run()
