import json
import logging
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


def _project_dirs(projects_root: Path) -> list[Path]:
    if not projects_root.exists():
        logger.warning("Projects root does not exist: %s", projects_root)
        return []
    return [path for path in projects_root.iterdir() if path.is_dir()]


def load_projects() -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    projects_root = get_settings().projects_root

    for project_dir in _project_dirs(projects_root):
        project_file = project_dir / "project.json"
        if not project_file.exists():
            continue
        try:
            data = json.loads(project_file.read_text(encoding="utf-8"))
            if not data.get("is_active", False):
                continue
            data.setdefault("folder", project_dir.name)
            projects.append(data)
        except Exception:
            logger.exception("Could not load project config: %s", project_file)

    return sorted(projects, key=lambda item: item.get("order", 9999))


def get_project(project_id: str) -> dict[str, Any] | None:
    for project in load_projects():
        if project.get("id") == project_id:
            return project
    return None
