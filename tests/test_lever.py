import unittest

from src.config import JobBoardDefinition, SourceDefinition
from src.sources.lever import LeverJobSource


class LeverJobSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = LeverJobSource(
            source_key="lever",
            config=SourceDefinition(
                type="lever",
                boards=[JobBoardDefinition(name="Belvedere Trading", slug="belvederetrading")],
            ),
            timeout_seconds=20,
            user_agent="test-agent",
        )

    def test_parse_payload_normalizes_posting(self) -> None:
        payload = [
            {
                "id": "abc-123",
                "text": "Quantitative Analyst - Treasury",
                "hostedUrl": "https://jobs.lever.co/belvederetrading/abc-123",
                "createdAt": 1_783_166_400_000,
                "descriptionPlain": "Build systematic trading analytics.",
                "additionalPlain": "Python, statistics, options.",
                "categories": {
                    "commitment": "Full-Time",
                    "team": "Investments",
                    "department": "Trading",
                    "location": "Chicago, Illinois",
                    "allLocations": ["Chicago, Illinois", "New York, New York"],
                },
            }
        ]

        jobs = self.source._parse_payload(
            payload=payload,
            board=JobBoardDefinition(name="Belvedere Trading", slug="belvederetrading"),
        )

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.source, "Lever")
        self.assertEqual(job.id, "belvederetrading:abc-123")
        self.assertEqual(job.company, "Belvedere Trading")
        self.assertEqual(job.location, "Chicago, Illinois, New York, New York")
        self.assertEqual(job.posted_at, "2026-07-04T12:00:00+00:00")
        self.assertEqual(job.employment_type, "Full-Time")
        self.assertIn("Investments", job.tags)
        self.assertIn("Python, statistics, options.", job.description_snippet or "")

    def test_build_api_url_escapes_slug(self) -> None:
        self.assertEqual(
            self.source._build_api_url("example board"),
            "https://api.lever.co/v0/postings/example%20board?mode=json",
        )


if __name__ == "__main__":
    unittest.main()
