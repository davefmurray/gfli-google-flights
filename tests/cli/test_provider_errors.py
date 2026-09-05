"""CLI JSON differentiates provider failures from successful empty searches."""

import json
from datetime import datetime, timedelta

import pytest
from typer.testing import CliRunner

from fli.cli.main import app
from fli.search.exceptions import SearchParseError, SearchPriceUnavailableError, SearchTimeoutError


@pytest.mark.parametrize("command", ["flights", "dates"])
@pytest.mark.parametrize(
    "error,category",
    [
        (SearchParseError("blocked page"), "parse_error"),
        (SearchPriceUnavailableError("no prices"), "price_unavailable"),
        (SearchTimeoutError("timeout"), "timeout"),
    ],
)
def test_cli_error_categories(command, error, category, monkeypatch, tmp_path):
    monkeypatch.setattr("fli.cli.errors._LOG_DIR", tmp_path)

    def search(*args, **kwargs):
        raise error

    monkeypatch.setattr("fli.search.SearchFlights.search", search)
    monkeypatch.setattr("fli.search.SearchDates.search", search)
    day = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    dates = [day] if command == "flights" else ["--from", day, "--to", day]
    result = CliRunner().invoke(app, [command, "JFK", "LHR", *dates, "--format", "json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error"]["type"] == category
