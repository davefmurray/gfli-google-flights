"""Exercise new controls through actual FastMCP schemas and adapters."""

from datetime import datetime, timedelta

import pytest
from fastmcp import Client

from fli.mcp.server import mcp


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", ["search_flights", "search_dates", "get_booking_options"])
async def test_controls_reach_search(tool, monkeypatch):
    captured = []

    def search(self, filters, **kwargs):
        captured.append((filters, kwargs))
        return []

    monkeypatch.setattr("fli.mcp.server.SearchFlights.search", search)
    monkeypatch.setattr("fli.mcp.server.SearchDates.search", search)
    day = datetime.now() + timedelta(days=30)
    args = {
        "origin": "JFK,LGA",
        "destination": "LHR,CDG",
        "passengers": 2,
        "children": 1,
        "departure_window": "6-12",
        "return_departure_window": "16-23",
        "cabin_class": "BUSINESS",
    }
    if tool == "search_dates":
        args.update(
            start_date=day.strftime("%Y-%m-%d"),
            end_date=day.strftime("%Y-%m-%d"),
            is_round_trip=True,
            min_duration=4,
            max_duration=7,
        )
    else:
        args.update(
            departure_date=day.strftime("%Y-%m-%d"),
            return_date=(day + timedelta(days=4)).strftime("%Y-%m-%d"),
        )
    async with Client(mcp) as client:
        result = await client.call_tool(tool, args)
    assert result.data["success"] is True
    assert len(captured) == 1
    filters, kwargs = captured[0]
    assert filters.flight_segments[0].time_restrictions.earliest_departure == 6
    assert filters.flight_segments[1].time_restrictions.earliest_departure == 16
    assert [a[0].name for a in filters.flight_segments[0].departure_airport] == ["JFK", "LGA"]
    assert filters.passenger_info.children == 1
    if tool == "search_dates":
        assert kwargs["durations"] == [4, 5, 6, 7]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "extra",
    [
        {"min_duration": 4},
        {"max_duration": 7},
        {"min_duration": 7, "max_duration": 4, "is_round_trip": True},
        {"min_duration": 4, "max_duration": 7, "is_round_trip": True, "trip_duration": 3},
        {"min_duration": 4, "max_duration": 7},
        {"return_departure_window": "16-23"},
    ],
)
async def test_invalid_date_controls_are_clear_errors(extra, monkeypatch):
    def search(*args, **kwargs):
        pytest.fail("Invalid input reached search")

    monkeypatch.setattr("fli.mcp.server.SearchDates.search", search)
    day = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    async with Client(mcp) as client:
        result = await client.call_tool(
            "search_dates",
            dict(origin="JFK", destination="LHR", start_date=day, end_date=day, **extra),
        )
    assert result.data["success"] is False
    assert result.data["error"]


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", ["search_flights", "search_dates", "get_booking_options"])
async def test_departure_window_does_not_filter_return(tool, monkeypatch):
    captured = []

    def search(self, filters, **kwargs):
        captured.append(filters)
        return []

    monkeypatch.setattr("fli.mcp.server.SearchFlights.search", search)
    monkeypatch.setattr("fli.mcp.server.SearchDates.search", search)
    day = datetime.now() + timedelta(days=30)
    args = {"origin": "SFO", "destination": "BOS", "departure_window": "22-23"}
    if tool == "search_dates":
        args.update(
            start_date=day.strftime("%Y-%m-%d"),
            end_date=day.strftime("%Y-%m-%d"),
            is_round_trip=True,
        )
    else:
        args.update(
            departure_date=day.strftime("%Y-%m-%d"),
            return_date=(day + timedelta(days=4)).strftime("%Y-%m-%d"),
        )
    async with Client(mcp) as client:
        await client.call_tool(tool, args)
    assert len(captured) == 1
    assert captured[0].flight_segments[0].time_restrictions.earliest_departure == 22
    assert captured[0].flight_segments[1].time_restrictions is None
