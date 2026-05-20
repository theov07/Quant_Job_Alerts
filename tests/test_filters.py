import unittest

from src.config import FilterConfig, ScoreWeights
from src.filters import JobFilter
from src.models import Job


def build_filter() -> JobFilter:
    config = FilterConfig(
        minimum_score=3,
        positive_keywords=[
            "quant",
            "quantitative",
            "research",
            "trader",
            "trading",
            "internship",
            "graduate",
        ],
        negative_keywords=["compliance", "marketing", "sales"],
        preferred_locations=["London", "New York", "Paris"],
        weights=ScoreWeights(
            title_quant=3,
            title_core_role=2,
            title_early_career=2,
            preferred_location=1,
            negative_keyword=-5,
            additional_positive_keyword=1,
        ),
    )
    return JobFilter(config)


class JobFilterTests(unittest.TestCase):
    def test_filter_passes_relevant_quant_job(self) -> None:
        job = Job.create(
            source="Sample",
            company="Optiver",
            title="Graduate Quant Trader",
            location="Amsterdam",
            url="https://example.com/optiver",
            description_snippet="Systematic trading internship style rotation.",
            tags=["Trading"],
        )

        decision = build_filter().evaluate(job)

        self.assertTrue(decision.passed)
        self.assertGreaterEqual(decision.score, 5)

    def test_filter_penalizes_negative_keywords(self) -> None:
        job = Job.create(
            source="Sample",
            company="Acme",
            title="Quant Compliance Analyst",
            location="London",
            url="https://example.com/acme",
        )

        decision = build_filter().evaluate(job)

        self.assertFalse(decision.passed)
        self.assertIn("compliance", decision.matched_negative)


if __name__ == "__main__":
    unittest.main()
