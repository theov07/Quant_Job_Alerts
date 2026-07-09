from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
import time
from typing import Any
from urllib.parse import quote

from src.config import JobBoardDefinition
from src.models import Job, normalize_text

from .base import BaseJobSource


LEVER_API_ROOT = "https://api.lever.co/v0/postings"


class LeverJobSource(BaseJobSource):
    name = "Lever"

    def fetch_jobs(self) -> list[Job]:
        if not self.config.boards:
            self.logger.warning("Lever source has no configured job boards.")
            return []

        jobs_by_key: OrderedDict[str, Job] = OrderedDict()
        for board in self.config.boards:
            payload = self.fetch_json(self._build_api_url(board.slug))
            if not isinstance(payload, list):
                continue

            board_jobs = self._parse_payload(payload=payload, board=board)
            self.logger.info("Lever board %s fetched %d jobs.", board.name, len(board_jobs))
            for job in board_jobs:
                jobs_by_key[job.dedupe_key] = job

            if self.config.pause_seconds > 0:
                time.sleep(self.config.pause_seconds)

        return list(jobs_by_key.values())

    @staticmethod
    def _build_api_url(board_slug: str) -> str:
        return f"{LEVER_API_ROOT}/{quote(board_slug, safe='')}?mode=json"

    def _parse_payload(self, *, payload: list[Any], board: JobBoardDefinition) -> list[Job]:
        jobs: list[Job] = []
        for posting in payload:
            if not isinstance(posting, dict):
                continue

            title = normalize_text(posting.get("text"))
            job_url = normalize_text(posting.get("hostedUrl") or posting.get("applyUrl"))
            source_job_id = normalize_text(posting.get("id"))
            if not title or not job_url or not source_job_id:
                continue

            description_bits = [
                normalize_text(posting.get("descriptionPlain")),
                normalize_text(posting.get("additionalPlain")),
            ]

            jobs.append(
                Job.create(
                    source=self.name,
                    source_job_id=f"{board.slug}:{source_job_id}",
                    company=board.name,
                    title=title,
                    location=self._location(posting.get("categories")),
                    url=job_url,
                    posted_at=self._posted_at(posting.get("createdAt")),
                    description_snippet=" | ".join(value for value in description_bits if value) or None,
                    employment_type=self._employment_type(posting.get("categories")),
                    tags=self._tags(posting.get("categories")),
                    raw={"board": board.slug, **posting},
                )
            )

        return jobs

    @staticmethod
    def _posted_at(value: Any) -> str | None:
        try:
            timestamp = float(value)
        except (TypeError, ValueError):
            return None
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(microsecond=0).isoformat()

    @staticmethod
    def _location(categories: Any) -> str | None:
        if not isinstance(categories, dict):
            return None
        locations = categories.get("allLocations")
        if isinstance(locations, list):
            values = [normalize_text(location) for location in locations]
            return ", ".join(value for value in values if value) or None
        return normalize_text(categories.get("location"))

    @staticmethod
    def _employment_type(categories: Any) -> str | None:
        if not isinstance(categories, dict):
            return None
        return normalize_text(categories.get("commitment"))

    @staticmethod
    def _tags(categories: Any) -> list[str]:
        if not isinstance(categories, dict):
            return []

        tags: list[str] = []
        for key in ("team", "department", "commitment"):
            value = normalize_text(categories.get(key))
            if value and value not in tags:
                tags.append(value)
        return tags
