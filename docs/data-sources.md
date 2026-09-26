# CBS StatLine: household wealth tables

The table survey behind phase 1, done against CBS's live catalogue in September 2026. It
records what each table can and cannot answer, so that later answers and charts don't claim
more than the data supports.

## Definitions (from the CBS table metadata)

- **Vermogen** (wealth) = bezittingen − schulden (assets minus debts). Assets are mainly bank
  and savings balances, securities, real estate (including the owner-occupied home), business
  assets and substantial shareholdings (*aanmerkelijk belang*). Debts include the mortgage
  on the owner-occupied home and consumer credit.
- **Vermogen exclusief eigen woning** = wealth minus the owner-occupied home and the mortgage
  on it (component `1021480` in 83834NED).
- Wealth figures are the position on **1 January** of the year. Population: private
  households.
- **Pension entitlements are not included** in the income/wealth statistics tables (838xx,
  84476, 83934). They are included in the national-accounts tables (85889, 84104, 82960),
  which use a different wealth concept (*vermogenssaldo*). Don't mix the two in one series.
- CBS notes a methodology break in 2011, which is why some series start in 2011.

## Tables

| Table | Rows | Structure | Use for |
|---|---|---|---|
| **83834NED** | 86,085 | household characteristics (73, incl. wealth 10%-groups) × wealth component (16) × year | Bottom 50%, 10%-groups, composition, **excl. eigen woning** |
| **84476NED** | 18,453 | concept (income/wealth) × household characteristics × year; measures incl. total amount of top 10% / 1% / 0.1% | **Top 1%**, top 0.1%, Gini, Theil |
| **83835NED** | 87,609 | household characteristics × wealth class (euro bands + 10%-groups) × year | Number of households per wealth band (e.g. ≥ €1 mln) |
| **83934NED** | 882 | population × percentile (10..90) × year | Euro boundaries of the 10%-groups |
| **85889NED** | 5,166 | household groups (incl. *vermogenssaldo* 10%-groups) × year 2021–2023 | NR wealth incl. pensions by 10%-group; housing only inside *niet-financiële activa* |
| **84104NED** | 13,804 | household groups (incl. *vermogenssaldo* **20%**-groups) × year 2015–2021 | NR by wealth quintile; housing split into *woningen* + *grond onder woningen* |
| **82960NED** | 14,720 | household type / income 20%-groups × year 2005–2014 | NR by household type; **no wealth groups** |

All codes are **table-specific**. The same measure code can mean different things in
different tables; `A047160_1`, for example, is a housing total in one table and an average
receivable in another. The `core` views therefore always select by code within one table.

## The core question: top 1% vs bottom 50%, with and without housing

| | incl. eigen woning | excl. eigen woning |
|---|---|---|
| Bottom 50% | 83834NED, 10%-groups 1–5 | 83834NED, component `1021480`, groups 1–5 ⚠ |
| Top 10% | 83834NED group 10, or 84476NED | 83834NED, component `1021480`, group 10 ⚠ |
| Top 1% | 84476NED | **not published by CBS** |
| Top 0.1% | 84476NED | not published |

⚠ The 10%-groups are ranked on total wealth **including** the home. The "excl." figures are
the non-housing wealth *of those same households*; the households are not re-ranked on
non-housing wealth. A household with a large home and few other assets sits in a high group
on both lines. Every answer and chart that uses the "excl." figures has to say this;
`core.wealth_group_shares.note` carries it.

**Top 1% excl. housing** is not in StatLine. Agreed approach: use the top 10% excl. housing
as the nearest proxy and label it as such. Outside StatLine, estimates exist from research on
CBS microdata, but that is not CBS StatLine data.

Values on 1 January 2023 (final), from `core.wealth_group_shares`:

| | incl. eigen woning | excl. eigen woning |
|---|---|---|
| Bottom 50% | 2.3% | 2.6% |
| Middle 40% | 41.0% | 19.1% |
| Top 10% | 56.7% | 78.2% |
| Top 1% | 25.1% | n/a |

## Provisional figures and revisions

Each period has a status in `meta.dimension_codes.status`, surfaced as `period_status` in
every `core` view. 2024 is currently *Voorlopig* (provisional) in the 838xx/84476/83934
tables, and all national-accounts years from 2015 on are provisional.

Provisional figures do get revised. The January 2025 news release gave 2023 as top 10% 55.7%,
top 1% 23.7% and top 0.1% 9.9%. The final 2023 figures from October 2025 are 56.7%, 25.1% and
10.9%. Charts should mark provisional years visibly.

## Known CBS quirks handled by the pipeline

- **82960NED:** v4 metadata works, but `Observations` returns 404, so the data comes from v3.
- **82960NED:** `Properties.ObservationCount` = 14,721, while the v3 API and the v4 bulk CSV
  both hold 14,720.
- **MeasureGroups:** not present on every table. The client reads the service document first.
- **v3 vs v4:** v3 pads dimension keys with spaces and returns empty cells as null, whereas v4
  omits empty cells.
- **v4 bulk CSV:** uses a decimal comma (`290,3`).
- **84476NED:** the top-10% amounts are whole billions from 2018 on and differ by up to 0.08%
  from the 10e 10%-groep in 83834NED. That is more than rounding explains, so the two tables
  apparently define the group slightly differently.
