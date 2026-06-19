from __future__ import annotations

from collections import OrderedDict
import re
import time
from typing import Any
from urllib.parse import quote, urlencode, urlparse

from src.config import JobBoardDefinition
from src.models import Job, normalize_text

from .base import BaseJobSource


ASHBY_API_ROOT = "https://api.ashbyhq.com/posting-api/job-board"


class AshbyJobSource(BaseJobSource):
    name = "Ashby"

    def fetch_jobs(self) -> list[Job]:
        if not self.config.boards:
            self.logger.warning("Ashby source has no configured job boards.")
            return []

        jobs_by_key: OrderedDict[str, Job] = OrderedDict()
        for board in self.config.boards:
            url = self._build_api_url(board.slug)
            payload = self.fetch_json(url)
            if not isinstance(payload, dict):
                continue

            for job in self._parse_payload(payload=payload, board=board):
                jobs_by_key[job.dedupe_key] = job

            if self.config.pause_seconds > 0:
                time.sleep(self.config.pause_seconds)

        return list(jobs_by_key.values())

    def _build_api_url(self, board_slug: str) -> str:
        query = urlencode({"includeCompensation": str(self.config.include_compensation).lower()})
        return f"{ASHBY_API_ROOT}/{quote(board_slug, safe='')}?{query}"

    def _parse_payload(
        self,
        *,
        payload: dict[str, Any],
        board: JobBoardDefinition,
    ) -> list[Job]:
        postings = payload.get("jobs")
        if not isinstance(postings, list):
            self.logger.warning("Ashby board %s returned no jobs list.", board.slug)
            return []

        jobs: list[Job] = []
        for posting in postings:
            if not isinstance(posting, dict) or posting.get("isListed") is False:
                continue

            title = normalize_text(posting.get("title"))
            job_url = normalize_text(posting.get("jobUrl") or posting.get("applyUrl"))
            if not title or not job_url:
                continue

            description = normalize_text(posting.get("descriptionPlain"))
            compensation = self._compensation_summary(posting.get("compensation"))
            description_bits = [value for value in [description, compensation] if value]

            jobs.append(
                Job.create(
                    source=self.name,
                    source_job_id=self._source_job_id(board.slug, job_url),
                    company=board.name,
                    title=title,
                    location=self._location(posting),
                    url=job_url,
                    posted_at=normalize_text(posting.get("publishedAt")),
                    description_snippet=" | ".join(description_bits) or None,
                    employment_type=self._humanize_enum(posting.get("employmentType")),
                    tags=self._tags(posting),
                    raw={"board": board.slug, **posting},
                )
            )

        return jobs

    @staticmethod
    def _location(posting: dict[str, Any]) -> str | None:
        locations: list[str] = []
        primary = normalize_text(posting.get("location"))
        if primary:
            locations.append(primary)

        for secondary in posting.get("secondaryLocations") or []:
            if not isinstance(secondary, dict):
                continue
            value = normalize_text(secondary.get("location"))
            if value and value not in locations:
                locations.append(value)

        is_remote = posting.get("isRemote") is True or posting.get("workplaceType") == "Remote"
        if is_remote and not any("remote" in value.lower() for value in locations):
            locations.insert(0, "Remote")
        return ", ".join(locations) or None

    @classmethod
    def _tags(cls, posting: dict[str, Any]) -> list[str]:
        tags: list[str] = []
        for key in ("department", "team", "workplaceType"):
            value = cls._humanize_enum(posting.get(key))
            if value and value not in tags:
                tags.append(value)
        return tags

    @staticmethod
    def _compensation_summary(value: Any) -> str | None:
        if not isinstance(value, dict):
            return None
        summary = normalize_text(
            value.get("scrapeableCompensationSalarySummary")
            or value.get("compensationTierSummary")
        )
        return f"Compensation: {summary}" if summary else None

    @staticmethod
    def _humanize_enum(value: Any) -> str | None:
        text = normalize_text(value)
        if not text:
            return None
        return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text).replace("_", " ")

    @staticmethod
    def _source_job_id(board_slug: str, job_url: str) -> str:
        path_parts = [part for part in urlparse(job_url).path.split("/") if part]
        posting_id = path_parts[-1] if path_parts else job_url
        return f"{board_slug}:{posting_id}"
