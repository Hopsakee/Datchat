import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    from datchat import nb

    # Tables inspected (synced) to establish what CBS does and doesn't publish.
    TABLES = ["84476NED", "86160NED", "37662"]
    nb.require(TABLES)
    return TABLES, mo, nb


@app.cell
def _(mo):
    mo.md(
        r"""
        # Vermogen van de top 0,01% per gemeente in 1950: niet beschikbaar

        **Vraag:** Vermogen van de top 0,01% per gemeente in 1950.
        """
    )
    return


@app.cell
def _(nb):
    # What each candidate table covers, read from CBS's own metadata (no typed facts):
    # finest top group, whether there is a municipal breakdown, and the years covered.
    dekking = nb.sql(
        """
        WITH groups AS (
            SELECT table_id,
                   CASE WHEN bool_or(title ILIKE '%top 0,1%%') THEN 'top 0,1%'
                        WHEN bool_or(title ILIKE '%top 1%%') THEN 'top 1%'
                        WHEN bool_or(title ILIKE '%10\\%-groep%' ESCAPE '\\') THEN '10%-groep'
                        WHEN bool_or(title ILIKE '%20\\%-groep%' ESCAPE '\\') THEN '20%-groep'
                        ELSE 'geen verdeling' END AS kleinste_topgroep
            FROM (SELECT table_id, title FROM meta.measures
                  UNION ALL SELECT table_id, title FROM meta.dimension_codes
                  WHERE dimension_id <> 'Perioden')
            GROUP BY table_id
        ),
        regio AS (
            SELECT table_id, count(*) FILTER (WHERE code LIKE 'GM%') AS gemeenten
            FROM meta.dimension_codes GROUP BY table_id
        ),
        jaren AS (
            SELECT table_id, min(title) AS eerste_jaar, max(title) AS laatste_jaar,
                   bool_or(code = '1950JJ00') AS bevat_1950
            FROM meta.dimension_codes WHERE dimension_id = 'Perioden' GROUP BY table_id
        )
        SELECT t.table_id, trim(t.title) AS titel, g.kleinste_topgroep,
               r.gemeenten, j.eerste_jaar, j.laatste_jaar, j.bevat_1950
        FROM meta.tables t
        JOIN groups g USING (table_id) JOIN regio r USING (table_id) JOIN jaren j USING (table_id)
        WHERE t.table_id IN ('84476NED', '86160NED', '37662')
        ORDER BY t.table_id
        """
    )
    dekking
    return (dekking,)


@app.cell
def _(dekking, mo):
    _has = lambda cond: ", ".join(dekking.loc[cond, "table_id"]) or "geen"  # noqa: E731
    mo.md(
        f"""
        ## Niet beschikbaar

        CBS StatLine publiceert dit niet. De vraag heeft drie eisen tegelijk nodig, en geen
        enkele tabel voldoet aan meer dan één:

        | Eis | Tabellen die eraan voldoen |
        |---|---|
        | Een groep zo klein als de top 0,01% | geen (kleinste gepubliceerde topgroep: top 0,1%, in {_has(dekking["kleinste_topgroep"] == "top 0,1%")}) |
        | Uitsplitsing per gemeente | {_has(dekking["gemeenten"] > 0)} |
        | Het jaar 1950 | {_has(dekking["bevat_1950"])} |

        Daarom geen grafiek en geen getal. Er is bewust geen benadering gemaakt (zoals een
        landelijk totaal, een later jaar of een grotere groep).
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Tabelkeuze (overwogen en afgewezen)

        | Tabel | Levert | Waarom niet |
        |---|---|---|
        | 84476NED Ongelijkheid in inkomen en vermogen | Vermogen van de top 10%, 1% en 0,1%, landelijk | Geen top 0,01%, geen gemeenten, pas vanaf 2011 |
        | 86160NED Vermogen van huishoudens; regio (indeling 2025) | Vermogen per gemeente, naar 20%-groepen en vermogensklassen | Kleinste groep 20% of klasse ≥ 1 mln euro, pas vanaf 2006 |
        | 37662 Historie inkomen, vermogen en consumptie; 1900-1998 | Totaal vermogen van natuurlijke personen, landelijk, jaarlijks | Wel 1950, maar alleen één landelijk totaal: geen verdeling en geen gemeenten |
        | 81513NED, 86007NED en andere regio-indelingen van vermogen | Vermogen per regio | Zelfde opzet als 86160NED, kortere reeksen (niet opgehaald) |

        Gezocht in de CBS-catalogus op onder meer *vermogen gemeente*, *vermogen regio*,
        *vermogen 1950*, *vermogen historie* en *vermogensverdeling*.
        """
    )
    return


@app.cell
def _(TABLES, mo, nb):
    mo.vstack([mo.md("## Bronnen (geraadpleegde metadata)"), nb.sources(TABLES)])
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## Controle

        | Bewering | Nagegaan | Gecontroleerd |
        |---|---|---|
        | 37662 bevat 1950 maar heeft alleen de dimensie Perioden | `datchat describe 37662` | 2026-09-28 |
        | 86160NED: 343 gemeenten, 2006–2024, kleinste vermogensgroep 20% | `datchat describe 86160NED` | 2026-09-28 |
        | 84476NED: kleinste groep top 0,1%, geen regio-dimensie, 2011–2024 | `datchat describe 84476NED` | 2026-09-28 |
        """
    )
    return


if __name__ == "__main__":
    app.run()
