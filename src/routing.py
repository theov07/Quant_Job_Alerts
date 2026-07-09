from __future__ import annotations

import re

from .models import Job


DEFAULT_ROUTE = "default"
INTERNSHIP_ROUTE = "internship"

INTERNSHIP_KEYWORDS = [
    "intern",
    "internship",
    "internships",
    "summer intern",
    "summer internship",
    "summer analyst",
    "summer associate",
    "stage",
    "stagiaire",
]


def alert_route_for_job(job: Job) -> str:
    if is_internship_job(job):
        return INTERNSHIP_ROUTE
    return DEFAULT_ROUTE


def is_internship_job(job: Job) -> bool:
    text = " ".join(
        filter(
            None,
            [
                job.title,
                job.employment_type,
                " ".join(job.tags),
            ],
        )
    ).lower()
    return any(_contains_keyword(text, keyword) for keyword in INTERNSHIP_KEYWORDS)


def _contains_keyword(text: str, keyword: str) -> bool:
    pattern = r"\b" + re.escape(keyword.lower()).replace(r"\ ", r"\s+") + r"\b"
    return re.search(pattern, text) is not None
