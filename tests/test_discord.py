import unittest

from src.discord import DiscordWebhookClient
from src.models import Job


class DiscordWebhookClientTests(unittest.TestCase):
    def test_embed_is_compact_by_default(self) -> None:
        client = DiscordWebhookClient(
            webhook_url="https://example.com/webhook",
            show_match_reasons=False,
        )
        job = Job.create(
            source="Simplify",
            source_job_id="sample-1",
            company="DRW",
            title="Quantitative Researcher",
            location="London, UK",
            url="https://example.com/job",
            posted_at="2026-05-20T12:00:00+00:00",
            employment_type="Full-Time",
            tags=["Quantitative Research", "Python", "Machine Learning", "Options", "Alpha", "SQL"],
        )

        embed = client._build_embed(job=job, score=7, reasons=["+3 quant", "+2 researcher"])

        self.assertEqual(embed["title"], "DRW — Quantitative Researcher")
        self.assertIn("New relevant quant job found on Simplify.", embed["description"])
        self.assertIn("[Open job posting](https://example.com/job)", embed["description"])
        self.assertEqual(embed["fields"][0]["name"], "Location")
        self.assertEqual(embed["fields"][1]["name"], "Type")
        self.assertEqual(embed["fields"][2]["name"], "Posted")
        self.assertEqual(embed["fields"][2]["value"], "2026-05-20")
        self.assertEqual(embed["fields"][3]["name"], "Score")
        self.assertEqual(embed["fields"][4]["name"], "Tags")
        self.assertEqual(
            embed["fields"][4]["value"],
            "Quantitative Research, Python, Machine Learning, Options, Alpha, ...",
        )
        self.assertEqual(len(embed["fields"]), 5)

    def test_embed_can_include_match_reasons(self) -> None:
        client = DiscordWebhookClient(
            webhook_url="https://example.com/webhook",
            show_match_reasons=True,
        )
        job = Job.create(
            source="eFinancialCareers",
            source_job_id="sample-2",
            company="Jane Street",
            title="Quant Trader Intern",
            location="New York, United States",
            url="https://example.com/job-2",
        )

        embed = client._build_embed(job=job, score=6, reasons=["+3 quant title match", "+2 core role title match"])

        self.assertEqual(embed["fields"][-1]["name"], "Why it matched")
        self.assertIn("quant title match", embed["fields"][-1]["value"])

    def test_payload_includes_apply_button_and_components_flag(self) -> None:
        client = DiscordWebhookClient(
            webhook_url="https://example.com/webhook?wait=true",
            show_match_reasons=False,
        )
        job = Job.create(
            source="Simplify",
            source_job_id="sample-3",
            company="Optiver",
            title="Graduate Quant Trader",
            location="Amsterdam, Netherlands",
            url="https://example.com/job-3",
        )

        payload = client._build_payload(job=job, score=8, reasons=[])

        self.assertEqual(payload["components"][0]["components"][0]["label"], "Apply")
        self.assertEqual(payload["components"][0]["components"][0]["url"], "https://example.com/job-3")
        self.assertEqual(
            client._build_webhook_request_url(),
            "https://example.com/webhook?wait=true&with_components=true",
        )


if __name__ == "__main__":
    unittest.main()
