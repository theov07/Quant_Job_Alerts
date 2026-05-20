from __future__ import annotations

from .models import Job, utc_now_iso


def build_sample_jobs() -> list[Job]:
    timestamp = utc_now_iso()
    return [
        Job.create(
            source="Sample",
            source_job_id="sample-drw-intern",
            company="DRW",
            title="Quantitative Research Intern",
            location="London, United Kingdom",
            url="https://example.com/drw-quant-intern",
            posted_at=timestamp,
            employment_type="Internship",
            description_snippet="Research, alpha generation, Python, machine learning, systematic trading.",
            tags=["Quantitative Research", "Internship", "Systematic Trading"],
            raw={"sample": True},
        ),
        Job.create(
            source="Sample",
            source_job_id="sample-optiver-grad",
            company="Optiver",
            title="Graduate Quant Trader",
            location="Amsterdam, Netherlands",
            url="https://example.com/optiver-grad-quant-trader",
            posted_at=timestamp,
            employment_type="Graduate",
            description_snippet="Trading, market making, derivatives, execution, options.",
            tags=["Trading", "Graduate", "Market Making"],
            raw={"sample": True},
        ),
    ]

