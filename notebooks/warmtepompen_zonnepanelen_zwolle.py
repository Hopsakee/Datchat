import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import plotly.graph_objects as go

    from datchat import charts, nb

    TABLES = ["84783NED", "85005NED", "85523NED", "84948NED"]
    nb.require(TABLES)

    def nl(v, d=1):
        """Dutch number formatting for text: 12.345,6."""
        return f"{v:,.{d}f}".replace(",", "_").replace(".", ",").replace("_", ".")

    REGIO = {
        "GM0193": "Zwolle",
        "PV23": "Overijssel",
        "PV22": "Drenthe",
        "NL01": "Nederland",
    }
    return REGIO, TABLES, charts, go, mo, nb, nl


@app.cell
def _(mo):
    mo.md(
        r"""
        # Zonnepanelen en warmtepompen bij woningen: Zwolle, Overijssel en Drenthe naast Nederland

        **Vraag:** Hoe snel zijn warmtepompen en zonnepanelen bij huishoudens gegroeid in Zwolle
        en de WDODelta-gemeenten, vergeleken met de rest van Nederland?

        **Uitwerking:** CBS kent geen waterschapsgebieden. Dit notebook vergelijkt daarom Zwolle,
        de provincies Overijssel en Drenthe (waar het beheergebied van WDODelta grotendeels in
        ligt) en heel Nederland. "Bij huishoudens" is de CBS-sector *woningen*: installaties op
        een adres met alleen een woonfunctie. Groei wordt getoond als index, zodat een gemeente
        en het hele land op één schaal passen.
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
        | 84783NED Zonnestroom; vermogen bedrijven en woningen, regio (indeling 2019) | Opgesteld vermogen en aantal installaties op woningen per gemeente en provincie, 2012–2019 | ja, 2012–2018 | Enige regionale reeks vóór 2019. Gemeentelijke indeling 2019 voor alle jaren; Zwolle en beide provincies veranderden niet van grens. |
        | 85005NED Zonnestroom; vermogen en vermogensklasse, bedrijven en woningen, regio | Zelfde grootheden, 2019–2025 | ja, 2019–2025 | Opvolger van 84783NED. 2019 staat in beide tabellen en is identiek (gecontroleerd hieronder), dus de reeksen sluiten aan zonder breuk. |
        | 85523NED Warmtepompen; aantallen, thermisch vermogen en energiestromen | Opgestelde warmtepompen in woningen per type, 1994–2025 | ja | Enige tabel met aantallen warmtepompen, maar **alleen voor heel Nederland**. |
        | 84948NED Woningen; hoofdverwarmingsinstallaties, regio 2017-2022 | Aandeel woningen per type verwarming, per gemeente en provincie | ja, als apart feit | Telt geen warmtepompen. "Aardgasvrij" (elektrisch of stadsverwarming zonder gas) is wel een regionale maat voor dezelfde overstap, en wordt alleen onder die naam getoond. |
        | 84948NED wijk- en buurttabellen 84950NED … 85677NED | Zelfde indeling per buurt, per jaar | nee | Regio-tabel 84948NED dekt dezelfde jaren voor gemeenten en provincies. |
        | 86044NED e.a. Zonnestroom; wijken en buurten | Vermogen per buurt, één jaar per tabel | nee | Fijner dan nodig; 84783NED/85005NED geven de jaarreeks per gemeente. |
        | 82380NED Warmtepompen 1994-2021 | Voorganger van 85523NED | nee | Stopgezet; 85523NED loopt verder en is ook alleen landelijk. |
        """
    )
    return


@app.cell
def _(nb):
    # Solar on woningen: 84783NED up to 2018, 85005NED from 2019. Both tables carry 2019,
    # which is used below to prove the two series join.
    zon_alle = nb.sql(
        """
        SELECT '84783NED' AS tabel, year, period_status, RegioS, measure, value
        FROM core.t84783ned
        WHERE BedrijfstakkenWoningen = 'E007037'
          AND RegioS IN ('GM0193', 'PV23', 'PV22', 'NL01')
          AND measure IN ('M002460', 'M002461')
        UNION ALL
        SELECT '85005NED', year, period_status, RegioS, measure, value
        FROM core.t85005ned
        WHERE SectorEnVermogensklasse = 'E007037'
          AND RegioS IN ('GM0193', 'PV23', 'PV22', 'NL01')
          AND measure IN ('M002460', 'M002461')
        ORDER BY RegioS, measure, year, tabel
        """
    )
    zon_alle
    return (zon_alle,)


