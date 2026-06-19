from .ashby import AshbyJobSource
from .base import BaseJobSource
from .cryptocurrencyjobs import CryptocurrencyJobsSource
from .efinancialcareers import EFinancialCareersJobSource
from .greenhouse import GreenhouseJobSource
from .simplify import SimplifyJobSource


SOURCE_REGISTRY: dict[str, type[BaseJobSource]] = {
    "ashby": AshbyJobSource,
    "cryptocurrencyjobs": CryptocurrencyJobsSource,
    "simplify": SimplifyJobSource,
    "efinancialcareers": EFinancialCareersJobSource,
    "greenhouse": GreenhouseJobSource,
}
