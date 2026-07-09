# quant-job-alerts

A clean Python job alert bot for Discord focused on Quant Research, Quant Trading, Hedge Fund internship, and graduate roles.

It currently supports:

- Ashby public job boards for selected crypto and quantitative trading companies
- Breezy public JSON boards, including Marex
- Greenhouse public job boards for major quantitative funds and trading firms
- Lever public postings boards, including Belvedere, Gauntlet, and Valkyrie
- Pinpoint public postings boards, including Systematica and Wolverine
- SAP SuccessFactors careers pages, including CFM
- Cryptocurrency Jobs crypto/Web3 listing pages
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
│   ├── quant_firms.yaml
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
│       ├── ashby.py
│       ├── base.py
│       ├── breezy.py
│       ├── cryptocurrencyjobs.py
│       ├── efinancialcareers.py
│       ├── greenhouse.py
│       ├── lever.py
│       ├── pinpoint.py
│       ├── simplify.py
│       └── successfactors.py
├── tests/
│   ├── test_ashby.py
│   ├── test_breezy.py
│   ├── test_cryptocurrencyjobs.py
│   ├── test_filters.py
│   ├── test_greenhouse.py
│   ├── test_lever.py
│   ├── test_models.py
│   ├── test_pinpoint.py
│   ├── test_quant_firms.py
│   ├── test_successfactors.py
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
DISCORD_INTERNSHIP_WEBHOOK_URL=https://discord.com/api/webhooks/...
LOG_LEVEL=INFO
MIN_SCORE=4
DATABASE_PATH=data/seen_jobs.sqlite
REQUEST_TIMEOUT_SECONDS=20
DISCORD_MIN_INTERVAL_SECONDS=0.75
DISCORD_MAX_RETRIES=6
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

Run only Cryptocurrency Jobs:

```bash
python -m src.main --source cryptocurrencyjobs
```

Run only the configured Ashby boards:

```bash
python -m src.main --source ashby
```

Run only the configured Greenhouse boards:

```bash
python -m src.main --source greenhouse
```

Run only Lever, Breezy, Pinpoint, or SuccessFactors:

