"""Verify passenger fields through the actual MCP tool schemas and adapters."""

from datetime import datetime, timedelta

import pytest
from fastmcp import Client

from fli.mcp.server import mcp


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", ["search_flights", "search_dates", "get_booking_options"])
async def test_party_reaches_search_through_mcp(tool, monkeypatch):
    captured = []

    def search(self, filters, **kwargs):
        captured.append(filters.passenger_info.model_dump())
        return []

    monkeypatch.setattr("fli.mcp.server.SearchFlights.search", search)
    monkeypatch.setattr("fli.mcp.server.SearchDates.search", search)
    date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    args = {
        "origin": "JAX",
        "destination": "JFK",
        "passengers": 2,
        "children": 1,
        "infants_in_seat": 1,
        "infants_on_lap": 1,
    }
    if tool == "search_dates":
        args.update(start_date=date, end_date=date)
    else:
        args["departure_date"] = date
    async with Client(mcp) as client:
        await client.call_tool(tool, args)
    assert captured == [{"adults": 2, "children": 1, "infants_in_seat": 1, "infants_on_lap": 1}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [("passengers", 0), ("children", -1), ("infants_in_seat", -1), ("infants_on_lap", -1)],
)
async def test_invalid_party_never_reaches_search(field, value, monkeypatch):
    def search(*args, **kwargs):
        pytest.fail("Invalid passenger configuration reached Google")

    monkeypatch.setattr("fli.mcp.server.SearchFlights.search", search)
    date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    async with Client(mcp) as client:
        result = await client.call_tool(
            "search_flights",
            {
                "origin": "JAX",
                "destination": "JFK",
                "departure_date": date,
                field: value,
            },
            raise_on_error=False,
        )
    assert result.is_error
