import unittest

from src.models import Job, build_hash_id


class JobModelTests(unittest.TestCase):
    def test_job_uses_source_job_id_when_available(self) -> None:
        job = Job.create(
            source="Simplify",
            source_job_id="abc123",
            company="DRW",
            title="Quantitative Researcher",
            location="London",
            url="https://example.com/role",
        )

        self.assertEqual(job.id, "abc123")
        self.assertEqual(job.dedupe_key, "simplify:abc123")

    def test_job_hash_id_is_stable_without_source_id(self) -> None:
        first = Job.create(
            source="eFinancialCareers",
            company="Jane Street",
            title="Quant Trader Intern",
            location="New York",
            url="https://example.com/role",
        )
        second = Job.create(
            source="eFinancialCareers",
            company="Jane Street",
            title="Quant Trader Intern",
            location="New York",
            url="https://example.com/role",
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(
            first.id,
            build_hash_id(["Jane Street", "Quant Trader Intern", "New York", "https://example.com/role"]),
        )


if __name__ == "__main__":
    unittest.main()
