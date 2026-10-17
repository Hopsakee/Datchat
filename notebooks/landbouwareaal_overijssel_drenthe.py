import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    from datchat import charts, nb

    TABLES = ["80780ned"]
    nb.require(TABLES)

    def nl(v, d=1):
        """Dutch number formatting for text: 12.345,6."""
        return f"{v:,.{d}f}".replace(",", "_").replace(".", ",").replace("_", ".")

    PROV = {"PV23": "Overijssel", "PV22": "Drenthe"}
    CAT = ["Grasland", "Maïs", "Akkerbouw zonder maïs", "Overig"]
    return CAT, PROV, TABLES, charts, go, make_subplots, mo, nb, nl


@app.cell
def _(mo):
    mo.md(
        r"""
        # Grasland, maïs en akkerbouw in Overijssel en Drenthe, 2005–2025

        **Vraag:** Hoe is het landbouwareaal in Overijssel en Drenthe de afgelopen 20 jaar
        verschoven tussen grasland, mais en akkerbouw?

        **Uitwerking:** CBS deelt maïs over twee groepen: **snijmaïs** (veevoer) valt onder
        *grasland en groenvoedergewassen*, **korrelmaïs en corncob mix** vallen onder
        *akkerbouw* (granen). Om niets dubbel te tellen splitst dit notebook de cultuurgrond in
        vier delen die samen precies de CBS-cultuurgrond zijn:

        - **Grasland**: alle grasland (blijvend, tijdelijk en natuurlijk)
        - **Maïs**: snijmaïs + korrelmaïs + corncob mix
        - **Akkerbouw zonder maïs**: akkerbouw totaal min korrelmaïs en corncob mix
        - **Overig**: overige groenvoedergewassen (luzerne, voederbieten, …) en tuinbouw

        De periode is 2005–2025: twintig jaar terug vanaf het laatste definitieve jaar. 2026 is voorlopig en mist
        nog de tuinbouw onder glas, dus de cultuurgrond van 2026 is niet compleet.
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
        | 80780ned Landbouw; gewassen, dieren en grondgebruik naar regio | Areaal per gewas(groep) per provincie, 2000–2026 (landbouwtelling) | ja | Enige reeks met grasland, snijmaïs, korrelmaïs en akkerbouw per provincie over de hele periode. |
        | 80781ned … naar gemeente | Zelfde, per gemeente | nee | De vraag gaat over provincies; de provinciale tabel geeft dezelfde bron zonder optelling. |
        | 7140gras Grasland; oppervlakte en opbrengst | Grasland en opbrengst | nee | Geen maïs en akkerbouw; zou een tweede bron voor hetzelfde grasland zijn. |
        | 85636NED Akkerbouwgewassen; productie, regio | Areaal en oogst akkerbouwgewassen | nee | Geen grasland en snijmaïs. |
        | 71284ned Landbouw; gewassen, dieren, grondgebruik, regio, 2000-2009 | Oudere regionale reeks | nee | Stopgezet; 80780ned dekt 2000–2009 al, herberekend volgens de huidige afbakening. |
        """
    )
    return


@app.cell
def _(nb):
    # All land-use measures needed for the four-way split, in are (CBS unit); converted to ha.
    #   M10373 cultuurgrond totaal      M9902 grasland totaal     M9912 groenvoedergewassen totaal
    #   M9916  snijmaïs                 M9028 akkerbouw totaal    M9068 maïs, corncob mix
    #   M9069  maïs, korrel             M10377 tuinbouw open grond M10381 tuinbouw onder glas
    ruw = nb.sql(
        """
        SELECT year, period_status, RegioS, measure, value / 100 AS ha
        FROM core.t80780ned
        WHERE RegioS IN ('PV23', 'PV22')
          AND measure IN ('M10373', 'M9902', 'M9912', 'M9916', 'M9028', 'M9068', 'M9069',
                          'M10377', 'M10381')
          AND year BETWEEN 2005 AND 2025
        ORDER BY RegioS, year, measure
        """
    )
    ruw
    return (ruw,)


