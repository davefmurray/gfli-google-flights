"""Exercise registered tools, not only internal adapters."""

from datetime import date, timedelta

import pytest
from fastmcp import Client

from fli.mcp.server import mcp
from fli.models import Airport
from fli.presets import load_preset, save_preset
from tests.search.test_reliability import query


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", ["search_flights", "search_dates", "get_booking_options"])
async def test_connection_tools_schema_and_wiring(tool, monkeypatch):
    captured = []
    monkeypatch.setattr(
        "fli.search.SearchFlights.search",
        lambda self, filters, **kwargs: captured.append(filters) or [],
    )
    monkeypatch.setattr(
        "fli.search.SearchDates.search",
        lambda self, filters, **kwargs: captured.append(filters) or [],
    )
    day = (date.today() + timedelta(days=30)).isoformat()
    args = {
        "origin": "JAX",
        "destination": "JFK",
        "min_layover": 60,
        "max_layover": 180,
        "exclude_layover": ["ATL", "ORD"],
        "no_overnight_layovers": True,
    }
    args.update(
        {"start_date": day, "end_date": day}
        if tool == "search_dates"
        else {"departure_date": day, "starlink": "possible", "starlink_premium": True}
    )
    async with Client(mcp) as client:
        schemas = {tool.name: tool.inputSchema for tool in await client.list_tools()}
        assert "exclude_layover" in schemas[tool]["properties"]
        response = await client.call_tool(tool, args)
    assert response.data["success"]
    rules = captured[0].layover_restrictions
    assert rules.exclude_airports == [Airport.ATL, Airport.ORD]
    assert rules.exclude_overnight
    assert rules.min_duration == 60 and rules.max_duration == 180
    if tool != "search_dates":
        assert captured[0].starlink_premium


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["flights", "dates"])
async def test_save_then_run_cross_surface(kind, monkeypatch, tmp_path):
    monkeypatch.setenv("GLFI_PRESET_DIR", str(tmp_path))
    captured = []
    monkeypatch.setattr(
        "fli.search.SearchFlights.search",
        lambda self, filters, **kwargs: captured.append(filters) or [],
    )
    monkeypatch.setattr(
        "fli.search.SearchDates.search",
        lambda self, filters, **kwargs: captured.append(filters) or [],
    )
    day = (date.today() + timedelta(days=30)).isoformat()
    params = {
        "origin": "JAX",
        "destination": "JFK",
        "children": 1,
        "starlink": "possible",
        "no_overnight_layovers": True,
        "exclude_layover": ["ATL"],
    }
    params.update(
        {"departure_date": day} if kind == "flights" else {"start_date": day, "end_date": day}
    )
    async with Client(mcp) as client:
        saved = await client.call_tool("save_search_preset", {"name": "work", kind: params})
        assert saved.data["success"], saved.data
        assert captured == []
        assert load_preset("work").kind == kind
        assert load_preset("work").filters["passenger_info"]["children"] == 1
        duplicate = await client.call_tool("save_search_preset", {"name": "work", kind: params})
        assert not duplicate.data["success"]
        assert captured == []
        run = await client.call_tool("run_search_preset", {"name": "work"})
        assert run.data["success"]
        assert captured[0].layover_restrictions.exclude_overnight
        assert captured[0].starlink == "possible"
        show = await client.call_tool("manage_search_presets", {"action": "show", "name": "work"})
        assert show.data["preset"]["kind"] == kind
        deleted = await client.call_tool(
            "manage_search_presets", {"action": "delete", "name": "work"}
        )
        assert deleted.data["success"]


@pytest.mark.asyncio
async def test_mcp_runs_cli_created_preset(monkeypatch, tmp_path):
    monkeypatch.setenv("GLFI_PRESET_DIR", str(tmp_path))
    save_preset("cli-work", query("flights"))
    captured = []
    monkeypatch.setattr(
        "fli.search.SearchFlights.search",
        lambda self, filters, **kwargs: captured.append(filters) or [],
    )
    async with Client(mcp) as client:
        result = await client.call_tool("run_search_preset", {"name": "cli-work"})
    assert result.data["success"]
    assert len(captured) == 1


@pytest.mark.asyncio
async def test_empty_preset_name_cannot_trigger_search(monkeypatch, tmp_path):
    monkeypatch.setenv("GLFI_PRESET_DIR", str(tmp_path))
    monkeypatch.setattr(
        "fli.search.SearchFlights.search", lambda *args, **kwargs: pytest.fail("Network")
    )
    async with Client(mcp) as client:
        result = await client.call_tool(
            "save_search_preset",
            {
                "name": "",
                "flights": {
                    "origin": "JAX",
                    "destination": "JFK",
                    "departure_date": (date.today() + timedelta(days=30)).isoformat(),
                },
            },
        )
    assert not result.data["success"]
