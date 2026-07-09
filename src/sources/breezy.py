from __future__ import annotations

from collections import OrderedDict
from html import unescape
import time
from typing import Any
from urllib.parse import quote

from src.config import JobBoardDefinition
from src.models import Job, normalize_text

from .base import BaseJobSource


class BreezyJobSource(BaseJobSource):
    name = "Breezy"

    def fetch_jobs(self) -> list[Job]:
        if not self.config.boards:
            self.logger.warning("Breezy source has no configured job boards.")
            return []

        jobs_by_key: OrderedDict[str, Job] = OrderedDict()
        for board in self.config.boards:
            payload = self.fetch_json(self._build_api_url(board.slug))
            if not isinstance(payload, list):
                continue

            board_jobs = self._parse_payload(payload=payload, board=board)
            self.logger.info("Breezy board %s fetched %d jobs.", board.name, len(board_jobs))
            for job in board_jobs:
                jobs_by_key[job.dedupe_key] = job

            if self.config.pause_seconds > 0:
                time.sleep(self.config.pause_seconds)

        return list(jobs_by_key.values())

    @staticmethod
    def _build_api_url(board_slug: str) -> str:
        return f"https://{quote(board_slug, safe='')}.breezy.hr/json"

    def _parse_payload(self, *, payload: list[Any], board: JobBoardDefinition) -> list[Job]:
        jobs: list[Job] = []
        for posting in payload:
            if not isinstance(posting, dict):
                continue

            title = normalize_text(posting.get("name"))
            job_url = normalize_text(posting.get("url"))
            source_job_id = normalize_text(posting.get("id") or posting.get("friendly_id"))
            if not title or not job_url or not source_job_id:
                continue

            jobs.append(
                Job.create(
                    source=self.name,
                    source_job_id=f"{board.slug}:{source_job_id}",
                    company=board.name,
                    title=title,
                    location=self._location(posting),
                    url=job_url,
                    posted_at=normalize_text(posting.get("published_date")),
                    description_snippet=self._description(posting),
                    employment_type=self._employment_type(posting.get("type")),
                    tags=self._tags(posting),
                    raw={"board": board.slug, **posting},
                )
            )

        return jobs

    @staticmethod
    def _location(posting: dict[str, Any]) -> str | None:
        locations = posting.get("locations")
        if isinstance(locations, list):
            values = []
            for location in locations:
                if isinstance(location, dict):
                    value = normalize_text(location.get("name"))
                    if value and value not in values:
                        values.append(value)
            if values:
                return ", ".join(values)

        location = posting.get("location")
        if isinstance(location, dict):
            return normalize_text(location.get("name"))
        return normalize_text(location)

    @staticmethod
    def _employment_type(value: Any) -> str | None:
        if isinstance(value, dict):
            return normalize_text(value.get("name"))
        return normalize_text(value)

    def _description(self, posting: dict[str, Any]) -> str | None:
        parts: list[str] = []
        for key in ("description", "requirements", "application"):
            text = self._html_to_text(posting.get(key))
            if text:
                parts.append(text)

        salary = normalize_text(posting.get("salary"))
        if salary:
            parts.append(f"Compensation: {salary}")

        return " | ".join(parts) or None

    @classmethod
    def _tags(cls, posting: dict[str, Any]) -> list[str]:
        tags: list[str] = []
        for key in ("department",):
            value = normalize_text(posting.get(key))
            if value and value not in tags:
                tags.append(value)
        employment_type = cls._employment_type(posting.get("type"))
        if employment_type and employment_type not in tags:
            tags.append(employment_type)
        return tags

    def _html_to_text(self, value: Any) -> str | None:
        text = normalize_text(value)
        if not text:
            return None
        decoded = unescape(text)
        if "<" not in decoded:
            return normalize_text(decoded)
        return normalize_text(self.make_soup(decoded).get_text(" ", strip=True))
