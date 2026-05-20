from __future__ import annotations

from collections import OrderedDict
import re
import time
from typing import Iterable
from urllib.parse import urlencode, urljoin, urlparse, urlunparse

from bs4 import Tag

from src.models import Job, parse_relative_datetime

from .base import BaseJobSource


EMPLOYMENT_TYPES = (
    "Internships & Graduate Trainee",
    "Permanent",
    "Contract",
    "Temporary",
    "Part time",
    "Part Time",
    "Graduate",
    "Internship",
)
WORK_ARRANGEMENTS = ("Hybrid", "Remote", "Flexible", "In-Office")
POSTED_PATTERN = re.compile(
    r"^(today|yesterday|\d+\s+(minute|minutes|hour|hours|day|days|week|weeks|month|months|year|years)\s+ago)$",
    re.IGNORECASE,
)


class EFinancialCareersJobSource(BaseJobSource):
    name = "eFinancialCareers"

    def fetch_jobs(self) -> list[Job]:
        configured_urls = self.config.urls or ([self.config.url] if self.config.url else [])
        if not configured_urls:
            self.logger.warning("eFinancialCareers source has no configured URLs.")
            return []

        jobs_by_key: OrderedDict[str, Job] = OrderedDict()
        for base_url in configured_urls:
            for page_url in self._iter_page_urls(base_url, self.config.max_pages):
                html = self.fetch_text(page_url)
                if not html:
                    continue
                if "Scheduled Maintenance" in html:
                    self.logger.warning(
                        "eFinancialCareers returned a maintenance page for %s. Skipping this fetch cycle.",
                        page_url,
                    )
                    continue

                parsed_jobs = self._parse_listing_page(html=html, source_url=page_url)
                for job in parsed_jobs:
                    jobs_by_key[job.dedupe_key] = job

                if self.config.pause_seconds > 0:
                    time.sleep(self.config.pause_seconds)

        return list(jobs_by_key.values())

    def _parse_listing_page(self, *, html: str, source_url: str) -> list[Job]:
        soup = self.make_soup(html)
        jobs: OrderedDict[str, Job] = OrderedDict()

        for anchor in soup.select("a[href]"):
            href = (anchor.get("href") or "").strip()
            title = self._clean_text(anchor.get_text(" ", strip=True))
            if not self._is_candidate_job_link(href=href, title=title):
                continue

            container = self._find_card_container(anchor)
            if container is None:
                continue

            lines = self._extract_card_lines(container)
            if "Apply now" not in lines:
                continue

            job = self._build_job_from_card(
                href=href,
                title=title,
                lines=lines,
                source_url=source_url,
            )
            if job is not None:
                jobs[job.dedupe_key] = job

        if not jobs:
            self.logger.warning(
                "No eFinancialCareers job cards were parsed from %s. "
                "The page structure may have changed or the site may be blocking scriptless clients.",
                source_url,
            )

        return list(jobs.values())

    def _build_job_from_card(
        self,
        *,
        href: str,
        title: str,
        lines: list[str],
        source_url: str,
    ) -> Job | None:
        cleaned_lines = [line for line in self._dedupe_preserve_order(lines) if line]
        if title not in cleaned_lines:
            cleaned_lines.insert(0, title)

        try:
            title_index = cleaned_lines.index(title)
        except ValueError:
            title_index = 0

        tail = [
            line
            for line in cleaned_lines[title_index + 1 :]
            if line.lower() not in {"apply now", "save", "apply now save"}
        ]
        if not tail:
            return None

        company = tail[0]
        location_line = tail[1] if len(tail) > 1 else None
        details_line = tail[2] if len(tail) > 2 else None
        posted_line = next((line for line in tail if POSTED_PATTERN.match(line)), None)

        location = self._strip_trailing_tokens(location_line, EMPLOYMENT_TYPES)
        employment_type = self._extract_first_token(location_line, EMPLOYMENT_TYPES)
        work_arrangement = self._extract_first_token(details_line, WORK_ARRANGEMENTS)
        posted_at = parse_relative_datetime(posted_line)

        description_bits = [
            line
            for line in tail[2:5]
            if line not in {posted_line, work_arrangement} and not POSTED_PATTERN.match(line)
        ]
        description_snippet = " | ".join(description_bits[:2]) or None

        tags = [value for value in [employment_type, work_arrangement] if value]
        absolute_url = urljoin(source_url, href)
        job_id = self._job_id_from_url(absolute_url)

        return Job.create(
            source=self.name,
            source_job_id=job_id,
            company=company,
            title=title,
            location=location,
            url=absolute_url,
            posted_at=posted_at,
            description_snippet=description_snippet,
            employment_type=employment_type,
            tags=tags,
            raw={"search_url": source_url, "card_lines": cleaned_lines},
        )

    @staticmethod
    def _iter_page_urls(base_url: str, max_pages: int) -> Iterable[str]:
        if max_pages <= 1:
            yield base_url
            return

        for page in range(1, max_pages + 1):
            if page == 1:
                yield base_url
                continue

            parsed = urlparse(base_url)
            query_params = []
            if parsed.query:
                for part in parsed.query.split("&"):
                    if part and not part.startswith("page="):
                        key, _, value = part.partition("=")
                        query_params.append((key, value))
            query_params.append(("page", str(page)))
            yield urlunparse(parsed._replace(query=urlencode(query_params)))

    @staticmethod
    def _is_candidate_job_link(*, href: str, title: str | None) -> bool:
        if not href or not title:
            return False
        if "/jobs/" not in href:
            return False

        lowered = title.lower()
        if lowered in {"apply now", "save", "show more", "get started"}:
            return False
        if lowered.endswith(" jobs"):
            return False
        if len(title) < 4:
            return False
        return True

    @staticmethod
    def _find_card_container(anchor: Tag) -> Tag | None:
        current: Tag | None = anchor
        for _ in range(8):
            if current is None or current.parent is None:
                return None
            current = current.parent
            if not isinstance(current, Tag):
                return None
            text = " ".join(current.stripped_strings)
            if "Apply now" in text and len(text) < 1200:
                return current
            if current.name in {"main", "body"}:
                break
        return None

    @staticmethod
    def _extract_card_lines(container: Tag) -> list[str]:
        return [" ".join(line.split()) for line in container.stripped_strings if line and line.strip()]

    @staticmethod
    def _dedupe_preserve_order(values: list[str]) -> list[str]:
        deduped: list[str] = []
        for value in values:
            if value not in deduped:
                deduped.append(value)
        return deduped

    @staticmethod
    def _extract_first_token(value: str | None, choices: Iterable[str]) -> str | None:
        if not value:
            return None
        lowered = value.lower()
        for choice in choices:
            if choice.lower() in lowered:
                return choice
        return None

    @staticmethod
    def _strip_trailing_tokens(value: str | None, tokens: Iterable[str]) -> str | None:
        if not value:
            return None
        cleaned = value
        for token in sorted(tokens, key=len, reverse=True):
            cleaned = re.sub(rf"\s*{re.escape(token)}\s*$", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip() or None

    @staticmethod
    def _job_id_from_url(url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        return path.split("/")[-1] if path else url

    @staticmethod
    def _clean_text(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

