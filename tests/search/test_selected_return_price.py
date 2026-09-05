"""A constrained return can change the fare quoted on the outbound board."""

from copy import deepcopy
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from fli.cli.utils import serialize_flight_result
from fli.core.builders import build_flight_segments
from fli.mcp.server import _serialize_flight_result
from fli.models import Airport, FlightSearchFilters, PassengerInfo, SortBy
from fli.search.flights import SearchFlights
from tests.search.test_booking_url import _round_trip


@pytest.mark.parametrize("price", [500.0, 350.0, 0.0, None])
def test_serializers_use_final_quote_without_starting_fare_fallback(price):
    outbound, inbound = _round_trip(price=400.0)
    inbound.price = price
    inbound.currency = "EUR"
    for result in (
        serialize_flight_result((outbound, inbound)),
        _serialize_flight_result((outbound, inbound), True),
    ):
        assert result["price"] == price
        assert result["currency"] == "EUR"


def test_cheapest_sort_uses_selected_return_quote():
    first, first_return = _round_trip(price=200.0)
    second, second_return = deepcopy(first), deepcopy(first_return)
    second.price = 300.0
    first_return.price, second_return.price = 800.0, 500.0
    day = datetime.now() + timedelta(days=30)
    segments, trip_type = build_flight_segments(
        Airport.JFK,
        Airport.LAX,
        day.strftime("%Y-%m-%d"),
        (day + timedelta(days=4)).strftime("%Y-%m-%d"),
    )
    filters = FlightSearchFilters(
        trip_type=trip_type,
        flight_segments=segments,
        passenger_info=PassengerInfo(),
        sort_by=SortBy.CHEAPEST,
    )
    client = SearchFlights()

    def fetch(current, **kwargs):
        price = current.flight_segments[0].selected_flight.price
        return [first_return] if price == 200 else [second_return]

    client._fetch_flights = MagicMock(side_effect=fetch)
    results = client._expand_multi_leg(
        [first, second], filters, top_n=5, currency="USD", language=None, country=None
    )
    assert [trip[-1].price for trip in results] == [500.0, 800.0]
