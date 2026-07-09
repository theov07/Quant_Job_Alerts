import unittest

from src.config import JobBoardDefinition, SourceDefinition
from src.sources.pinpoint import PinpointJobSource


class PinpointJobSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = PinpointJobSource(
            source_key="pinpoint",
            config=SourceDefinition(
                type="pinpoint",
                boards=[JobBoardDefinition(name="Wolverine Trading", slug="careers.wolve.com")],
            ),
            timeout_seconds=20,
            user_agent="test-agent",
        )

    def test_parse_payload_normalizes_posting_with_detail_schema(self) -> None:
        self.source._job_posting_schema = lambda _: {  # type: ignore[method-assign]
            "datePosted": "2026-07-01T17:30:31+00:00",
            "description": "<p>High-performance C++ trading systems.</p>",
        }
        payload = {
            "data": [
                {
                    "id": "445793",
                    "title": "Entry-Level C++ Software Engineer",
                    "url": "https://careers.wolve.com/en/postings/abc",
                    "description": "<p>Build trading platforms.</p>",
                    "employment_type_text": "Full Time",
                    "workplace_type_text": "Onsite",
                    "location": {"name": "Chicago, IL"},
                    "job": {
                        "department": {"name": "Technology"},
                        "division": {"name": "Wolverine Trading"},
                    },
                }
            ]
        }

        jobs = self.source._parse_payload(
            payload=payload,
            board=JobBoardDefinition(name="Wolverine Trading", slug="careers.wolve.com"),
        )

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.source, "Pinpoint")
        self.assertEqual(job.id, "careers.wolve.com:445793")
        self.assertEqual(job.company, "Wolverine Trading")
        self.assertEqual(job.location, "Chicago, IL")
        self.assertEqual(job.posted_at, "2026-07-01T17:30:31+00:00")
        self.assertEqual(job.employment_type, "Full Time")
        self.assertIn("Technology", job.tags)
        self.assertIn("High-performance C++ trading systems.", job.description_snippet or "")

    def test_build_api_url_accepts_custom_domain(self) -> None:
        self.assertEqual(
            self.source._build_api_url("careers.wolve.com"),
            "https://careers.wolve.com/postings.json",
        )

    def test_build_api_url_accepts_pinpoint_subdomain(self) -> None:
        self.assertEqual(
            self.source._build_api_url("systematica"),
            "https://systematica.pinpointhq.com/postings.json",
        )


if __name__ == "__main__":
    unittest.main()
