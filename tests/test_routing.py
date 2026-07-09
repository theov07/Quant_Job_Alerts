import unittest

from src.models import Job
from src.routing import DEFAULT_ROUTE, INTERNSHIP_ROUTE, alert_route_for_job, is_internship_job


class JobRoutingTests(unittest.TestCase):
    def test_routes_title_internship_to_internship_channel(self) -> None:
        job = Job.create(
            source="Sample",
            company="DRW",
            title="Quantitative Research Intern",
            url="https://example.com/intern",
            employment_type="Full-Time: Campus",
        )

        self.assertTrue(is_internship_job(job))
        self.assertEqual(alert_route_for_job(job), INTERNSHIP_ROUTE)

    def test_routes_employment_type_internship_to_internship_channel(self) -> None:
        job = Job.create(
            source="Sample",
            company="Jane Street",
            title="Quantitative Researcher",
            url="https://example.com/researcher",
            employment_type="Internship",
        )

        self.assertEqual(alert_route_for_job(job), INTERNSHIP_ROUTE)

    def test_routes_summer_analyst_to_internship_channel(self) -> None:
        job = Job.create(
            source="Sample",
            company="AQR",
            title="Quantitative Research Summer Analyst",
            url="https://example.com/summer-analyst",
        )

        self.assertEqual(alert_route_for_job(job), INTERNSHIP_ROUTE)

    def test_keeps_full_time_job_on_default_channel(self) -> None:
        job = Job.create(
            source="Sample",
            company="QRT",
            title="Quantitative Developer",
            url="https://example.com/full-time",
            employment_type="Full-Time",
            tags=["Quantitative Research"],
        )

        self.assertFalse(is_internship_job(job))
        self.assertEqual(alert_route_for_job(job), DEFAULT_ROUTE)

    def test_does_not_match_internal_as_intern(self) -> None:
        job = Job.create(
            source="Sample",
            company="Example",
            title="Internal Tools Software Engineer",
            url="https://example.com/internal-tools",
            employment_type="Full-Time",
        )

        self.assertEqual(alert_route_for_job(job), DEFAULT_ROUTE)


if __name__ == "__main__":
    unittest.main()
