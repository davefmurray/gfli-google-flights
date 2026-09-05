"""Return actionable date validation messages without making network requests."""

from datetime import datetime, timedelta

import pytest

from fli.mcp.server import (
    DateSearchParams,
    FlightSearchParams,
    _get_booking_options_from_params,
    _search_dates_from_params,
    _search_flights_from_params,
)


@pytest.mark.parametrize(
    "operation", [_search_flights_from_params, _get_booking_options_from_params]
)
def test_return_before_departure_has_actionable_error(operation, monkeypatch):
    def search(*args, **kwargs):
        pytest.fail("Invalid dates reached the search transport")

    monkeypatch.setattr("fli.mcp.server.SearchFlights.search", search)
    params = FlightSearchParams(
        origin="JAX",
        destination="JFK",
        departure_date=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        return_date=(datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d"),
    )
    result = operation(params)
    assert result["success"] is False
    assert "Return date" in result["error"]
    assert "cannot be before departure date" in result["error"]


def test_past_date_error_identifies_field():
    params = DateSearchParams(
        origin="JAX", destination="JFK", start_date="2020-01-01", end_date="2020-01-02"
    )
    result = _search_dates_from_params(params)
    assert result["success"] is False
    assert "travel_date" in result["error"]
    assert "cannot be in the past" in result["error"]
