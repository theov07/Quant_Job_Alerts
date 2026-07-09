import unittest

from src.config import JobBoardDefinition, SourceDefinition
from src.sources.breezy import BreezyJobSource


class BreezyJobSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = BreezyJobSource(
            source_key="breezy",
            config=SourceDefinition(
                type="breezy",
                boards=[JobBoardDefinition(name="Marex", slug="marex")],
            ),
            timeout_seconds=20,
            user_agent="test-agent",
        )

    def test_parse_payload_normalizes_posting(self) -> None:
        payload = [
            {
                "id": "abc",
                "friendly_id": "abc-front-office-developer",
                "name": "Front Office Developer",
                "url": "https://marex.breezy.hr/p/abc-front-office-developer",
                "published_date": "2026-07-02T09:38:50.836Z",
                "description": "<p>Build trading systems in Python.</p>",
                "requirements": "<p>Market data and risk technology.</p>",
                "type": {"id": "fullTime", "name": "Full-Time"},
                "location": {"name": "London, GB"},
                "department": "Technology",
            }
        ]

        jobs = self.source._parse_payload(
            payload=payload,
            board=JobBoardDefinition(name="Marex", slug="marex"),
        )

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.source, "Breezy")
        self.assertEqual(job.id, "marex:abc")
        self.assertEqual(job.company, "Marex")
        self.assertEqual(job.location, "London, GB")
        self.assertEqual(job.posted_at, "2026-07-02T09:38:50.836Z")
        self.assertEqual(job.employment_type, "Full-Time")
        self.assertIn("Technology", job.tags)
        self.assertIn("Build trading systems in Python.", job.description_snippet or "")

    def test_build_api_url_uses_breezy_json_feed(self) -> None:
        self.assertEqual(self.source._build_api_url("marex"), "https://marex.breezy.hr/json")


if __name__ == "__main__":
    unittest.main()
