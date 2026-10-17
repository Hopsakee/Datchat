import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import plotly.graph_objects as go

    from datchat import charts, nb

    TABLES = ["82027NED", "80059ned"]
    nb.require(TABLES)

    def nl(v, d=0):
        """Dutch number formatting for text: 12.345,6."""
        return f"{v:,.{d}f}".replace(",", "_").replace(".", ",").replace("_", ".")

    def add_series(fig, d, y, name, color, width, hover, custom):
        """Definitive years as a solid line; provisional years (if any) as a dotted tail."""
        d = d.sort_values("year")
        _def = d[d["period_status"] == "Definitief"]
        fig.add_trace(
            go.Scatter(
                x=_def["year"], y=_def[y], name=name, mode="lines",
                line={"color": color, "width": width},
                customdata=_def[custom], hovertemplate=hover,
            )
        )
        if (d["period_status"] != "Definitief").any():
            _tail = d[d["year"] >= _def["year"].max()]
            fig.add_trace(
                go.Scatter(
                    x=_tail["year"], y=_tail[y], name=f"{name} (voorlopig)",
                    mode="lines+markers",
                    line={"color": color, "width": 2, "dash": charts.PROVISIONAL_DASH},
                    marker={"color": color, "size": [0] + [7] * (len(_tail) - 1)},
                    customdata=_tail[custom], hovertemplate=hover,
                )
            )

    def jaar_titel(df):
        """X-axis title naming the provisional years, if there are any."""
        _v = sorted(df.loc[df["period_status"] != "Definitief", "year"].unique())
        if not _v:
            return "Jaar"
        return f"Jaar (* {', '.join(str(int(y)) for y in _v)} voorlopig, stippellijn)"

    return TABLES, add_series, charts, go, jaar_titel, mo, nb, nl


@app.cell
def _(mo):
    mo.md(
        r"""
        # Stemgedrag naast azc's en immigratie: CBS heeft alleen de immigratiekant

        **Vraag:** what is the relationship in the Netherlands with voting patterns for both
        local government parties and national parties through the years when compared to both
        the existence of an asylum nearby and also the influx of immigrants. Distinguish this
        influx into the different kinds of immigrants that we distinguish in the Netherlands.
        So at least the fugitives separate from the people commimg here for work or study or
        family reunion.

        **Kort:** het verband zelf is met CBS StatLine **niet te leggen**. CBS publiceert
        verkiezingsuitslagen per gemeente alleen voor 2002 en 2003 (daarna niets per gemeente;
        de Tweede Kamer landelijk tot en met 2006) en geen locaties of capaciteit van
        asielzoekerscentra. Wat CBS wél heeft, zijn landelijke jaarcijfers per soort migrant:
        eerste verblijfsvergunningen naar grond (asiel, gezin, studie, arbeid) en
        asielverzoeken. Dat deel staat hieronder; de rest staat onder *Niet beschikbaar*.
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
        | 82027NED Verblijfsvergunningen voor bepaalde tijd; verblijfsgrond en nationaliteit | Eerste verblijfsvergunningen per jaar naar grond: asiel, gezin, studie, arbeid, overig; 2008–2025 | ja | Precies de gevraagde splitsing vluchtelingen / werk / studie / gezin. Alleen landelijk, alleen niet-EU/EFTA (EU-burgers hebben geen vergunning nodig). |
        | 80059ned Asielverzoeken; nationaliteit, vanaf 1975 | Asielverzoeken en nareizigers per jaar, 1975–2025 | ja | De asielinstroom over de lange termijn, ook in de jaren van de oude verkiezingstabellen. Alleen landelijk. |
        | 84809NED Immigranten niet EU/EFTA; migratiemotief | Immigranten (niet ingezetenen met vergunning) naar motief, 1999–2025 | nee | De juiste bron voor *immigranten* naar motief, maar 57 mln rijen: `datchat sync` laadt alleen hele tabellen en liep na bijna 5 minuten vast. Geen regio-dimensie, dus ook deze tabel legt geen verband met gemeenten. |
        | 84808NED Immigranten EU/EFTA; afgeleid migratiedoel | EU-immigranten naar afgeleid doel (arbeid, gezin, studie), 1999–2024 | nee | Zelfde probleem: 23 mln rijen, niet te laden. Zonder deze tabel ontbreekt de EU-arbeidsmigratie in dit notebook. Geen regio-dimensie. |
        | 85468NED Immigratie en emigratie; geslacht, leeftijd, geboorteland, regio | Immigratie per gemeente, 2010–2025 | nee | Wel per gemeente, maar zonder migratiemotief, dus asiel niet te scheiden van werk, studie of gezin. 26 mln rijen. |
        | 37278 Verkiezingen; historische uitslagen Tweede Kamer | Landelijke uitslag per partij, 1918–2006 | nee | Alleen landelijk en stopt in 2006. Een tijdlijn van landelijke uitslagen naast landelijke asielaantallen laat gelijktijdigheid zien, geen verband. |
        | 70097NED Verkiezing gemeenteraden, 2002 | Stemmen per partij per gemeente, inclusief lokale groeperingen, 2002 | nee | Eén verkiezing. Er is geen migratie-naar-motief per gemeente om het mee te vergelijken. |
        | 70075NED, 70163NED Verkiezing Tweede Kamer, 2002 en 2003 | Stemmen per partij per gemeente (± 490 gemeenten) | nee | Twee verkiezingen kort na elkaar, en ook hier geen migratie of azc-gegevens per gemeente om het mee te vergelijken. |
        | 71277NED Verkiezingen; 2006 uitslag Tweede Kamer | Landelijke uitslag 2006 | nee | Eén verkiezing, landelijk. |
        | 82025NED Uitgenodigde vluchtelingen | Hervestigde vluchtelingen (resettlement), 2008–2025 | nee | Een kleine deelgroep die al in de asielvergunningen van 82027NED zit. |
        | — (azc-locaties) | — | nee | Geen enkele StatLine-tabel bevat azc's of asielopvang per gemeente; zoektermen *azc*, *asielzoekerscentrum*, *opvang*, *COA* leveren niets relevants op (alleen kinderopvang, maatschappelijke opvang en kolen). |
        """
    )
    return


