import unittest

from src.config import FilterConfig, ScoreWeights
from src.filters import JobFilter
from src.models import Job, utc_now_iso


def build_filter() -> JobFilter:
    config = FilterConfig(
        minimum_score=3,
        maximum_age_days=31,
        require_posted_at=True,
        excluded_title_keywords=[
            "senior",
            "expert",
            "experienced",
            "years minimum",
            "head",
            "manager",
            "business",
            "hr",
            "people",
            "recruiter",
            "compliance",
            "growth",
            "support",
        ],
        required_title_keywords=[
            "quant",
            "quantitative",
            "research",
            "researcher",
            "trader",
            "trading",
            "quant developer",
            "quantitative developer",
            "research engineer",
            "software engineer",
            "software developer",
            "data scientist",
            "data engineer",
            "machine learning",
            "machine learning engineer",
            "mev",
            "defi",
        ],
        positive_keywords=[
            "quant",
            "quantitative",
            "research",
            "trader",
            "trading",
            "internship",
            "graduate",
        ],
        crypto_domain_keywords=["defi", "mev", "cex", "dex", "prediction market", "prediction markets"],
        negative_keywords=["compliance", "marketing", "sales"],
        preferred_locations=["London", "New York", "Paris"],
        weights=ScoreWeights(
            title_quant=3,
            title_core_role=2,
            title_early_career=2,
            title_crypto_domain=2,
            preferred_location=1,
            negative_keyword=-5,
            crypto_domain_keyword=1,
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
            posted_at=utc_now_iso(),
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
            posted_at=utc_now_iso(),
        )

        decision = build_filter().evaluate(job)

        self.assertFalse(decision.passed)
        self.assertIn("compliance", decision.matched_negative)

    def test_filter_scores_crypto_domain_title_keywords(self) -> None:
        job = Job.create(
            source="Sample",
            company="Flashbots",
            title="MEV Researcher",
            location="Remote",
            url="https://example.com/flashbots",
            posted_at=utc_now_iso(),
            description_snippet="DeFi market structure and protocol research.",
            tags=["DeFi", "Protocol"],
        )

        decision = build_filter().evaluate(job, minimum_score=4)

        self.assertTrue(decision.passed)
        self.assertIn("mev", decision.matched_positive)

    def test_filter_keeps_negative_crypto_jobs_below_threshold(self) -> None:
        job = Job.create(
            source="Sample",
            company="Example DEX",
            title="Head of Growth",
            location="Remote",
            url="https://example.com/growth",
            posted_at=utc_now_iso(),
            description_snippet="Category: Marketing | Tags: DEX, DeFi",
            tags=["DEX", "DeFi", "Marketing"],
        )

        decision = build_filter().evaluate(job, minimum_score=4)

        self.assertFalse(decision.passed)
        self.assertIn("head", decision.matched_negative)
        self.assertIn("growth", decision.matched_negative)

    def test_filter_rejects_senior_title_before_scoring(self) -> None:
        job = Job.create(
            source="Ashby",
            company="Keyrock",
            title="Senior Quantitative Researcher",
            location="London",
            url="https://example.com/senior-quant",
            posted_at=utc_now_iso(),
            description_snippet="Crypto DeFi CEX DEX market-making research.",
            tags=["Trading", "Quantitative Research"],
        )

        decision = build_filter().evaluate(job, minimum_score=4)

        self.assertFalse(decision.passed)
        self.assertEqual(decision.score, 0)
        self.assertEqual(decision.matched_negative, ["senior"])
        self.assertIn("excluded title keyword: senior", decision.reasons)

    def test_filter_rejects_expert_or_experienced_title_before_scoring(self) -> None:
        job = Job.create(
            source="SuccessFactors",
            company="Capital Fund Management",
            title="Expert Data Scientist Macroeconomics - 8 years minimum",
            location="Paris",
            url="https://example.com/expert-data-scientist",
            posted_at=utc_now_iso(),
            description_snippet="Research machine learning signals.",
            tags=["Research"],
        )

        decision = build_filter().evaluate(job, minimum_score=4)

        self.assertFalse(decision.passed)
        self.assertEqual(decision.score, 0)
        self.assertIn("expert", decision.matched_negative)
        self.assertIn("years minimum", decision.matched_negative)

    def test_filter_does_not_match_seniority_as_senior(self) -> None:
        job = Job.create(
            source="Sample",
            company="Example",
            title="Quant Trader - Open Seniority",
            location="London",
            url="https://example.com/open-seniority",
            posted_at=utc_now_iso(),
        )

        decision = build_filter().evaluate(job, minimum_score=4)

        self.assertTrue(decision.passed)

    def test_filter_rejects_business_manager_title_before_scoring(self) -> None:
        job = Job.create(
            source="Greenhouse",
            company="Example Fund",
            title="Business Manager, Quant Trading",
            location="London",
            url="https://example.com/business-manager",
            posted_at=utc_now_iso(),
            description_snippet="Quant research, DeFi, MEV, trading, machine learning.",
            tags=["Quantitative Research"],
        )

        decision = build_filter().evaluate(job, minimum_score=4)

        self.assertFalse(decision.passed)
        self.assertEqual(decision.score, 0)
        self.assertIn("business", decision.matched_negative)
        self.assertIn("manager", decision.matched_negative)

    def test_filter_rejects_hr_title_before_scoring(self) -> None:
        job = Job.create(
            source="Greenhouse",
            company="Example Fund",
            title="HR Business Partner - Quant Research",
            location="Paris",
            url="https://example.com/hr",
            posted_at=utc_now_iso(),
            description_snippet="Quantitative trading research team.",
            tags=["Quantitative Research"],
        )

        decision = build_filter().evaluate(job, minimum_score=4)

        self.assertFalse(decision.passed)
        self.assertEqual(decision.score, 0)
        self.assertIn("hr", decision.matched_negative)

    def test_filter_requires_scientific_title_keyword(self) -> None:
        job = Job.create(
            source="Greenhouse",
            company="Example Fund",
            title="Graduate Rotational Associate",
            location="London",
            url="https://example.com/graduate-rotation",
            posted_at=utc_now_iso(),
            description_snippet="Quant research, DeFi, MEV, trading, machine learning.",
            tags=["Quantitative Research"],
        )

        decision = build_filter().evaluate(job, minimum_score=4)

        self.assertFalse(decision.passed)
        self.assertEqual(decision.score, 0)
        self.assertIn("missing required scientific title keyword", decision.reasons)

    def test_filter_rejects_support_engineer_title_before_scoring(self) -> None:
        job = Job.create(
            source="Greenhouse",
            company="Example Fund",
            title="Application Support Engineer - Vendor Service",
            location="London",
            url="https://example.com/support-engineer",
            posted_at=utc_now_iso(),
            description_snippet="Supports quant trading systems and machine learning research.",
            tags=["Trading"],
        )

        decision = build_filter().evaluate(job, minimum_score=4)

        self.assertFalse(decision.passed)
        self.assertEqual(decision.score, 0)
        self.assertIn("support", decision.matched_negative)

    def test_filter_rejects_jobs_older_than_configured_age(self) -> None:
        job = Job.create(
            source="Sample",
            company="Kronos Research",
            title="2025 Summer Analyst (Summer Internship Program)",
            location="Taipei",
            url="https://example.com/kronos-2025",
            posted_at="2025-03-19T18:53:27+00:00",
            description_snippet="Quant research internship.",
            tags=["Quant", "Internship"],
        )

        decision = build_filter().evaluate(job, minimum_score=4)

        self.assertFalse(decision.passed)
        self.assertIn("older than maximum age", decision.reasons[0])

    def test_filter_rejects_jobs_without_posted_date_when_required(self) -> None:
        job = Job.create(
            source="Sample",
            company="Unknown",
            title="Quant Trader",
            location="London",
            url="https://example.com/no-date",
            description_snippet="Trading role.",
            tags=["Trading"],
        )

        decision = build_filter().evaluate(job, minimum_score=4)

        self.assertFalse(decision.passed)
        self.assertIn("missing posted date", decision.reasons[0])


if __name__ == "__main__":
    unittest.main()
