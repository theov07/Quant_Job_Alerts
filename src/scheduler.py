from __future__ import annotations

from pathlib import Path


GITHUB_ACTIONS_CRON = "*/30 * * * *"


def build_local_cron_command(project_root: Path, python_executable: str = "python3") -> str:
    return f"*/30 * * * * cd {project_root} && {python_executable} -m src.main"
