# Chart checklist (Plotly / Panel)

Our own design rules for every chart this project produces. The idea comes from pairing a
written checklist with an automated gate, so that a chart is not "done" until it passes both.

**Phase 3 plan:** a `check_figure(fig) -> list[str]` function that inspects the Plotly figure
object (`fig.to_dict()`) rather than the source code, and returns the names of the rules it
fails. It runs in tests and before a view is added to the Panel app. Rules marked *(manual)*
need a human or model review of the rendered image.

## Data honesty (specific to this project)

1. **Source on the chart.** Every figure carries a caption with the CBS table id(s), e.g.
   "Bron: CBS StatLine 83834NED, 84476NED". *(check: annotation containing "CBS")*
2. **Provisional years are visible.** Values with `period_status = 'Voorlopig'` get a distinct
   marker or dash, plus an asterisk in the axis label or caption.
3. **Caveats travel with the numbers.** Excl.-housing figures show the ranking caveat
   (`core.wealth_group_shares.note`). Proxies, such as top 10% standing in for top 1% excl.
   housing, are labelled as proxies.
4. **One wealth concept per axis.** Statistics wealth (838xx/84476) and national-accounts
   *vermogenssaldo* (incl. pensions) are never drawn as one continuous series.
5. **Reference date stated.** Wealth is "op 1 januari"; say so in the title or axis.

## Visual rules

6. **No default gridlines.** `showgrid=False`, or at most a faint horizontal grid on the value
   axis only.
7. **Direct labels, no legend.** Label each series at its line end or bar
   (`showlegend=False`, annotations or `texttemplate`). A legend is allowed only with more
   than 5 series, and then we should question the chart instead.
8. **Axis titles with units.** "Aandeel in totaal vermogen (%)", "Vermogen (mld euro)". No
   bare "value".
9. **Muted palette, one accent.** Greys for context, a single accent colour for the series the
   story is about. No Plotly default colour cycle. Colours come from one project palette
   module.
10. **Title states the finding.** "Top 1% bezit een kwart van het vermogen", not
    "Vermogensaandeel per jaar".
11. **Zero-based where it matters.** Bar charts start at 0. Share charts show 0–100% unless
    zooming in is the point, and then the title or caption says so.
12. **Readable numbers.** Dutch number formatting in labels and hover (`separators=",."`),
    sensible rounding, percentages to one decimal.
13. **Clean frame.** No top or right axis lines, white background, no 3D, no pie charts.

## Export

14. **Static export** (for sharing outside the app): PNG at ≥ 1600 px wide, exported with
    `scale` so it is equivalent to 300 dpi at print size. SVG for documents.
15. **Interactive hover** shows the exact value, unit, year, period status and source table.

## Review loop

- The automated check runs first. A chart with failing rules goes back for revision.
- Then a *(manual)* look at the rendered chart: does it answer the question it was made for?
  Is the story readable in five seconds?
- There is a limit of 3 revision rounds per chart. If it still fails, the problem is usually
  the data or the chart type, not the styling, so step back.
