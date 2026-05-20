from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import re
import unicodedata
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(str(value).split())
    return cleaned or None


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_value).strip("-")
    return slug or "job"


def build_hash_id(parts: Iterable[str | None]) -> str:
    normalized_parts = [(normalize_text(part) or "").lower() for part in parts]
    digest = hashlib.sha256("|".join(normalized_parts).encode("utf-8")).hexdigest()
    return digest[:20]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def unix_timestamp_to_iso(timestamp: int | float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(microsecond=0).isoformat()


def parse_relative_datetime(value: str | None, reference: datetime | None = None) -> str | None:
    text = (normalize_text(value) or "").lower()
    if not text:
        return None

    current = reference or datetime.now(timezone.utc)
    if text == "today":
        return current.replace(microsecond=0).isoformat()
    if text == "yesterday":
        return (current - timedelta(days=1)).replace(microsecond=0).isoformat()

    match = re.fullmatch(r"(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago", text)
    if match is None:
        return None

    amount = int(match.group(1))
    unit = match.group(2)
    delta_map = {
        "minute": timedelta(minutes=amount),
        "hour": timedelta(hours=amount),
        "day": timedelta(days=amount),
        "week": timedelta(weeks=amount),
        "month": timedelta(days=30 * amount),
        "year": timedelta(days=365 * amount),
    }
    return (current - delta_map[unit]).replace(microsecond=0).isoformat()


class Job(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    source: str
    company: str | None = None
    title: str
    location: str | None = None
    url: str
    posted_at: str | None = None
    description_snippet: str | None = None
    employment_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    raw: dict[str, Any] | None = None

    @field_validator("id", "source", "title", "url", mode="before")
    @classmethod
    def _normalize_required_text(cls, value: Any) -> str:
        cleaned = normalize_text(str(value) if value is not None else None)
        if not cleaned:
            raise ValueError("field must not be empty")
        return cleaned

    @field_validator(
        "company",
        "location",
        "posted_at",
        "description_snippet",
        "employment_type",
        mode="before",
    )
    @classmethod
    def _normalize_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        return normalize_text(str(value))

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        tags = value if isinstance(value, list) else [value]
        normalized: list[str] = []
        for tag in tags:
            cleaned = normalize_text(str(tag))
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        return normalized

    @property
    def dedupe_key(self) -> str:
        return f"{slugify(self.source).lower()}:{self.id.lower()}"

    @classmethod
    def create(
        cls,
        *,
        source: str,
        title: str,
        url: str,
        company: str | None = None,
        location: str | None = None,
        posted_at: str | None = None,
        description_snippet: str | None = None,
        employment_type: str | None = None,
        tags: list[str] | None = None,
        raw: dict[str, Any] | None = None,
        source_job_id: str | None = None,
    ) -> "Job":
        stable_id = normalize_text(source_job_id) or build_hash_id([company, title, location, url])
        return cls(
            id=stable_id,
            source=source,
            company=company,
            title=title,
            location=location,
            url=url,
            posted_at=posted_at,
            description_snippet=description_snippet,
            employment_type=employment_type,
            tags=tags or [],
            raw=raw,
        )