@app.cell
def _(nb):
    # Eerste verblijfsvergunningen naar grond, Nederland totaal (Nationaliteit T001059).
    #   D004501_2 asiel totaal          D004505  regulier totaal
    #   D004506_2 gezinshereniging/-vorming     D004510 studie       D004512 arbeid totaal
    #   D004515_2 overig regulier       D004516  slachtoffer mensenhandel
    vergunning = nb.sql(
        """
        SELECT year, period_status, measure, value
        FROM core.t82027ned
        WHERE Nationaliteit = 'T001059'
          AND measure IN ('D004501_2', 'D004505', 'D004506_2', 'D004510', 'D004512',
                          'D004515_2', 'D004516')
        ORDER BY year, measure
        """
    )
    vergunning
    return (vergunning,)


@app.cell
def _(vergunning):
    GROND = {
        "D004501_2": "Asiel",
        "D004506_2": "Gezin",
        "D004510": "Studie",
        "D004512": "Arbeid",
        "Overig": "Overig regulier",
    }
    _w = vergunning.pivot_table(
        index=["year", "period_status"], columns="measure", values="value"
    ).reset_index()
    assert _w.notna().all().all(), "ontbrekende waarden"
    # Regulier = gezin + studie + arbeid + overig + mensenhandel, in elk jaar. CBS rounds every
    # cell to a multiple of 5, so the five parts may miss the total by a few fives (max 10 seen).
    _diff = (
        _w[["D004506_2", "D004510", "D004512", "D004515_2", "D004516"]].sum(axis=1) - _w["D004505"]
    ).abs()
    assert (_diff <= 15).all(), _w.loc[_diff > 15, "year"]
    _w["Overig"] = _w["D004515_2"] + _w["D004516"]
    _w["totaal"] = _w["D004501_2"] + _w["D004505"]
    grond = _w.melt(
        id_vars=["year", "period_status", "totaal"],
        value_vars=list(GROND),
        var_name="code",
        value_name="aantal",
    )
    grond["grond"] = grond["code"].map(GROND)
    grond["aandeel"] = 100 * grond["aantal"] / grond["totaal"]
    return GROND, grond


