from __future__ import annotations

from pathlib import Path
import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


def parse_bool(value: str | bool | None, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class AppSettings(BaseModel):
    discord_webhook_url: str | None = None
    log_level: str = "INFO"
    min_score: int = 3
    database_path: Path = PROJECT_ROOT / "data" / "seen_jobs.sqlite"
    request_timeout_seconds: float = 20.0
    user_agent: str = "quant-job-alerts/1.0 (+respectful scraping; contact the repo owner before production scale)"
    discord_embed_color: int = 3_447_003
    show_match_reasons: bool | None = None

    @classmethod
    def from_env(cls) -> "AppSettings":
        database_path = Path(os.getenv("DATABASE_PATH", "data/seen_jobs.sqlite"))
        if not database_path.is_absolute():
            database_path = PROJECT_ROOT / database_path

        show_match_reasons_env = os.getenv("SHOW_MATCH_REASONS")

        return cls(
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL") or None,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            min_score=int(os.getenv("MIN_SCORE", "3")),
            database_path=database_path,
            request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")),
            show_match_reasons=(
                parse_bool(show_match_reasons_env) if show_match_reasons_env is not None else None
            ),
        )


class SourceDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    type: str
    url: str | None = None
    urls: list[str] = Field(default_factory=list)
    max_pages: int = 1
    pause_seconds: float = 0.0


class SourcesConfig(BaseModel):
    sources: dict[str, SourceDefinition]


class ScoreWeights(BaseModel):
    title_quant: int = 3
    title_core_role: int = 2
    title_early_career: int = 2
    preferred_location: int = 1
    negative_keyword: int = -5
    additional_positive_keyword: int = 1


class FilterConfig(BaseModel):
    minimum_score: int = 3
    show_match_reasons: bool = False
    positive_keywords: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    weights: ScoreWeights = Field(default_factory=ScoreWeights)


def load_yaml_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_sources_config(path: Path | None = None) -> SourcesConfig:
    config_path = path or (CONFIG_DIR / "sources.yaml")
    return SourcesConfig.model_validate(load_yaml_file(config_path))


def load_filter_config(path: Path | None = None) -> FilterConfig:
    config_path = path or (CONFIG_DIR / "filters.yaml")
    return FilterConfig.model_validate(load_yaml_file(config_path))
