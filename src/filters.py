from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import re

from .config import FilterConfig
from .models import Job


QUANT_TITLE_KEYWORDS = {"quant", "quantitative"}
CORE_ROLE_KEYWORDS = {"research", "researcher", "trader", "trading"}
EARLY_CAREER_KEYWORDS = {
    "intern",
    "internship",
    "graduate",
    "summer",
    "new grad",
    "new grads",
    "early career",
    "graduate program",
    "campus",
    "entry level",
    "junior",
}


@dataclass(slots=True)
class FilterDecision:
    score: int
    passed: bool
    reasons: list[str] = field(default_factory=list)
    matched_positive: list[str] = field(default_factory=list)
    matched_negative: list[str] = field(default_factory=list)


class JobFilter:
    def __init__(self, config: FilterConfig) -> None:
        self.config = config

    def evaluate(self, job: Job, minimum_score: int | None = None) -> FilterDecision:
        threshold = minimum_score if minimum_score is not None else self.config.minimum_score
        title_exclusion_decision = self._evaluate_title_exclusions(job)
        if title_exclusion_decision is not None:
            return title_exclusion_decision

        freshness_decision = self._evaluate_freshness(job)
        if freshness_decision is not None:
            return freshness_decision

        required_title_decision = self._evaluate_required_title_keywords(job)
        if required_title_decision is not None:
            return required_title_decision

        title_text = (job.title or "").lower()
        full_text = " ".join(
            filter(
                None,
                [
                    job.title,
                    job.company,
                    job.location,
                    job.description_snippet,
                    " ".join(job.tags),
                ],
            )
        ).lower()
        negative_text = " ".join(
            filter(
                None,
                [
                    job.title,
                    job.company,
                    job.location,
                    job.description_snippet,
                ],
            )
        ).lower()

        score = 0
        reasons: list[str] = []
        matched_positive: list[str] = []
        matched_negative: list[str] = []

        quant_hits = self._find_matches(title_text, QUANT_TITLE_KEYWORDS)
        if quant_hits:
            score += self.config.weights.title_quant
            reasons.append(f"+{self.config.weights.title_quant} quant title match: {', '.join(quant_hits)}")
            matched_positive.extend(quant_hits)

        core_hits = self._find_matches(title_text, CORE_ROLE_KEYWORDS)
        if core_hits:
            score += self.config.weights.title_core_role
            reasons.append(f"+{self.config.weights.title_core_role} core role title match: {', '.join(core_hits)}")
            matched_positive.extend(core_hits)

        early_hits = self._find_matches(title_text, EARLY_CAREER_KEYWORDS)
        if early_hits:
            score += self.config.weights.title_early_career
            reasons.append(
                f"+{self.config.weights.title_early_career} early-career title match: {', '.join(early_hits)}"
            )
            matched_positive.extend(early_hits)

        title_domain_hits = self._find_matches(title_text, self.config.crypto_domain_keywords)
        if title_domain_hits:
            score += self.config.weights.title_crypto_domain
            reasons.append(
                f"+{self.config.weights.title_crypto_domain} crypto domain title match: "
                f"{', '.join(title_domain_hits)}"
            )
            matched_positive.extend(title_domain_hits)

        location_hits = self._find_matches(full_text, self.config.preferred_locations)
        if location_hits:
            score += self.config.weights.preferred_location
            reasons.append(
                f"+{self.config.weights.preferred_location} preferred location match: {location_hits[0]}"
            )
            matched_positive.append(location_hits[0])

        negative_hits = self._find_matches(negative_text, self.config.negative_keywords)
        if negative_hits:
            penalty = self.config.weights.negative_keyword * len(negative_hits)
            score += penalty
            reasons.append(f"{penalty} negative keyword match: {', '.join(negative_hits)}")
            matched_negative.extend(negative_hits)

        domain_hits = [
            keyword
            for keyword in self._find_matches(full_text, self.config.crypto_domain_keywords)
            if keyword not in matched_positive
        ]
        if domain_hits:
            bonus_count = min(len(domain_hits), 3)
            bonus = self.config.weights.crypto_domain_keyword * bonus_count
            score += bonus
            reasons.append(f"+{bonus} crypto domain support: {', '.join(domain_hits[:bonus_count])}")
            matched_positive.extend(domain_hits[:bonus_count])

        additional_hits = [
            keyword
            for keyword in self._find_matches(full_text, self.config.positive_keywords)
            if keyword not in matched_positive
        ]
        if additional_hits:
            bonus_count = min(len(additional_hits), 3)
            bonus = self.config.weights.additional_positive_keyword * bonus_count
            score += bonus
            reasons.append(f"+{bonus} broader keyword support: {', '.join(additional_hits[:bonus_count])}")
            matched_positive.extend(additional_hits[:bonus_count])

        return FilterDecision(
            score=score,
            passed=score >= threshold,
            reasons=reasons,
            matched_positive=matched_positive,
            matched_negative=matched_negative,
        )

    def _evaluate_title_exclusions(self, job: Job) -> FilterDecision | None:
        matches = self._find_matches(job.title.lower(), self.config.excluded_title_keywords)
        if not matches:
            return None
        return FilterDecision(
            score=0,
            passed=False,
            reasons=[f"excluded title keyword: {', '.join(matches)}"],
            matched_negative=matches,
        )

    def _evaluate_required_title_keywords(self, job: Job) -> FilterDecision | None:
        if not self.config.required_title_keywords:
            return None

        matches = self._find_matches(job.title.lower(), self.config.required_title_keywords)
        if matches:
            return None

        return FilterDecision(
            score=0,
            passed=False,
            reasons=["missing required scientific title keyword"],
        )

    def _evaluate_freshness(self, job: Job) -> FilterDecision | None:
        max_age_days = self.config.maximum_age_days
        if max_age_days is None:
            return None

        if not job.posted_at:
            if self.config.require_posted_at:
                return FilterDecision(
                    score=0,
                    passed=False,
                    reasons=[f"missing posted date; maximum age is {max_age_days} days"],
                )
            return None

        posted_at = self._parse_posted_at(job.posted_at)
        if posted_at is None:
            if self.config.require_posted_at:
                return FilterDecision(
                    score=0,
                    passed=False,
                    reasons=[f"unparseable posted date '{job.posted_at}'; maximum age is {max_age_days} days"],
                )
            return None

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=max_age_days)
        if posted_at < cutoff:
            age_days = max(0, (now - posted_at).days)
            return FilterDecision(
                score=0,
                passed=False,
                reasons=[f"older than maximum age: {age_days} days > {max_age_days} days"],
            )

        return None

    @staticmethod
    def _parse_posted_at(value: str) -> datetime | None:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _find_matches(text: str, keywords: set[str] | list[str]) -> list[str]:
        hits: list[str] = []
        for keyword in keywords:
            lowered = keyword.lower()
            pattern = r"\b" + re.escape(lowered).replace(r"\ ", r"\s+") + r"\b"
            if re.search(pattern, text) and lowered not in hits:
                hits.append(lowered)
        return hits