@app.cell
def _(zon_alle):
    # Two tables, one number: every 2019 value must be identical in both tables.
    _o = zon_alle[zon_alle["year"] == 2019].pivot_table(
        index=["RegioS", "measure"], columns="tabel", values="value"
    )
    assert len(_o) == 8 and (_o["84783NED"] == _o["85005NED"]).all(), _o
    zon = zon_alle[
        ((zon_alle["tabel"] == "84783NED") & (zon_alle["year"] <= 2018))
        | ((zon_alle["tabel"] == "85005NED") & (zon_alle["year"] >= 2019))
    ].copy()
    zon["voorlopig"] = zon["period_status"] != "Definitief"
    return (zon,)


@app.cell
def _(mo, zon):
    _jaren = sorted(int(y) for y in zon["year"].unique())
    basisjaar = mo.ui.dropdown(
        options=[str(y) for y in _jaren[:-1]], value="2019", label="Basisjaar index (= 100)"
    )
    mo.vstack(
        [
            mo.md(
                "In de eerste jaren lagen er zo weinig panelen dat een index vanaf 2012 vooral "
                "dat lage begin laat zien. Standaard staat de basis op 2019, het eerste jaar van "
                "de huidige CBS-tabel. Kies een ander jaar en de grafiek rekent mee."
            ),
            basisjaar,
        ]
    )
    return (basisjaar,)


@app.cell
def _(REGIO, TABLES, basisjaar, charts, go, nl, zon):
    _b = int(basisjaar.value)
    _kw = zon[zon["measure"] == "M002461"]
    _base = _kw[_kw["year"] == _b].set_index("RegioS")["value"]
    _kw = _kw.assign(index=100 * _kw["value"] / _kw["RegioS"].map(_base))
    _c = charts.colors(4)
    fig_zon = go.Figure()
    _labels = []
    for _i, (_code, _naam) in enumerate(REGIO.items()):
        _d = _kw[_kw["RegioS"] == _code].sort_values("year")
        _def = _d[~_d["voorlopig"]]
        _prov = _d[_d["year"] >= _def["year"].max()]
        _w = 3 if _i == 0 else 2
        fig_zon.add_trace(
            go.Scatter(
                x=_def["year"],
                y=_def["index"],
                name=_naam,
                mode="lines",
                line={"color": _c[_i], "width": _w},
                customdata=_def[["value", "tabel", "period_status"]],
                hovertemplate=(
                    f"{_naam} %{{x}}: index %{{y:,.0f}}<br>%{{customdata[0]:,.0f}} kWp "
                    "(%{customdata[2]}, %{customdata[1]})<extra></extra>"
                ),
            )
        )
        fig_zon.add_trace(
            go.Scatter(
                x=_prov["year"],
                y=_prov["index"],
                name=f"{_naam} (voorlopig)",
                mode="lines",
                line={"color": _c[_i], "width": _w, "dash": charts.PROVISIONAL_DASH},
                customdata=_prov[["value", "tabel", "period_status"]],
                hovertemplate=(
                    f"{_naam} %{{x}}: index %{{y:,.0f}}<br>%{{customdata[0]:,.0f}} kWp "
                    "(%{customdata[2]}, %{customdata[1]})<extra></extra>"
                ),
            )
        )
        _last = _d.iloc[-1]
        _labels.append((_last["year"], _last["index"], f"{_naam} {nl(_last['index'], 0)}", _c[_i]))
    charts.direct_labels(fig_zon, _labels)
    fig_zon.add_hline(y=100, line_color="#999", line_width=1)

    _end = _kw[_kw["year"] == _kw["year"].max()].set_index("RegioS")
    _y1 = int(_kw["year"].max())
    _f_z = _end.loc["GM0193", "value"] / _base["GM0193"]
    _f_nl = _end.loc["NL01", "value"] / _base["NL01"]
    _verb = "sneller" if _f_z > _f_nl else "langzamer"
    charts.style(
        fig_zon,
        title=(
            f"Zonnepanelen op woningen: Zwolle groeide sinds {_b} {_verb} dan Nederland "
            f"(×{nl(_f_z, 1)} tegen ×{nl(_f_nl, 1)})"
        ),
        x_title="Jaar (einde jaar)",
        y_title=f"Opgesteld vermogen, index ({_b} = 100)",
        tables=TABLES[:2],
        note=(
            f"Gestippeld: niet-definitieve cijfers ({', '.join(f'{int(y)} {st.lower().replace("nader", "nader ")}' for y, st in _kw.loc[_kw['voorlopig'], ['year', 'period_status']].drop_duplicates().sort_values('year').itertuples(index=False))}*). "
            "84783NED t/m 2018, 85005NED vanaf 2019; 2019 is in beide gelijk."
        ),
    )
    fig_zon.update_yaxes(rangemode="tozero")
    charts.checked(fig_zon)
    return (fig_zon,)


