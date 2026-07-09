from __future__ import annotations

from collections import OrderedDict
from html import unescape
import json
import time
from typing import Any
from urllib.parse import quote, urljoin

from src.config import JobBoardDefinition
from src.models import Job, normalize_text

from .base import BaseJobSource


class PinpointJobSource(BaseJobSource):
    name = "Pinpoint"

    def fetch_jobs(self) -> list[Job]:
        if not self.config.boards:
            self.logger.warning("Pinpoint source has no configured job boards.")
            return []

        jobs_by_key: OrderedDict[str, Job] = OrderedDict()
        for board in self.config.boards:
            payload = self.fetch_json(self._build_api_url(board.slug))
            if not isinstance(payload, dict):
                continue

            board_jobs = self._parse_payload(payload=payload, board=board)
            self.logger.info("Pinpoint board %s fetched %d jobs.", board.name, len(board_jobs))
            for job in board_jobs:
                jobs_by_key[job.dedupe_key] = job

            if self.config.pause_seconds > 0:
                time.sleep(self.config.pause_seconds)

        return list(jobs_by_key.values())

    @staticmethod
    def _base_url(board_slug: str) -> str:
        if board_slug.startswith(("http://", "https://")):
            return board_slug.rstrip("/")
        if "." in board_slug:
            return f"https://{board_slug}".rstrip("/")
        return f"https://{board_slug}.pinpointhq.com"

    @classmethod
    def _build_api_url(cls, board_slug: str) -> str:
        return f"{cls._base_url(board_slug)}/postings.json"

    def _parse_payload(self, *, payload: dict[str, Any], board: JobBoardDefinition) -> list[Job]:
        postings = payload.get("data")
        if not isinstance(postings, list):
            self.logger.warning("Pinpoint board %s returned no data list.", board.slug)
            return []

        jobs: list[Job] = []
        for posting in postings:
            if not isinstance(posting, dict):
                continue

            title = normalize_text(posting.get("title"))
            job_url = normalize_text(posting.get("url"))
            source_job_id = normalize_text(posting.get("id"))
            if not title or not job_url or not source_job_id:
                continue

            absolute_url = urljoin(self._base_url(board.slug), job_url)
            detail = self._job_posting_schema(absolute_url)

            jobs.append(
                Job.create(
                    source=self.name,
                    source_job_id=f"{board.slug}:{source_job_id}",
                    company=board.name,
                    title=title,
                    location=self._location(posting),
                    url=absolute_url,
                    posted_at=(
                        normalize_text(detail.get("datePosted"))
                        or normalize_text(posting.get("published_at"))
                        or normalize_text(posting.get("created_at"))
                    ),
                    description_snippet=self._description(posting, detail),
                    employment_type=self._employment_type(posting),
                    tags=self._tags(posting),
                    raw={"board": board.slug, **posting},
                )
            )

            if self.config.pause_seconds > 0:
                time.sleep(self.config.pause_seconds)

        return jobs

    def _job_posting_schema(self, job_url: str) -> dict[str, Any]:
        html = self.fetch_text(job_url)
        if not html:
            return {}

        soup = self.make_soup(html)
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                payload = json.loads(script.get_text(strip=True))
            except json.JSONDecodeError:
                continue
            for item in self._iter_schema_items(payload):
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    return item
        return {}

    @classmethod
    def _iter_schema_items(cls, value: Any) -> list[Any]:
        if isinstance(value, list):
            return [item for entry in value for item in cls._iter_schema_items(entry)]
        if isinstance(value, dict):
            items = [value]
            graph = value.get("@graph")
            if isinstance(graph, list):
                items.extend(graph)
            return items
        return []

    @staticmethod
    def _location(posting: dict[str, Any]) -> str | None:
        location = posting.get("location")
        if isinstance(location, dict):
            return normalize_text(location.get("name") or location.get("city"))
        return normalize_text(location)

    @staticmethod
    def _employment_type(posting: dict[str, Any]) -> str | None:
        return normalize_text(posting.get("employment_type_text") or posting.get("employment_type"))

    def _description(self, posting: dict[str, Any], detail: dict[str, Any]) -> str | None:
        parts: list[str] = []
        for value in [
            detail.get("description"),
            posting.get("description"),
            posting.get("key_responsibilities"),
            posting.get("skills_knowledge_expertise"),
            posting.get("benefits"),
        ]:
            text = self._html_to_text(value)
            if text and text not in parts:
                parts.append(text)
        return " | ".join(parts[:3]) or None

    @staticmethod
    def _tags(posting: dict[str, Any]) -> list[str]:
        tags: list[str] = []
        job = posting.get("job")
        if isinstance(job, dict):
            for field in ("department", "division", "structure_custom_group_one"):
                value = job.get(field)
                if isinstance(value, dict):
                    name = normalize_text(value.get("name"))
                    if name and name not in tags:
                        tags.append(name)

        for value in [posting.get("workplace_type_text"), posting.get("employment_type_text")]:
            text = normalize_text(value)
            if text and text not in tags:
                tags.append(text)
        return tags

    def _html_to_text(self, value: Any) -> str | None:
        text = normalize_text(value)
        if not text:
            return None
        decoded = unescape(text)
        if "<" not in decoded:
            return normalize_text(decoded)
        return normalize_text(self.make_soup(decoded).get_text(" ", strip=True))
