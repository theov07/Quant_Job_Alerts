from __future__ import annotations

from pathlib import Path
import sqlite3

from .models import Job, utc_now_iso


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS seen_jobs (
    dedupe_key TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    company TEXT,
    title TEXT NOT NULL,
    location TEXT,
    url TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
)
"""


class SeenJobStore:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(CREATE_TABLE_SQL)
            connection.commit()

    def has_seen(self, job: Job) -> bool:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT 1 FROM seen_jobs WHERE dedupe_key = ?",
                (job.dedupe_key,),
            ).fetchone()
        return row is not None

    def mark_seen(self, job: Job) -> None:
        now = utc_now_iso()
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO seen_jobs (
                    dedupe_key,
                    source,
                    company,
                    title,
                    location,
                    url,
                    first_seen_at,
                    last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dedupe_key) DO UPDATE SET
                    source = excluded.source,
                    company = excluded.company,
                    title = excluded.title,
                    location = excluded.location,
                    url = excluded.url,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    job.dedupe_key,
                    job.source,
                    job.company,
                    job.title,
                    job.location,
                    job.url,
                    now,
                    now,
                ),
            )
            connection.commit()

    def reset(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(CREATE_TABLE_SQL)
            connection.execute("DELETE FROM seen_jobs")
            connection.commit()

    def count(self) -> int:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute("SELECT COUNT(*) FROM seen_jobs").fetchone()
        return int(row[0]) if row else 0

