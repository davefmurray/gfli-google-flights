"""Search links using the same airport, passenger, and cabin encoding as requests."""

from fli.core.links import with_locale_params
from fli.models import DateSearchFilters, FlightSearchFilters
from fli.search._tfs import PAGE_URL, build_tfs


def search_url(
    filters: DateSearchFilters | FlightSearchFilters,
    *,
    travel_dates: list[str] | None = None,
    currency: str | None = None,
    language: str | None = None,
    country: str | None = None,
) -> str:
    """Preserve the full route/party/cabin; client-only filters are not encoded."""
    token = build_tfs(filters, travel_dates=travel_dates)
    return with_locale_params(f"{PAGE_URL}?tfs={token}", currency, language, country)
