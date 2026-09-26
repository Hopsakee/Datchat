"""Where the database lives."""

from __future__ import annotations

import os
from pathlib import Path


def db_path() -> Path:
    """DuckDB file location; override with DATCHAT_DB."""
    return Path(os.environ.get("DATCHAT_DB", "data/datchat.duckdb"))