@app.cell
def _(CAT, ruw):
    _w = ruw.pivot_table(
        index=["RegioS", "year", "period_status"], columns="measure", values="ha"
    ).reset_index()
    assert _w.notna().all().all(), "ontbrekende waarden"
    _w["Grasland"] = _w["M9902"]
    _w["Maïs"] = _w["M9916"] + _w["M9068"] + _w["M9069"]
    _w["Akkerbouw zonder maïs"] = _w["M9028"] - _w["M9068"] - _w["M9069"]
    _w["Overig"] = _w["M9912"] - _w["M9916"] + _w["M10377"] + _w["M10381"]
    # The four parts must add up to CBS's own cultuurgrond total in every year.
    _diff = (_w[CAT].sum(axis=1) - _w["M10373"]).abs()
    assert (_diff < 1).all(), _w.loc[_diff >= 1, ["RegioS", "year"]]
    deel = _w.melt(
        id_vars=["RegioS", "year", "period_status", "M10373"], value_vars=CAT, var_name="categorie", value_name="ha"
    )
    deel["aandeel"] = 100 * deel["ha"] / deel["M10373"]
    return (deel,)


@app.cell
def _(CAT, PROV, TABLES, charts, deel, go, make_subplots, nl):
    _main = CAT[:3]
    _c = dict(zip(_main, [charts.ACCENT, charts.GREYS[0], charts.GREYS[2]], strict=True))
    fig_aandeel = make_subplots(
        rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.3,
        subplot_titles=list(PROV.values()),
    )
    for _j, (_code, _naam) in enumerate(PROV.items(), start=1):
        _labels = []
        for _k in _main:
            _d = deel[(deel["RegioS"] == _code) & (deel["categorie"] == _k)].sort_values("year")
            fig_aandeel.add_trace(
                go.Scatter(
                    x=_d["year"],
                    y=_d["aandeel"],
                    name=f"{_k} {_naam}",
                    mode="lines",
                    line={"color": _c[_k], "width": 2.5},
                    customdata=_d[["ha", "period_status"]],
                    hovertemplate=(
                        f"{_naam}, {_k} %{{x}}: %{{y:,.1f}}% van de cultuurgrond"
                        "<br>%{customdata[0]:,.0f} ha (80780ned, %{customdata[1]})<extra></extra>"
                    ),
                ),
                row=1,
                col=_j,
            )
            _l = _d.iloc[-1]
            _labels.append((_l["year"], _l["aandeel"], f"{_k} {nl(_l['aandeel'], 0)}%", _c[_k]))
        # direct labels per panel, pushed apart within the panel's own axis
        _ax = "x" if _j == 1 else f"x{_j}"
        _ay = "y" if _j == 1 else f"y{_j}"
        _placed = []
        for _x, _y, _t, _col in sorted(_labels, key=lambda t: t[1]):
            _y = max(_y, _placed[-1] + 4) if _placed else _y
            _placed.append(_y)
            fig_aandeel.add_annotation(
                x=_x, y=_y, xref=_ax, yref=_ay, text=_t, xanchor="left", xshift=6,
                showarrow=False, font={"color": _col, "size": 12},
            )
    for _j in (1, 2):
        fig_aandeel.add_vline(x=2015.5, line_dash="dot", line_color="#999", line_width=1, row=1, col=_j)

    _a = deel.pivot_table(index=["RegioS", "categorie"], columns="year", values="aandeel")
    _y0, _y1 = int(deel["year"].min()), int(deel["year"].max())
    # Title: the largest share shift of the three asked-for groups, either province.
    _shift = (_a[_y1] - _a[_y0]).drop(index="Overig", level=1)
    _rk, _ck = _shift.abs().idxmax()
    _s = _a.loc[(_rk, _ck)]
    charts.style(
        fig_aandeel,
        title=(
            f"Grootste verschuiving: {_ck.lower()} in {PROV[_rk]}, van {nl(_s[_y0], 0)}% naar "
            f"{nl(_s[_y1], 0)}% van de cultuurgrond ({_y0}–{_y1})"
        ),
        x_title="Jaar (peildatum 15 mei)",
        y_title="Aandeel in de cultuurgrond (%)",
        tables=TABLES,
        note=(
            "Maïs = snijmaïs + korrelmaïs + corncob mix. Stippellijn: vanaf 2016 bakent CBS "
            "landbouwbedrijven af via het Handelsregister;<br>volgens CBS beperkt effect op "
            "arealen, behalve natuurlijk grasland. Regio = hoofdvestiging van het bedrijf."
        ),
    )
    fig_aandeel.update_layout(margin={"r": 210, "b": 150})
    fig_aandeel.update_yaxes(rangemode="tozero")
    fig_aandeel.update_yaxes(title_text="", showgrid=False, row=1, col=2)
    fig_aandeel.update_xaxes(showgrid=False, ticks="outside", linecolor="#999", row=1, col=2)
    fig_aandeel.update_xaxes(range=[_y0 - 0.5, _y1 + 0.5], dtick=5)
    charts.checked(fig_aandeel)
    return (fig_aandeel,)


