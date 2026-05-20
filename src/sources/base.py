from __future__ import annotations

from abc import ABC, abstractmethod
import logging

from bs4 import BeautifulSoup
import httpx

from src.config import SourceDefinition
from src.models import Job


class BaseJobSource(ABC):
    name: str

    def __init__(self, source_key: str, config: SourceDefinition, timeout_seconds: float, user_agent: str) -> None:
        self.source_key = source_key
        self.config = config
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.logger = logging.getLogger(f"{__name__}.{source_key}")

    @abstractmethod
    def fetch_jobs(self) -> list[Job]:
        raise NotImplementedError

    @property
    def headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    def fetch_text(self, url: str) -> str | None:
        try:
            with httpx.Client(
                headers=self.headers,
                timeout=self.timeout_seconds,
                follow_redirects=True,
            ) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as error:
            self.logger.warning("Failed to fetch %s from %s: %s", self.name, url, error)
            return None

    @staticmethod
    def make_soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

