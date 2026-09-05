"""Starlink CLI option wiring, validation and inspectable evidence catalog."""

import json
from datetime import datetime, timedelta

import pytest
from typer.testing import CliRunner

from fli.cli.main import app
from fli.models.starlink import StarlinkFilter


@pytest.mark.parametrize("command", ["flights", "dates"])
@pytest.mark.parametrize("mode", ["likely", "possible"])
def test_filter_reaches_search(command, mode, monkeypatch):
    captured = []

    def search(self, filters, **kwargs):
        captured.append(filters)
        return []

    monkeypatch.setattr("fli.search.SearchFlights.search", search)
    monkeypatch.setattr("fli.search.SearchDates.search", search)
    day = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    dates = [day] if command == "flights" else ["--from", day, "--to", day]
    result = CliRunner().invoke(
        app, [command, "JFK", "LHR", *dates, "--starlink", mode, "--format", "json"]
    )
    assert result.exit_code == 0, result.output
    assert captured[0].starlink == StarlinkFilter(mode)
    assert json.loads(result.output)["query"]["starlink"] == mode


def test_catalog_has_sources():
    result = CliRunner().invoke(app, ["starlink", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["basis"] == "fleet_inference"
    assert all(r["source_url"] and r["review_after"] for r in data["rules"])


def test_invalid_mode_never_searches(monkeypatch):
    def search(*args, **kwargs):
        pytest.fail("Invalid mode reached network")

    monkeypatch.setattr("fli.search.SearchFlights.search", search)
    day = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    result = CliRunner().invoke(app, ["flights", "JFK", "LHR", day, "--starlink", "confirmed"])
    assert result.exit_code != 0
