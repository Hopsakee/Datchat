"""Plotly helpers that implement docs/chart-checklist.md, plus a checker for it.

Use in a notebook chart cell:

    fig = go.Figure(...)
    charts.style(fig, title=..., x_title=..., y_title="Aandeel (%)", tables=["84476NED"])
    charts.label_ends(fig)
    charts.checked(fig)        # raises if the figure breaks a checkable rule

``checked`` makes ``datchat check`` (headless export) fail on a non-compliant chart.
"""

from __future__ import annotations

from collections.abc import Iterable

import plotly.graph_objects as go

ACCENT = "#C4461A"  # the one colour for the series the story is about
GREYS = ["#4D4D4D", "#8C8C8C", "#B3B3B3", "#6E6E6E", "#A0A0A0", "#C8C8C8"]
TEXT = "#333333"
FONT = "Inter, Helvetica, Arial, sans-serif"
PROVISIONAL_DASH = "dot"


class ChartCheckError(AssertionError):
    pass


def colors(n: int, accent: int | None = 0) -> list[str]:
    """n series colours: greys, with the series at index ``accent`` in the accent colour."""
    out = [GREYS[i % len(GREYS)] for i in range(n)]
    if accent is not None and 0 <= accent < n:
        out[accent] = ACCENT
    return out


def style(
    fig: go.Figure,
    *,
    title: str,
    x_title: str,
    y_title: str,
    tables: Iterable[str],
    note: str | None = None,
) -> go.Figure:
    """Apply the house style: finding as title, units on axes, source caption, no legend."""
    caption = "Bron: CBS StatLine " + ", ".join(tables)
    if note:
        caption += "<br>" + note
    fig.update_layout(
        title={"text": title, "x": 0, "xanchor": "left", "font": {"size": 18}},
        template="simple_white",
        font={"family": FONT, "color": TEXT, "size": 13},
        showlegend=False,
        separators=",.",
        margin={"l": 80, "r": 190, "t": 70, "b": 130},
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    # simple_white draws shapes with line width 0, so an add_vline/add_hline without an
    # explicit width is invisible (a trend-break line vanished that way). Opacity stays the
    # template's, so rectangles used as bands keep their soft fill.
    fig.update_layout(template_layout_shapedefaults_line_width=1.5)
    axis = {"showgrid": False, "zeroline": False, "ticks": "outside", "linecolor": "#999"}
    fig.update_xaxes(title_text=x_title, mirror=False, **axis)
    fig.update_yaxes(title_text=y_title, mirror=False, **axis)
    fig.add_annotation(
        text=caption,
        xref="paper",
        yref="paper",
        x=0,
        y=0,
        yshift=-75,
        xanchor="left",
        yanchor="top",
        align="left",
        showarrow=False,
        font={"size": 11, "color": "#666"},
        name="source",
    )
    return fig


def direct_labels(
    fig: go.Figure, labels: Iterable[tuple[float, float, str, str]], min_gap: float | None = None
) -> go.Figure:
    """Place direct labels (x, y, text, colour) right of their points without overlapping.

    Labels closer than ``min_gap`` (default: 4% of the y-range of the labels' traces) are
    pushed apart vertically; the label keeps its colour so it still reads as its series.
    """
    items = sorted(labels, key=lambda t: t[1])
    if not items:
        return fig
    if min_gap is None:
        ys = [v for tr in fig.data if tr.y is not None for v in tr.y if v is not None]
        span = (max(ys) - min(ys)) if ys else 1.0
        min_gap = 0.04 * (span or 1.0)
    placed: list[float] = []
    for _, y, _, _ in items:
        placed.append(max(y, placed[-1] + min_gap) if placed else y)
    for (x, _, text, color), y in zip(items, placed, strict=True):
        fig.add_annotation(
            x=x,
            y=y,
            text=text,
            xanchor="left",
            xshift=8,
            showarrow=False,
            font={"color": color, "size": 12},
        )
    return fig


def label_ends(fig: go.Figure, fmt: str = "{name}") -> go.Figure:
    """Direct labels at the last point of every line trace, in the trace's colour."""
    labels = []
    for tr in fig.data:
        if tr.type != "scatter" or tr.x is None or len(tr.x) == 0:
            continue
        color = (tr.line.color if tr.line and tr.line.color else None) or TEXT
        labels.append((tr.x[-1], tr.y[-1], fmt.format(name=tr.name, y=tr.y[-1]), color))
    return direct_labels(fig, labels)


def check_figure(fig: go.Figure, value_axis: str = "y") -> list[str]:
    """Names of checklist rules the figure breaks (empty list = passes)."""
    d = fig.to_dict()
    layout = d.get("layout", {})
    failed: list[str] = []
    title = (layout.get("title") or {}).get("text") or ""
    if not title.strip():
        failed.append("title_missing")
    for ax in ("xaxis", "yaxis"):
        a = layout.get(ax, {})
        ax_title = ((a.get("title") or {}).get("text") or "").strip()
        if not ax_title:
            failed.append(f"{ax}_title_missing")
        elif ax[0] == value_axis and "(" not in ax_title:
            failed.append(f"{ax}_unit_missing")
        if a.get("showgrid", True):
            failed.append(f"{ax}_default_gridlines")
    if layout.get("showlegend", True) and len(d.get("data", [])) > 1:
        failed.append("legend_instead_of_direct_labels")
    annotations = layout.get("annotations", [])
    if not any("CBS" in (a.get("text") or "") for a in annotations):
        failed.append("source_caption_missing")
    if any(t.get("type") == "pie" for t in d.get("data", [])):
        failed.append("pie_chart")
    used = set()
    for t in d.get("data", []):
        for c in ((t.get("line") or {}).get("color"), (t.get("marker") or {}).get("color")):
            if isinstance(c, str):
                used.add(c.upper())
    allowed = {c.upper() for c in [ACCENT, *GREYS, TEXT]}
    if not used:
        failed.append("default_colours")
    elif used - allowed:
        failed.append("colour_outside_palette")
    return failed


def checked(fig: go.Figure, value_axis: str = "y") -> go.Figure:
    failed = check_figure(fig, value_axis)
    if failed:
        raise ChartCheckError("Chart breaks docs/chart-checklist.md: " + ", ".join(failed))
    return fig