@app.cell
def _(CAT, PROV, TABLES, charts, deel, go, nl):
    _y0, _y1 = int(deel["year"].min()), int(deel["year"].max())
    _p = deel.pivot_table(index=["RegioS", "categorie"], columns="year", values="ha")
    _rows = []
    for _code, _naam in PROV.items():
        for _k in CAT:
            _rows.append((f"{_naam} · {_k}", _p.loc[(_code, _k), _y1] - _p.loc[(_code, _k), _y0]))
    _rows = _rows[::-1]  # Overijssel at the top
    _big = max(_rows, key=lambda r: abs(r[1]))
    fig_verschuiving = go.Figure()
    for _sel, _kleur in ((lambda r: r is not _big, charts.GREYS[1]), (lambda r: r is _big, charts.ACCENT)):
        _d = [r for r in _rows if _sel(r)]
        fig_verschuiving.add_trace(
            go.Bar(
                x=[r[1] / 1000 for r in _d],
                y=[r[0] for r in _d],
                orientation="h",
                marker={"color": _kleur},
                text=[f"{'+' if r[1] > 0 else '−'}{nl(abs(r[1]) / 1000, 1)}" for r in _d],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="%{y}: %{x:+,.1f} duizend ha<extra></extra>",
            )
        )
    fig_verschuiving.update_yaxes(categoryorder="array", categoryarray=[r[0] for r in _rows])
    _lo = min(0, min(r[1] for r in _rows)) / 1000
    _hi = max(0, max(r[1] for r in _rows)) / 1000
    _pad = 0.25 * (_hi - _lo)
    fig_verschuiving.update_xaxes(zeroline=True, zerolinecolor="#999", range=[_lo - _pad, _hi + _pad])
    charts.style(
        fig_verschuiving,
        title=(
            f"Grootste verschuiving: {_big[0].replace(' · ', ', ')} "
            f"{'+' if _big[1] > 0 else '−'}{nl(abs(_big[1]) / 1000, 1)} duizend ha ({_y0}–{_y1})"
        ),
        x_title=f"Verandering in areaal {_y0}–{_y1} (duizend ha)",
        y_title="",
        tables=TABLES,
        note=(
            "Overig = overige groenvoedergewassen en tuinbouw. Status: "
            + ", ".join(
                f"{st.lower()} {g.min()}–{g.max()}"
                for st, g in deel.groupby("period_status")["year"]
            )
            + "."
        ),
    )
    fig_verschuiving.update_yaxes(title_text="Provincie · gewasgroep (ha)")
    fig_verschuiving.update_layout(height=460, margin={"l": 260, "r": 80})
    charts.checked(fig_verschuiving, value_axis="x")
    return (fig_verschuiving,)


@app.cell
def _(CAT, PROV, deel, mo, nl):
    _y0, _y1 = int(deel["year"].min()), int(deel["year"].max())
    _p = deel.pivot_table(index=["RegioS", "categorie"], columns="year", values="ha")
    _rows = []
    for _code, _naam in PROV.items():
        for _k in CAT:
            _a, _b = _p.loc[(_code, _k), _y0], _p.loc[(_code, _k), _y1]
            _rows.append(
                f"| {_naam} | {_k} | {nl(_a, 0)} | {nl(_b, 0)} | "
                f"{'+' if _b > _a else '−'}{nl(abs(_b - _a), 0)} | {'+' if _b > _a else '−'}{nl(abs(100 * (_b - _a) / _a), 0)}% |"
            )
    mo.md(
        f"### Areaal in ha, {_y0} en {_y1}\n\n"
        f"| Provincie | Gewasgroep | {_y0} | {_y1} | Verschil | Verschil (%) |\n"
        "|---|---|---:|---:|---:|---:|\n" + "\n".join(_rows)
    )
    return


@app.cell
def _(nb):
    # 2026 is provisional and incomplete (no tuinbouw onder glas yet), so it stays out of the
    # charts. The three asked-for groups are complete and shown here as a first look.
    voorl = nb.sql(
        """
        SELECT RegioS, measure, value / 100 AS ha
        FROM core.t80780ned
        WHERE RegioS IN ('PV23', 'PV22') AND year = 2026 AND period_status = 'Voorlopig'
          AND measure IN ('M9902', 'M9916', 'M9028', 'M9068', 'M9069')
        """
    )
    return (voorl,)


