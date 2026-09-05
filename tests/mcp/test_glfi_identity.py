"""Verify GLFI identity, isolated configuration, and installed stdio transport."""

import sysconfig
from pathlib import Path
from unittest.mock import patch

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from fli.mcp.server import FlightSearchConfig, mcp, run_http


def test_identity():
    assert mcp.name == "GLFI"


def test_config_uses_glfi_namespace(monkeypatch):
    monkeypatch.setenv("FLI_MCP_DEFAULT_CURRENCY", "GBP")
    monkeypatch.setenv("GLFI_MCP_DEFAULT_CURRENCY", "EUR")
    assert FlightSearchConfig().default_currency == "EUR"


def test_http_defaults_to_loopback(monkeypatch):
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    with patch.object(mcp, "run") as run:
        run_http()
    run.assert_called_once_with(transport="http", host="127.0.0.1", port=8000)


@pytest.mark.asyncio
async def test_installed_stdio_server():
    command = str(Path(sysconfig.get_path("scripts")) / "glfi-mcp")
    async with Client(StdioTransport(command=command, args=[]), timeout=20) as client:
        tools = await client.list_tools()
        assert {tool.name for tool in tools} == {
            "search_flights",
            "search_dates",
            "get_booking_options",
            "find_airports",
        }
        resources = await client.list_resources()
        assert "resource://glfi-mcp/configuration" in {str(r.uri) for r in resources}
        result = await client.call_tool("find_airports", {"query": "Jacksonville"})
        assert not result.is_error
        assert "JAX" in str(result)
