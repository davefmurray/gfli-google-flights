"""Evidence labels for inferred Starlink availability, never flight confirmation."""

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class StarlinkFilter(str, Enum):
    """Minimum fleet-evidence level required on every leg."""

    ANY = "any"
    LIKELY = "likely"
    POSSIBLE = "possible"


class StarlinkAssessment(BaseModel):
    """An auditable inference, not a guarantee or numerical probability."""

    status: Literal["likely", "possible", "unknown"] = "unknown"
    reason: str
    source_url: str | None = None
    checked_on: date | None = None
    review_after: date | None = None
    basis: Literal["fleet_inference"] = "fleet_inference"
    caveat: str = "Not flight-confirmed. Aircraft swaps, outages and route restrictions can apply."