@app.cell
def _(REGIO, mo, nl, zon):
    # Level, not growth: kWp per installation, so the index above is not mistaken for size.
    _p = zon.pivot_table(index=["RegioS", "year"], columns="measure", values="value").reset_index()
    _y0, _y1 = int(_p["year"].min()), int(_p["year"].max())
    _rows = []
    for _code, _naam in REGIO.items():
        _a = _p[(_p["RegioS"] == _code) & (_p["year"] == _y0)].iloc[0]
        _e = _p[(_p["RegioS"] == _code) & (_p["year"] == _y1)].iloc[0]
        _rows.append(
            f"| {_naam} | {nl(_a['M002460'], 0)} | {nl(_e['M002460'], 0)} | "
            f"{nl(_e['M002461'] / 1000, 1)} | {nl(_e['M002461'] / _e['M002460'], 1)} |"
        )
    mo.md(
        f"### Zonnepanelen op woningen, {_y0} en {_y1}*\n\n"
        f"| Regio | Installaties {_y0} | Installaties {_y1}* | Vermogen {_y1}* (MWp) | kWp per installatie {_y1}* |\n"
        "|---|---:|---:|---:|---:|\n" + "\n".join(_rows) + "\n\n"
        f"\\* {_y1}: nader voorlopig. Bron: CBS 84783NED ({_y0}), 85005NED ({_y1})."
    )
    return


@app.cell
def _(nb):
    # Heat pumps in woningen, Nederland only (the table has no regions), per type.
    wp = nb.sql(
        """
        SELECT year, period_status, Warmtepompen, Warmtepompen_title, value
        FROM core.t85523ned
        WHERE Sector = 'E007037' AND measure = 'D002272'
          AND Warmtepompen IN ('T001364', 'A043945', 'A043949', 'A043950')
          AND year >= 2012
        ORDER BY Warmtepompen, year
        """
    )
    wp
    return (wp,)


@app.cell
def _(TABLES, charts, go, nl, wp):
    _types = {
        "A043949": "Buitenlucht-lucht",
        "A043950": "Buitenlucht-water",
        "A043945": "Bodem of water",
    }
    _c = charts.colors(3)
    fig_wp = go.Figure()
    _labels = []
    for _i, (_code, _naam) in enumerate(_types.items()):
        _d = wp[wp["Warmtepompen"] == _code].sort_values("year")
        _def = _d[_d["period_status"] == "Definitief"]
        _prov = _d[_d["year"] >= _def["year"].max()]
        for _s, _dash, _sfx in ((_def, None, ""), (_prov, charts.PROVISIONAL_DASH, " (voorlopig)")):
            fig_wp.add_trace(
                go.Scatter(
                    x=_s["year"],
                    y=_s["value"] / 1000,
                    name=_naam + _sfx,
                    mode="lines",
                    line={"color": _c[_i], "width": 2.5, "dash": _dash},
                    customdata=_s[["period_status"]],
                    hovertemplate=(
                        f"{_naam} %{{x}}: %{{y:,.0f}} duizend (%{{customdata[0]}}, 85523NED)"
                        "<extra></extra>"
                    ),
                )
            )
        _l = _d.iloc[-1]
        _labels.append((_l["year"], _l["value"] / 1000, _naam, _c[_i]))
    charts.direct_labels(fig_wp, _labels)

    _tot = wp[wp["Warmtepompen"] == "T001364"].set_index("year")["value"]
    _ll = wp[wp["Warmtepompen"] == "A043949"].set_index("year")["value"]
    _y1 = int(_tot.index.max())
    charts.style(
        fig_wp,
        title=(
            f"{nl(100 * _ll[_y1] / _tot[_y1], 0)}% van de warmtepompen in woningen is "
            f"buitenlucht-lucht ({_y1}*)"
        ),
        x_title="Jaar (einde jaar)",
        y_title="Opgestelde warmtepompen in woningen (duizend)",
        tables=[TABLES[2]],
        note=(
            "Alleen Nederland: CBS publiceert geen warmtepompen per gemeente of provincie. "
            "Gestippeld: nader voorlopig*.<br>Buitenlucht-lucht verwarmt (en koelt) via de lucht "
            "in de kamer, zoals een airco-split."
        ),
    )
    fig_wp.update_yaxes(rangemode="tozero")
    charts.checked(fig_wp)
    return (fig_wp,)


