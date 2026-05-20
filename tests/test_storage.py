from pathlib import Path
import tempfile
import unittest

from src.models import Job
from src.storage import SeenJobStore


class SeenJobStoreTests(unittest.TestCase):
    def test_storage_marks_jobs_as_seen(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "seen_jobs.sqlite"
            store = SeenJobStore(database_path)
            store.initialize()

            job = Job.create(
                source="Simplify",
                source_job_id="sample-1",
                company="DRW",
                title="Quantitative Researcher",
                location="London",
                url="https://example.com/drw",
            )

            self.assertFalse(store.has_seen(job))
            store.mark_seen(job)
            self.assertTrue(store.has_seen(job))
            self.assertEqual(store.count(), 1)

    def test_storage_reset_clears_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "seen_jobs.sqlite"
            store = SeenJobStore(database_path)
            store.initialize()

            job = Job.create(
                source="Simplify",
                source_job_id="sample-2",
                company="Jane Street",
                title="Quant Trader",
                location="New York",
                url="https://example.com/jane-street",
            )
            store.mark_seen(job)

            store.reset()

            self.assertEqual(store.count(), 0)


if __name__ == "__main__":
    unittest.main()
