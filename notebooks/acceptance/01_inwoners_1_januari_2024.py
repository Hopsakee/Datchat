import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    from datchat import nb

    TABLES = ["85496NED", "7461bev"]
    nb.require(TABLES)
    return TABLES, mo, nb


@app.cell
def _(mo):
    mo.md(
        r"""
        # Inwoners van Nederland op 1 januari 2024

        **Vraag:** Hoeveel inwoners had Nederland op 1 januari 2024?
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
        | 85496NED Bevolking; kerncijfers | Totale bevolking op 1 januari, 1950–2025 | ja, antwoord | Actuele kerncijfertabel; *Totale bevolking* per 1 januari, status Definitief. |
        | 7461bev Bevolking; geslacht, leeftijd en burgerlijke staat, 1 januari | Bevolking naar geslacht, leeftijd en burgerlijke staat, 1950–2026 | ja, controle | Onafhankelijke tweede tabel: totaal over alle leeftijden, geslachten en burgerlijke staten moet gelijk zijn. |
        | 37296ned Bevolking; kerncijfers, 1950-2022 | Idem, tot en met 2022 | nee | Stopgezet; bevat 2024 niet (opgevolgd door 85496NED). |
        """
    )
    return


@app.cell
def _(nb):
    # The answer: Totale bevolking (measure T001038_2, group "Bevolking naar geslacht").
    antwoord = nb.sql(
        """
        SELECT year, period_status, measure_title, unit, value
        FROM core.t85496ned
        WHERE measure = 'T001038_2' AND Perioden = '2024JJ00'
        """
    )
    antwoord
    return (antwoord,)


@app.cell
def _(nb):
    # Independent check: the same count in a different table, summed nowhere, just the total
    # category of each dimension.
    controle = nb.sql(
        """
        SELECT '85496NED' AS tabel, value FROM core.t85496ned
        WHERE measure = 'T001038_2' AND Perioden = '2024JJ00'
        UNION ALL
        SELECT '7461bev', value FROM core.t7461bev
        WHERE measure = 'M000352' AND Perioden = '2024JJ00'
          AND Geslacht = 'T001038'          -- Totaal mannen en vrouwen
          AND Leeftijd = '10000'            -- Totaal leeftijd
          AND BurgerlijkeStaat = 'T001019'  -- Totaal burgerlijke staat
        """
    )
    assert controle["value"].nunique() == 1, f"Tables disagree: {controle.to_dict('records')}"
    controle
    return (controle,)


@app.cell
def _(antwoord, controle, mo):
    _r = antwoord.iloc[0]
    _n = f"{int(_r['value']):,}".replace(",", ".")
    mo.md(
        f"""
        **Antwoord:** op 1 januari {int(_r["year"])} had Nederland **{_n} inwoners**
        ({_r["period_status"].lower()} cijfer, CBS StatLine 85496NED).
        Tabel 7461bev geeft hetzelfde aantal ({len(controle)} tabellen, één waarde).

        *Definitie (CBS):* personen die zijn opgenomen in het bevolkingsregister van een
        Nederlandse gemeente, dus zonder bijvoorbeeld diplomaten, NAVO-militairen en personen
        die niet legaal in Nederland verblijven.
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
        | 17.942.942 | 85496NED · *Bevolking naar geslacht / Totale bevolking* (T001038_2) · 2024 | Definitief | https://opendata.cbs.nl/#/CBS/nl/dataset/85496NED/table | 2026-09-28: `datchat verify 85496NED --cross-check`, alle 3.345 waarden gelijk aan de v4-bulk-CSV (v3 heeft andere labels voor herkomst) |
        | 17.942.942 | 7461bev · Totaal mannen en vrouwen · Totaal leeftijd · Totaal burgerlijke staat · 2024 | geen status in metadata; toelichting: "Alle in de tabel opgenomen cijfers zijn definitief" | https://opendata.cbs.nl/#/CBS/nl/dataset/7461bev/table | 2026-09-28: `datchat verify 7461bev --cross-check`, alle 131.591 waarden gelijk aan de v3-API |
        """
    )
    return


if __name__ == "__main__":
    app.run()