@app.cell
def _(PROV, deel, mo, nl, voorl):
    _v = voorl.pivot_table(index="RegioS", columns="measure", values="ha")
    _y0, _y1 = int(deel["year"].min()), int(deel["year"].max())
    _p = deel.pivot_table(index=["RegioS", "categorie"], columns="year", values="ha")
    _zin = []
    for _code, _naam in PROV.items():
        _g = (_p.loc[(_code, "Grasland"), _y0], _p.loc[(_code, "Grasland"), _y1])
        _m = (_p.loc[(_code, "Maïs"), _y0], _p.loc[(_code, "Maïs"), _y1])
        _a = (_p.loc[(_code, "Akkerbouw zonder maïs"), _y0], _p.loc[(_code, "Akkerbouw zonder maïs"), _y1])
        _r = _v.loc[_code]
        _zin.append(
            f"- **{_naam}:** grasland {nl(_g[0] / 1000, 1)} → {nl(_g[1] / 1000, 1)} duizend ha, "
            f"maïs {nl(_m[0] / 1000, 1)} → {nl(_m[1] / 1000, 1)}, akkerbouw zonder maïs "
            f"{nl(_a[0] / 1000, 1)} → {nl(_a[1] / 1000, 1)}. "
            f"Voorlopig 2026*: grasland {nl(_r['M9902'] / 1000, 1)}, maïs "
            f"{nl((_r['M9916'] + _r['M9068'] + _r['M9069']) / 1000, 1)}, akkerbouw zonder maïs "
            f"{nl((_r['M9028'] - _r['M9068'] - _r['M9069']) / 1000, 1)} duizend ha."
        )
    mo.md(f"**Antwoord ({_y0}–{_y1}).**\n\n" + "\n".join(_zin) + "\n\n\\* voorlopig.")
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Let op

        - **Regio = hoofdvestiging.** De landbouwtelling telt het areaal bij de provincie waar
          het bedrijf zijn hoofdvestiging heeft, niet waar het perceel ligt. Bij de grens
          Overijssel–Drenthe kan grond dus "verkeerd" geteld zijn.
        - **Afbakening 2016.** Vanaf 2016 telt CBS alleen bedrijven met een agrarische
          inschrijving in het Handelsregister. Volgens CBS is het effect op arealen beperkt,
          behalve bij natuurlijk grasland (een klein deel van het grasland hier).
        - **Voedselbossen 2025.** Sinds 2025 rekent CBS voedselbossen tot de cultuurgrond in
          plaats van de niet-cultuurgrond. Ook in 2025 tellen de vier groepen exact op tot de
          CBS-cultuurgrond (controle hieronder).
        - Het waterschapsgebied valt niet samen met de twee provincies; CBS publiceert niets per
          waterschap.
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

        De vier groepen tellen per provincie en jaar op tot CBS' eigen cultuurgrond totaal
        (`M10373`); het notebook stopt als het verschil 1 ha of meer is.

        | Waarde | Tabel en selectie | Status | StatLine | Gecontroleerd |
        |---|---|---|---|---|
        | Snijmaïs Overijssel 2025: 32.447,78 ha | 80780ned, RegioS PV23 Overijssel, M9916 Groenvoedergewassen / Snijmaïs (3.244.778 are), 2025 | definitief | https://opendata.cbs.nl/#/CBS/nl/dataset/80780ned/table | 2026-10-17, `datchat verify 80780ned --cross-check`: 8/8 checks geslaagd; 459.823 waarden identiek aan de v3-API |
        | Maïs Overijssel 2005 → 2025: 46.585 → 33.595 ha (−12.991) | 80780ned, PV23, M9916 Snijmaïs + M9068 Maïs, corncob mix + M9069 Maïs, korrel; 2005: 44.799,72 + 490,32 + 1.295,27; 2025: 32.447,78 + 463,28 + 683,45 | definitief | idem | idem; som met de hand nagerekend uit de losse CBS-waarden |
        | Grasland Drenthe 2025: 64.332,6 ha | 80780ned, RegioS PV22 Drenthe, M9902 Grasland / Grasland, totaal, 2025 | definitief | idem | idem |
        """
    )
    return


if __name__ == "__main__":
    app.run()
