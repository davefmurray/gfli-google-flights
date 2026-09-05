"""Date scans must preserve filters when chunking and pricing decoded rows."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from fli.models import (
    Airline,
    Airport,
    Alliance,
    DateSearchFilters,
    FlightLeg,
    FlightResult,
    FlightSegment,
    PassengerInfo,
    TimeRestrictions,
)
from fli.search import SearchDates


def filters():
    date = datetime.now() + timedelta(days=30)
    return DateSearchFilters(
        passenger_info=PassengerInfo(adults=2, children=1),
        flight_segments=[
            FlightSegment(
                departure_airport=[[Airport.JAX, 0]],
                arrival_airport=[[Airport.JFK, 0]],
                travel_date=date.strftime("%Y-%m-%d"),
            )
        ],
        from_date=date.strftime("%Y-%m-%d"),
        to_date=date.strftime("%Y-%m-%d"),
    )


def test_chunks_preserve_exclusions_and_alliances():
    query = filters()
    query.airlines_exclude = [Airline.AA]
    query.alliances = [Alliance.SKYTEAM]
    query.alliances_exclude = [Alliance.ONEWORLD]
    chunks = SearchDates()._build_chunk_filters(
        query,
        query.parsed_from_date,
        query.parsed_from_date + timedelta(days=70),
    )
    assert len(chunks) == 2
    for chunk in chunks:
        assert chunk.airlines_exclude == query.airlines_exclude
        assert chunk.alliances == query.alliances
        assert chunk.alliances_exclude == query.alliances_exclude
        assert chunk.passenger_info == query.passenger_info


@pytest.mark.parametrize("mode", ["include", "exclude", "time"])
def test_date_price_uses_only_matching_flights(mode, monkeypatch):
    query = filters()
    if mode == "include":
        query.airlines = [Airline.DL]
    elif mode == "exclude":
        query.airlines_exclude = [Airline.AA]
    else:
        query.flight_segments[0].time_restrictions = TimeRestrictions(earliest_departure=12)

    def result(carrier, hour, price):
        departure = query.parsed_from_date.replace(hour=hour)
        return FlightResult(
            price=price,
            currency="USD",
            duration=120,
            stops=0,
            legs=[
                FlightLeg(
                    airline=carrier,
                    flight_number="123",
                    departure_airport=Airport.JAX,
                    arrival_airport=Airport.JFK,
                    departure_datetime=departure,
                    arrival_datetime=departure + timedelta(hours=2),
                    duration=120,
                ),
            ],
        )

    search = SearchDates()
    monkeypatch.setattr(
        search.client,
        "get",
        Mock(
            return_value=SimpleNamespace(
                text="fixture",
                raise_for_status=lambda: None,
            )
        ),
    )
    monkeypatch.setattr(
        "fli.search.dates.extract_payload", lambda text: [None, None, [[1, 2]], None]
    )
    monkeypatch.setattr(
        "fli.search._decoders.parse_flight_row",
        Mock(
            side_effect=[
                result(Airline.AA, 8, 100),
                result(Airline.DL, 14, 200),
            ]
        ),
    )
    results = search.search(query)
    assert results and results[0].price == 200