@app.cell
def _(nb):
    # Aardgasvrije woningen (A052175 = stadsverwarming of elektrisch, beide zonder gas), %.
    # The Nederland total sits under NL00 in this table; NL01 is empty ("Impossible").
    gasvrij = nb.sql(
        """
        SELECT year, period_status, RegioS, RegioS_title, value
        FROM core.t84948ned
        WHERE TypeVerwarmingsinstallatie = 'A052175'
          AND RegioS IN ('GM0193', 'PV23', 'PV22', 'NL00')
        ORDER BY RegioS, year
        """
    )
    assert gasvrij["value"].notna().all(), gasvrij
    gasvrij
    return (gasvrij,)


@app.cell
def _(TABLES, charts, gasvrij, go, nl):
    _reg = {"GM0193": "Zwolle", "PV23": "Overijssel", "PV22": "Drenthe", "NL00": "Nederland"}
    _c = charts.colors(4)
    fig_gasvrij = go.Figure()
    _labels = []
    for _i, (_code, _naam) in enumerate(_reg.items()):
        _d = gasvrij[gasvrij["RegioS"] == _code].sort_values("year")
        _def = _d[_d["period_status"] == "Definitief"]
        _prov = _d[_d["year"] >= _def["year"].max()]
        _w = 3 if _i == 0 else 2
        for _s, _dash, _sfx in ((_def, None, ""), (_prov, charts.PROVISIONAL_DASH, " (voorlopig)")):
            fig_gasvrij.add_trace(
                go.Scatter(
                    x=_s["year"],
                    y=_s["value"],
                    name=_naam + _sfx,
                    mode="lines+markers",
                    line={"color": _c[_i], "width": _w, "dash": _dash},
                    marker={"color": _c[_i], "size": 6},
                    customdata=_s[["period_status"]],
                    hovertemplate=(
                        f"{_naam} %{{x}}: %{{y:,.1f}}% (%{{customdata[0]}}, 84948NED)<extra></extra>"
                    ),
                )
            )
        _l = _d.iloc[-1]
        _labels.append((_l["year"], _l["value"], f"{_naam} {nl(_l['value'], 1)}%", _c[_i]))
    charts.direct_labels(fig_gasvrij, _labels)
    _e = gasvrij[gasvrij["year"] == gasvrij["year"].max()].set_index("RegioS")["value"]
    _y1 = int(gasvrij["year"].max())
    _verb = "boven" if _e["GM0193"] > _e["NL00"] else "onder"
    charts.style(
        fig_gasvrij,
        title=(
            f"Aardgasvrije woningen: Zwolle {nl(_e['GM0193'], 1)}%, {_verb} het landelijke "
            f"{nl(_e['NL00'], 1)}% ({_y1}*)"
        ),
        x_title="Jaar (woningvoorraad 1 januari)",
        y_title="Aardgasvrije woningen (% van de voorraad)",
        tables=[TABLES[3]],
        note=(
            "Aardgasvrij = stadsverwarming of elektrisch verwarmd, beide zonder gasverbruik. "
            "<br>Dat is géén telling van warmtepompen: hybride warmtepompen gebruiken gas en vallen "
            f"erbuiten.<br>Gestippeld: voorlopig ({_y1}*). Tabel is stopgezet na {_y1}."
        ),
    )
    fig_gasvrij.update_layout(margin={"b": 160})
    fig_gasvrij.update_yaxes(rangemode="tozero")
    charts.checked(fig_gasvrij)
    return (fig_gasvrij,)


