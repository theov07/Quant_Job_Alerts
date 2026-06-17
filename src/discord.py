from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from .models import Job


LOGGER = logging.getLogger(__name__)


class DiscordWebhookClient:
    def __init__(
        self,
        webhook_url: str,
        timeout_seconds: float = 10.0,
        embed_color: int = 3_447_003,
        show_match_reasons: bool = False,
        min_interval_seconds: float = 0.75,
        max_retries: int = 6,
    ) -> None:
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds
        self.embed_color = embed_color
        self.show_match_reasons = show_match_reasons
        self.min_interval_seconds = max(0.0, min_interval_seconds)
        self.max_retries = max(0, max_retries)
        self._last_send_monotonic: float | None = None

    def send_job_embed(self, job: Job, score: int, reasons: list[str] | None = None) -> None:
        payload = self._build_payload(job=job, score=score, reasons=reasons or [])

        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
            self._post_webhook_with_retries(client=client, payload=payload)

        LOGGER.info("Sent Discord embed for %s at %s", job.title, job.company or "Unknown company")

    def _post_webhook_with_retries(self, *, client: httpx.Client, payload: dict[str, Any]) -> None:
        request_url = self._build_webhook_request_url()
        for attempt in range(self.max_retries + 1):
            self._respect_min_interval()
            response = client.post(request_url, json=payload)

            if response.status_code != 429:
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as error:
                    raise RuntimeError(
                        f"Discord webhook rejected the request with status {response.status_code}: {response.text}"
                    ) from error
                self._last_send_monotonic = time.monotonic()
                return

            if attempt >= self.max_retries:
                raise RuntimeError(
                    f"Discord webhook rejected the request with status {response.status_code} "
                    f"after {self.max_retries} retries: {response.text}"
                )

            retry_after = max(self._parse_retry_after_seconds(response), self.min_interval_seconds)
            LOGGER.warning(
                "Discord rate limited a webhook request. Retrying in %.2fs (attempt %d/%d).",
                retry_after,
                attempt + 1,
                self.max_retries,
            )
            time.sleep(retry_after)

    def _respect_min_interval(self) -> None:
        if self._last_send_monotonic is None or self.min_interval_seconds <= 0:
            return

        elapsed = time.monotonic() - self._last_send_monotonic
        remaining = self.min_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _build_payload(self, *, job: Job, score: int, reasons: list[str]) -> dict[str, Any]:
        return {
            "username": "Quant Job Alerts",
            "allowed_mentions": {"parse": []},
            "embeds": [self._build_embed(job=job, score=score, reasons=reasons)],
            "components": [self._build_apply_button(job.url)],
        }

    def _build_embed(self, *, job: Job, score: int, reasons: list[str]) -> dict[str, Any]:
        title_company = job.company or "Unknown Company"
        formatted_title = f"{title_company} — {job.title}"
        fields: list[dict[str, Any]] = [
            {"name": "Location", "value": job.location or "N/A", "inline": True},
            {"name": "Type", "value": job.employment_type or "N/A", "inline": True},
            {"name": "Posted", "value": self._format_posted_at(job.posted_at), "inline": True},
            {"name": "Score", "value": str(score), "inline": True},
            {"name": "Tags", "value": self._format_tags(job.tags), "inline": False},
        ]

        if self.show_match_reasons and reasons:
            fields.append(
                {
                    "name": "Why it matched",
                    "value": self._truncate_text("; ".join(reasons), limit=300),
                    "inline": False,
                }
            )

        return {
            "title": formatted_title,
            "url": job.url,
            "color": self.embed_color,
            "description": (
                f"New relevant quant job found on {job.source}.\n"
                f"[Open job posting]({job.url})"
            ),
            "fields": fields,
            "footer": {"text": "Quant Job Alerts"},
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }

    def _build_webhook_request_url(self) -> str:
        parts = urlsplit(self.webhook_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query["with_components"] = "true"
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

    @staticmethod
    def _parse_retry_after_seconds(response: httpx.Response) -> float:
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        retry_after = payload.get("retry_after")
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except (TypeError, ValueError):
                pass

        header_value = response.headers.get("Retry-After")
        if header_value is not None:
            try:
                return max(0.0, float(header_value))
            except ValueError:
                pass

        return 1.0

    @staticmethod
    def _build_apply_button(job_url: str) -> dict[str, Any]:
        return {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 5,
                    "label": "Apply",
                    "url": job_url,
                }
            ],
        }

    @staticmethod
    def _format_posted_at(value: str | None) -> str:
        if not value:
            return "N/A"
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
        return parsed.date().isoformat()

    @staticmethod
    def _format_tags(tags: list[str]) -> str:
        if not tags:
            return "N/A"
        visible_tags = tags[:5]
        rendered = ", ".join(visible_tags)
        if len(tags) > 5:
            rendered = f"{rendered}, ..."
        return rendered

    @staticmethod
    def _truncate_text(value: str, limit: int = 300) -> str:
        if len(value) <= limit:
            return value
        return value[: limit - 3].rstrip() + "..."
