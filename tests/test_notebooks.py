"""Every notebook in notebooks/ must run headless (plan v2, criterion 5).

Live: syncs the tables each notebook declares in ``TABLES`` / ``*_TABLES`` lists into the configured
database first. Run with: uv run pytest -m live
"""

import ast
import pathlib

import pytest

from datchat import cli

pytestmark = pytest.mark.live

NOTEBOOKS = sorted(pathlib.Path("notebooks").rglob("*.py"))


def declared_tables(path: pathlib.Path) -> list[str]:
    """Table ids from literal lists assigned to TABLES or *_TABLES in the notebook."""
    ids: list[str] = []
    for node in ast.walk(ast.parse(path.read_text())):
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.List)
            and any(isinstance(t, ast.Name) and t.id.endswith("TABLES") for t in node.targets)
        ):
            ids += [e.value for e in node.value.elts if isinstance(e, ast.Constant)]
    return list(dict.fromkeys(ids))


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_runs_headless(notebook):
    tables = declared_tables(notebook)
    if tables:
        assert cli.main(["sync", *tables]) == 0
    assert cli.main(["check", str(notebook)]) == 0
