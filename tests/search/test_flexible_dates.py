"""Flexible stays use one bounded implementation and preserve every filter."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from fli.core.builders import build_date_search_segments
from fli.models import Airport, DateSearchFilters, PassengerInfo, SeatType, TimeRestrictions
from fli.search.dates import DatePrice, SearchDates


def filters_for_range(days=2, return_window=None):
    day = datetime.now() + timedelta(days=30)
    segments, trip_type = build_date_search_segments(
        [Airport.JFK, Airport.LGA],
        Airport.LHR,
        day.strftime("%Y-%m-%d"),
        trip_duration=3,
        is_round_trip=True,
        return_time_restrictions=return_window,
    )
    return DateSearchFilters(
        trip_type=trip_type,
        passenger_info=PassengerInfo(adults=2, children=1),
        seat_type=SeatType.BUSINESS,
        flight_segments=segments,
        duration=3,
        from_date=day.strftime("%Y-%m-%d"),
        to_date=(day + timedelta(days=days - 1)).strftime("%Y-%m-%d"),
    )


def test_range_search_copies_filters_and_sorts(monkeypatch):
    captured = []
    original = filters_for_range()
    before = original.model_dump()

    def search_chunk(self, filters, **kwargs):
        captured.append(filters)
        assert kwargs == {"currency": "EUR", "language": "en-GB", "country": "GB"}
        result = DatePrice(
            date=(
                filters.parsed_from_date,
                filters.parsed_from_date + timedelta(days=filters.duration),
            ),
            price=500 - filters.duration,
        )
        return [result, result.model_copy(update={"price": result.price + 50})]

    monkeypatch.setattr(SearchDates, "_search_chunk", search_chunk)
    results = SearchDates().search(original, "EUR", "en-GB", "GB", durations=[3, 4, 4, 5])
    assert [f.duration for f in captured] == [3, 4, 5]
    assert [r.price for r in results] == [495, 496, 497]
    assert original.model_dump() == before
    for f in captured:
        assert f.passenger_info == original.passenger_info
        assert f.seat_type == SeatType.BUSINESS
        assert (
            f.flight_segments[1].parsed_travel_date - f.flight_segments[0].parsed_travel_date
        ).days == f.duration


def test_request_budget_checked_before_fetch(monkeypatch):
    search = MagicMock(side_effect=AssertionError("must reject before network"))
    monkeypatch.setattr(SearchDates, "_search_chunk", search)
    with pytest.raises(ValueError, match="366 date/duration"):
        SearchDates().search(filters_for_range(days=61), durations=list(range(1, 8)))
    search.assert_not_called()


def test_return_window_prices_only_complete_itineraries(monkeypatch):
    filters = filters_for_range(
        return_window=TimeRestrictions(earliest_departure=16, latest_departure=23)
    )
    captured = []

    def flights(self, current, **kwargs):
        captured.append(current)
        return [
            (MagicMock(price=100), MagicMock(price=420)),
            (MagicMock(price=90), MagicMock(price=450)),
        ]

    monkeypatch.setattr("fli.search.flights.SearchFlights.search", flights)
    day = filters.parsed_from_date + timedelta(days=1)
    result = SearchDates()._price_one_date(
        filters, day, currency="USD", language=None, country=None
    )
    assert result.price == 420
    assert captured[0].flight_segments[0].travel_date == day.strftime("%Y-%m-%d")
    assert captured[0].flight_segments[1].time_restrictions.earliest_departure == 16
    assert captured[0].passenger_info.children == 1
    assert captured[0].sort_by.name == "CHEAPEST"


def test_no_qualifying_return_is_not_outbound_price(monkeypatch):
    filters = filters_for_range(return_window=TimeRestrictions(earliest_departure=16))
    monkeypatch.setattr("fli.search.flights.SearchFlights.search", lambda *a, **k: [])
    assert (
        SearchDates()._price_one_date(
            filters, filters.parsed_from_date, currency=None, language=None, country=None
        )
        is None
    )
