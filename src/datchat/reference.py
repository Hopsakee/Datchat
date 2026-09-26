"""Figures CBS printed in its own publications, used to check our recomputed numbers.

Only final ("definitief") years are pinned; provisional years get revised (2023 was published
as 55.7 / 23.7 / 9.9 in January 2025 and revised to 56.7 / 25.1 / 10.9 in October 2025).
"""

PUBLISHED_TOP_SHARES = {
    "source": (
        "CBS, '56 procent vermogen in handen van 10 procent huishoudens', 15-1-2025, "
        "https://www.cbs.nl/nl-nl/nieuws/2025/03/56-procent-vermogen-in-handen-van-10-procent-huishoudens"
    ),
    # Shares are computed by CBS from unrounded amounts, ours from the published
    # (rounded) billions, hence a small tolerance in percentage points.
    "tolerance_pp": 0.1,
    # year: (top 10%, top 1%, top 0.1%) in % of total household wealth on 1 January
    "values": {
        2011: (62.4, 25.6, 10.1),
        2012: (65.2, 27.2, 10.7),
        2013: (71.0, 31.8, 13.0),
        2014: (70.9, 31.9, 13.6),
        2015: (69.8, 31.8, 13.0),
        2016: (68.4, 30.8, 12.9),
        2017: (66.9, 30.4, 13.1),
        2018: (65.1, 29.3, 12.4),
        2019: (62.9, 27.8, 11.4),
        2020: (61.9, 27.6, 11.4),
        2021: (58.2, 24.5, 9.7),
        2022: (55.4, 23.6, 10.0),
    },
}
