import unittest

from src.config import JobBoardDefinition, SourceDefinition
from src.sources.ashby import AshbyJobSource


class AshbyJobSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = AshbyJobSource(
            source_key="ashby",
            config=SourceDefinition(
                type="ashby",
                include_compensation=True,
                boards=[JobBoardDefinition(name="Keyrock", slug="Keyrock")],
            ),
            timeout_seconds=20,
            user_agent="test-agent",
        )

    def test_parse_payload_normalizes_published_job(self) -> None:
        payload = {
            "apiVersion": "1",
            "jobs": [
                {
                    "title": "Graduate Quantitative Trader",
                    "location": "London",
                    "secondaryLocations": [{"location": "Paris"}],
                    "isRemote": True,
                    "workplaceType": "Remote",
                    "department": "Trading",
                    "team": "Algorithmic Market Making",
                    "descriptionPlain": "Build systematic CEX and DEX market-making strategies.",
                    "publishedAt": "2026-06-18T12:00:00.000Z",
                    "employmentType": "FullTime",
                    "jobUrl": "https://jobs.ashbyhq.com/Keyrock/abc-123",
                    "applyUrl": "https://jobs.ashbyhq.com/Keyrock/abc-123/application",
                    "isListed": True,
                    "compensation": {
                        "scrapeableCompensationSalarySummary": "EUR 80K - 100K",
                    },
                },
                {
                    "title": "Hidden Quant Role",
                    "jobUrl": "https://jobs.ashbyhq.com/Keyrock/hidden",
                    "isListed": False,
                },
            ],
        }

        jobs = self.source._parse_payload(
            payload=payload,
            board=JobBoardDefinition(name="Keyrock", slug="Keyrock"),
        )

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.source, "Ashby")
        self.assertEqual(job.id, "Keyrock:abc-123")
        self.assertEqual(job.company, "Keyrock")
        self.assertEqual(job.title, "Graduate Quantitative Trader")
        self.assertEqual(job.location, "Remote, London, Paris")
        self.assertEqual(job.posted_at, "2026-06-18T12:00:00.000Z")
        self.assertEqual(job.employment_type, "Full Time")
        self.assertIn("Algorithmic Market Making", job.tags)
        self.assertIn("Compensation: EUR 80K - 100K", job.description_snippet or "")

    def test_build_api_url_requests_compensation(self) -> None:
        self.assertEqual(
            self.source._build_api_url("Kuru Labs"),
            "https://api.ashbyhq.com/posting-api/job-board/Kuru%20Labs?includeCompensation=true",
        )


if __name__ == "__main__":
    unittest.main()
