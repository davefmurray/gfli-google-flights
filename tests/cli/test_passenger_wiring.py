"""Passenger counts must survive the CLI, search, and deep-link boundaries."""

from datetime import datetime, timedelta

import pytest
from typer.testing import CliRunner

from fli.cli.main import app


@pytest.mark.parametrize("adult_option", ["--passengers", "--adults", "-p"])
def test_booking_links_receive_whole_party(adult_option, mock_search_flights):
    date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    result = CliRunner().invoke(
        app,
        [
            "flights",
            "JAX",
            "JFK",
            date,
            adult_option,
            "2",
            "--children",
            "1",
            "--infants-in-seat",
            "1",
            "--infants-on-lap",
            "1",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    expected = {"adults": 2, "children": 1, "infants_in_seat": 1, "infants_on_lap": 1}
    assert mock_search_flights.search.call_args.args[0].passenger_info.model_dump() == expected
    for call in mock_search_flights.build_flight_booking_url.call_args_list:
        assert call.kwargs["passenger_info"].model_dump() == expected


@pytest.mark.parametrize(
    "option,value",
    [
        ("--passengers", "0"),
        ("--children", "-1"),
        ("--infants-in-seat", "-1"),
        ("--infants-on-lap", "-1"),
    ],
)
def test_negative_or_zero_party_rejected(option, value, mock_search_flights):
    date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    result = CliRunner().invoke(app, ["flights", "JAX", "JFK", date, option, value])
    assert result.exit_code == 2
    mock_search_flights.search.assert_not_called()
