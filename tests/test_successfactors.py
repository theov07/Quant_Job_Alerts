import unittest

from src.config import JobBoardDefinition, SourceDefinition
from src.sources.successfactors import SuccessFactorsJobSource


class SuccessFactorsJobSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = SuccessFactorsJobSource(
            source_key="successfactors",
            config=SourceDefinition(
                type="successfactors",
                boards=[JobBoardDefinition(name="Capital Fund Management", slug="jobs.cfm.com")],
            ),
            timeout_seconds=20,
            user_agent="test-agent",
        )

    def test_parse_detail_normalizes_job_posting_schema(self) -> None:
        html = """
        <html>
          <head><title>AI native quant researcher Job Details | Capital Fund Management</title></head>
          <body>
            <div class="jobDisplayShell" itemscope itemtype="http://schema.org/JobPosting">
              <span itemprop="jobLocation" itemscope itemtype="http://schema.org/Place">
                <span itemprop="address" itemscope itemtype="http://schema.org/PostalAddress">
                  <meta itemprop="addressLocality" content="Paris">
                  <meta itemprop="addressRegion" content="75">
                  <meta itemprop="addressCountry" content="FR">
                </span>
              </span>
              <meta itemprop="datePosted" content="Tue Jul 07 00:00:00 UTC 2026">
              <h1><span itemprop="title">AI native quant researcher</span></h1>
              <div class="job" itemprop="description">
                Research systematic trading signals with machine learning.
              </div>
            </div>
          </body>
        </html>
        """

        job = self.source._parse_detail(
            html=html,
            board=JobBoardDefinition(name="Capital Fund Management", slug="jobs.cfm.com"),
            job_url="https://jobs.cfm.com/job/Paris-AI-native-quant-researcher-75/1359709355/",
        )

        self.assertIsNotNone(job)
        assert job is not None
        self.assertEqual(job.source, "SuccessFactors")
        self.assertEqual(job.id, "jobs.cfm.com:1359709355")
        self.assertEqual(job.company, "Capital Fund Management")
        self.assertEqual(job.location, "Paris, 75, FR")
        self.assertEqual(job.posted_at, "2026-07-07T00:00:00+00:00")
        self.assertIn("systematic trading signals", job.description_snippet or "")

    def test_job_links_are_deduped_and_absolutized(self) -> None:
        html = """
        <a href="/job/Paris-Quantitative-researcher-75/123/">Quant</a>
        <a href="/job/Paris-Quantitative-researcher-75/123/">Quant duplicate</a>
        """

        self.assertEqual(
            self.source._job_links("https://jobs.cfm.com", html),
            ["https://jobs.cfm.com/job/Paris-Quantitative-researcher-75/123/"],
        )


if __name__ == "__main__":
    unittest.main()
