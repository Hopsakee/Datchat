"""Every notebook in notebooks/ must run headless (plan v2, criterion 5).

Live: syncs the tables each notebook declares in ``TABLES = [...]`` into the configured
database first. Run with: uv run pytest -m live
"""

import ast
import pathlib

import pytest

from datchat import cli

pytestmark = pytest.mark.live

NOTEBOOKS = sorted(pathlib.Path("notebooks").rglob("*.py"))


def declared_tables(path: pathlib.Path) -> list[str]:
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "TABLES" for t in node.targets
        ):
            return [e.value for e in node.value.elts]
    return []


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_runs_headless(notebook):
    tables = declared_tables(notebook)
    if tables:
        assert cli.main(["sync", *tables]) == 0
    assert cli.main(["check", str(notebook)]) == 0
