"""Starlink filtering is exposed by the real MCP tool schemas and adapters."""

from datetime import datetime, timedelta

import pytest
from fastmcp import Client

from fli.mcp.server import mcp


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", ["search_flights", "search_dates", "get_booking_options"])
async def test_starlink_tool_wiring(tool, monkeypatch):
    captured = []

    def search(self, filters, **kwargs):
        captured.append(filters)
        return []

    monkeypatch.setattr("fli.search.SearchFlights.search", search)
    monkeypatch.setattr("fli.search.SearchDates.search", search)
    day = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    args = {"origin": "JFK", "destination": "LHR", "starlink": "likely"}
    args.update(
        {"start_date": day, "end_date": day} if tool == "search_dates" else {"departure_date": day}
    )
    async with Client(mcp) as client:
        response = await client.call_tool(tool, args)
    assert response.data["success"] is True
    assert captured[0].starlink == "likely"
