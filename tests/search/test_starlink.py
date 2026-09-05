"""Starlink is sourced fleet inference, never free-Wi-Fi detection or a guarantee."""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest

from fli.models import Airline, Airport, Amenities
from fli.models.starlink import StarlinkFilter
from fli.search import SearchDates, SearchFlights
from fli.search._tfs import apply_client_side_filters
from fli.search.starlink import RULES, assess_starlink, itinerary_status, normalize_aircraft
from tests.search.test_expand_multi_leg import _result
from tests.search.test_reliability import query

TODAY = date(2026, 9, 5)


def flight(carrier="QR", aircraft="Airbus A350-1000", operator=None):
    result = _result(Airport.JFK, Airport.LHR)
    leg = result.legs[0]
    leg.airline = Airline[carrier]
    leg.operating_airline = Airline[operator] if operator else None
    leg.aircraft = aircraft
    leg.departure_datetime = datetime(2026, 10, 15, 10)
    return result


@pytest.mark.parametrize(
    "carrier,aircraft,expected",
    [
        ("QR", "Airbus A350-1000", "likely"),
        ("QR", "Boeing 787-8", "likely"),
        ("QR", "Boeing 787-9", "possible"),
        ("QR", "Boeing 787", "possible"),
        ("QR", "Airbus A380", "unknown"),
        ("HA", "Airbus A330-200", "likely"),
        ("HA", "Airbus A321neo", "likely"),
        ("HA", "Boeing 787-9", "unknown"),
        ("AS", "Airbus A330-200", "unknown"),
        ("UA", "Boeing 737-800", "possible"),
        ("UA", "Boeing 737 MAX 8", "unknown"),
        ("UA", "Embraer 175", "possible"),
        ("DL", "Embraer 175", "unknown"),
        ("AA", None, "unknown"),
    ],
)
def test_fleet_evidence(carrier, aircraft, expected):
    evidence = assess_starlink(flight(carrier, aircraft).legs[0], today=TODAY)
    assert evidence.status == expected
    assert evidence.basis == "fleet_inference"
    assert "Not flight-confirmed" in evidence.caveat
    if expected != "unknown":
        assert evidence.source_url.startswith("https://")
        assert evidence.checked_on == TODAY


@pytest.mark.parametrize(
    "carrier,operator,expected",
    [("AA", "QR", "likely"), ("QR", "BA", "unknown"), ("AS", "HA", "unknown")],
)
def test_operating_carrier_takes_precedence(carrier, operator, expected):
    assert (
        assess_starlink(flight(carrier, operator=operator).legs[0], today=TODAY).status == expected
    )


def test_united_express_is_scoped_to_united():
    assert (
        assess_starlink(flight("UA", "Embraer 175", "OO").legs[0], today=TODAY).status == "possible"
    )
    assert (
        assess_starlink(flight("DL", "Embraer 175", "OO").legs[0], today=TODAY).status == "unknown"
    )


@pytest.mark.parametrize("today", [date(2026, 9, 4), date(2026, 12, 5)])
def test_unreviewed_or_stale_evidence_is_unknown(today):
    evidence = assess_starlink(flight().legs[0], today=today)
    assert evidence.status == "unknown"
    assert "review" in evidence.reason


def test_far_future_is_unknown():
    leg = flight().legs[0]
    leg.departure_datetime = datetime(2027, 1, 1)
    assert assess_starlink(leg, today=TODAY).status == "unknown"


def test_wifi_flag_is_not_starlink_proof():
    leg = flight("DL", "Airbus A350").legs[0]
    leg.amenities = Amenities(wifi=True, wifi_type="free")
    assert assess_starlink(leg, today=TODAY).status == "unknown"
    leg = flight().legs[0]
    leg.amenities = Amenities(wifi=False)
    assert "conflicting" in assess_starlink(leg, today=TODAY).reason


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Airbus A321 neo", "A321NEO"),
        ("Boeing 777-300ER", "B777-300ER"),
        ("Embraer E175", "E175"),
        ("Canadair RJ 550", "CRJ550"),
        ("Boeing 737 MAX 8", "B737MAX8"),
        (None, ""),
    ],
)
def test_aircraft_normalization(raw, expected):
    assert normalize_aircraft(raw) == expected


