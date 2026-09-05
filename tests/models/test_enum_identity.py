"""Every IATA code must retain its identity through parsing and serialization."""

from fli.core.parsers import resolve_airport
from fli.models import Airline, Airport, FlightSearchFilters, FlightSegment, PassengerInfo
from fli.search._tfs import build_tfs
from scripts.generate_enums import _disambiguate_names


def test_all_airport_codes_have_distinct_members():
    assert all(code == member.name for code, member in Airport.__members__.items())


def test_all_airline_codes_have_distinct_members():
    assert all(code == member.name for code, member in Airline.__members__.items())


def test_w4_uses_current_airline_name():
    assert Airline.W4.value == "Wizz Air Malta"


def test_disambiguation_preserves_unique_names():
    entries = [("TRI", "Tri-Cities Airport"), ("PSC", "Tri-Cities Airport"), ("JFK", "JFK")]
    assert _disambiguate_names(entries) == [
        ("TRI", "Tri-Cities Airport (TRI)"),
        ("PSC", "Tri-Cities Airport (PSC)"),
        ("JFK", "JFK"),
    ]


def test_tri_search_never_encodes_pasco():
    import base64
    from datetime import datetime, timedelta

    origin = resolve_airport("TRI")
    assert origin.name == "TRI"
    assert origin is not Airport.PSC
    filters = FlightSearchFilters(
        passenger_info=PassengerInfo(),
        flight_segments=[
            FlightSegment(
                departure_airport=[[origin, 0]],
                arrival_airport=[[Airport.SFB, 0]],
                travel_date=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            )
        ],
    )
    token = build_tfs(filters)
    payload = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    assert b"TRI" in payload
    assert b"PSC" not in payload
