"""Provider failures and truncated coverage must never become empty success."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from fli.core.builders import build_flight_segments
from fli.models import Airport, DateSearchFilters, FlightSearchFilters, PassengerInfo
from fli.search import SearchDates, SearchFlights
from fli.search._decoders import parse_search_payload
from fli.search._wire import iter_wrb_chunks
from fli.search.exceptions import SearchParseError, SearchPriceUnavailableError, SearchTimeoutError
from tests.search._pages import as_search_page
from tests.search.test_expand_multi_leg import _result
from tests.search.test_parse_flights_data import _leg, _row
from tests.search.test_wire import _multi_chunk


def query(engine, round_trip=False):
    day = datetime.now() + timedelta(days=30)
    segments, trip_type = build_flight_segments(
        Airport.JFK,
        Airport.LAX,
        day.strftime("%Y-%m-%d"),
        (day + timedelta(days=4)).strftime("%Y-%m-%d") if round_trip else None,
    )
    args = {"flight_segments": segments, "trip_type": trip_type, "passenger_info": PassengerInfo()}
    if engine == "dates":
        return DateSearchFilters(
            **args,
            from_date=day.strftime("%Y-%m-%d"),
            to_date=day.strftime("%Y-%m-%d"),
            duration=4 if round_trip else None,
        )
    return FlightSearchFilters(**args)


@pytest.mark.parametrize("engine", ["flights", "dates"])
@pytest.mark.parametrize(
    "payload",
    [{}, [], [None, None, {}, None], [None, None, [], None], [None, None, [[[None]]], None]],
)
def test_invalid_payload_is_an_error(engine, payload):
    search = SearchFlights() if engine == "flights" else SearchDates()
    search.client = MagicMock()
    search.client.get.return_value.text = as_search_page(payload)
    with pytest.raises(SearchParseError):
        search.search(query(engine))


@pytest.mark.parametrize("engine", ["flights", "dates"])
def test_valid_empty_payload_is_empty(engine):
    search = SearchFlights() if engine == "flights" else SearchDates()
    search.client = MagicMock()
    search.client.get.return_value.text = as_search_page([None, None, None, None])
    assert search.search(query(engine)) is None


@pytest.mark.parametrize("engine", ["flights", "dates"])
def test_blocked_page_is_not_empty(engine):
    search = SearchFlights() if engine == "flights" else SearchDates()
    search.client = MagicMock()
    search.client.get.return_value.text = "<html>Consent required</html>"
    with pytest.raises(SearchParseError, match="ds:1"):
        search.search(query(engine))


def test_partial_decode_is_not_complete_success():
    good = _row(legs=[_leg(dep_iata="JFK", arr_iata="LAX")])
    with pytest.raises(SearchParseError, match="Parsed 1/2"):
        parse_search_payload([None, None, [[good, []]], None])


def test_failed_search_clears_previous_booking_session():
    search = SearchFlights()
    search._last_session_id = "previous-search-session"
    search.client = MagicMock()
    search.client.get.return_value.text = "<html>Consent required</html>"
    with pytest.raises(SearchParseError):
        search.search(query("flights"))
    assert search._last_session_id is None


def test_unknown_date_price_is_not_no_flights():
    row = _row(legs=[_leg(dep_iata="JFK", arr_iata="LAX")])
    row[1][0] = []
    search = SearchDates()
    search.client = MagicMock()
    search.client.get.return_value.text = as_search_page([None, None, [[row]], None])
    with pytest.raises(SearchPriceUnavailableError):
        search.search(query("dates"))


def test_one_failed_date_fails_entire_scan(monkeypatch):
    filters = query("dates")
    filters.to_date = (filters.parsed_from_date + timedelta(days=1)).strftime("%Y-%m-%d")

    def price(self, current, day, **kwargs):
        if day == current.parsed_from_date:
            return None
        raise SearchTimeoutError("provider timed out")

    monkeypatch.setattr(SearchDates, "_price_one_date", price)
    with pytest.raises(SearchTimeoutError):
        SearchDates().search(filters)


@pytest.mark.parametrize("cap,expected", [(None, 1), (5, 0)])
def test_seventh_outbound_is_expanded_by_default(cap, expected, caplog):
    flights = [_result(Airport.JFK, Airport.LAX) for _ in range(7)]
    for index, flight in enumerate(flights):
        flight.legs[0].flight_number = str(index)
    search = SearchFlights()

    def fetch(filters, **kwargs):
        selected = filters.flight_segments[0].selected_flight
        if selected is None:
            return flights
        return (
            [_result(Airport.LAX, Airport.JFK)] if selected.legs[0].flight_number == "6" else None
        )

    search._fetch_flights = MagicMock(side_effect=fetch)
    kwargs = {} if cap is None else {"top_n": cap}
    results = search.search(query("flights", round_trip=True), **kwargs)
    assert len(results) == expected
    assert search._fetch_flights.call_count == (8 if cap is None else 6)
    if cap:
        assert "Incomplete round-trip search" in caplog.text


@pytest.mark.parametrize("cap", [0, -1, True, 1.5, "5"])
def test_invalid_expansion_limit_rejected_before_network(cap):
    search = SearchFlights()
    search.client = MagicMock()
    with pytest.raises(ValueError, match="top_n"):
        search.search(query("flights", round_trip=True), top_n=cap)
    search.client.get.assert_not_called()


@pytest.mark.parametrize(
    "body", ["", "not-json", "999\n[]\n", '[["wrb.fr",null,"{"]]', '[["wrb.fr"]]']
)
def test_strict_wire_rejects_invalid_frames(body):
    with pytest.raises(SearchParseError):
        list(iter_wrb_chunks(body, strict=True))


def test_strict_wire_rejects_partial_stream():
    with pytest.raises(SearchParseError):
        list(iter_wrb_chunks(_multi_chunk([1]) + "broken\n", strict=True))


def test_strict_wire_accepts_complete_stream():
    assert list(iter_wrb_chunks(_multi_chunk([1], [2]), strict=True)) == [[1], [2]]
