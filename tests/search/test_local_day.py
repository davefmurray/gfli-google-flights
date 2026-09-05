"""Same-day searches must survive both validation and the date-sweep transport."""

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from fli.models import Airport, DateSearchFilters, FlightSegment, PassengerInfo
from fli.search import SearchDates
from fli.search._wire import iter_wrb_chunks
from tests.search._pages import as_search_page


class UTCServerClock(datetime):
    @classmethod
    def now(cls, tz=None):
        instant = datetime(2026, 9, 6, 1, tzinfo=timezone.utc)
        return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)


def test_date_sweep_fetches_previous_utc_day(monkeypatch):
    monkeypatch.setattr("fli.models.google_flights.base.datetime", UTCServerClock)
    monkeypatch.setattr("fli.models.google_flights.dates.datetime", UTCServerClock)
    monkeypatch.setattr("fli.search.dates.datetime", UTCServerClock)
    segment = FlightSegment(
        departure_airport=[[Airport.SFO, 0]],
        arrival_airport=[[Airport.JFK, 0]],
        travel_date="2026-09-05",
    )
    filters = DateSearchFilters(
        passenger_info=PassengerInfo(),
        flight_segments=[segment],
        from_date="2026-09-05",
        to_date="2026-09-05",
    )
    fixture = Path(__file__).parent / "fixtures/flight_search_jfk_lax_oneway_usd.bin"
    page = as_search_page(next(iter_wrb_chunks(fixture.read_text())))
    urls = []

    def get(url, **kwargs):
        urls.append(url)
        return SimpleNamespace(text=page, raise_for_status=lambda: None)

    search = SearchDates()
    monkeypatch.setattr(search.client, "get", get)
    results = search.search(filters)
    assert len(urls) == 1
    assert results and results[0].date[0].strftime("%Y-%m-%d") == "2026-09-05"
    with pytest.raises(ValueError, match="cannot be in the past"):
        FlightSegment(
            departure_airport=[[Airport.SFO, 0]],
            arrival_airport=[[Airport.JFK, 0]],
            travel_date="2026-09-04",
        )
