from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta, timezone
import re
import time
from urllib.parse import urljoin, urlparse

from bs4 import Tag

from src.models import Job

from .base import BaseJobSource


EMPLOYMENT_TYPES = {
    "contract",
    "freelance",
    "full-time",
    "internship",
    "part-time",
}
ROLE_CATEGORIES = {
    "customer support",
    "design",
    "engineering",
    "finance",
    "marketing",
    "non-tech",
    "operations",
    "other",
    "product",
    "sales",
}
POSTED_PATTERN = re.compile(r"^(today|yesterday|\d+\s*(?:mo|m|h|d|w|y))$", re.IGNORECASE)


class CryptocurrencyJobsSource(BaseJobSource):
    name = "Cryptocurrency Jobs"

    def fetch_jobs(self) -> list[Job]:
        configured_urls = self.config.urls or ([self.config.url] if self.config.url else [])
        if not configured_urls:
            self.logger.warning("Cryptocurrency Jobs source has no configured URLs.")
            return []

        jobs_by_key: OrderedDict[str, Job] = OrderedDict()
        for page_url in configured_urls:
            html = self.fetch_text(page_url)
            if not html:
                continue

            parsed_jobs = self._parse_listing_page(html=html, source_url=page_url)
            for job in parsed_jobs:
                jobs_by_key[job.dedupe_key] = job

            if self.config.pause_seconds > 0:
                time.sleep(self.config.pause_seconds)

        return list(jobs_by_key.values())

    def _parse_listing_page(self, *, html: str, source_url: str) -> list[Job]:
        soup = self.make_soup(html)
        cards = soup.select("ul.mt-6 > li")
        if not cards:
            cards = self._find_fallback_cards(soup.body if soup.body else soup)

        jobs: OrderedDict[str, Job] = OrderedDict()
        for card in cards:
            job = self._build_job_from_card(card=card, source_url=source_url)
            if job is not None:
                jobs[job.dedupe_key] = job

        if not jobs:
            self.logger.warning(
                "No Cryptocurrency Jobs cards were parsed from %s. The page structure may have changed.",
                source_url,
            )

        return list(jobs.values())

    def _build_job_from_card(self, *, card: Tag, source_url: str) -> Job | None:
        if card.has_attr("data-listing-ad"):
            return None

        title_anchor = card.select_one("h2 a[href]")
        if title_anchor is None:
            return None

        href = self._clean_text(title_anchor.get("href"))
        title = self._clean_text(title_anchor.get_text(" ", strip=True))
        if not href or not title:
            return None

        absolute_url = urljoin(source_url, href)
        if not self._is_job_url(absolute_url):
            return None

        company_node = card.select_one("h3")
        company = self._clean_text(company_node.get_text(" ", strip=True)) if company_node else None

        metadata = [
            value
            for value in (self._clean_text(node.get_text(" ", strip=True)) for node in card.select("h4"))
            if value
        ]
        location: str | None = None
        categories: list[str] = []
        employment_types: list[str] = []
        tags = self._extract_tags(card)
        for value in metadata:
            if self._is_employment_type(value):
                self._append_unique(employment_types, value)
            elif self._is_role_category(value):
                self._append_unique(categories, value)
            elif location is None:
                location = value
            else:
                self._append_unique(tags, value)

        for value in categories + employment_types:
            self._append_unique(tags, value)

        posted_text = self._extract_posted_text(card)
        salary = self._extract_salary(card)

        description_bits: list[str] = []
        if categories:
            description_bits.append("Category: " + ", ".join(categories[:2]))
        if salary:
            description_bits.append(f"Salary: {salary}")
        if tags:
            description_bits.append("Tags: " + ", ".join(tags[:8]))
        if posted_text:
            description_bits.append(f"Posted: {posted_text}")

        return Job.create(
            source=self.name,
            source_job_id=self._job_id_from_url(absolute_url),
            company=company,
            title=title,
            location=location,
            url=absolute_url,
            posted_at=self._parse_posted_at(posted_text),
            description_snippet=" | ".join(description_bits) or None,
            employment_type=", ".join(employment_types) or None,
            tags=tags,
            raw={
                "listing_url": source_url,
                "metadata": metadata,
                "posted_text": posted_text,
                "salary": salary,
            },
        )

    @staticmethod
    def _find_fallback_cards(root: Tag) -> list[Tag]:
        cards: list[Tag] = []
        for anchor in root.select("h2 a[href]"):
            current = anchor
            for _ in range(6):
                if current.parent is None or not isinstance(current.parent, Tag):
                    break
                current = current.parent
                if current.name == "li":
                    cards.append(current)
                    break
        return cards

    @staticmethod
    def _extract_tags(card: Tag) -> list[str]:
        tags: list[str] = []
        for node in card.select("ul.flex span.block, ul.flex a.block"):
            text = CryptocurrencyJobsSource._clean_text(node.get_text(" ", strip=True))
            if text and text not in {",", "Featured"}:
                CryptocurrencyJobsSource._append_unique(tags, text)
        return tags

    @staticmethod
    def _extract_posted_text(card: Tag) -> str | None:
        for node in reversed(card.find_all("span")):
            text = CryptocurrencyJobsSource._clean_text(node.get_text(" ", strip=True))
            if text and POSTED_PATTERN.fullmatch(text):
                return text
        return None

    @staticmethod
    def _extract_salary(card: Tag) -> str | None:
        for node in card.find_all("span"):
            text = CryptocurrencyJobsSource._clean_text(node.get_text(" ", strip=True))
            if text and "$" in text and any(char.isdigit() for char in text):
                return text
        return None

    @staticmethod
    def _parse_posted_at(value: str | None) -> str | None:
        text = (CryptocurrencyJobsSource._clean_text(value) or "").lower()
        if not text:
            return None

        current = datetime.now(timezone.utc)
        if text == "today":
            return current.replace(microsecond=0).isoformat()
        if text == "yesterday":
            return (current - timedelta(days=1)).replace(microsecond=0).isoformat()

        match = re.fullmatch(r"(\d+)\s*(mo|m|h|d|w|y)", text)
        if match is None:
            return None

        amount = int(match.group(1))
        unit = match.group(2)
        delta_map = {
            "m": timedelta(minutes=amount),
            "h": timedelta(hours=amount),
            "d": timedelta(days=amount),
            "w": timedelta(weeks=amount),
            "mo": timedelta(days=30 * amount),
            "y": timedelta(days=365 * amount),
        }
        return (current - delta_map[unit]).replace(microsecond=0).isoformat()

    @staticmethod
    def _is_job_url(url: str) -> bool:
        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc not in {"cryptocurrencyjobs.co", "www.cryptocurrencyjobs.co"}:
            return False
        path_parts = [part for part in parsed.path.split("/") if part]
        return len(path_parts) >= 2

    @staticmethod
    def _is_employment_type(value: str) -> bool:
        return value.lower() in EMPLOYMENT_TYPES

    @staticmethod
    def _is_role_category(value: str) -> bool:
        return value.lower() in ROLE_CATEGORIES

    @staticmethod
    def _job_id_from_url(url: str) -> str:
        parsed = urlparse(url)
        return parsed.path.strip("/") or url

    @staticmethod
    def _append_unique(values: list[str], value: str) -> None:
        if value not in values:
            values.append(value)

    @staticmethod
    def _clean_text(value: object | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(str(value).split())
        return cleaned or None
