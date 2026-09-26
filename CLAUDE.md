# Datchat: notes for Claude

Personal Dutch-statistics explorer. Phase 1 (CBS → DuckDB sync + verification) is in place.
The Panel UI and other sources come later; see docs/project-plan.md.

## Commands
- `uv run datchat sync [TABLE…] [--force]` / `verify [--cross-check]` / `status` / `spotcheck`
- `uv run pytest` (offline) · `uv run pytest -m live` (real CBS) · `uv run ruff check src tests`

## Conventions
- Data source: CBS OData v4 (`datasets.cbs.nl`); v3 only as automatic fallback. No `cbsodata`.
- CBS codes are table-specific: never reuse a measure/dimension code across tables.
- Every answer or chart states source table ids, years, and whether figures are *Voorlopig*.
- "Excl. eigen woning" per 10%-group is ranked on total wealth, so say so (docs/data-sources.md).
- Charts follow docs/chart-checklist.md.
- When blocked (network, access, missing tool), stop and discuss with the user. No workarounds.
