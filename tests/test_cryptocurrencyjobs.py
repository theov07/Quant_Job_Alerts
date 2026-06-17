import unittest

from src.config import SourceDefinition
from src.sources.cryptocurrencyjobs import CryptocurrencyJobsSource


class CryptocurrencyJobsSourceTests(unittest.TestCase):
    def test_parse_listing_page_extracts_job_card(self) -> None:
        source = CryptocurrencyJobsSource(
            source_key="cryptocurrencyjobs",
            config=SourceDefinition(type="cryptocurrencyjobs", url="https://cryptocurrencyjobs.co/"),
            timeout_seconds=20,
            user_agent="test-agent",
        )
        html = """
        <html>
          <body>
            <ul class="mt-6">
              <li data-listing-ad="Sponsor">
                <h2><a href="https://example.com/jobs">Sponsored role</a></h2>
              </li>
              <li class="grid text-sm text-gray-600 bg-gray-50 border-t border-gray-200 p-4 sm:p-6">
                <h2><a href="/quant/wintermute-c-plus-plus-quant-developer-options/">C++ Quant Developer - Options</a></h2>
                <h3>Wintermute</h3>
                <h4 class="inline">London</h4>
                <h4 class="leading-relaxed sm:leading-normal">Engineering</h4>
                <h4 class="inline">Full-Time</h4>
                <span>$120K - $180K</span>
                <ul class="flex flex-wrap">
                  <li><span class="block p-1">MEV</span></li>
                  <li><a class="block group-hover:text-purple p-1" href="/defi/">DeFi</a></li>
                  <li><span class="block p-1">CEX</span></li>
                </ul>
                <div>
                  <span>4d</span>
                  <span>Featured</span>
                </div>
              </li>
            </ul>
          </body>
        </html>
        """

        jobs = source._parse_listing_page(html=html, source_url="https://cryptocurrencyjobs.co/")

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.source, "Cryptocurrency Jobs")
        self.assertEqual(job.id, "quant/wintermute-c-plus-plus-quant-developer-options")
        self.assertEqual(job.company, "Wintermute")
        self.assertEqual(job.title, "C++ Quant Developer - Options")
        self.assertEqual(job.location, "London")
        self.assertEqual(job.employment_type, "Full-Time")
        self.assertEqual(job.url, "https://cryptocurrencyjobs.co/quant/wintermute-c-plus-plus-quant-developer-options/")
        self.assertIn("MEV", job.tags)
        self.assertIn("DeFi", job.tags)
        self.assertIn("Engineering", job.tags)
        self.assertIn("Salary: $120K - $180K", job.description_snippet or "")
        self.assertIsNotNone(job.posted_at)

    def test_parse_listing_page_does_not_treat_category_as_location(self) -> None:
        source = CryptocurrencyJobsSource(
            source_key="cryptocurrencyjobs",
            config=SourceDefinition(type="cryptocurrencyjobs", url="https://cryptocurrencyjobs.co/"),
            timeout_seconds=20,
            user_agent="test-agent",
        )
        html = """
        <html>
          <body>
            <ul class="mt-6">
              <li class="grid text-sm">
                <h2><a href="/engineering/example-smart-contract-engineer/">Smart Contract Engineer</a></h2>
                <h3>Example Labs</h3>
                <h4 class="leading-relaxed sm:leading-normal">Engineering</h4>
                <h4 class="inline">Full-Time</h4>
                <ul class="flex flex-wrap">
                  <li><span class="block p-1">Solidity</span></li>
                </ul>
                <div><span>1w</span></div>
              </li>
            </ul>
          </body>
        </html>
        """

        jobs = source._parse_listing_page(html=html, source_url="https://cryptocurrencyjobs.co/")

        self.assertEqual(len(jobs), 1)
        self.assertIsNone(jobs[0].location)
        self.assertIn("Engineering", jobs[0].tags)


if __name__ == "__main__":
    unittest.main()