@pytest.fixture
def fresh_rules(monkeypatch):
    today = datetime.now(timezone.utc).date()
    monkeypatch.setattr(
        "fli.search.starlink.RULES",
        tuple(replace(r, checked_on=today, effective_from=date.min) for r in RULES),
    )
    return datetime.now() + timedelta(days=30)


@pytest.mark.parametrize("mode,expected", [("any", 1), ("likely", 0), ("possible", 1)])
def test_every_connection_must_qualify(mode, expected, fresh_rules):
    result = flight()
    result.legs.append(flight("UA", "Boeing 737-800").legs[0])
    for leg in result.legs:
        leg.departure_datetime = fresh_rules
    filters = query("flights")
    filters.starlink = StarlinkFilter(mode)
    assert len(apply_client_side_filters([result], filters)) == expected
    assert itinerary_status(result.legs) == "possible"


def test_unknown_connection_excluded(fresh_rules):
    result = flight()
    result.legs.append(flight("DL", "Airbus A350").legs[0])
    for leg in result.legs:
        leg.departure_datetime = fresh_rules
    filters = query("flights")
    filters.starlink = StarlinkFilter.POSSIBLE
    assert apply_client_side_filters([result], filters) == []
    assert itinerary_status(result.legs) == "unknown"


def test_roundtrip_dates_expand_returns_even_without_time_window(monkeypatch, fresh_rules):
    filters = query("dates", round_trip=True)
    filters.starlink = StarlinkFilter.LIKELY
    captured = []

    def search(self, current, **kwargs):
        captured.append(current)
        return []

    monkeypatch.setattr(SearchFlights, "search", search)
    assert SearchDates().search(filters) is None
    assert len(captured) == 1
    assert captured[0].starlink == StarlinkFilter.LIKELY


def test_date_chunks_preserve_filter():
    filters = query("dates")
    filters.starlink = StarlinkFilter.POSSIBLE
    search = SearchDates()
    chunks = search._build_chunk_filters(
        filters, filters.parsed_from_date, filters.parsed_from_date + timedelta(days=70)
    )
    assert len(chunks) > 1
    assert all(chunk.starlink == StarlinkFilter.POSSIBLE for chunk in chunks)


@pytest.mark.parametrize("engine", ["flights", "dates"])
def test_stale_filter_fails_before_network(engine, monkeypatch):
    from unittest.mock import MagicMock

    from fli.search.exceptions import SearchUnsupportedError

    monkeypatch.setattr("fli.search.starlink.RULES", ())
    search = SearchFlights() if engine == "flights" else SearchDates()
    search.client = MagicMock()
    filters = query(engine)
    filters.starlink = StarlinkFilter.LIKELY
    with pytest.raises(SearchUnsupportedError, match="stale"):
        search.search(filters)
    search.client.get.assert_not_called()


def test_roundtrip_excludes_unknown_return(monkeypatch, fresh_rules):
    filters = query("flights", round_trip=True)
    filters.starlink = StarlinkFilter.LIKELY
    outbound = flight()
    returning = flight("DL", "Airbus A350")
    outbound.legs[0].departure_datetime = fresh_rules
    returning.legs[0].departure_datetime = fresh_rules + timedelta(days=4)

    def fetch(self, current, **kwargs):
        result = outbound if current.flight_segments[0].selected_flight is None else returning
        return apply_client_side_filters([result], current)

    monkeypatch.setattr(SearchFlights, "_fetch_flights", fetch)
    assert not SearchFlights().search(filters)


def test_serialized_leg_keeps_evidence():
    from fli.cli.utils import serialize_flight_leg
    from fli.mcp.server import _serialize_flight_leg

    leg = flight().legs[0]
    leg.starlink = assess_starlink(leg, today=TODAY)
    for serialize in (serialize_flight_leg, _serialize_flight_leg):
        evidence = serialize(leg)["starlink"]
        assert evidence["checked_on"] == "2026-09-05"
        assert evidence["status"] == "likely"
        assert evidence["source_url"]
