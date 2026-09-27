"""Shared input rules for independent returns and bounded flexible stays."""

from datetime import datetime, timedelta

import pytest

from fli.core.builders import (
    build_date_search_segments,
    build_flight_segments,
    resolve_trip_durations,
)
from fli.core.parsers import ParseError, resolve_airports
from fli.models import Airport, TimeRestrictions


@pytest.mark.parametrize("builder", [build_flight_segments, build_date_search_segments])
@pytest.mark.parametrize("mode", ["inherit", "clear", "separate"])
def test_return_time_states(builder, mode):
    outbound = TimeRestrictions(earliest_departure=6, latest_departure=12)
    inbound = TimeRestrictions(earliest_departure=16, latest_departure=23)
    date = datetime.now() + timedelta(days=30)
    args = {"origin": Airport.JAX, "destination": Airport.JFK, "time_restrictions": outbound}
    if builder is build_flight_segments:
        args.update(
            departure_date=date.strftime("%Y-%m-%d"),
            return_date=(date + timedelta(days=3)).strftime("%Y-%m-%d"),
        )
    else:
        args.update(start_date=date.strftime("%Y-%m-%d"), trip_duration=3, is_round_trip=True)
    if mode != "inherit":
        args["return_time_restrictions"] = None if mode == "clear" else inbound
    segments, _ = builder(**args)
    assert segments[0].time_restrictions == outbound
    assert (
        segments[1].time_restrictions
        == {"inherit": outbound, "clear": None, "separate": inbound}[mode]
    )


def test_cleared_return_time_is_allowed_one_way():
    date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    segments, _ = build_flight_segments(
        Airport.SFO, Airport.BOS, date, return_time_restrictions=None
    )
    assert len(segments) == 1
    segments, _ = build_date_search_segments(
        Airport.SFO, Airport.BOS, date, return_time_restrictions=None
    )
    assert len(segments) == 1
    with pytest.raises(ValueError):
        build_flight_segments(
            Airport.SFO,
            Airport.BOS,
            date,
            return_time_restrictions=TimeRestrictions(earliest_departure=5),
        )


@pytest.mark.parametrize(
    "args",
    [
        (None, 4, None, True),
        (None, None, 7, True),
        (3, 4, 7, True),
        (None, 7, 4, True),
        (None, 0, 3, True),
        (None, 1, 367, True),
        (None, 4, 7, False),
        (0, None, None, True),
    ],
)
def test_invalid_duration_controls(args):
    with pytest.raises(ValueError):
        resolve_trip_durations(*args)


def test_duration_defaults_and_range():
    assert resolve_trip_durations(None, None, None, True) == [3]
    assert resolve_trip_durations(None, None, None, False) == [None]
    assert resolve_trip_durations(None, 4, 7, True) == [4, 5, 6, 7]


@pytest.mark.parametrize("codes", ["", ",", "JFK,", ",JFK", "JFK,,LGA", "JFK,NOTREAL"])
def test_invalid_airport_lists(codes):
    with pytest.raises(ParseError):
        resolve_airports(codes)


def test_airport_lists_normalized_and_deduplicated():
    assert resolve_airports(" jfk, LGA, jfk ") == [Airport.JFK, Airport.LGA]
