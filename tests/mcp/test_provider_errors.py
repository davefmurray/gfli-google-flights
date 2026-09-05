"""MCP exposes stable provider-error categories rather than empty successes."""

from datetime import datetime, timedelta

import pytest
from fastmcp import Client

from fli.mcp.server import mcp
from fli.search.exceptions import (
    SearchConnectionError,
    SearchHTTPError,
    SearchParseError,
    SearchPriceUnavailableError,
    SearchRejectedError,
    SearchTimeoutError,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", ["search_flights", "search_dates", "get_booking_options"])
@pytest.mark.parametrize(
    "error,category",
    [
        (SearchTimeoutError("timeout"), "timeout"),
        (SearchConnectionError("network"), "connection_error"),
        (SearchHTTPError("rate limited", status_code=429), "http_error"),
        (SearchParseError("bad payload"), "parse_error"),
        (SearchPriceUnavailableError("no prices"), "price_unavailable"),
        (SearchRejectedError(13), "provider_rejected"),
    ],
)
async def test_mcp_provider_errors(tool, error, category, monkeypatch):
    def search(*args, **kwargs):
        raise error

    monkeypatch.setattr("fli.mcp.server.SearchFlights.search", search)
    monkeypatch.setattr("fli.mcp.server.SearchDates.search", search)
    day = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    args = {"origin": "JFK", "destination": "LHR"}
    args.update(
        {"start_date": day, "end_date": day} if tool == "search_dates" else {"departure_date": day}
    )
    async with Client(mcp) as client:
        result = await client.call_tool(tool, args)
    assert result.data["success"] is False
    assert result.data["error_type"] == category
    assert result.data["error"]
