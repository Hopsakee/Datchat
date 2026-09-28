# Datchat: notes for Claude

A Claude Code skill that turns a question about Dutch statistics into one marimo notebook built
from CBS StatLine data, or answers "niet beschikbaar". The current plan is docs/project-plan.md
(v2). v1 (Panel, Hetzner hosting) is superseded.

- To answer a question, use the `cbs-question` skill (.claude/skills/cbs-question/SKILL.md).
- Commands: `uv run datchat catalog | search | sync | describe | query | verify | check | status`
- Tests: `uv run pytest` (offline) · `uv run pytest -m live` (real CBS, runs every notebook)
- uv only: no pip, requirements.txt, conda or poetry. The DuckDB file is gitignored.
- Never invent numbers and never use proxies. What CBS doesn't publish is "niet beschikbaar".
- CBS codes are table-specific.
- Out of scope: hosting or publishing, sources other than CBS, an LLM inside the app.
- When blocked (network, CBS outage, locked database), stop and tell the user. No workarounds.