@app.cell
def _(basisjaar, gasvrij, mo, nl, wp, zon):
    # Answer text: every number interpolated from the query results above.
    _b = int(basisjaar.value)
    _kw = zon[zon["measure"] == "M002461"].pivot_table(index="year", columns="RegioS", values="value")
    _y1 = int(_kw.index.max())
    _f = (_kw.loc[_y1] / _kw.loc[_b]).to_dict()
    _wt = wp[wp["Warmtepompen"] == "T001364"].set_index("year")["value"]
    _wy0, _wy1 = _b, int(_wt.index.max())
    _g = gasvrij.pivot_table(index="year", columns="RegioS", values="value")
    _gy0, _gy1 = int(_g.index.min()), int(_g.index.max())
    mo.md(
        f"""
**Antwoord.**

- **Zonnepanelen (wel per gemeente):** het opgestelde vermogen op woningen werd tussen {_b} en
  {_y1}* in Zwolle ×{nl(_f['GM0193'], 1)}, in Overijssel ×{nl(_f['PV23'], 1)}, in Drenthe
  ×{nl(_f['PV22'], 1)} en in heel Nederland ×{nl(_f['NL01'], 1)}.
- **Warmtepompen (alleen landelijk):** in woningen stonden er eind {_wy0}
  {nl(_wt[_wy0] / 1000, 0)} duizend en eind {_wy1}* {nl(_wt[_wy1] / 1000, 0)} duizend
  (×{nl(_wt[_wy1] / _wt[_wy0], 1)}). Het grootste deel daarvan is buitenlucht-lucht.
- **Aardgasvrije woningen (regionaal, maar geen warmtepompen):** Zwolle ging van
  {nl(_g.loc[_gy0, 'GM0193'], 1)}% naar {nl(_g.loc[_gy1, 'GM0193'], 1)}% ({_gy0}–{_gy1}*),
  Overijssel van {nl(_g.loc[_gy0, 'PV23'], 1)}% naar {nl(_g.loc[_gy1, 'PV23'], 1)}%, Drenthe van
  {nl(_g.loc[_gy0, 'PV22'], 1)}% naar {nl(_g.loc[_gy1, 'PV22'], 1)}%, Nederland van
  {nl(_g.loc[_gy0, 'NL00'], 1)}% naar {nl(_g.loc[_gy1, 'NL00'], 1)}%.

\\* voorlopig of nader voorlopig.
"""
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Niet beschikbaar

        - **Warmtepompen per gemeente of provincie.** 85523NED (en voorganger 82380NED) telt
          warmtepompen alleen voor heel Nederland. De regionale verwarmingstabel 84948NED
          (en de buurttabellen 84950NED t/m 85677NED) delen woningen in naar gasgebruik en
          onderscheiden geen warmtepomp. Een all-electric warmtepomp valt onder "elektrisch
          verwarmd zonder gas", maar daar vallen ook elektrische kachels onder, en hybride
          warmtepompen vallen er juist buiten. Daarom is het aardgasvrije aandeel hierboven
          als apart feit getoond en niet als warmtepompen.
        - **De WDODelta-gemeenten als geheel.** CBS publiceert geen cijfers per waterschap.
          Een optelling van gemeenten zou een eigen indeling vragen (`Aanname, niet CBS`);
          dit notebook laat de provincies Overijssel en Drenthe zien in plaats daarvan, onder
          hun eigen naam.
        - **Aardgasvrije woningen na 2022.** 84948NED is stopgezet wegens een methodewijziging;
          CBS kondigt een nieuwe regionale tabel aan.
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

        De 2019-waarden van 84783NED en 85005NED (aantal en vermogen, vier regio's) zijn
        identiek; het notebook stopt als dat niet zo is.

        | Waarde | Tabel en selectie | Status | StatLine | Gecontroleerd |
        |---|---|---|---|---|
        | Zonnepanelen op woningen Zwolle 2025: 93.337 kWp | 85005NED, RegioS GM0193 Zwolle, SectorEnVermogensklasse E007037 Woningen, M002461 Opgesteld vermogen van zonnepanelen, 2025 | nader voorlopig | https://opendata.cbs.nl/#/CBS/nl/dataset/85005NED/table | 2026-10-17, `datchat verify 84783NED 85005NED 85523NED 84948NED --cross-check`: 36/36 checks geslaagd; alle waarden in de vier tabellen identiek aan de v3-API |
        | Warmtepompen in woningen eind 2025: 2.567.794 | 85523NED, Sector E007037 Woningen, Warmtepompen T001364 totaal, D002272 Opgestelde warmtepompen einde van jaar, 2025 | nader voorlopig | https://opendata.cbs.nl/#/CBS/nl/dataset/85523NED/table | idem |
        | Aardgasvrije woningen Zwolle 2022: 5,7% | 84948NED, RegioS GM0193 Zwolle, TypeVerwarmingsinstallatie A052175 Totaal zonder gasverbruik (ex. onbekend), A007233 Woningen, 2022 | voorlopig | https://opendata.cbs.nl/#/CBS/nl/dataset/84948NED/table | idem |
        """
    )
    return


if __name__ == "__main__":
    app.run()