@app.cell
def _(GROND, add_series, charts, go, grond, jaar_titel, nl):
    _kleur = dict(
        zip(GROND.values(), [charts.ACCENT, *charts.GREYS[:3], charts.GREYS[5]], strict=True)
    )
    fig_motief = go.Figure()
    _labels = []
    for _g in GROND.values():
        _d = grond[grond["grond"] == _g].sort_values("year")
        _hover = (
            f"{_g} %{{x}}: %{{y:,.0f}} eerste vergunningen"
            "<br>%{customdata[0]:,.1f}% van alle eerste vergunningen"
            " (82027NED, %{customdata[1]})<extra></extra>"
        )
        add_series(
            fig_motief, _d, "aantal", _g, _kleur[_g], 3 if _g == "Asiel" else 2, _hover,
            ["aandeel", "period_status"],
        )
        _l = _d.iloc[-1]
        _labels.append((_l["year"], _l["aantal"], f"{_g} {nl(_l['aantal'])}", _kleur[_g]))
    charts.direct_labels(fig_motief, _labels)

    _y1 = int(grond.loc[grond["period_status"] == "Definitief", "year"].max())
    _last = grond[grond["year"] == _y1].set_index("grond")
    _top = _last["aantal"].idxmax()
    charts.style(
        fig_motief,
        title=(
            f"{_top} is de grootste grond voor een eerste verblijfsvergunning; "
            f"asiel was {nl(_last.loc['Asiel', 'aandeel'], 1)}% in {_y1}"
        ),
        x_title=jaar_titel(grond),
        y_title="Eerste verblijfsvergunningen (aantal)",
        tables=["82027NED"],
        note=(
            "Alleen niet-EU/EFTA-nationaliteiten: EU-burgers hebben geen verblijfsvergunning "
            "nodig, dus EU-arbeidsmigratie ontbreekt.<br>Overig regulier = overige reguliere "
            "vergunningen + slachtoffers mensenhandel. Afgerond op vijftallen. Landelijk; CBS "
            "publiceert dit niet per gemeente."
        ),
    )
    fig_motief.update_yaxes(rangemode="tozero", showgrid=False)
    fig_motief.update_xaxes(
        showgrid=False, dtick=2, range=[grond["year"].min() - 0.3, grond["year"].max() + 0.3]
    )
    charts.checked(fig_motief)
    return (fig_motief,)


@app.cell
def _(nb):
    # Asielverzoeken en nareizigers, Nederland totaal.
    #   D004634 totaal asielverzoeken en nareizigers   D004637 eerste asielverzoeken
    #   D000099 volgende asielverzoeken                M007134 nareizigers
    asiel = nb.sql(
        """
        SELECT year, period_status,
               max(CASE WHEN measure = 'D004634' THEN value END) AS totaal,
               max(CASE WHEN measure = 'D004637' THEN value END) AS eerste,
               max(CASE WHEN measure = 'D000099' THEN value END) AS volgende,
               max(CASE WHEN measure = 'M007134' THEN value END) AS nareizigers
        FROM core.t80059ned
        WHERE Nationaliteit = 'T001059'
        GROUP BY year, period_status
        ORDER BY year
        """
    )
    asiel
    return (asiel,)


@app.cell
def _(add_series, asiel, charts, go, jaar_titel, nl):
    # Method break (CBS toelichting 80059ned): nareizigers are counted from 2013 on, so the
    # total before and after is a different quantity. Two segments, never one connected line.
    # (Before 2007 CBS could not split first and follow-up requests, but the plotted total
    # covers all requests on both sides of 2007, so that is not a break in this series.)
    _seg = [
        (1975, 2012, "asielverzoeken"),
        (2013, 2100, "asielverzoeken en nareizigers"),
    ]
    fig_asiel = go.Figure()
    for _a, _b, _naam in _seg:
        _d = asiel[(asiel["year"] >= _a) & (asiel["year"] <= _b)]
        _hover = f"%{{x}}: %{{y:,.0f}} {_naam} (80059ned, %{{customdata}})<extra></extra>"
        add_series(fig_asiel, _d, "totaal", _naam, charts.ACCENT, 2.5, _hover, "period_status")
    fig_asiel.add_vline(x=2012.5, line_dash="dot", line_color="#999", line_width=1)

    _recent = asiel[(asiel["year"] >= 2013) & (asiel["period_status"] == "Definitief")]
    _pk = _recent.loc[_recent["totaal"].idxmax()]
    charts.style(
        fig_asiel,
        title=(
            f"Sinds 2013 piekte de asielinstroom in {int(_pk['year'])}: "
            f"{nl(_pk['totaal'])} asielverzoeken en nareizigers"
        ),
        x_title=jaar_titel(asiel),
        y_title="Asielverzoeken, vanaf 2013 incl. nareizigers (aantal)",
        tables=["80059ned"],
        note=(
            "Stippellijn bij 2013: vanaf dan telt CBS nareizigers (gezinsleden van een "
            "asielvergunninghouder) mee;<br>daarvoor zijn het alleen asielverzoeken. Vanaf 2016 "
            "inclusief relocatie. Landelijk; CBS publiceert dit niet per gemeente."
        ),
    )
    fig_asiel.update_yaxes(rangemode="tozero", showgrid=False)
    fig_asiel.update_xaxes(
        showgrid=False, dtick=5, range=[asiel["year"].min() - 0.5, asiel["year"].max() + 0.5]
    )
    charts.checked(fig_asiel)
    return (fig_asiel,)


