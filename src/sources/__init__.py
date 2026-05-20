from .base import BaseJobSource
from .efinancialcareers import EFinancialCareersJobSource
from .simplify import SimplifyJobSource


SOURCE_REGISTRY: dict[str, type[BaseJobSource]] = {
    "simplify": SimplifyJobSource,
    "efinancialcareers": EFinancialCareersJobSource,
}

