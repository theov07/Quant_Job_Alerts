from __future__ import annotations

import json
import re
from typing import Any

from src.models import Job, slugify, unix_timestamp_to_iso

from .base import BaseJobSource


class SimplifyJobSource(BaseJobSource):
    name = "Simplify"

    def fetch_jobs(self) -> list[Job]:
        if not self.config.url:
            self.logger.warning("Simplify source is missing its configured URL.")
            return []

        html = self.fetch_text(self.config.url)
        if not html:
            return []

        jobs = self._parse_next_data(html=html, source_url=self.config.url)
        if jobs:
            return jobs

        self.logger.warning(
            "Simplify did not expose the expected server-rendered data. "
            "The site may have changed or moved more logic to JavaScript."
        )
        return self._parse_anchor_fallback(html=html, source_url=self.config.url)

    def _parse_next_data(self, *, html: str, source_url: str) -> list[Job]:
        script_match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html,
        )
        if script_match is None:
            return []

        payload = json.loads(script_match.group(1))
        page_props = payload.get("props", {}).get("pageProps", {})
        initial_hits = page_props.get("initialJobHits", [])

        jobs: list[Job] = []
        for hit in initial_hits:
            posting_id = self._clean_text(hit.get("posting_id") or hit.get("id"))
            title = self._clean_text(hit.get("title"))
            if not posting_id or not title:
                continue

            job_url = self._build_job_url(posting_id=posting_id, title=title)
            company = self._clean_text(hit.get("company_name"))
            location = ", ".join(hit.get("locations", [])[:2]) or None
            employment_type = self._clean_text(hit.get("type"))
            posted_at = unix_timestamp_to_iso(hit.get("updated_date") or hit.get("start_date"))

            tags = self._build_tags(hit)
            description_snippet = self._build_description_snippet(hit)
            jobs.append(
                Job.create(
                    source=self.name,
                    source_job_id=posting_id,
                    company=company,
                    title=title,
                    location=location,
                    url=job_url,
                    posted_at=posted_at,
                    description_snippet=description_snippet,
                    employment_type=employment_type,
                    tags=tags,
                    raw=hit,
                )
            )

        return jobs

    def _parse_anchor_fallback(self, *, html: str, source_url: str) -> list[Job]:
        soup = self.make_soup(html)
        jobs: list[Job] = []
        for anchor in soup.select("a[href^='/p/']"):
            title = self._clean_text(anchor.get_text(" ", strip=True))
            href = anchor.get("href", "")
            if not title or not href:
                continue
            jobs.append(
                Job.create(
                    source=self.name,
                    title=title,
                    company=None,
                    location=None,
                    url=source_url,
                    description_snippet="Fallback parse from server-rendered anchor. Review source structure if needed.",
                    raw={"href": href, "fallback": True},
                )
            )
        return jobs

    @staticmethod
    def _build_job_url(*, posting_id: str, title: str) -> str:
        return f"https://simplify.jobs/p/{posting_id}/{slugify(title)}"

    @staticmethod
    def _build_tags(hit: dict[str, Any]) -> list[str]:
        tags: list[str] = []
        for key in ("functions", "experience_level", "majors", "seasons"):
            for value in hit.get(key, []) or []:
                cleaned = SimplifyJobSource._clean_text(value)
                if cleaned and cleaned != "N/A" and cleaned not in tags:
                    tags.append(cleaned)
        return tags

    @staticmethod
    def _build_description_snippet(hit: dict[str, Any]) -> str | None:
        parts: list[str] = []
        functions = [value for value in hit.get("functions", []) if value]
        experience = [value for value in hit.get("experience_level", []) if value]
        if functions:
            parts.append("Functions: " + ", ".join(functions[:3]))
        if experience:
            parts.append("Experience: " + ", ".join(experience[:2]))
        travel = SimplifyJobSource._clean_text(hit.get("travel_requirements"))
        if travel:
            parts.append(f"Work style: {travel}")
        return " | ".join(parts) if parts else None

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(str(value).split())
        return cleaned or None