```bash
python -m src.main --source lever
python -m src.main --source breezy
python -m src.main --source pinpoint
python -m src.main --source successfactors
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
  Your default Discord webhook URL for full-time, CDD, contract, and non-internship roles.
- `DISCORD_INTERNSHIP_WEBHOOK_URL`
  Optional dedicated Discord webhook URL for internship alerts. When set, jobs whose title,
  employment type, or tags contain internship terms are sent there instead of the default webhook.
- `LOG_LEVEL`
  Recommended value: `INFO`
- `MIN_SCORE`
  Default minimum score used when `--min-score` is not passed
- `DATABASE_PATH`
  Local SQLite file path. The default is `data/seen_jobs.sqlite`
- `REQUEST_TIMEOUT_SECONDS`
  HTTP timeout for source fetches and webhook delivery
- `DISCORD_MIN_INTERVAL_SECONDS`
  Minimum delay between Discord webhook sends. Default: `0.75`
- `DISCORD_MAX_RETRIES`
  Number of retry attempts when Discord returns a rate-limit response. Default: `6`
- `SHOW_MATCH_REASONS`
  Optional override for whether Discord embeds include a final `Why it matched` field. Default: `false`

## Filtering Logic

Filtering is score-based, not just boolean.

Current defaults:

- Jobs must have a parseable posted date and be no older than `31` days
- Titles containing seniority, business, HR, recruiting, legal, compliance, marketing,
  sales, product, project, or operations terms are rejected before scoring
- Titles must contain at least one scientific/technical role keyword such as
  `quant`, `research`, `trader`, `engineer`, `developer`, `data scientist`,
  `machine learning`, `algorithmic`, `MEV`, `DeFi`, or `prediction markets`
- `+3` if the title contains `quant` or `quantitative`
- `+2` if the title contains `research`, `researcher`, `trader`, or `trading`
- `+2` if the title contains `intern`, `internship`, `graduate`, or `summer`
- `+2` if the title contains crypto/Web3 domain terms such as `defi`, `mev`, `cex`, `dex`, or `prediction markets`
- `+1` if the job mentions a preferred location
- `-5` per matched negative keyword
- `+1` for crypto/Web3 domain support in the full job text, capped at 3 matches
- `+1` for additional broader quant keywords in the full job text

Only fresh jobs at or above the configured threshold are eligible for alerting. The current default minimum score is `4`.

All keywords, weights, and freshness rules live in `config/filters.yaml`.

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

### Ashby

The source uses Ashby's public JSON job-board API and reads the exact `publishedAt` value, so the
31-day freshness rule applies without estimating dates from page text. The default boards cover
Keyrock, Wincent, BlockTech, Wormhole Labs, Kuru Labs, Noise Labs, Field Technologies, and Paradigm.

Add or remove companies through the `boards` list in `config/sources.yaml`; each entry needs a
display `name` and the final `slug` from its `jobs.ashbyhq.com/{slug}` URL.

### Greenhouse

The generic Greenhouse connector uses the public Job Board API with full posting content. It uses
`first_published` for the 31-day freshness rule and intentionally does not treat a later edit as a
new posting. The default configuration monitors 37 verified boards, including Jane Street, IMC,
DRW, Jump Trading, DV Trading, Maven Securities, Radix, Headlands, Gelber, Mako, B2C2, CTC,
Tower Research, QRT, Squarepoint, WorldQuant, Point72/Cubist, AQR, and Man Group.

`config/quant_firms.yaml` is a curated directory of 67 quantitative funds, prop shops, market
makers, and crypto trading firms. It records each official career page and whether the firm is
already monitored by Greenhouse, Ashby, Lever, Breezy, Pinpoint, SuccessFactors, or still needs a
provider-specific connector. It is a coverage universe rather than a formal assets-under-management
ranking.

### Lever

The Lever connector uses the public postings JSON feed. The default boards cover Belvedere Trading,
Gauntlet, and Valkyrie Trading.

### Breezy

The Breezy connector uses each public `{company}.breezy.hr/json` feed. The default board covers
Marex.

### Pinpoint

The Pinpoint connector uses each public `postings.json` feed, then reads the posting detail page's
JobPosting schema when needed to recover `datePosted`. The default boards cover Systematica and
Wolverine Trading.

### SuccessFactors

The SuccessFactors connector parses SAP SuccessFactors career pages and detail-page JobPosting
metadata. The default board covers Capital Fund Management.

### Cryptocurrency Jobs

The source parses server-rendered HTML listing cards from configured pages in `config/sources.yaml`.

The default config checks the home page plus targeted pages for quant, research, trading, DeFi, finance, and engineering roles. Tags such as `DeFi`, `MEV`, `CEX`, `DEX`, `Prediction Markets`, `EVM`, and `onchain` are scored through `config/filters.yaml`.

### Simplify

The current implementation prefers the server-rendered `__NEXT_DATA__` payload on the list page, which exposes stable posting IDs and metadata.

If that payload disappears or changes shape, the source falls back to a basic anchor parse and logs a warning.

### eFinancialCareers

The current implementation parses HTML job cards from configured search pages.

This site can intermittently return maintenance or anti-bot pages to scriptable clients. The source handles that gracefully by logging and skipping the cycle rather than inventing data.

If the configured URLs change, update `config/sources.yaml`.

## How To Add A New Source Later

To add LinkedIn, Workday, Jobvite, or another direct hedge fund careers page later:

1. Create a new file in `src/sources/`, for example `workday.py`
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
- `DISCORD_INTERNSHIP_WEBHOOK_URL`

GitHub Actions persistence:

GitHub-hosted runners are ephemeral, so this project now persists `data/seen_jobs.sqlite` on a dedicated branch named `job-alert-state`.

That means scheduled runs restore the last seen-job state before scraping, which prevents the repeated duplicate alerts you were seeing.

This is a practical GitHub-only solution, but a hosted database is still the more robust long-term option. Good future options are:

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
- Workday and Jobvite adapters
- Better salary extraction
- Persistent hosted dedupe storage
- Richer Discord embeds with logos or source-specific badges
