from __future__ import annotations

from dataclasses import dataclass, field
import re

from .config import FilterConfig
from .models import Job


QUANT_TITLE_KEYWORDS = {"quant", "quantitative"}
CORE_ROLE_KEYWORDS = {"research", "researcher", "trader", "trading"}
EARLY_CAREER_KEYWORDS = {"intern", "internship", "graduate", "summer"}


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

    @staticmethod
    def _find_matches(text: str, keywords: set[str] | list[str]) -> list[str]:
        hits: list[str] = []
        for keyword in keywords:
            lowered = keyword.lower()
            pattern = r"\b" + re.escape(lowered).replace(r"\ ", r"\s+") + r"\b"
            if re.search(pattern, text) and lowered not in hits:
                hits.append(lowered)
        return hits
