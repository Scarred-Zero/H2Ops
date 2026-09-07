from __future__ import annotations

import sys
from pathlib import Path


def find_project_root(start_path: str | Path | None = None) -> Path:
    search_path = (
        Path(start_path or Path(__file__).resolve().parent).expanduser().resolve()
    )
    for candidate in (search_path, *search_path.parents):
        if (candidate / "src").exists():
            return candidate
    return search_path


def ensure_project_root_on_path(start_path: str | Path | None = None) -> Path:
    project_root = find_project_root(start_path)
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    return project_root
