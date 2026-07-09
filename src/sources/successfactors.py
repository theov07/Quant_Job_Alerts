from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
from html import unescape
import re
import time
from typing import Any
from urllib.parse import quote, urljoin

from src.config import JobBoardDefinition
from src.models import Job, normalize_text

from .base import BaseJobSource


class SuccessFactorsJobSource(BaseJobSource):
    name = "SuccessFactors"

    def fetch_jobs(self) -> list[Job]:
        if not self.config.boards:
            self.logger.warning("SuccessFactors source has no configured job boards.")
            return []

        jobs_by_key: OrderedDict[str, Job] = OrderedDict()
        for board in self.config.boards:
            board_jobs = self._fetch_board_jobs(board)
            self.logger.info("SuccessFactors board %s fetched %d jobs.", board.name, len(board_jobs))
            for job in board_jobs:
                jobs_by_key[job.dedupe_key] = job

            if self.config.pause_seconds > 0:
                time.sleep(self.config.pause_seconds)

        return list(jobs_by_key.values())

    def _fetch_board_jobs(self, board: JobBoardDefinition) -> list[Job]:
        base_url = self._base_url(board.slug)
        search_urls = [self._build_search_url(base_url, 1)]
        jobs: list[Job] = []

        first_page = self.fetch_text(search_urls[0])
        if not first_page:
            return []
        search_urls.extend(self._additional_search_urls(base_url, first_page))

        for index, search_url in enumerate(search_urls):
            html = first_page if index == 0 else self.fetch_text(search_url)
            if not html:
                continue
            for job_url in self._job_links(base_url, html):
                detail_html = self.fetch_text(job_url)
                if not detail_html:
                    continue
                job = self._parse_detail(html=detail_html, board=board, job_url=job_url)
                if job:
                    jobs.append(job)
                if self.config.pause_seconds > 0:
                    time.sleep(self.config.pause_seconds)

        return jobs

    @staticmethod
    def _base_url(board_slug: str) -> str:
        if board_slug.startswith(("http://", "https://")):
            return board_slug.rstrip("/")
        return f"https://{board_slug}".rstrip("/")

    @staticmethod
    def _build_search_url(base_url: str, startrow: int) -> str:
        if startrow <= 1:
            return f"{base_url}/search/?createNewAlert=false&q="
        return f"{base_url}/search/?createNewAlert=false&q=&startrow={startrow}"

    def _additional_search_urls(self, base_url: str, html: str) -> list[str]:
        label = self.make_soup(html).select_one("#tile-search-results-label")
        text = label.get_text(" ", strip=True) if label else ""
        match = re.search(r"Showing\s+1\s+to\s+(\d+)\s+of\s+(\d+)\s+Jobs", text, flags=re.I)
        if not match:
            return []

        page_size = int(match.group(1))
        total = int(match.group(2))
        return [self._build_search_url(base_url, startrow) for startrow in range(page_size + 1, total + 1, page_size)]

    def _job_links(self, base_url: str, html: str) -> list[str]:
        links: list[str] = []
        soup = self.make_soup(html)
        for anchor in soup.find_all("a", href=True):
            href = unescape(anchor["href"])
            if "/job/" not in href:
                continue
            url = urljoin(base_url, href)
            if url not in links:
                links.append(url)
        return links

    def _parse_detail(self, *, html: str, board: JobBoardDefinition, job_url: str) -> Job | None:
        soup = self.make_soup(html)
        title = self._title(soup)
        source_job_id = self._source_job_id(job_url)
        if not title or not source_job_id:
            return None

        location = self._location(soup)
        posted_at = self._posted_at(soup)

        return Job.create(
            source=self.name,
            source_job_id=f"{board.slug}:{source_job_id}",
            company=board.name,
            title=title,
            location=location,
            url=job_url,
            posted_at=posted_at,
            description_snippet=self._description(soup),
            employment_type=self._employment_type(title),
            tags=self._tags(soup),
            raw={"board": board.slug, "url": job_url},
        )

    @staticmethod
    def _source_job_id(job_url: str) -> str | None:
        match = re.search(r"/(\d+)/?$", job_url)
        return match.group(1) if match else None

    @staticmethod
    def _title(soup: Any) -> str | None:
        value = soup.select_one("[itemprop='title']")
        if value:
            return normalize_text(value.get_text(" ", strip=True))
        title = normalize_text(soup.title.get_text(" ", strip=True) if soup.title else None)
        if title and " Job Details" in title:
            return normalize_text(title.split(" Job Details", 1)[0])
        return title

    @staticmethod
    def _location(soup: Any) -> str | None:
        values: list[str] = []
        for prop in ("addressLocality", "addressRegion", "addressCountry"):
            node = soup.select_one(f"meta[itemprop='{prop}']")
            value = normalize_text(node.get("content") if node else None)
            if value and value not in values:
                values.append(value)
        return ", ".join(values) or None

    @classmethod
    def _posted_at(cls, soup: Any) -> str | None:
        node = soup.select_one("meta[itemprop='datePosted']")
        raw = normalize_text(node.get("content") if node else None)
        if not raw:
            return None

        for pattern in ("%a %b %d %H:%M:%S %Z %Y", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(raw, pattern)
            except ValueError:
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        return raw

    @staticmethod
    def _employment_type(title: str) -> str | None:
        lowered = title.lower()
        if "intern" in lowered or "internship" in lowered:
            return "Internship"
        return None

    @staticmethod
    def _tags(soup: Any) -> list[str]:
        tags: list[str] = []
        for row in soup.select(".joblayouttoken, .jobdescription, .job"):
            text = normalize_text(row.get_text(" ", strip=True))
            if not text:
                continue
            for keyword in ("Research", "Data", "Technology", "Trading", "Internship", "Quantitative"):
                if keyword.lower() in text.lower() and keyword not in tags:
                    tags.append(keyword)
        return tags[:5]

    def _description(self, soup: Any) -> str | None:
        description = soup.select_one("[itemprop='description']") or soup.select_one(".jobdescription") or soup.select_one(".job")
        if not description:
            return None
        return normalize_text(description.get_text(" ", strip=True))
