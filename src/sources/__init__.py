from .ashby import AshbyJobSource
from .base import BaseJobSource
from .breezy import BreezyJobSource
from .cryptocurrencyjobs import CryptocurrencyJobsSource
from .efinancialcareers import EFinancialCareersJobSource
from .greenhouse import GreenhouseJobSource
from .lever import LeverJobSource
from .pinpoint import PinpointJobSource
from .simplify import SimplifyJobSource
from .successfactors import SuccessFactorsJobSource


SOURCE_REGISTRY: dict[str, type[BaseJobSource]] = {
    "ashby": AshbyJobSource,
    "breezy": BreezyJobSource,
    "cryptocurrencyjobs": CryptocurrencyJobsSource,
    "simplify": SimplifyJobSource,
    "efinancialcareers": EFinancialCareersJobSource,
    "greenhouse": GreenhouseJobSource,
    "lever": LeverJobSource,
    "pinpoint": PinpointJobSource,
    "successfactors": SuccessFactorsJobSource,
}
