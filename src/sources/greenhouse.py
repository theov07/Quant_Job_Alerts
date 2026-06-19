from __future__ import annotations

from collections import OrderedDict
from html import unescape
import time
from typing import Any
from urllib.parse import quote, urlencode

from src.config import JobBoardDefinition
from src.models import Job, normalize_text

from .base import BaseJobSource


GREENHOUSE_API_ROOT = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseJobSource(BaseJobSource):
    name = "Greenhouse"

    def fetch_jobs(self) -> list[Job]:
        if not self.config.boards:
            self.logger.warning("Greenhouse source has no configured job boards.")
            return []

        jobs_by_key: OrderedDict[str, Job] = OrderedDict()
        for board in self.config.boards:
            payload = self.fetch_json(self._build_api_url(board.slug))
            if not isinstance(payload, dict):
                continue

            board_jobs = self._parse_payload(payload=payload, board=board)
            self.logger.info("Greenhouse board %s fetched %d jobs.", board.name, len(board_jobs))
            for job in board_jobs:
                jobs_by_key[job.dedupe_key] = job

            if self.config.pause_seconds > 0:
                time.sleep(self.config.pause_seconds)

        return list(jobs_by_key.values())

    @staticmethod
    def _build_api_url(board_slug: str) -> str:
        query = urlencode({"content": "true"})
        return f"{GREENHOUSE_API_ROOT}/{quote(board_slug, safe='')}/jobs?{query}"

    def _parse_payload(
        self,
        *,
        payload: dict[str, Any],
        board: JobBoardDefinition,
    ) -> list[Job]:
        postings = payload.get("jobs")
        if not isinstance(postings, list):
            self.logger.warning("Greenhouse board %s returned no jobs list.", board.slug)
            return []

        jobs: list[Job] = []
        for posting in postings:
            if not isinstance(posting, dict):
                continue

            title = normalize_text(posting.get("title"))
            job_url = normalize_text(posting.get("absolute_url"))
            source_job_id = normalize_text(posting.get("id"))
            if not title or not job_url or not source_job_id:
                continue

            description = self._description(posting.get("content"))
            compensation = self._compensation(posting.get("metadata"))
            description_bits = [value for value in [description, compensation] if value]

            jobs.append(
                Job.create(
                    source=self.name,
                    source_job_id=f"{board.slug}:{source_job_id}",
                    company=board.name,
                    title=title,
                    location=self._location(posting.get("location")),
                    url=job_url,
                    posted_at=normalize_text(posting.get("first_published")),
                    description_snippet=" | ".join(description_bits) or None,
                    employment_type=self._employment_type(posting.get("metadata")),
                    tags=self._tags(posting),
                    raw={"board": board.slug, **posting},
                )
            )

        return jobs

    def _description(self, value: Any) -> str | None:
        text = normalize_text(value)
        if not text:
            return None
        decoded = unescape(text)
        if "<" not in decoded:
            return normalize_text(decoded)
        return normalize_text(self.make_soup(decoded).get_text(" ", strip=True))

    @staticmethod
    def _location(value: Any) -> str | None:
        if isinstance(value, dict):
            return normalize_text(value.get("name"))
        return normalize_text(value)

    @classmethod
    def _employment_type(cls, metadata: Any) -> str | None:
        values = cls._metadata_values(metadata)
        for name, value in values.items():
            if "employment type" in name or name == "employment":
                return value
        return None

    @classmethod
    def _compensation(cls, metadata: Any) -> str | None:
        values = cls._metadata_values(metadata)
        minimum = cls._first_matching_value(values, ("min salary", "minimum salary"))
        maximum = cls._first_matching_value(values, ("max salary", "maximum salary"))
        currency = cls._first_matching_value(values, ("currency", "salary currency"))
        if not minimum and not maximum:
            return None

        salary_range = " - ".join(value for value in (minimum, maximum) if value)
        if currency:
            salary_range = f"{salary_range} {currency}"
        return f"Compensation: {salary_range}"

    @classmethod
    def _tags(cls, posting: dict[str, Any]) -> list[str]:
        tags: list[str] = []
        for field in ("departments", "offices"):
            for item in posting.get(field) or []:
                if not isinstance(item, dict):
                    continue
                value = normalize_text(item.get("name"))
                if value and value not in tags:
                    tags.append(value)

        for name, value in cls._metadata_values(posting.get("metadata")).items():
            if any(keyword in name for keyword in ("experience", "job type", "employment type")):
                if value not in tags:
                    tags.append(value)
        return tags

    @staticmethod
    def _metadata_values(metadata: Any) -> dict[str, str]:
        values: dict[str, str] = {}
        if not isinstance(metadata, list):
            return values

        for item in metadata:
            if not isinstance(item, dict):
                continue
            name = (normalize_text(item.get("name")) or "").lower()
            raw_value = item.get("value")
            if isinstance(raw_value, list):
                value = ", ".join(str(part) for part in raw_value if part is not None)
            else:
                value = normalize_text(raw_value)
            if name and value:
                values[name] = value
        return values

    @staticmethod
    def _first_matching_value(values: dict[str, str], names: tuple[str, ...]) -> str | None:
        for name, value in values.items():
            if name in names:
                return value
        return None
