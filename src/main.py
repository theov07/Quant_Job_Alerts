from __future__ import annotations

import argparse
import logging
import sys

from dotenv import load_dotenv

from .config import PROJECT_ROOT, AppSettings, load_filter_config, load_sources_config
from .discord import DiscordWebhookClient
from .filters import JobFilter
from .sample_jobs import build_sample_jobs
from .sources import SOURCE_REGISTRY, BaseJobSource
from .storage import SeenJobStore


LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor quant job boards and send Discord webhook alerts.")
    parser.add_argument("--dry-run", action="store_true", help="Print matching jobs without sending Discord messages.")
    parser.add_argument("--source", action="append", help="Limit execution to a specific configured source key.")
    parser.add_argument("--min-score", type=int, help="Override the minimum score threshold for this run.")
    parser.add_argument(
        "--reset-seen",
        action="store_true",
        help="Clear the SQLite deduplication table and exit without fetching jobs.",
    )
    parser.add_argument(
        "--sample-data",
        action="store_true",
        help="Use bundled sample jobs instead of live scraping so you can test filters and Discord embeds safely.",
    )
    return parser.parse_args()


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def build_sources(settings: AppSettings, selected_sources: set[str] | None = None) -> list[BaseJobSource]:
    source_config = load_sources_config()
    sources: list[BaseJobSource] = []

    for source_key, definition in source_config.sources.items():
        if not definition.enabled:
            continue
        if selected_sources and source_key not in selected_sources:
            continue

        source_class = SOURCE_REGISTRY.get(definition.type)
        if source_class is None:
            LOGGER.warning("No source implementation is registered for type '%s'.", definition.type)
            continue

        sources.append(
            source_class(
                source_key=source_key,
                config=definition,
                timeout_seconds=settings.request_timeout_seconds,
                user_agent=settings.user_agent,
            )
        )

    return sources


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    settings = AppSettings.from_env()
    args = parse_args()
    configure_logging(settings.log_level)

    store = SeenJobStore(settings.database_path)
    store.initialize()

    if args.reset_seen:
        store.reset()
        LOGGER.info("Cleared deduplication state in %s", settings.database_path)
        return 0

    filter_config = load_filter_config()
    minimum_score = args.min_score if args.min_score is not None else settings.min_score
    job_filter = JobFilter(filter_config)
    show_match_reasons = (
        settings.show_match_reasons
        if settings.show_match_reasons is not None
        else filter_config.show_match_reasons
    )

    discord_client: DiscordWebhookClient | None = None
    if not args.dry_run:
        if not settings.discord_webhook_url:
            LOGGER.error("DISCORD_WEBHOOK_URL is required unless you are using --dry-run.")
            return 1
        discord_client = DiscordWebhookClient(
            webhook_url=settings.discord_webhook_url,
            timeout_seconds=settings.request_timeout_seconds,
            embed_color=settings.discord_embed_color,
            show_match_reasons=show_match_reasons,
        )

    if args.sample_data:
        all_jobs = build_sample_jobs()
        LOGGER.info("Loaded %d bundled sample jobs.", len(all_jobs))
    else:
        selected_sources = set(args.source or [])
        sources = build_sources(settings=settings, selected_sources=selected_sources or None)
        if not sources:
            LOGGER.error("No sources were selected or enabled.")
            return 1

        all_jobs = []
        for source in sources:
            source_jobs = source.fetch_jobs()
            LOGGER.info("%s fetched %d jobs.", source.name, len(source_jobs))
            all_jobs.extend(source_jobs)

    processed_keys: set[str] = set()
    fetched_count = len(all_jobs)
    relevant_count = 0
    duplicate_count = 0
    new_count = 0
    sent_count = 0

    for job in all_jobs:
        if job.dedupe_key in processed_keys:
            continue
        processed_keys.add(job.dedupe_key)

        decision = job_filter.evaluate(job, minimum_score=minimum_score)
        if not decision.passed:
            continue

        relevant_count += 1
        if store.has_seen(job):
            duplicate_count += 1
            continue

        new_count += 1
        if args.dry_run:
            print(
                f"DRY RUN | score={decision.score} | {job.company or 'Unknown'} | {job.title} | "
                f"{job.location or 'Unknown'} | {job.url}"
            )
            continue

        assert discord_client is not None
        try:
            discord_client.send_job_embed(job=job, score=decision.score, reasons=decision.reasons)
            store.mark_seen(job)
            sent_count += 1
        except Exception as error:  # pragma: no cover - defensive production logging
            LOGGER.exception("Failed to send Discord alert for %s: %s", job.title, error)

    LOGGER.info(
        "Run complete. fetched=%d relevant=%d new=%d duplicates=%d sent=%d dry_run=%s min_score=%d db=%s",
        fetched_count,
        relevant_count,
        new_count,
        duplicate_count,
        sent_count,
        args.dry_run,
        minimum_score,
        settings.database_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
