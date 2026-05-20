# quant-job-alerts

A clean Python job alert bot for Discord focused on Quant Research, Quant Trading, Hedge Fund internship, and graduate roles.

It currently supports:

- Simplify Quant Finance Jobs
- eFinancialCareers quant search pages

The project is built to be modular so you can add new sources later with minimal changes.

## Features

- Normalized `Job` model with stable deduplication keys
- Modular source adapters via `BaseJobSource`
- YAML-driven source and filter configuration
- SQLite deduplication for local use
- Discord webhook alerts sent as embeds
- `--dry-run` mode for safe testing
- `--sample-data` mode for end-to-end testing even if live scraping is flaky
- Type hints and clean logging

## Project Structure

```text
quant-job-alerts/
├── .github/
│   └── workflows/
│       └── job-monitor.yml
├── config/
│   ├── filters.yaml
│   └── sources.yaml
├── data/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── discord.py
│   ├── filters.py
│   ├── main.py
│   ├── models.py
│   ├── sample_jobs.py
│   ├── scheduler.py
│   ├── storage.py
│   └── sources/
│       ├── __init__.py
│       ├── base.py
│       ├── efinancialcareers.py
│       └── simplify.py
├── tests/
│   ├── test_filters.py
│   ├── test_models.py
│   └── test_storage.py
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## Setup

1. Create a virtual environment and install dependencies.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env`.

```bash
cp .env.example .env
```

3. Fill in your Discord webhook URL in `.env`.

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
LOG_LEVEL=INFO
MIN_SCORE=3
DATABASE_PATH=data/seen_jobs.sqlite
REQUEST_TIMEOUT_SECONDS=20
SHOW_MATCH_REASONS=false
```

Do not commit your real `.env` file or webhook URL.

## Running The Bot

Run all enabled sources:

```bash
python -m src.main
```

Dry run without Discord sending:

```bash
python -m src.main --dry-run
```

Run only Simplify:

```bash
python -m src.main --source simplify
```

Run only eFinancialCareers:

```bash
python -m src.main --source efinancialcareers
```

Override the score threshold:

```bash
python -m src.main --min-score 4
```

Reset the deduplication database:

```bash
python -m src.main --reset-seen
```

Run with bundled sample jobs:

```bash
python -m src.main --sample-data --dry-run
```

## How `.env` Should Be Configured

Set these values:

- `DISCORD_WEBHOOK_URL`
  Your Discord webhook URL. Leave it empty only if you are using `--dry-run`.
- `LOG_LEVEL`
  Recommended value: `INFO`
- `MIN_SCORE`
  Default minimum score used when `--min-score` is not passed
- `DATABASE_PATH`
  Local SQLite file path. The default is `data/seen_jobs.sqlite`
- `REQUEST_TIMEOUT_SECONDS`
  HTTP timeout for source fetches and webhook delivery
- `SHOW_MATCH_REASONS`
  Optional override for whether Discord embeds include a final `Why it matched` field. Default: `false`

## Filtering Logic

Filtering is score-based, not just boolean.

Current defaults:

- `+3` if the title contains `quant` or `quantitative`
- `+2` if the title contains `research`, `researcher`, `trader`, or `trading`
- `+2` if the title contains `intern`, `internship`, `graduate`, or `summer`
- `+1` if the job mentions a preferred location
- `-5` per matched negative keyword
- `+1` for additional broader quant keywords in the full job text

Only jobs at or above the configured threshold are eligible for alerting.

All keywords and weights live in `config/filters.yaml`.

## Deduplication

Seen jobs are stored locally in SQLite.

Table:

- `dedupe_key`
- `source`
- `company`
- `title`
- `location`
- `url`
- `first_seen_at`
- `last_seen_at`

Deduplication key behavior:

- Uses `source + source_job_id` when a stable source job ID is available
- Otherwise falls back to a hash of `company + title + location + url`

If a job is already in SQLite, it will not be sent again.

## Discord Embed Alerts

The bot sends Discord webhook payloads using embeds, not raw text messages.

Each embed includes:

- Clickable title in the format `{company} — {title}`
- Short description: `New relevant quant job found on {source}.`
- Compact fields for `Location`, `Type`, `Posted`, `Score`, and `Tags`
- Up to 5 tags, then `...` when more exist
- Optional `Why it matched` field when `SHOW_MATCH_REASONS=true`

The bot does not use `@everyone` or `@here`.

## Testing Discord Embed Sending

The safest flow is:

1. Put your webhook into `.env`
2. Run:

```bash
python -m src.main --sample-data
```

That sends a couple of sample embeds so you can verify formatting without relying on live site scraping.

If you want to inspect the pipeline without sending anything:

```bash
python -m src.main --sample-data --dry-run
```

## Notes On The Live Sources

### Simplify

The current implementation prefers the server-rendered `__NEXT_DATA__` payload on the list page, which exposes stable posting IDs and metadata.

If that payload disappears or changes shape, the source falls back to a basic anchor parse and logs a warning.

### eFinancialCareers

The current implementation parses HTML job cards from configured search pages.

This site can intermittently return maintenance or anti-bot pages to scriptable clients. The source handles that gracefully by logging and skipping the cycle rather than inventing data.

If the configured URLs change, update `config/sources.yaml`.

## How To Add A New Source Later

To add LinkedIn, Greenhouse, Lever, Ashby, Workday, or a direct hedge fund careers page later:

1. Create a new file in `src/sources/`, for example `greenhouse.py`
2. Implement a class that inherits from `BaseJobSource`
3. Normalize each listing into the shared `Job` model
4. Register the source class in `src/sources/__init__.py`
5. Add the new source entry in `config/sources.yaml`

No major changes to the filtering, storage, Discord, or CLI layers should be needed.

## Scheduling

### Local cron

Example:

```bash
*/30 * * * * cd /path/to/quant-job-alerts && /usr/bin/python3 -m src.main
```

### GitHub Actions

The repo includes `.github/workflows/job-monitor.yml`, which:

- runs automatically on every push to `main`
- runs every 30 minutes
- supports manual dispatch from the GitHub Actions UI

Add this secret before using it:

- `DISCORD_WEBHOOK_URL`

Important caveat:

GitHub-hosted runners do not persist `data/seen_jobs.sqlite` between runs.

That means the included workflow is fine as a starting point, but it can resend duplicate jobs unless you later add persistent state. Good future options are:

- a small hosted database
- a persistent object store
- a lightweight external KV store

For local usage, SQLite is perfectly fine.

## Running Tests

```bash
python -m unittest discover -s tests
```

## Extension Ideas

- LinkedIn alert email parsing
- Greenhouse, Lever, Ashby, and Workday adapters
- Better salary extraction
- Persistent hosted dedupe storage
- Richer Discord embeds with logos or source-specific badges
