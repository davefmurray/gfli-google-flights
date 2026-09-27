"""CLI controls and encoded links retain the full request."""

import base64
import json
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from typer.testing import CliRunner

from fli.cli.main import app
from fli.search.dates import DatePrice


def test_flights_multi_airport_return_and_search_link(mock_search_flights):
    date = datetime.now() + timedelta(days=30)
    departure = date.strftime("%Y-%m-%d")
    inbound = (date + timedelta(days=4)).strftime("%Y-%m-%d")
    mock_search_flights.search.return_value = []
    result = CliRunner().invoke(
        app,
        [
            "flights",
            " jfk,LGA,JFK ",
            "LHR,CDG",
            departure,
            "--return",
            inbound,
            "--time",
            "6-12",
            "--return-time",
            "16-23",
            "--adults",
            "2",
            "--children",
            "1",
            "--class",
            "BUSINESS",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    filters = mock_search_flights.search.call_args.args[0]
    assert [a[0].name for a in filters.flight_segments[0].departure_airport] == ["JFK", "LGA"]
    assert filters.flight_segments[0].time_restrictions.earliest_departure == 6
    assert filters.flight_segments[1].time_restrictions.earliest_departure == 16
    data = json.loads(result.output)
    token = parse_qs(urlparse(data["booking_url"]).query)["tfs"][0]
    raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    for code in (b"JFK", b"LGA", b"LHR", b"CDG", departure.encode(), inbound.encode()):
        assert code in raw
    assert b"\x40\x01\x40\x01\x40\x02\x48\x03" in raw


def test_dates_range_multi_airport_and_party_link(mock_search_dates):
    day = datetime.now() + timedelta(days=30)
    mock_search_dates.search.return_value = [
        DatePrice(date=(day, day + timedelta(days=5)), price=500)
    ]
    result = CliRunner().invoke(
        app,
        [
            "dates",
            "JFK,LGA",
            "LHR,CDG",
            "--from",
            day.strftime("%Y-%m-%d"),
            "--to",
            day.strftime("%Y-%m-%d"),
            "--round",
            "--min-duration",
            "4",
            "--max-duration",
            "7",
            "--return-time",
            "16-23",
            "--adults",
            "2",
            "--children",
            "1",
            "--class",
            "BUSINESS",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert mock_search_dates.search.call_args.kwargs["durations"] == [4, 5, 6, 7]
    filters = mock_search_dates.search.call_args.args[0]
    assert filters.duration == 4
    assert filters.flight_segments[1].time_restrictions.earliest_departure == 16
    data = json.loads(result.output)
    assert data["query"]["sort_by_price"] is True
    token = parse_qs(urlparse(data["dates"][0]["booking_url"]).query)["tfs"][0]
    raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    assert (day + timedelta(days=5)).strftime("%Y-%m-%d").encode() in raw
    assert b"LGA" in raw and b"CDG" in raw
    assert b"\x40\x01\x40\x01\x40\x02\x48\x03" in raw


@pytest.mark.parametrize(
    "flags",
    [
        ["--return-time", "16-23"],
        ["--round", "--min-duration", "4"],
        ["--round", "--max-duration", "7"],
        ["--min-duration", "4", "--max-duration", "7"],
        ["--round", "--duration", "3", "--min-duration", "4", "--max-duration", "7"],
        ["--round", "--min-duration", "7", "--max-duration", "4"],
    ],
)
def test_invalid_dates_controls_never_search(flags, mock_search_dates):
    day = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    result = CliRunner().invoke(
        app, ["dates", "JFK", "LHR", "--from", day, "--to", day, "--format", "json", *flags]
    )
    assert result.exit_code != 0
    assert json.loads(result.output)["success"] is False
    mock_search_dates.search.assert_not_called()


@pytest.mark.parametrize(
    "args", [["JFK,", "LHR"], ["JFK", ","], ["JFK", "LHR", "--return-time", "16-23"]]
)
def test_invalid_flights_controls_never_search(args, mock_search_flights):
    day = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    result = CliRunner().invoke(app, ["flights", *args[:2], day, *args[2:], "--format", "json"])
    assert result.exit_code != 0
    mock_search_flights.search.assert_not_called()


@pytest.mark.parametrize("command", ["flights", "dates"])
def test_outbound_time_does_not_filter_return(command, mock_search_flights, mock_search_dates):
    day = datetime.now() + timedelta(days=30)
    start = day.strftime("%Y-%m-%d")
    if command == "flights":
        mock_search_flights.search.return_value = []
        args = [start, "--return", (day + timedelta(days=4)).strftime("%Y-%m-%d")]
        mock = mock_search_flights
    else:
        mock_search_dates.search.return_value = []
        args = ["--from", start, "--to", start, "--round"]
        mock = mock_search_dates
    result = CliRunner().invoke(
        app, [command, "SFO", "BOS", *args, "--time", "22-23", "--format", "json"]
    )
    assert result.exit_code == 0, result.output
    filters = mock.search.call_args.args[0]
    assert filters.flight_segments[0].time_restrictions.earliest_departure == 22
    assert filters.flight_segments[1].time_restrictions is None
