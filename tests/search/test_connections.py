"""Connection constraints apply locally, on both directions of date searches."""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from fli.models import Airport, LayoverRestrictions
from fli.search import SearchDates, SearchFlights
from fli.search._tfs import apply_client_side_filters
from fli.search.connections import matches_connections
from tests.search.test_expand_multi_leg import _result
from tests.search.test_reliability import query


def connection(minutes=90, overnight=False, transfer=False):
    first = _result(Airport.JAX, Airport.JFK)
    second = _result(Airport.LGA if transfer else Airport.JFK, Airport.LHR)
    arrival = datetime.now().replace(
        hour=23 if overnight else 10, minute=0, second=0, microsecond=0
    ) + timedelta(days=30)
    first.legs[0].arrival_datetime = arrival
    second.legs[0].departure_datetime = arrival + timedelta(minutes=minutes)
    first.legs.extend(second.legs)
    first.stops = 1
    # Deliberately omit the optional layover summary: the legs still prove the wait.
    first.layovers = None
    return first


@pytest.mark.parametrize("minutes,expected", [(59, False), (60, True), (120, True), (121, False)])
def test_inclusive_connection_bounds(minutes, expected):
    assert (
        matches_connections(
            connection(minutes), LayoverRestrictions(min_duration=60, max_duration=120)
        )
        is expected
    )


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"airports": [Airport.JFK]}, True),
        ({"airports": [Airport.ATL]}, False),
        ({"exclude_airports": [Airport.JFK]}, False),
        ({"exclude_airports": [Airport.ATL]}, True),
    ],
)
def test_connection_airport_rules(kwargs, expected):
    assert matches_connections(connection(), LayoverRestrictions(**kwargs)) is expected


def test_transfer_checks_both_airports_and_does_not_guess_duration():
    result = connection(transfer=True)
    assert not matches_connections(result, LayoverRestrictions(exclude_airports=[Airport.LGA]))
    assert not matches_connections(result, LayoverRestrictions(airports=[Airport.JFK]))
    assert not matches_connections(result, LayoverRestrictions(min_duration=30))
    assert not matches_connections(result, LayoverRestrictions(exclude_overnight=True))
    assert matches_connections(result, LayoverRestrictions(exclude_airports=[Airport.ATL]))


def test_overnight_connection_not_overnight_flight():
    rules = LayoverRestrictions(exclude_overnight=True)
    assert not matches_connections(connection(overnight=True), rules)
    result = connection()
    result.legs[-1].overnight = True
    assert matches_connections(result, rules)
    assert matches_connections(_result(Airport.JAX, Airport.JFK), rules)


def test_every_connection_is_checked():
    result = connection()
    result.legs.append(_result(Airport.LHR, Airport.CDG).legs[0])
    assert not matches_connections(result, LayoverRestrictions(exclude_airports=[Airport.LHR]))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_duration": 100, "max_duration": 99},
        {"min_duration": 0},
        {"airports": [Airport.JFK], "exclude_airports": [Airport.JFK]},
    ],
)
def test_invalid_constraints(kwargs):
    with pytest.raises(ValidationError):
        LayoverRestrictions(**kwargs)


def test_local_postfilter_enforces_connection_rules():
    filters = query("flights")
    filters.layover_restrictions = LayoverRestrictions(max_duration=60)
    assert apply_client_side_filters([connection(90)], filters) == []


def test_roundtrip_dates_expand_connection_constrained_returns(monkeypatch):
    filters = query("dates", round_trip=True)
    filters.layover_restrictions = LayoverRestrictions(exclude_overnight=True)
    captured = []
    monkeypatch.setattr(
        SearchFlights, "search", lambda self, current, **kwargs: captured.append(current) or []
    )
    assert SearchDates().search(filters) is None
    assert len(captured) == 1
    assert captured[0].layover_restrictions.exclude_overnight


def test_chunks_keep_connection_rules():
    filters = query("dates")
    filters.layover_restrictions = LayoverRestrictions(exclude_airports=[Airport.JFK])
    chunks = SearchDates()._build_chunk_filters(
        filters, filters.parsed_from_date, filters.parsed_from_date + timedelta(days=70)
    )
    assert len(chunks) > 1
    assert all(chunk.layover_restrictions == filters.layover_restrictions for chunk in chunks)
