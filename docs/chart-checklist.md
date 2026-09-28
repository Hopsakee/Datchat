# Chart checklist (Plotly in marimo notebooks)

Our own design rules for every chart this project produces. The idea comes from pairing a
written checklist with an automated gate, so that a chart is not "done" until it passes both.

**Enforced in code.** `datchat.charts` implements the house style (`style`, `colors`,
`label_ends`, `direct_labels`, which keeps line-end labels from overlapping), and `charts.checked(fig)` raises when a figure breaks a checkable rule. Every
notebook chart cell ends with `charts.checked(fig)`, so `datchat check` (headless export)
fails on a non-compliant chart. Rules marked *(manual)* need a look at the rendered chart:
`datchat render NOTEBOOK` writes every `fig_*` to PNG. The first review of the acceptance
charts found clipped captions and labels and overlapping direct labels, none of which the
checker can see.

## Data honesty (specific to this project)

1. **Source on the chart.** Every figure carries a caption with the CBS table id(s), e.g.
   "Bron: CBS StatLine 83834NED, 84476NED". *(checked: `source_caption_missing`)*
2. **Provisional years are visible.** Values with `period_status = 'Voorlopig'` get a distinct
   marker or dash, plus an asterisk in the axis label or caption.
3. **Caveats travel with the numbers.** Definitions that change the meaning go next to the
   chart, e.g. that the excl.-housing figures per 10%-group are ranked on total wealth.
   No proxies: what CBS doesn't publish is *niet beschikbaar*, not approximated.
4. **One wealth concept per axis.** Statistics wealth (838xx/84476) and national-accounts
   *vermogenssaldo* (incl. pensions) are never drawn as one continuous series.
5. **Reference date stated.** Wealth is "op 1 januari"; say so in the title or axis.
6. **Numbers in titles come from the data.** A title such as "de top 1% bezit 11 keer zoveel"
   is computed from the query result and handles edge cases (e.g. a negative denominator).

## Visual rules

7. **No default gridlines.** `showgrid=False`, or at most a faint horizontal grid on the value
   axis only.
8. **Direct labels, no legend.** Label each series at its line end or bar
   (`showlegend=False`, annotations or `texttemplate`). A legend is allowed only with more
   than 5 series, and then we should question the chart instead.
9. **Axis titles with units.** "Aandeel in totaal vermogen (%)", "Vermogen (mld euro)". No
   bare "value".
10. **Muted palette, one accent.** Greys for context, a single accent colour for the series the
   story is about. No Plotly default colour cycle. Colours come from one project palette
   module.
11. **Title states the finding.** "Top 1% bezit een kwart van het vermogen", not
    "Vermogensaandeel per jaar".
12. **Zero-based where it matters.** Bar charts start at 0. Never clip negative values: if a
    series goes below zero, the zero line is visible.
13. **Readable numbers.** Dutch number formatting in labels and hover (`separators=",."`),
    sensible rounding, percentages to one decimal.
14. **Clean frame.** No top or right axis lines, white background, no 3D, no pie charts.

## Export

15. **Static export** (when a chart leaves the notebook): PNG at ≥ 1600 px wide, exported
    with `scale` so it is equivalent to 300 dpi at print size. SVG for documents.
16. **Interactive hover** shows the exact value, unit, year, period status and source table.

## Review loop

- The automated check runs first. A chart with failing rules goes back for revision.
- Then a *(manual)* look at the rendered chart: does it answer the question it was made for?
  Is the story readable in five seconds?
- There is a limit of 3 revision rounds per chart. If it still fails, the problem is usually
  the data or the chart type, not the styling, so step back.