@app.cell
def _(asiel, grond, mo, nl):
    # Answer text: numbers are interpolated from query results, never typed.
    _y1 = int(grond.loc[grond["period_status"] == "Definitief", "year"].max())
    _y0 = int(grond["year"].min())
    _p = grond.pivot_table(index="grond", columns="year", values="aantal")
    # CBS's own total (asiel + regulier), not the sum of the rounded parts.
    _tot = grond.drop_duplicates("year").set_index("year")["totaal"]
    _a = _p.loc["Asiel"]
    _reg1 = _tot[_y1] - _a[_y1]
    _r = asiel[(asiel["year"] >= 2013) & (asiel["period_status"] == "Definitief")].iloc[-1]
    mo.md(
        f"""
        **Antwoord (alleen het immigratiedeel):** in {_y1} kregen
        {nl(_tot[_y1])} niet-EU-burgers een eerste verblijfsvergunning, tegen
        {nl(_tot[_y0])} in {_y0}. Daarvan waren er {nl(_a[_y1])} asielvergunningen en
        {nl(_reg1)} reguliere: {nl(_p.loc['Gezin', _y1])} voor gezin,
        {nl(_p.loc['Studie', _y1])} voor studie en {nl(_p.loc['Arbeid', _y1])} voor arbeid.
        Asielvergunningen piekten in die reeks in {int(_a.idxmax())} ({nl(_a.max())}). In
        {int(_r['year'])} kwamen er {nl(_r['eerste'])} eerste asielverzoeken en
        {nl(_r['nareizigers'])} nareizigers binnen.

        Vergunningen en verzoeken zijn niet hetzelfde getal. Een vergunning telt in het jaar
        van het besluit, niet van aankomst; niet elk verzoek wordt toegewezen; en de
        asielvergunningen omvatten ook die voor nareizigers. Daarom verschillen de twee
        grafieken in hetzelfde jaar.

        Hoe dit samenhangt met stemgedrag of met een azc in de buurt, kan uit CBS-data niet
        worden afgeleid: zie *Niet beschikbaar*.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Niet beschikbaar

        **Stemgedrag, lokaal en landelijk, door de jaren heen.** CBS publiceerde
        verkiezingsuitslagen tot en met 2006 en is daarmee gestopt. Wat er nog staat:
        Tweede Kamer landelijk 1918–2006 (37278, 71277NED), de Tweede Kamer per gemeente in
        2002 en 2003 (70075NED, 70163NED) en de gemeenteraadsverkiezing van 2002 per gemeente,
        inclusief lokale groeperingen (70097NED, 70096NED). Per gemeente zijn dat drie
        verkiezingen binnen veertien maanden, en niets na 2003. Een reeks door de jaren heen
        komt van de Kiesraad, niet van CBS.

        **Een azc in de buurt.** Geen StatLine-tabel bevat locaties, capaciteit of bezetting van
        asielzoekerscentra per gemeente. De bron daarvoor is het COA.

        **Migratie naar soort migrant per gemeente.** De tabellen met migratiemotief (82027NED,
        84809NED, 84808NED, 80059ned) zijn alle landelijk. De enige tabel met immigratie per
        gemeente (85468NED) splitst naar geboorteland, niet naar motief.

        **EU-arbeidsmigratie.** 84808NED heeft EU-immigranten naar afgeleid doel, maar is met
        23 mln rijen niet te laden met `datchat sync`. Daarom ontbreekt die groep in de
        grafiek met vergunningen.

        Zonder uitslagen per gemeente en zonder azc-locaties valt er in CBS-data niets te
        correleren. Een landelijke tijdlijn van uitslagen naast landelijke asielaantallen laat
        alleen zien dat dingen tegelijk gebeuren, en is daarom weggelaten.
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
        | 31.120 eerste asielvergunningen | 82027NED, D004501_2 Totaal verblijfsvergunningen asiel, Nationaliteit T001059 Totaal, 2024 | Definitief | https://opendata.cbs.nl/#/CBS/nl/dataset/82027NED/table | 2026-10-17; `datchat verify --cross-check`: 28.348 waarden gelijk aan v3 API, versie actueel |
        | 42.210 eerste vergunningen gezin | 82027NED, D004506_2 Totaal gezinshereniging / gezinsvorming, Nationaliteit T001059 Totaal, 2024 | Definitief | https://opendata.cbs.nl/#/CBS/nl/dataset/82027NED/table | 2026-10-17; zelfde cross-check |
        | 58.880 asielverzoeken en nareizigers | 80059ned, D004634 Totaal asielverzoeken en nareizigers, Nationaliteit T001059 Totaal, 2015 | Definitief | https://opendata.cbs.nl/#/CBS/nl/dataset/80059ned/table | 2026-10-17; `datchat verify --cross-check`: 8.186 waarden gelijk aan v3 API, versie actueel |
        """
    )
    return


if __name__ == "__main__":
    app.run()
