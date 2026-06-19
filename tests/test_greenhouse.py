import unittest

from src.config import JobBoardDefinition, SourceDefinition
from src.sources.greenhouse import GreenhouseJobSource


class GreenhouseJobSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = GreenhouseJobSource(
            source_key="greenhouse",
            config=SourceDefinition(
                type="greenhouse",
                boards=[JobBoardDefinition(name="Jane Street", slug="janestreet")],
            ),
            timeout_seconds=20,
            user_agent="test-agent",
        )

    def test_parse_payload_normalizes_structured_job(self) -> None:
        payload = {
            "jobs": [
                {
                    "id": 12345,
                    "title": "Graduate Quantitative Trader",
                    "absolute_url": "https://job-boards.greenhouse.io/janestreet/jobs/12345",
                    "location": {"name": "London"},
                    "first_published": "2026-06-10T08:30:00-04:00",
                    "updated_at": "2026-06-19T09:00:00-04:00",
                    "content": (
                        "&lt;h3&gt;The role&lt;/h3&gt;"
                        "&lt;p&gt;Research systematic trading signals &amp;amp; market microstructure.&lt;/p&gt;"
                    ),
                    "departments": [{"name": "Quantitative Research"}],
                    "offices": [{"name": "London"}],
                    "metadata": [
                        {"name": "Employment Type", "value": "Full-Time: Campus"},
                        {"name": "Experience Level", "value": "Graduate"},
                        {"name": "Min salary", "value": "150,000"},
                        {"name": "Max salary", "value": "200,000"},
                        {"name": "Currency", "value": "GBP"},
                    ],
                }
            ]
        }

        jobs = self.source._parse_payload(
            payload=payload,
            board=JobBoardDefinition(name="Jane Street", slug="janestreet"),
        )

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.id, "janestreet:12345")
        self.assertEqual(job.source, "Greenhouse")
        self.assertEqual(job.company, "Jane Street")
        self.assertEqual(job.location, "London")
        self.assertEqual(job.posted_at, "2026-06-10T08:30:00-04:00")
        self.assertEqual(job.employment_type, "Full-Time: Campus")
        self.assertIn("systematic trading signals & market microstructure", job.description_snippet or "")
        self.assertIn("Compensation: 150,000 - 200,000 GBP", job.description_snippet or "")
        self.assertIn("Quantitative Research", job.tags)
        self.assertIn("Graduate", job.tags)

    def test_parse_payload_does_not_use_update_date_as_publish_date(self) -> None:
        payload = {
            "jobs": [
                {
                    "id": 987,
                    "title": "Quantitative Researcher",
                    "absolute_url": "https://job-boards.greenhouse.io/example/jobs/987",
                    "updated_at": "2026-06-19T09:00:00Z",
                }
            ]
        }

        job = self.source._parse_payload(
            payload=payload,
            board=JobBoardDefinition(name="Example", slug="example"),
        )[0]

        self.assertIsNone(job.posted_at)

    def test_build_api_url_escapes_board_slug(self) -> None:
        self.assertEqual(
            self.source._build_api_url("example board"),
            "https://boards-api.greenhouse.io/v1/boards/example%20board/jobs?content=true",
        )

    def test_description_accepts_plain_text_that_looks_like_a_path(self) -> None:
        self.assertEqual(self.source._description("research/models/readme.md"), "research/models/readme.md")


if __name__ == "__main__":
    unittest.main()
